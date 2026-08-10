// Worker de recepción de paquetes por QR + menú post-recepción.
// Rutas:
//   GET  /r?c=<codigo_rma>&s=<firma>   -> pantalla de verificación + confirmación,
//                                          o menú de opciones si ya está recepcionado
//   GET  /registro?next=...            -> formulario de PIN (alta de dispositivo)
//   POST /registro                     -> valida PIN, registra dispositivo, fija cookie
//   POST /confirmar                    -> revalida todo server-side y registra la recepción
//   GET/POST /comentario?c=&s=         -> añade un comentario al historial del expediente
//   GET  /datos?c=&s=                  -> muestra datos de solo lectura del expediente
//   GET  /fotos?c=&s=                  -> captura/edición de fotos (cámara o galería)
//   POST /subir-foto                   -> sube una foto editada a B2 y la adjunta al expediente

const DEVICE_COOKIE = "device_token";
const DEVICE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 5; // 5 años
const B2_ROOT_FOLDER = "Adjuntos_RMA"; // mismo prefijo que usa la app de escritorio
const B2_AUTH_URL = "https://api.backblazeb2.com/b2api/v3/b2_authorize_account";

// ---------- Turso (misma API HTTP v2/pipeline que usa la app de escritorio) ----------

function tursoApiUrl(databaseUrl) {
  let url = databaseUrl.replace("libsql://", "https://").replace("wss://", "https://");
  if (!url.endsWith("/")) url += "/";
  return url + "v2/pipeline";
}

async function tursoExec(env, sql, params = []) {
  const args = params.map((v) => (v === null || v === undefined ? { type: "null" } : { type: "text", value: String(v) }));
  const res = await fetch(tursoApiUrl(env.TURSO_DATABASE_URL), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.TURSO_AUTH_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ requests: [{ type: "execute", stmt: { sql, args } }] }),
  });

  if (!res.ok) {
    throw new Error(`Turso API error: ${res.status} - ${await res.text()}`);
  }

  const data = await res.json();
  const item = data.results && data.results[0];
  if (!item) return { rows: [], lastInsertRowid: null, rowsAffected: 0 };

  if (item.type === "error") {
    throw new Error(`Turso SQL error: ${item.error && item.error.message}`);
  }

  const result = item.response.result;
  const rows = (result.rows || []).map((row) =>
    row.map((cell) => {
      if (cell === null || cell.value === null || cell.value === undefined) return null;
      if (cell.type === "integer") return parseInt(cell.value, 10);
      if (cell.type === "real" || cell.type === "float") return parseFloat(cell.value);
      return cell.value;
    })
  );

  return {
    rows,
    lastInsertRowid: result.last_insert_rowid || null,
    rowsAffected: result.rows_affected || 0,
  };
}

// ---------- Firma HMAC de los QR (debe coincidir con lib/qr_recepcion.py) ----------

async function hmacHex(secret, message) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sigBuffer = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(message));
  return [...new Uint8Array(sigBuffer)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

async function verificarFirmaQr(env, codigoRma, firma) {
  if (!codigoRma || !firma) return false;
  const esperada = (await hmacHex(env.HMAC_SECRET, codigoRma)).slice(0, 32);
  return timingSafeEqual(esperada, firma);
}

async function sha1Hex(bytes) {
  const buf = await crypto.subtle.digest("SHA-1", bytes);
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// ---------- Utilidades varias ----------

function generarToken() {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function generarPinNumericoValido(pin) {
  return /^\d{6}$/.test(pin);
}

function normalizarNombre(s) {
  return (s || "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "") // quitar acentos
    .trim()
    .toUpperCase()
    .replace(/\s+/g, " ");
}

function distanciaLevenshtein(a, b) {
  const m = a.length, n = b.length;
  const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = 0; i <= m; i++) dp[i][0] = i;
  for (let j = 0; j <= n; j++) dp[0][j] = j;
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      const coste = a[i - 1] === b[j - 1] ? 0 : 1;
      dp[i][j] = Math.min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + coste);
    }
  }
  return dp[m][n];
}

// Busca la persona de la lista cuyo nombre normalizado esté más cerca del
// nombre introducido (distancia <= 2). Si hay ambigüedad (varias igual de
// cerca), se trata como "no coincide" para no arriesgar un falso positivo.
function encontrarPersonaCoincidente(nombreIntroducido, personas) {
  const objetivo = normalizarNombre(nombreIntroducido);
  if (!objetivo) return null;

  let mejor = null;
  let mejorDistancia = Infinity;
  let empatados = 0;

  for (const persona of personas) {
    const distancia = distanciaLevenshtein(objetivo, normalizarNombre(persona));
    if (distancia < mejorDistancia) {
      mejorDistancia = distancia;
      mejor = persona;
      empatados = 1;
    } else if (distancia === mejorDistancia) {
      empatados += 1;
    }
  }

  if (mejor !== null && mejorDistancia <= 2 && empatados === 1) return mejor;
  return null;
}

function obtenerCookie(request, nombre) {
  const cabecera = request.headers.get("Cookie") || "";
  const match = cabecera.match(new RegExp(`(?:^|;\\s*)${nombre}=([^;]+)`));
  return match ? decodeURIComponent(match[1]) : null;
}

function cookieHeader(nombre, valor, maxAge) {
  return `${nombre}=${encodeURIComponent(valor)}; Max-Age=${maxAge}; Path=/; HttpOnly; Secure; SameSite=Lax`;
}

async function registrarAuditoria(env, codigoRma, resultado, dispositivoId, detalle) {
  try {
    await tursoExec(
      env,
      "INSERT INTO auditoria_qr (fecha, codigo_rma, resultado, dispositivo_id, detalle) VALUES (?, ?, ?, ?, ?)",
      [new Date().toISOString(), codigoRma || null, resultado, dispositivoId || null, detalle || null]
    );
  } catch (e) {
    // La auditoría no debe romper el flujo principal si falla
    console.error("Error registrando auditoría:", e);
  }
}

async function obtenerConfig(env) {
  const { rows } = await tursoExec(
    env,
    "SELECT personas_recepcion, mensaje_incidencias, pin_max_intentos, pin_caducidad_minutos FROM config_recepcion_qr WHERE id = 1"
  );
  if (!rows.length) {
    return { personas_recepcion: [], mensaje_incidencias: "", pin_max_intentos: 5, pin_caducidad_minutos: 15 };
  }
  const [personasJson, mensaje, maxIntentos, caducidad] = rows[0];
  let personas = [];
  try {
    personas = JSON.parse(personasJson || "[]");
  } catch (e) {
    personas = [];
  }
  return {
    personas_recepcion: personas,
    mensaje_incidencias: mensaje || "",
    pin_max_intentos: maxIntentos || 5,
    pin_caducidad_minutos: caducidad || 15,
  };
}

