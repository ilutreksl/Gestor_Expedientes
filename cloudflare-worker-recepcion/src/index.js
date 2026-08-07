// Worker de recepción de paquetes por QR.
// Rutas:
//   GET  /r?c=<codigo_rma>&s=<firma>   -> pantalla de verificación + confirmación
//   GET  /registro?next=...            -> formulario de PIN (alta de dispositivo)
//   POST /registro                     -> valida PIN, registra dispositivo, fija cookie
//   POST /confirmar                    -> revalida todo server-side y registra la recepción

const DEVICE_COOKIE = "device_token";
const DEVICE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 5; // 5 años

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

// ---------- GET /r — pantalla de escaneo ----------

async function manejarEscaneo(request, env, url) {
  const codigoRma = url.searchParams.get("c");
  const firma = url.searchParams.get("s");

  if (!(await verificarFirmaQr(env, codigoRma, firma))) {
    await registrarAuditoria(env, codigoRma, "firma_invalida", null, null);
    return respuestaHtml(
      "QR no válido",
      `<h1>⚠️ QR no válido</h1><div class="card"><p>Este código QR no es válido o ha sido manipulado. No se puede registrar la recepción.</p></div>`,
      400
    );
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
    const next = encodeURIComponent(url.pathname + url.search);
    return Response.redirect(`${url.origin}/registro?next=${next}`, 302);
  }

  const { rows } = await tursoExec(
    env,
    "SELECT cliente, motivo, fecha_emision, Persona_de_Contacto, fecha_recepcion FROM rma_maestro WHERE codigo_rma = ?",
    [codigoRma]
  );

  if (!rows.length) {
    await registrarAuditoria(env, codigoRma, "expediente_no_encontrado", dispositivo.id, null);
    return respuestaHtml(
      "Expediente no encontrado",
      `<h1>⚠️ Expediente no encontrado</h1><div class="card"><p>No existe ningún expediente con el código <strong>${escapeHtml(codigoRma)}</strong>.</p></div>`,
      404
    );
  }

  const [cliente, motivo, fechaEmision, personaContacto, fechaRecepcion] = rows[0];

  if (fechaRecepcion) {
    await registrarAuditoria(env, codigoRma, "ya_registrado", dispositivo.id, null);
    return respuestaHtml(
      "Ya registrado",
      `<h1>ℹ️ Recepción ya registrada</h1><div class="card"><p>El expediente <strong>${escapeHtml(codigoRma)}</strong> ya tiene una recepción registrada el <strong>${escapeHtml(fechaRecepcion)}</strong>. No se puede volver a registrar.</p></div>`,
      200
    );
  }

  const campoNombre =
    dispositivo.tipo === "personal"
      ? `<div class="info-row"><span>Recepcionado por</span><span>${escapeHtml(dispositivo.nombre_persona || "")}</span></div>
         <input type="hidden" name="nombre" value="${escapeHtml(dispositivo.nombre_persona || "")}">`
      : `<label for="nombre">¿Quién recepciona?</label>
         <input type="text" id="nombre" name="nombre" required autocomplete="off">`;

  return respuestaHtml(
    "Confirmar recepción",
    `<h1>📦 Confirmar recepción</h1>
     <div class="card">
       <div class="info-row"><span>Nº RMA</span><span>${escapeHtml(codigoRma)}</span></div>
       <div class="info-row"><span>Cliente</span><span>${escapeHtml(cliente || "")}</span></div>
       <div class="info-row"><span>Motivo</span><span>${escapeHtml(motivo || "")}</span></div>
       <div class="info-row"><span>Fecha emisión</span><span>${escapeHtml(fechaEmision || "")}</span></div>
       <div class="info-row"><span>Contacto</span><span>${escapeHtml(personaContacto || "")}</span></div>
       <p style="margin-top:16px; color:#666; font-size:0.9rem;">Verifica que el paquete recibido corresponde a este expediente antes de confirmar.</p>
     </div>
     <form method="POST" action="/confirmar" class="card">
       <input type="hidden" name="c" value="${escapeHtml(codigoRma)}">
       <input type="hidden" name="s" value="${escapeHtml(firma)}">
       ${campoNombre}
       <label for="comentario">Comentario (opcional)</label>
       <textarea id="comentario" name="comentario" placeholder="Se añadirá al historial del expediente"></textarea>
       <button type="submit">Confirmar recepción</button>
     </form>`
  );
}