// Resuelve el nombre de quien actúa: para un móvil "personal" es el nombre fijo
// del registro; para uno de "almacén" hay que verificar el nombre introducido
// contra la lista de personas autorizadas (misma lógica que /confirmar).
async function resolverNombrePersona(env, dispositivo, nombreIntroducido) {
  if (dispositivo.tipo === "personal") return dispositivo.nombre_persona;
  const config = await obtenerConfig(env);
  return encontrarPersonaCoincidente(nombreIntroducido, config.personas_recepcion);
}

// ---------- Validación común: firma + dispositivo + expediente ----------
// Usada por todas las rutas que cuelgan de un QR (/r, /confirmar, /comentario,
// /datos, /fotos, /subir-foto) para no duplicar la misma comprobación 6 veces.

async function validarContextoQr(env, request, codigoRma, firma, { requireRecepcionado }) {
  const url = new URL(request.url);

  if (!(await verificarFirmaQr(env, codigoRma, firma))) {
    await registrarAuditoria(env, codigoRma, "firma_invalida", null, null);
    return {
      ok: false,
      response: respuestaHtml(
        "QR no válido",
        `<h1>⚠️ QR no válido</h1><div class="card"><p>Este código QR no es válido o ha sido manipulado. No se puede continuar.</p></div>`,
        400
      ),
    };
  }

  const token = obtenerCookie(request, DEVICE_COOKIE);
  let dispositivo = null;
  if (token) {
    const { rows } = await tursoExec(
      env,
      "SELECT id, tipo, nombre_persona, revocado FROM dispositivos_qr WHERE token = ?",
      [token]
    );
    if (rows.length && rows[0][3] === 0) {
      dispositivo = { id: rows[0][0], tipo: rows[0][1], nombre_persona: rows[0][2] };
    }
  }

  if (!dispositivo) {
    const next = encodeURIComponent(`/r?c=${codigoRma}&s=${firma}`);
    const razonParam = token ? "&razon=revocado" : "";
    return { ok: false, response: Response.redirect(`${url.origin}/registro?next=${next}${razonParam}`, 302) };
  }

  const { rows } = await tursoExec(
    env,
    `SELECT id, cliente, motivo, fecha_emision, Persona_de_Contacto, fecha_recepcion,
            Numero_Documento_Cliente, Email_de_Contacto, recepcionado_por, Resultado_Expediente
     FROM rma_maestro WHERE codigo_rma = ?`,
    [codigoRma]
  );

  if (!rows.length) {
    await registrarAuditoria(env, codigoRma, "expediente_no_encontrado", dispositivo.id, null);
    return {
      ok: false,
      response: respuestaHtml(
        "Expediente no encontrado",
        `<h1>⚠️ Expediente no encontrado</h1><div class="card"><p>No existe ningún expediente con el código <strong>${escapeHtml(codigoRma)}</strong>.</p></div>`,
        404
      ),
    };
  }

  const [id, cliente, motivo, fechaEmision, personaContacto, fechaRecepcion, numeroDocCliente, emailContacto, recepcionadoPor, resultado] = rows[0];
  const rma = { id, codigoRma, cliente, motivo, fechaEmision, personaContacto, fechaRecepcion, numeroDocCliente, emailContacto, recepcionadoPor, resultado };

  if (requireRecepcionado && !fechaRecepcion) {
    return {
      ok: false,
      response: respuestaHtml(
        "Aún no recepcionado",
        `<h1>⚠️ Aún no recepcionado</h1><div class="card"><p>Esta opción solo está disponible después de confirmar la recepción del paquete.</p></div>`,
        400
      ),
    };
  }

  return { ok: true, dispositivo, rma };
}

// ---------- Plantilla HTML base ----------

function paginaHtml(titulo, cuerpoHtml) {
  return `<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${titulo}</title>
<style>
  body { font-family: -apple-system, system-ui, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px 16px; color: #1a1a1a; background: #fafafa; }
  h1 { font-size: 1.3rem; margin-bottom: 8px; }
  .card { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-top: 16px; }
  label { display: block; font-weight: 600; margin-top: 16px; margin-bottom: 6px; font-size: 0.9rem; }
  input[type=text], input[type=password], textarea { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 8px; font-size: 1rem; box-sizing: border-box; }
  textarea { min-height: 80px; resize: vertical; }
  button { width: 100%; padding: 12px; margin-top: 20px; background: #d35400; color: #fff; border: none; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; }
  button:active { opacity: 0.85; }
  .info-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #eee; font-size: 0.95rem; }
  .info-row span:first-child { color: #666; }
  .error { color: #c0392b; background: #fdecea; padding: 12px; border-radius: 8px; margin-top: 12px; }
  .ok { color: #196f3d; background: #eafaf1; padding: 12px; border-radius: 8px; margin-top: 12px; }
  .radio-group label { font-weight: 400; display: flex; align-items: center; gap: 8px; }
  .hidden { display: none !important; }
  .menu-btn { display: block; text-align: center; text-decoration: none; width: 100%; padding: 14px; margin-top: 14px; background: #d35400; color: #fff; border-radius: 8px; font-size: 1rem; font-weight: 600; box-sizing: border-box; border: none; cursor: pointer; }
  .menu-btn:active { opacity: 0.85; }
  .menu-btn.secondary { background: #fff; color: #d35400; border: 2px solid #d35400; }
  .volver { display: inline-block; margin-top: 18px; color: #666; font-size: 0.9rem; text-decoration: none; }
  .toolbar { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; align-items: center; }
  .toolbar button, .toolbar select, .toolbar input[type=color] { width: auto; margin-top: 0; padding: 8px 10px; border: 1px solid #ccc; border-radius: 6px; background: #fff; color: #1a1a1a; font-size: 0.85rem; cursor: pointer; }
  .tool-btn.active { background: #d35400; color: #fff; border-color: #d35400; }
  canvas { display: block; max-width: 100%; touch-action: none; background: #eee; }
  #panelSubiendo p { text-align: center; }
</style>
</head>
<body>
${cuerpoHtml}
</body>
</html>`;
}