function escapeHtml(s) {
  return String(s || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
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

// ---------- POST /confirmar — revalida todo y registra la recepción ----------

async function manejarConfirmar(request, env) {
  const form = await request.formData();
  const codigoRma = (form.get("c") || "").toString();
  const firma = (form.get("s") || "").toString();
  const nombre = (form.get("nombre") || "").toString().trim();
  const comentario = (form.get("comentario") || "").toString().trim();

  if (!(await verificarFirmaQr(env, codigoRma, firma))) {
    return respuestaHtml("QR no válido", `<h1>⚠️ QR no válido</h1><div class="card"><p>Firma inválida.</p></div>`, 400);
  }

  const token = obtenerCookie(request, DEVICE_COOKIE);
  const { rows: dispRows } = token
    ? await tursoExec(env, "SELECT id, tipo, nombre_persona, revocado FROM dispositivos_qr WHERE token = ?", [token])
    : { rows: [] };

  if (!dispRows.length || dispRows[0][3] !== 0) {
    const url = new URL(request.url);
    const next = encodeURIComponent(`/r?c=${codigoRma}&s=${firma}`);
    return Response.redirect(`${url.origin}/registro?next=${next}&razon=revocado`, 302);
  }

  const [dispositivoId, tipoDispositivo, nombrePersonaFijo] = dispRows[0];

  const { rows: rmaRows } = await tursoExec(
    env,
    "SELECT id, fecha_recepcion FROM rma_maestro WHERE codigo_rma = ?",
    [codigoRma]
  );

  if (!rmaRows.length) {
    return respuestaHtml("Expediente no encontrado", `<h1>⚠️ Expediente no encontrado</h1>`, 404);
  }

  const [rmaId, fechaRecepcionActual] = rmaRows[0];

  if (fechaRecepcionActual) {
    await registrarAuditoria(env, codigoRma, "ya_registrado", dispositivoId, null);
    return respuestaHtml(
      "Ya registrado",
      `<h1>ℹ️ Recepción ya registrada</h1><div class="card"><p>Este expediente ya se registró como recibido el <strong>${escapeHtml(fechaRecepcionActual)}</strong>.</p></div>`
    );
  }

  const config = await obtenerConfig(env);
  let nombreFinal;

  if (tipoDispositivo === "personal") {
    nombreFinal = nombrePersonaFijo;
  } else {
    nombreFinal = encontrarPersonaCoincidente(nombre, config.personas_recepcion);
    if (!nombreFinal) {
      await registrarAuditoria(env, codigoRma, "nombre_no_coincide", dispositivoId, nombre);
      return respuestaHtml(
        "No coincide",
        `<h1>⚠️ No se pudo verificar</h1><div class="card"><div class="error">${escapeHtml(config.mensaje_incidencias)}</div></div>`
      );
    }
  }

  const ahoraIso = new Date().toISOString();
  const fechaSolo = ahoraIso.slice(0, 10);

  await tursoExec(
    env,
    "UPDATE rma_maestro SET fecha_recepcion = ?, metodo_recepcion = 'QR', recepcionado_por = ? WHERE id = ?",
    [fechaSolo, nombreFinal, rmaId]
  );

  const descripcion = comentario
    ? `Recepción registrada por escaneo de QR. Comentario: ${comentario}`
    : "Recepción registrada por escaneo de QR.";

  await tursoExec(
    env,
    "INSERT INTO rma_historial (rma_id, fecha_cambio, usuario, descripcion_cambio) VALUES (?, ?, ?, ?)",
    [rmaId, ahoraIso, `QR - ${nombreFinal}`, descripcion]
  );

  await registrarAuditoria(env, codigoRma, "exito", dispositivoId, comentario || null);

  return respuestaHtml(
    "Recepción confirmada",
    `<h1>✅ Recepción confirmada</h1><div class="card"><p>Se ha registrado la recepción del expediente <strong>${escapeHtml(codigoRma)}</strong>.</p></div>`
  );
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

      return new Response("Worker de recepción QR: funcionando.", {
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    } catch (e) {
      console.error("Error no controlado:", e);
      return respuestaHtml("Error", `<h1>⚠️ Error</h1><div class="card"><p>Ha ocurrido un error inesperado. Inténtalo de nuevo o contacta con administración.</p></div>`, 500);
    }
  },
};