function respuestaHtml(titulo, cuerpo, status = 200, headers = {}) {
  return new Response(paginaHtml(titulo, cuerpo), {
    status,
    headers: { "content-type": "text/html; charset=utf-8", ...headers },
  });
}

function respuestaJson(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

function escapeHtml(s) {
  return String(s || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Campo para identificar quién actúa: fijo (oculto) si el móvil es "personal",
// o un campo de texto a rellenar si es un móvil compartido de "almacén".
function campoNombreHtml(dispositivo, etiquetaPregunta, etiquetaInfo) {
  return dispositivo.tipo === "personal"
    ? `<div class="info-row"><span>${escapeHtml(etiquetaInfo)}</span><span>${escapeHtml(dispositivo.nombre_persona || "")}</span></div>
       <input type="hidden" id="nombre" name="nombre" value="${escapeHtml(dispositivo.nombre_persona || "")}">`
    : `<label for="nombre">${escapeHtml(etiquetaPregunta)}</label>
       <input type="text" id="nombre" name="nombre" required autocomplete="off">`;
}

// ---------- Subida a Backblaze B2 (API REST — el SDK Python no corre en el Worker) ----------

async function b2Autorizar(env) {
  const credenciales = btoa(`${env.B2_KEY_ID}:${env.B2_APP_KEY}`);
  const res = await fetch(B2_AUTH_URL, { headers: { Authorization: `Basic ${credenciales}` } });
  if (!res.ok) throw new Error(`b2_authorize_account: ${res.status} - ${await res.text()}`);
  const data = await res.json();
  const apiUrl = data.apiInfo && data.apiInfo.storageApi && data.apiInfo.storageApi.apiUrl;
  const bucketId =
    (data.apiInfo && data.apiInfo.storageApi && data.apiInfo.storageApi.bucketId) ||
    (data.allowed && data.allowed.bucketId);
  if (!apiUrl || !bucketId) {
    throw new Error("Respuesta inesperada de B2 al autorizar: falta apiUrl o bucketId (¿la clave está restringida a un bucket?).");
  }
  return { apiUrl, authToken: data.authorizationToken, bucketId };
}

async function b2ObtenerUrlSubida(apiUrl, authToken, bucketId) {
  const res = await fetch(`${apiUrl}/b2api/v3/b2_get_upload_url`, {
    method: "POST",
    headers: { Authorization: authToken, "Content-Type": "application/json" },
    body: JSON.stringify({ bucketId }),
  });
  if (!res.ok) throw new Error(`b2_get_upload_url: ${res.status} - ${await res.text()}`);
  const data = await res.json();
  return { uploadUrl: data.uploadUrl, uploadAuthToken: data.authorizationToken };
}

async function b2SubirArchivo(env, key, bytes, contentType) {
  const { apiUrl, authToken, bucketId } = await b2Autorizar(env);
  const { uploadUrl, uploadAuthToken } = await b2ObtenerUrlSubida(apiUrl, authToken, bucketId);
  const sha1 = await sha1Hex(bytes);
  const nombreCodificado = key.split("/").map(encodeURIComponent).join("/");

  const res = await fetch(uploadUrl, {
    method: "POST",
    headers: {
      Authorization: uploadAuthToken,
      "X-Bz-File-Name": nombreCodificado,
      "Content-Type": contentType,
      "Content-Length": String(bytes.length),
      "X-Bz-Content-Sha1": sha1,
    },
    body: bytes,
  });

  if (!res.ok) throw new Error(`b2_upload_file: ${res.status} - ${await res.text()}`);
  return await res.json();
}

// Nombre de archivo generado en el servidor (evita colisiones sin consultas extra):
// RMA25001_QR_20260810143205_a1b2.jpg
function generarNombreFotoQr(codigoRma) {
  const ts = new Date().toISOString().replace(/[-:TZ.]/g, "").slice(0, 14);
  const rand = crypto.getRandomValues(new Uint8Array(2));
  const sufijo = [...rand].map((b) => b.toString(16).padStart(2, "0")).join("");
  return `${codigoRma}_QR_${ts}_${sufijo}.jpg`;
}

// ---------- GET /r — pantalla de escaneo / menú post-recepción ----------

async function manejarEscaneo(request, env, url) {
  const codigoRma = url.searchParams.get("c");
  const firma = url.searchParams.get("s");

  const contexto = await validarContextoQr(env, request, codigoRma, firma, { requireRecepcionado: false });
  if (!contexto.ok) return contexto.response;
  const { dispositivo, rma } = contexto;

  if (rma.fechaRecepcion) {
    await registrarAuditoria(env, codigoRma, "menu_post_recepcion", dispositivo.id, null);
    return paginaMenuHtml(codigoRma, firma, rma);
  }

  return respuestaHtml(
    "Confirmar recepción",
    `<h1>📦 Confirmar recepción</h1>
     <div class="card">
       <div class="info-row"><span>Nº RMA</span><span>${escapeHtml(codigoRma)}</span></div>
       <div class="info-row"><span>Cliente</span><span>${escapeHtml(rma.cliente || "")}</span></div>
       <div class="info-row"><span>Motivo</span><span>${escapeHtml(rma.motivo || "")}</span></div>
       <div class="info-row"><span>Fecha emisión</span><span>${escapeHtml(rma.fechaEmision || "")}</span></div>
       <div class="info-row"><span>Contacto</span><span>${escapeHtml(rma.personaContacto || "")}</span></div>
       <p style="margin-top:16px; color:#666; font-size:0.9rem;">Verifica que el paquete recibido corresponde a este expediente antes de confirmar.</p>
     </div>
     <form method="POST" action="/confirmar" class="card">
       <input type="hidden" name="c" value="${escapeHtml(codigoRma)}">
       <input type="hidden" name="s" value="${escapeHtml(firma)}">
       ${campoNombreHtml(dispositivo, "¿Quién recepciona?", "Recepcionado por")}
       <label for="comentario">Comentario (opcional)</label>
       <textarea id="comentario" name="comentario" placeholder="Se añadirá al historial del expediente"></textarea>
       <button type="submit">Confirmar recepción</button>
     </form>`
  );
}

// ---------- GET /registro — formulario de PIN ----------

function manejarRegistroGet(url) {
  const next = url.searchParams.get("next") || "/";
  const razon = url.searchParams.get("razon");
  const avisoRazon =
    razon === "revocado"
      ? `<div class="error">Este dispositivo fue revocado por un administrador. Pide un PIN nuevo para volver a registrarlo.</div>`
      : "";

  return respuestaHtml(
    "Registrar dispositivo",
    `<h1>🔐 Registrar este móvil</h1>
     <div class="card">
       <p>Este móvil no está registrado. Pide un PIN a un administrador para registrarlo (solo hace falta una vez).</p>
       ${avisoRazon}
       <form method="POST" action="/registro">
         <input type="hidden" name="next" value="${escapeHtml(next)}">
         <label for="pin">PIN</label>
         <input type="text" id="pin" name="pin" inputmode="numeric" pattern="\\d{6}" maxlength="6" required autocomplete="off">

         <label>Tipo de móvil</label>
         <div class="radio-group">
           <label><input type="radio" name="tipo" value="almacen" checked onclick="document.getElementById('campo_nombre').style.display='none'"> Compartido de almacén (lo usan varios compañeros)</label>
           <label><input type="radio" name="tipo" value="personal" onclick="document.getElementById('campo_nombre').style.display='block'"> Personal (solo lo uso yo)</label>
         </div>

         <div id="campo_nombre" style="display:none;">
           <label for="nombre_persona">Tu nombre</label>
           <input type="text" id="nombre_persona" name="nombre_persona" autocomplete="off">
         </div>

         <button type="submit">Registrar</button>
       </form>
     </div>`
  );
}

// ---------- POST /registro — valida PIN y registra el dispositivo ----------

async function manejarRegistroPost(request, env, url) {
  const form = await request.formData();
  const pin = (form.get("pin") || "").toString().trim();
  const tipo = (form.get("tipo") || "almacen").toString();
  const nombrePersona = (form.get("nombre_persona") || "").toString().trim();
  const next = (form.get("next") || "/").toString();

  if (!generarPinNumericoValido(pin)) {
    return respuestaHtml("PIN inválido", registroErrorHtml(next, "El PIN debe tener 6 dígitos."), 400);
  }

  if (tipo === "personal" && !nombrePersona) {
    return respuestaHtml("Falta el nombre", registroErrorHtml(next, "Indica tu nombre para un móvil personal."), 400);
  }

  const { rows: pendientes } = await tursoExec(
    env,
    "SELECT id, fecha_caducidad FROM pins_qr WHERE pin = ? AND estado = 'pendiente'",
    [pin]
  );

  if (!pendientes.length) {
    // PIN incorrecto: penalizar los PIN actualmente pendientes (protección
    // básica contra fuerza bruta cuando hay un PIN activo esperando uso).
    await penalizarPinsPendientes(env);
    return respuestaHtml("PIN incorrecto", registroErrorHtml(next, "El PIN no es correcto o ya ha caducado."), 400);
  }

  const [pinId, fechaCaducidad] = pendientes[0];

  if (new Date(fechaCaducidad).getTime() < Date.now()) {
    await tursoExec(env, "UPDATE pins_qr SET estado = 'caducado' WHERE id = ?", [pinId]);
    return respuestaHtml("PIN caducado", registroErrorHtml(next, "Este PIN ha caducado. Pide uno nuevo."), 400);
  }

  const token = generarToken();
  const ahora = new Date().toISOString();

  const insertDispositivo = await tursoExec(
    env,
    "INSERT INTO dispositivos_qr (token, tipo, nombre_persona, fecha_registro, revocado) VALUES (?, ?, ?, ?, 0)",
    [token, tipo, tipo === "personal" ? nombrePersona.toUpperCase() : null, ahora]
  );

  await tursoExec(
    env,
    "UPDATE pins_qr SET estado = 'usado', dispositivo_id = ? WHERE id = ?",
    [insertDispositivo.lastInsertRowid, pinId]
  );

  const destino = next && next.startsWith("/") ? next : "/";

  return new Response(null, {
    status: 302,
    headers: {
      Location: destino,
      "Set-Cookie": cookieHeader(DEVICE_COOKIE, token, DEVICE_COOKIE_MAX_AGE),
    },
  });
}

async function penalizarPinsPendientes(env) {
  const config = await obtenerConfig(env);
  const { rows } = await tursoExec(env, "SELECT id, intentos_fallidos FROM pins_qr WHERE estado = 'pendiente'");
  for (const [id, intentos] of rows) {
    const nuevosIntentos = (intentos || 0) + 1;
    if (nuevosIntentos >= config.pin_max_intentos) {
      await tursoExec(env, "UPDATE pins_qr SET estado = 'bloqueado', intentos_fallidos = ? WHERE id = ?", [nuevosIntentos, id]);
    } else {
      await tursoExec(env, "UPDATE pins_qr SET intentos_fallidos = ? WHERE id = ?", [nuevosIntentos, id]);
    }
  }
}

function registroErrorHtml(next, mensaje) {
  return `<h1>🔐 Registrar este móvil</h1>
    <div class="card">
      <div class="error">${escapeHtml(mensaje)}</div>
      <p style="margin-top:16px;"><a href="/registro?next=${encodeURIComponent(next)}">Volver a intentarlo</a></p>
    </div>`;
}

// ---------- POST /confirmar — revalida todo y registra la recepción ----------

async function manejarConfirmar(request, env) {
  const form = await request.formData();
  const codigoRma = (form.get("c") || "").toString();
  const firma = (form.get("s") || "").toString();
  const nombre = (form.get("nombre") || "").toString().trim();
  const comentario = (form.get("comentario") || "").toString().trim();

  const contexto = await validarContextoQr(env, request, codigoRma, firma, { requireRecepcionado: false });
  if (!contexto.ok) return contexto.response;
  const { dispositivo, rma } = contexto;

  if (rma.fechaRecepcion) {
    await registrarAuditoria(env, codigoRma, "ya_registrado", dispositivo.id, null);
    return respuestaHtml(
      "Ya registrado",
      `<h1>ℹ️ Recepción ya registrada</h1><div class="card"><p>Este expediente ya se registró como recibido el <strong>${escapeHtml(rma.fechaRecepcion)}</strong>.</p></div>`
    );
  }

  const config = await obtenerConfig(env);
  const nombreFinal = await resolverNombrePersona(env, dispositivo, nombre);

  if (!nombreFinal) {
    await registrarAuditoria(env, codigoRma, "nombre_no_coincide", dispositivo.id, nombre);
    return respuestaHtml(
      "No coincide",
      `<h1>⚠️ No se pudo verificar</h1><div class="card"><div class="error">${escapeHtml(config.mensaje_incidencias)}</div></div>`
    );
  }

  const ahoraIso = new Date().toISOString();
  const fechaSolo = ahoraIso.slice(0, 10);

  await tursoExec(
    env,
    "UPDATE rma_maestro SET fecha_recepcion = ?, metodo_recepcion = 'QR', recepcionado_por = ? WHERE id = ?",
    [fechaSolo, nombreFinal, rma.id]
  );

  const descripcion = comentario
    ? `Recepción registrada por escaneo de QR. Comentario: ${comentario}`
    : "Recepción registrada por escaneo de QR.";

  await tursoExec(
    env,
    "INSERT INTO rma_historial (rma_id, fecha_cambio, usuario, descripcion_cambio) VALUES (?, ?, ?, ?)",
    [rma.id, ahoraIso, `QR - ${nombreFinal}`, descripcion]
  );

  await registrarAuditoria(env, codigoRma, "exito", dispositivo.id, comentario || null);

  return respuestaHtml(
    "Recepción confirmada",
    `<h1>✅ Recepción confirmada</h1><div class="card"><p>Se ha registrado la recepción del expediente <strong>${escapeHtml(codigoRma)}</strong>.</p></div>`
  );
}

// ---------- Menú post-recepción ----------

function paginaMenuHtml(codigoRma, firma, rma) {
  const qs = `c=${encodeURIComponent(codigoRma)}&s=${encodeURIComponent(firma)}`;
  return respuestaHtml(
    `Expediente ${codigoRma}`,
    `<h1>📋 Expediente ${escapeHtml(codigoRma)}</h1>
     <div class="card">
       <div class="info-row"><span>Cliente</span><span>${escapeHtml(rma.cliente || "")}</span></div>
       <div class="info-row"><span>Recepcionado</span><span>${escapeHtml(rma.fechaRecepcion || "")}</span></div>
     </div>
     <a class="menu-btn" href="/comentario?${qs}">💬 Añadir un comentario</a>
     <a class="menu-btn" href="/datos?${qs}">📄 Revisar datos del expediente</a>
     <a class="menu-btn" href="/fotos?${qs}">📷 Añadir fotos</a>`
  );
}

// ---------- GET/POST /comentario ----------

async function manejarComentarioGet(request, env, url) {
  const codigoRma = url.searchParams.get("c");
  const firma = url.searchParams.get("s");

  const contexto = await validarContextoQr(env, request, codigoRma, firma, { requireRecepcionado: true });
  if (!contexto.ok) return contexto.response;
  const { dispositivo } = contexto;

  const qs = `c=${encodeURIComponent(codigoRma)}&s=${encodeURIComponent(firma)}`;
  return respuestaHtml(
    "Añadir comentario",
    `<h1>💬 Añadir comentario</h1>
     <form method="POST" action="/comentario" class="card">
       <input type="hidden" name="c" value="${escapeHtml(codigoRma)}">
       <input type="hidden" name="s" value="${escapeHtml(firma)}">
       ${campoNombreHtml(dispositivo, "¿Quién añade el comentario?", "Comentario de")}
       <label for="texto">Comentario</label>
       <textarea id="texto" name="texto" required placeholder="Se añadirá al historial del expediente"></textarea>
       <button type="submit">Guardar comentario</button>
     </form>
     <a class="volver" href="/r?${qs}">← Volver al menú</a>`
  );
}

async function manejarComentarioPost(request, env) {
  const form = await request.formData();
  const codigoRma = (form.get("c") || "").toString();
  const firma = (form.get("s") || "").toString();
  const nombre = (form.get("nombre") || "").toString().trim();
  const texto = (form.get("texto") || "").toString().trim();

  const contexto = await validarContextoQr(env, request, codigoRma, firma, { requireRecepcionado: true });
  if (!contexto.ok) return contexto.response;
  const { dispositivo, rma } = contexto;

  if (!texto) {
    return respuestaHtml("Falta el comentario", `<h1>⚠️ Falta el comentario</h1><div class="card"><p>Escribe algo antes de guardar.</p></div>`, 400);
  }

  const config = await obtenerConfig(env);
  const nombreFinal = await resolverNombrePersona(env, dispositivo, nombre);
  if (!nombreFinal) {
    await registrarAuditoria(env, codigoRma, "nombre_no_coincide", dispositivo.id, nombre);
    return respuestaHtml(
      "No coincide",
      `<h1>⚠️ No se pudo verificar</h1><div class="card"><div class="error">${escapeHtml(config.mensaje_incidencias)}</div></div>`
    );
  }

  await tursoExec(
    env,
    "INSERT INTO rma_historial (rma_id, fecha_cambio, usuario, descripcion_cambio) VALUES (?, ?, ?, ?)",
    [rma.id, new Date().toISOString(), `QR - ${nombreFinal}`, `COMENTARIO MANUAL: ${texto}`]
  );
  await registrarAuditoria(env, codigoRma, "comentario_qr", dispositivo.id, null);

  const qs = `c=${encodeURIComponent(codigoRma)}&s=${encodeURIComponent(firma)}`;
  return respuestaHtml(
    "Comentario guardado",
    `<h1>✅ Comentario guardado</h1><div class="card"><p>Se ha añadido al historial del expediente <strong>${escapeHtml(codigoRma)}</strong>.</p></div>
     <a class="menu-btn" href="/r?${qs}">Volver al menú</a>`
  );
}

// ---------- GET /datos ----------

async function manejarDatosGet(request, env, url) {
  const codigoRma = url.searchParams.get("c");
  const firma = url.searchParams.get("s");

  const contexto = await validarContextoQr(env, request, codigoRma, firma, { requireRecepcionado: true });
  if (!contexto.ok) return contexto.response;
  const { rma } = contexto;

  const qs = `c=${encodeURIComponent(codigoRma)}&s=${encodeURIComponent(firma)}`;
  return respuestaHtml(
    "Datos del expediente",
    `<h1>📄 Datos del expediente</h1>
     <div class="card">
       <div class="info-row"><span>Nº RMA</span><span>${escapeHtml(codigoRma)}</span></div>
       <div class="info-row"><span>Cliente</span><span>${escapeHtml(rma.cliente || "")}</span></div>
       <div class="info-row"><span>Nº documento cliente</span><span>${escapeHtml(rma.numeroDocCliente || "")}</span></div>
       <div class="info-row"><span>Motivo</span><span>${escapeHtml(rma.motivo || "")}</span></div>
       <div class="info-row"><span>Persona de contacto</span><span>${escapeHtml(rma.personaContacto || "")}</span></div>
       <div class="info-row"><span>Email de contacto</span><span>${escapeHtml(rma.emailContacto || "")}</span></div>
       <div class="info-row"><span>Fecha emisión</span><span>${escapeHtml(rma.fechaEmision || "")}</span></div>
       <div class="info-row"><span>Fecha recepción</span><span>${escapeHtml(rma.fechaRecepcion || "")}</span></div>
       <div class="info-row"><span>Recepcionado por</span><span>${escapeHtml(rma.recepcionadoPor || "")}</span></div>
       <div class="info-row"><span>Resultado</span><span>${escapeHtml(rma.resultado || "—")}</span></div>
     </div>
     <a class="volver" href="/r?${qs}">← Volver al menú</a>`
  );
}

// ---------- GET /fotos — captura y edición ----------

async function manejarFotosGet(request, env, url) {
  const codigoRma = url.searchParams.get("c");
  const firma = url.searchParams.get("s");

  const contexto = await validarContextoQr(env, request, codigoRma, firma, { requireRecepcionado: true });
  if (!contexto.ok) return contexto.response;
  const { dispositivo } = contexto;

  const qs = `c=${encodeURIComponent(codigoRma)}&s=${encodeURIComponent(firma)}`;

  return respuestaHtml(
    "Añadir fotos",
    `<h1>📷 Añadir fotos</h1>
     <p id="contador" class="ok hidden"></p>

     <div class="card" id="panelInicio">
       ${campoNombreHtml(dispositivo, "¿Quién sube las fotos?", "Fotos de")}
       <p style="margin-top:16px;">Haz una foto o elige una de la galería. Podrás recortarla y marcarla antes de subirla.</p>
       <button type="button" class="menu-btn" id="btnCamara">📸 Hacer foto</button>
       <button type="button" class="menu-btn secondary" id="btnGaleria">🖼️ Elegir de galería</button>
       <input type="file" accept="image/*" capture="environment" id="inputCamara" class="hidden">
       <input type="file" accept="image/*" id="inputGaleria" class="hidden">
     </div>

     <div class="card hidden" id="panelEditor">
       <div class="toolbar" id="toolbar">
         <button type="button" data-tool="recortar" class="tool-btn">✂️ Recortar</button>
         <button type="button" data-tool="lapiz" class="tool-btn">✏️ Lápiz</button>
         <button type="button" data-tool="flecha" class="tool-btn">➡️ Flecha</button>
         <button type="button" data-tool="rectangulo" class="tool-btn">▭ Rectángulo</button>
         <button type="button" data-tool="texto" class="tool-btn">🔤 Texto</button>
       </div>
       <div class="toolbar">
         <input type="color" id="inputColor" value="#e53935">
         <select id="selectGrosor">
           <option value="2">Fino</option>
           <option value="4" selected>Normal</option>
           <option value="6">Grueso</option>
           <option value="8">Muy grueso</option>
         </select>
         <button type="button" id="btnDeshacer">↩️ Deshacer</button>
         <button type="button" id="btnRecortarAplicar" class="hidden">✅ Aplicar recorte</button>
       </div>
       <div style="overflow:auto; border:1px solid #ddd; border-radius:8px; margin-top:10px;">
         <canvas id="canvas"></canvas>
       </div>
       <button type="button" class="menu-btn" id="btnSubir">⬆️ Guardar y subir</button>
       <button type="button" class="menu-btn secondary" id="btnDescartar">🗑️ Descartar y elegir otra</button>
     </div>

     <div class="card hidden" id="panelSubiendo"><p>Subiendo foto…</p></div>

     <a class="volver" href="/r?${qs}">← Terminar y volver al menú</a>
     <input type="hidden" id="codigoRma" value="${escapeHtml(codigoRma)}">
     <input type="hidden" id="firma" value="${escapeHtml(firma)}">

     <script>
(function () {
  var canvas = document.getElementById('canvas');
  var ctx = canvas.getContext('2d');
  var st = { tool: null, color: '#e53935', grosor: 4, drawing: false, startX: 0, startY: 0, cropRect: null, undo: [], fotosSubidas: 0 };
  var snapshot = null;
  var botonesHerramienta = document.querySelectorAll('.tool-btn');

  function mostrar(id) { document.getElementById(id).classList.remove('hidden'); }
  function ocultar(id) { document.getElementById(id).classList.add('hidden'); }

  function pushUndo() {
    st.undo.push({ w: canvas.width, h: canvas.height, data: ctx.getImageData(0, 0, canvas.width, canvas.height) });
    if (st.undo.length > 8) st.undo.shift();
  }

  function deshacer() {
    if (!st.undo.length) return;
    var prev = st.undo.pop();
    canvas.width = prev.w;
    canvas.height = prev.h;
    ctx.putImageData(prev.data, 0, 0);
    st.cropRect = null;
    ocultar('btnRecortarAplicar');
  }

  function cargarImagen(file) {
    var url = URL.createObjectURL(file);
    var img = new Image();
    img.onload = function () {
      var maxLado = 1600;
      var w = img.naturalWidth, h = img.naturalHeight;
      var ratio = Math.min(1, maxLado / Math.max(w, h));
      canvas.width = Math.round(w * ratio);
      canvas.height = Math.round(h * ratio);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      st.undo = [];
      st.tool = null;
      botonesHerramienta.forEach(function (b) { b.classList.remove('active'); });
      ocultar('btnRecortarAplicar');
      ocultar('panelInicio');
      mostrar('panelEditor');
    };
    img.src = url;
  }

  document.getElementById('btnCamara').addEventListener('click', function () { document.getElementById('inputCamara').click(); });
  document.getElementById('btnGaleria').addEventListener('click', function () { document.getElementById('inputGaleria').click(); });
  document.getElementById('inputCamara').addEventListener('change', function (e) { if (e.target.files[0]) cargarImagen(e.target.files[0]); });
  document.getElementById('inputGaleria').addEventListener('change', function (e) { if (e.target.files[0]) cargarImagen(e.target.files[0]); });

  botonesHerramienta.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var nuevo = st.tool === btn.dataset.tool ? null : btn.dataset.tool;
      botonesHerramienta.forEach(function (b) { b.classList.remove('active'); });
      st.tool = nuevo;
      st.cropRect = null;
      if (nuevo) btn.classList.add('active');
      if (nuevo === 'recortar') mostrar('btnRecortarAplicar'); else ocultar('btnRecortarAplicar');
    });
  });

  document.getElementById('inputColor').addEventListener('change', function (e) { st.color = e.target.value; });
  document.getElementById('selectGrosor').addEventListener('change', function (e) { st.grosor = parseInt(e.target.value, 10); });
  document.getElementById('btnDeshacer').addEventListener('click', deshacer);

  function getPos(e) {
    var rect = canvas.getBoundingClientRect();
    var scaleX = canvas.width / rect.width;
    var scaleY = canvas.height / rect.height;
    return { x: (e.clientX - rect.left) * scaleX, y: (e.clientY - rect.top) * scaleY };
  }

  function normalizarRect(x1, y1, x2, y2) {
    return { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1) };
  }

  function dibujarRectSeleccion(x1, y1, x2, y2) {
    var r = normalizarRect(x1, y1, x2, y2);
    ctx.save();
    ctx.setLineDash([8, 6]);
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 3;
    ctx.strokeRect(r.x, r.y, r.w, r.h);
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 1;
    ctx.lineDashOffset = 8;
    ctx.strokeRect(r.x, r.y, r.w, r.h);
    ctx.restore();
  }

  function dibujarRectangulo(x1, y1, x2, y2) {
    var r = normalizarRect(x1, y1, x2, y2);
    ctx.setLineDash([]);
    ctx.strokeStyle = st.color;
    ctx.lineWidth = st.grosor;
    ctx.strokeRect(r.x, r.y, r.w, r.h);
  }

  function dibujarFlecha(x1, y1, x2, y2) {
    ctx.setLineDash([]);
    ctx.strokeStyle = st.color;
    ctx.fillStyle = st.color;
    ctx.lineWidth = st.grosor;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
    var angulo = Math.atan2(y2 - y1, x2 - x1);
    var tam = 10 + st.grosor * 2;
    ctx.beginPath();
    ctx.moveTo(x2, y2);
    ctx.lineTo(x2 - tam * Math.cos(angulo - Math.PI / 7), y2 - tam * Math.sin(angulo - Math.PI / 7));
    ctx.lineTo(x2 - tam * Math.cos(angulo + Math.PI / 7), y2 - tam * Math.sin(angulo + Math.PI / 7));
    ctx.closePath();
    ctx.fill();
  }

  function pedirTexto(p) {
    var rect = canvas.getBoundingClientRect();
    var scaleX = rect.width / canvas.width;
    var scaleY = rect.height / canvas.height;
    var input = document.createElement('input');
    input.type = 'text';
    input.style.position = 'absolute';
    input.style.left = (rect.left + window.scrollX + p.x * scaleX) + 'px';
    input.style.top = (rect.top + window.scrollY + p.y * scaleY) + 'px';
    input.style.fontSize = '16px';
    input.style.border = '1px dashed ' + st.color;
    input.style.background = 'rgba(255,255,255,0.9)';
    input.style.zIndex = '1000';
    document.body.appendChild(input);
    input.focus();

    function confirmar() {
      var texto = input.value;
      if (input.parentNode) document.body.removeChild(input);
      if (texto) {
        pushUndo();
        ctx.fillStyle = st.color;
        ctx.font = (16 + st.grosor * 3) + 'px sans-serif';
        ctx.fillText(texto, p.x, p.y + 16);
      }
    }
    input.addEventListener('blur', confirmar);
    input.addEventListener('keydown', function (e) { if (e.key === 'Enter') input.blur(); });
  }

  canvas.addEventListener('pointerdown', function (e) {
    if (!st.tool) return;
    e.preventDefault();
    var p = getPos(e);
    st.startX = p.x; st.startY = p.y;

    if (st.tool === 'texto') { pedirTexto(p); return; }

    st.drawing = true;
    snapshot = ctx.getImageData(0, 0, canvas.width, canvas.height);
    if (st.tool !== 'recortar') pushUndo(); // recortar guarda el deshacer al pulsar "Aplicar"

    if (st.tool === 'lapiz') {
      ctx.strokeStyle = st.color;
      ctx.lineWidth = st.grosor;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.moveTo(p.x, p.y);
    }
  });

  canvas.addEventListener('pointermove', function (e) {
    if (!st.drawing) return;
    e.preventDefault();
    var p = getPos(e);
    if (st.tool === 'lapiz') { ctx.lineTo(p.x, p.y); ctx.stroke(); return; }
    ctx.putImageData(snapshot, 0, 0);
    if (st.tool === 'recortar') dibujarRectSeleccion(st.startX, st.startY, p.x, p.y);
    else if (st.tool === 'rectangulo') dibujarRectangulo(st.startX, st.startY, p.x, p.y);
    else if (st.tool === 'flecha') dibujarFlecha(st.startX, st.startY, p.x, p.y);
  });

  canvas.addEventListener('pointerup', function (e) {
    if (!st.drawing) return;
    st.drawing = false;
    if (st.tool === 'recortar') {
      var p = getPos(e);
      st.cropRect = normalizarRect(st.startX, st.startY, p.x, p.y);
    }
  });

  document.getElementById('btnRecortarAplicar').addEventListener('click', function () {
    if (!st.cropRect || st.cropRect.w < 8 || st.cropRect.h < 8 || !snapshot) return;
    st.undo.push({ w: canvas.width, h: canvas.height, data: snapshot });
    if (st.undo.length > 8) st.undo.shift();

    var temp = document.createElement('canvas');
    temp.width = snapshot.width;
    temp.height = snapshot.height;
    temp.getContext('2d').putImageData(snapshot, 0, 0);

    var r = st.cropRect;
    canvas.width = Math.round(r.w);
    canvas.height = Math.round(r.h);
    ctx.drawImage(temp, r.x, r.y, r.w, r.h, 0, 0, r.w, r.h);

    st.cropRect = null;
    snapshot = null;
    st.tool = null;
    botonesHerramienta.forEach(function (b) { b.classList.remove('active'); });
    ocultar('btnRecortarAplicar');
  });

  document.getElementById('btnDescartar').addEventListener('click', function () {
    ocultar('panelEditor');
    mostrar('panelInicio');
    document.getElementById('inputCamara').value = '';
    document.getElementById('inputGaleria').value = '';
    st.undo = [];
  });

  function comprimirYSubir() {
    var nombre = document.getElementById('nombre').value;
    if (!nombre) { alert('Indica quién sube las fotos antes de continuar.'); return; }

    var w = canvas.width, h = canvas.height;
    var maxW = 1920, maxH = 1080;
    var calidad = 0.90;
    var origen = canvas;

    if (w > maxW || h > maxH) {
      var ratio = Math.min(maxW / w, maxH / h);
      var destino = document.createElement('canvas');
      destino.width = Math.round(w * ratio);
      destino.height = Math.round(h * ratio);
      destino.getContext('2d').drawImage(canvas, 0, 0, destino.width, destino.height);
      origen = destino;
      calidad = 0.85;
    }

    origen.toBlob(function (blob) { subirBlob(blob, nombre); }, 'image/jpeg', calidad);
  }

  function subirBlob(blob, nombre) {
    ocultar('panelEditor');
    mostrar('panelSubiendo');

    var fd = new FormData();
    fd.append('c', document.getElementById('codigoRma').value);
    fd.append('s', document.getElementById('firma').value);
    fd.append('nombre', nombre);
    fd.append('foto', blob, 'foto.jpg');

    fetch('/subir-foto', { method: 'POST', body: fd })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        ocultar('panelSubiendo');
        if (!data.ok) {
          alert('No se pudo subir la foto: ' + (data.error || 'error desconocido'));
          mostrar('panelInicio');
          return;
        }
        st.fotosSubidas++;
        var contador = document.getElementById('contador');
        contador.textContent = st.fotosSubidas + (st.fotosSubidas === 1 ? ' foto añadida' : ' fotos añadidas');
        mostrar('contador');
        mostrar('panelInicio');
        document.getElementById('inputCamara').value = '';
        document.getElementById('inputGaleria').value = '';
      })
      .catch(function () {
        ocultar('panelSubiendo');
        alert('Error de conexión al subir la foto. Inténtalo de nuevo.');
        mostrar('panelEditor');
      });
  }

  document.getElementById('btnSubir').addEventListener('click', comprimirYSubir);
})();
     </script>`
  );
}

// ---------- POST /subir-foto ----------

async function manejarSubirFotoPost(request, env) {
  const form = await request.formData();
  const codigoRma = (form.get("c") || "").toString();
  const firma = (form.get("s") || "").toString();
  const nombre = (form.get("nombre") || "").toString().trim();
  const archivo = form.get("foto");

  const contexto = await validarContextoQr(env, request, codigoRma, firma, { requireRecepcionado: true });
  if (!contexto.ok) {
    return respuestaJson({ ok: false, error: "Sesión no válida, vuelve a escanear el QR." }, 400);
  }
  const { dispositivo, rma } = contexto;

  if (!archivo || typeof archivo === "string") {
    return respuestaJson({ ok: false, error: "No se recibió ninguna foto." }, 400);
  }

  const MAX_BYTES = 15 * 1024 * 1024;
  if (archivo.size > MAX_BYTES) {
    return respuestaJson({ ok: false, error: "La foto es demasiado grande." }, 400);
  }

  const nombreFinal = await resolverNombrePersona(env, dispositivo, nombre);
  if (!nombreFinal) {
    await registrarAuditoria(env, codigoRma, "nombre_no_coincide", dispositivo.id, nombre);
    return respuestaJson({ ok: false, error: "No se pudo verificar el nombre indicado." }, 400);
  }

  const bytes = new Uint8Array(await archivo.arrayBuffer());
  const nombreArchivo = generarNombreFotoQr(codigoRma);

  try {
    await b2SubirArchivo(env, `${B2_ROOT_FOLDER}/${codigoRma}/${nombreArchivo}`, bytes, "image/jpeg");
  } catch (e) {
    console.error("Error subiendo a B2:", e);
    await registrarAuditoria(env, codigoRma, "error_subida_foto", dispositivo.id, String(e));
    return respuestaJson({ ok: false, error: "No se pudo subir la foto a almacenamiento. Inténtalo de nuevo." }, 500);
  }

  const ahoraIso = new Date().toISOString();

  await tursoExec(
    env,
    "INSERT INTO rma_adjuntos (rma_id, nombre_archivo, ruta_relativa, fecha_subida, usuario_subida, tipo_almacenamiento) VALUES (?, ?, ?, ?, ?, ?)",
    [rma.id, nombreArchivo, `${codigoRma}/${nombreArchivo}`, ahoraIso, `QR - ${nombreFinal}`, "backblaze"]
  );

  await tursoExec(
    env,
    "INSERT INTO rma_historial (rma_id, fecha_cambio, usuario, descripcion_cambio) VALUES (?, ?, ?, ?)",
    [rma.id, ahoraIso, `QR - ${nombreFinal}`, `Foto añadida por escaneo de QR: ${nombreArchivo}`]
  );

  await registrarAuditoria(env, codigoRma, "foto_subida", dispositivo.id, nombreArchivo);

  return respuestaJson({ ok: true, nombre_archivo: nombreArchivo });
}

// ---------- Router ----------

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    try {
      if (request.method === "GET" && url.pathname === "/r") {
        return await manejarEscaneo(request, env, url);
      }
      if (request.method === "GET" && url.pathname === "/registro") {
        return manejarRegistroGet(url);
      }
      if (request.method === "POST" && url.pathname === "/registro") {
        return await manejarRegistroPost(request, env, url);
      }
      if (request.method === "POST" && url.pathname === "/confirmar") {
        return await manejarConfirmar(request, env);
      }
      if (request.method === "GET" && url.pathname === "/comentario") {
        return await manejarComentarioGet(request, env, url);
      }
      if (request.method === "POST" && url.pathname === "/comentario") {
        return await manejarComentarioPost(request, env);
      }
      if (request.method === "GET" && url.pathname === "/datos") {
        return await manejarDatosGet(request, env, url);
      }
      if (request.method === "GET" && url.pathname === "/fotos") {
        return await manejarFotosGet(request, env, url);
      }
      if (request.method === "POST" && url.pathname === "/subir-foto") {
        return await manejarSubirFotoPost(request, env);
      }

      return new Response("Worker de recepción QR: funcionando.", {
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    } catch (e) {
      console.error("Error no controlado:", e);
      return respuestaHtml("Error", `<h1>⚠️ Error</h1><div class="card"><p>Ha ocurrido un error inesperado. Inténtalo de nuevo o contacta con administración.</p></div>`, 500);
    }
  },
};
