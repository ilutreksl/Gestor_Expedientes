"""Conector DB-API mínimo para Turso (libSQL) sobre su API HTTP (/v2/pipeline).

Cada `execute()` es una petición HTTP. Puntos importantes:

- Los parámetros se envían con su tipo real (NULL, entero, real, blob, texto),
  igual que hace sqlite3 en local. Antes todo se enviaba como texto y un `None`
  acababa guardado como la cadena "None".
- Turso confirma cada petición por separado: `commit()` y `rollback()` no hacen
  nada. Para que varias escrituras sean atómicas (todo o nada) hay que usar
  `ejecutar_transaccion()`, que las envía en un único lote con BEGIN/COMMIT y
  ROLLBACK si falla cualquier paso.
- Tiempo de espera separado para conectar (corto) y para recibir la respuesta,
  para no dejar la aplicación congelada 30 s cuando no hay red.
- Una sesión HTTP por hilo (requests.Session no es seguro entre hilos).
"""

import base64
import math
import sqlite3
import threading

import requests

# (segundos para establecer la conexión, segundos para recibir la respuesta).
# La lectura sigue siendo amplia porque obs_tecnica y las secciones del informe
# pueden llevar imágenes en base64 y tardar en subirse.
TIMEOUT_CONEXION = 5
TIMEOUT_LECTURA = 30

_hilo_local = threading.local()


def _sesion():
    """Sesión HTTP persistente, una por hilo."""
    sesion = getattr(_hilo_local, "sesion", None)
    if sesion is None:
        sesion = requests.Session()
        sesion.headers.update({"Content-Type": "application/json"})
        _hilo_local.sesion = sesion
    return sesion


# ---------------------------------------------------------------------------
# Conversión de valores
# ---------------------------------------------------------------------------

def _arg(valor):
    """Convierte un parámetro Python al formato tipado de Hrana."""
    if valor is None:
        return {"type": "null"}
    if isinstance(valor, bool):
        return {"type": "integer", "value": "1" if valor else "0"}
    if isinstance(valor, int):
        if -(2 ** 63) <= valor < 2 ** 63:
            return {"type": "integer", "value": str(valor)}
        return {"type": "text", "value": str(valor)}
    if isinstance(valor, float):
        if math.isfinite(valor):
            return {"type": "float", "value": valor}
        return {"type": "text", "value": str(valor)}
    if isinstance(valor, (bytes, bytearray, memoryview)):
        return {"type": "blob", "base64": base64.b64encode(bytes(valor)).decode("ascii")}
    return {"type": "text", "value": str(valor)}


def _args(params):
    return [_arg(v) for v in (params or ())]


def _sin_nulos(params):
    """Copia de los parámetros con None -> '' (reintento ante columnas NOT NULL)."""
    return tuple("" if v is None else v for v in (params or ()))


def _tiene_nulos(params):
    return any(v is None for v in (params or ()))


def _es_error_not_null(mensaje):
    return "NOT NULL constraint failed" in (mensaje or "")


def _valor_celda(celda):
    """Convierte una celda de la respuesta de Turso a su valor Python."""
    if not isinstance(celda, dict):
        return celda
    tipo = (celda.get("type") or "").lower()
    if tipo == "null":
        return None
    if tipo == "blob":
        datos = celda.get("base64") or ""
        datos += "=" * (-len(datos) % 4)  # Turso omite el relleno
        try:
            return base64.b64decode(datos)
        except Exception:
            return datos
    valor = celda.get("value")
    if valor is None:
        valor = celda.get("v")
    if valor is None:
        return None
    if tipo == "integer":
        try:
            return int(valor)
        except (ValueError, TypeError):
            return valor
    if tipo in ("float", "real"):
        try:
            return float(valor)
        except (ValueError, TypeError):
            return valor
    return valor


def _filas(resultado):
    """Extrae las filas de un resultado de Turso como lista de tuplas."""
    if not resultado:
        return []
    filas = resultado.get("rows") or resultado.get("values") or resultado.get("data") or []
    salida = []
    for fila in filas:
        if isinstance(fila, (list, tuple)):
            salida.append(tuple(_valor_celda(c) for c in fila))
        else:
            salida.append((fila,))
    return salida


def _lastrowid(resultado):
    valor = (resultado or {}).get("last_insert_rowid")
    if valor is None:
        return None
    try:
        return int(valor)
    except (ValueError, TypeError):
        return valor


def _rowcount(resultado):
    resultado = resultado or {}
    valor = resultado.get("affected_row_count")
    if valor is None:
        valor = resultado.get("rows_affected", -1)
    try:
        return int(valor)
    except (ValueError, TypeError):
        return -1


def _es_lectura(sql):
    inicio = (sql or "").lstrip().split(None, 1)
    return bool(inicio) and inicio[0].upper() in ("SELECT", "PRAGMA", "WITH", "EXPLAIN")


# Errores de esquema que se producen a propósito al comprobar columnas y no
# merece la pena imprimir.
def _es_error_esquema_esperado(sql, mensaje):
    return (
        ("tipo_almacenamiento" in sql and "SELECT" in sql)
        or ("numero_albaran" in mensaje and "no such column" in mensaje)
        or ("numero_order" in mensaje and "no such column" in mensaje)
        or ("duplicate column" in mensaje.lower())
    )


# ---------------------------------------------------------------------------
# Transporte
# ---------------------------------------------------------------------------

def _post(url, token, peticiones, reintentar):
    """Envía un pipeline a Turso y devuelve la lista `results`.

    `reintentar`: si True, se reintenta una vez ante un fallo de red. Solo debe
    activarse para lecturas (o cuando no se llegó a conectar), porque si la
    petición llegó al servidor un reintento podría duplicar una escritura.
    """
    cuerpo = {"requests": peticiones}
    intentos = 2
    for intento in range(intentos):
        try:
            respuesta = _sesion().post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=cuerpo,
                timeout=(TIMEOUT_CONEXION, TIMEOUT_LECTURA),
            )
            break
        except requests.exceptions.ConnectTimeout as e:
            # No se llegó a conectar: la petición no salió, reintentar es seguro.
            if intento + 1 < intentos:
                continue
            raise sqlite3.OperationalError(f"Error de conexión con Turso (sin respuesta del servidor): {e}")
        except requests.exceptions.RequestException as e:
            if reintentar and intento + 1 < intentos:
                # Sesión posiblemente rota (conexión cerrada por el servidor): empezar de cero.
                _hilo_local.sesion = None
                continue
            print(f"Error de conexión con Turso: {e}")
            raise sqlite3.OperationalError(f"Error de conexión con Turso: {e}")

    if respuesta.status_code != 200:
        print(f"Error - Response status: {respuesta.status_code}, text: {respuesta.text[:500]}")
        raise sqlite3.OperationalError(f"Turso API error: {respuesta.status_code} - {respuesta.text[:500]}")
    return respuesta.json().get("results", [])


def _error_sql(mensaje):
    mensaje = mensaje or "Unknown error"
    if not mensaje.startswith("SQLite error"):
        mensaje = f"SQLite error: {mensaje}"
    return sqlite3.OperationalError(mensaje)


def _peticion_execute(sql, params):
    return {"type": "execute", "stmt": {"sql": sql, "args": _args(params)}}


# ---------------------------------------------------------------------------
# DB-API
# ---------------------------------------------------------------------------

class TursoCursor:
    def __init__(self, connection):
        self._connection = connection
        self._filas = []
        self._idx = 0
        self.lastrowid = None
        self.rowcount = -1
        self.description = None

    def _cargar_resultado(self, resultado):
        self._filas = _filas(resultado)
        self._idx = 0
        self.lastrowid = _lastrowid(resultado)
        self.rowcount = _rowcount(resultado)
        cols = (resultado or {}).get("cols") or []
        self.description = [(c.get("name"), None, None, None, None, None, None) for c in cols] or None

    def execute(self, sql, params=None):
        conn = self._connection
        resultados = _post(conn._url, conn._token, [_peticion_execute(sql, params)], reintentar=_es_lectura(sql))
        item = resultados[0] if resultados else None
        if item and item.get("type") == "error":
            mensaje = item.get("error", {}).get("message", "Unknown error")
            # Antes un None se guardaba como "None": en columnas NOT NULL no fallaba.
            # Ahora se envía NULL de verdad; si la columna no lo admite, se guarda
            # cadena vacía (mejor que el texto "None") en vez de perder el guardado.
            if _es_error_not_null(mensaje) and _tiene_nulos(params):
                return self.execute(sql, _sin_nulos(params))
            if not _es_error_esquema_esperado(sql, mensaje):
                print(f"SQL Error: {mensaje}")
                print(f"Query: {sql}")
            raise _error_sql(mensaje)
        resultado = (item or {}).get("response", {}).get("result", {}) if item else {"rows": []}
        self._cargar_resultado(resultado)
        return self

    def executemany(self, sql, lista_params):
        """Ejecuta la misma sentencia con varios juegos de parámetros, de forma atómica."""
        lista_params = list(lista_params or [])
        if not lista_params:
            return self
        resultados = self._connection.ejecutar_transaccion([(sql, p) for p in lista_params])
        if resultados:
            ultimo = resultados[-1]
            self._filas = []
            self._idx = 0
            self.lastrowid = ultimo.lastrowid
            self.rowcount = sum(max(r.rowcount, 0) for r in resultados)
        return self

    def fetchall(self):
        restantes = self._filas[self._idx:]
        self._idx = len(self._filas)
        return restantes

    def fetchone(self):
        if self._idx < len(self._filas):
            fila = self._filas[self._idx]
            self._idx += 1
            return fila
        return None

    def fetchmany(self, size=1):
        trozo = self._filas[self._idx:self._idx + size]
        self._idx += len(trozo)
        return trozo

    def close(self):
        pass

    def __iter__(self):
        while True:
            fila = self.fetchone()
            if fila is None:
                return
            yield fila


class ResultadoSentencia:
    """Resultado de una sentencia dentro de una transacción o consulta múltiple."""

    def __init__(self, resultado):
        self.filas = _filas(resultado)
        self.lastrowid = _lastrowid(resultado)
        self.rowcount = _rowcount(resultado)
        cols = (resultado or {}).get("cols") or []
        self.columnas = [c.get("name") for c in cols]


class TursoConnection:
    def __init__(self, url, token):
        self._url = url
        self._token = token

    def cursor(self):
        return TursoCursor(self)

    def execute(self, sql, params=None):
        return self.cursor().execute(sql, params)

    def commit(self):
        # Turso confirma cada petición por separado. Para atomicidad usar
        # ejecutar_transaccion().
        pass

    def rollback(self):
        # Sin efecto (ver commit). Se define para que el código que lo llama no falle.
        pass

    def close(self):
        # La sesión HTTP se reutiliza entre conexiones.
        pass

    def ejecutar_transaccion(self, sentencias):
        """Ejecuta una lista de (sql, params) en una única petición y de forma atómica.

        Si cualquier sentencia falla, se deshace todo y se lanza
        sqlite3.OperationalError. Devuelve una lista de ResultadoSentencia.
        """
        sentencias = [(s, tuple(p or ())) for s, p in sentencias]
        if not sentencias:
            return []
        try:
            return self._ejecutar_lote(sentencias)
        except _ErrorNotNull:
            if any(_tiene_nulos(p) for _, p in sentencias):
                return self._ejecutar_lote([(s, _sin_nulos(p)) for s, p in sentencias])
            raise sqlite3.OperationalError("SQLite error: NOT NULL constraint failed")

    def _ejecutar_lote(self, sentencias):
        pasos = [{"stmt": {"sql": "BEGIN", "args": []}}]
        for i, (sql, params) in enumerate(sentencias):
            pasos.append({
                "stmt": {"sql": sql, "args": _args(params)},
                "condition": {"type": "ok", "step": i},
            })
        n = len(pasos)
        pasos.append({"stmt": {"sql": "COMMIT", "args": []}, "condition": {"type": "ok", "step": n - 1}})
        pasos.append({
            "stmt": {"sql": "ROLLBACK", "args": []},
            "condition": {"type": "not", "cond": {"type": "ok", "step": n}},
        })

        resultados = _post(self._url, self._token, [{"type": "batch", "batch": {"steps": pasos}}], reintentar=False)
        item = resultados[0] if resultados else None
        if not item:
            raise sqlite3.OperationalError("Turso no devolvió respuesta para la transacción")
        if item.get("type") == "error":
            mensaje = item.get("error", {}).get("message", "Unknown error")
            raise _error_sql(mensaje)

        lote = item.get("response", {}).get("result", {})
        step_results = lote.get("step_results") or []
        step_errors = lote.get("step_errors") or []

        # Un error en cualquier paso (o un COMMIT que no llegó a ejecutarse) implica
        # que la transacción se ha deshecho.
        for i, error in enumerate(step_errors):
            if error and i < n + 1:
                mensaje = error.get("message", "Unknown error")
                if _es_error_not_null(mensaje):
                    raise _ErrorNotNull(mensaje)
                sql_fallida = sentencias[i - 1][0] if 1 <= i <= len(sentencias) else ("BEGIN" if i == 0 else "COMMIT")
                print(f"SQL Error (transacción): {mensaje}")
                print(f"Query: {sql_fallida}")
                raise _error_sql(mensaje)
        if len(step_results) <= n or step_results[n] is None:
            raise sqlite3.OperationalError("La transacción no se confirmó en Turso; no se ha guardado ningún cambio")

        return [ResultadoSentencia(step_results[i + 1]) for i in range(len(sentencias))]

    def consultar_varias(self, consultas):
        """Ejecuta varias lecturas (sql, params) en una sola petición.

        Devuelve una lista con un ResultadoSentencia por consulta, o la excepción
        sqlite3.OperationalError correspondiente si esa consulta falló (no se lanza,
        para que el llamador decida).
        """
        consultas = [(s, tuple(p or ())) for s, p in consultas]
        if not consultas:
            return []
        peticiones = [_peticion_execute(s, p) for s, p in consultas]
        resultados = _post(self._url, self._token, peticiones, reintentar=True)
        salida = []
        for i in range(len(consultas)):
            item = resultados[i] if i < len(resultados) else None
            if not item or item.get("type") == "error":
                mensaje = (item or {}).get("error", {}).get("message", "Sin respuesta")
                salida.append(_error_sql(mensaje))
            else:
                salida.append(ResultadoSentencia(item.get("response", {}).get("result", {})))
        return salida


class _ErrorNotNull(Exception):
    pass


def url_pipeline(turso_url):
    """Convierte libsql://xxx o wss://xxx en la URL https del pipeline HTTP."""
    url = turso_url.replace("libsql://", "https://").replace("wss://", "https://")
    if not url.endswith("/"):
        url += "/"
    return url + "v2/pipeline"


# ---------------------------------------------------------------------------
# Utilidades que funcionan igual con Turso y con sqlite3 local
# ---------------------------------------------------------------------------

def ejecutar_transaccion(conn, sentencias):
    """Ejecuta una lista de (sql, params) de forma atómica en Turso o en SQLite local.

    Devuelve una lista de ResultadoSentencia (lastrowid, rowcount, filas).
    Lanza sqlite3.Error si algo falla; en ese caso no se ha guardado nada.
    """
    if hasattr(conn, "ejecutar_transaccion"):
        return conn.ejecutar_transaccion(sentencias)
    cur = conn.cursor()
    resultados = []
    try:
        if not getattr(conn, "in_transaction", False):
            cur.execute("BEGIN")
        for sql, params in sentencias:
            cur.execute(sql, tuple(params or ()))
            r = ResultadoSentencia({})
            r.lastrowid = cur.lastrowid
            r.rowcount = cur.rowcount
            try:
                r.filas = cur.fetchall()
            except sqlite3.Error:
                r.filas = []
            resultados.append(r)
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    return resultados


def consultar_varias(conn, consultas):
    """Varias lecturas en una sola petición en Turso; secuenciales en SQLite local.

    Cada elemento devuelto es un ResultadoSentencia o una excepción sqlite3.Error.
    """
    if hasattr(conn, "consultar_varias"):
        return conn.consultar_varias(consultas)
    salida = []
    cur = conn.cursor()
    for sql, params in consultas:
        try:
            cur.execute(sql, tuple(params or ()))
            r = ResultadoSentencia({})
            r.filas = cur.fetchall()
            r.columnas = [d[0] for d in (cur.description or [])]
            salida.append(r)
        except sqlite3.Error as e:
            salida.append(e)
    return salida


class TransaccionDB:
    """Acumula escrituras para enviarlas juntas con `confirmar()` de forma atómica.

    Imita lo justo de un cursor (`execute`/`executemany`) para poder pasarse a
    funciones que reciben un cursor y solo escriben (p.ej. guardar_cambio_historial).
    """

    def __init__(self, conn):
        self.conn = conn
        self.sentencias = []

    def execute(self, sql, params=None):
        self.sentencias.append((sql, tuple(params or ())))
        return self

    def executemany(self, sql, lista_params):
        for params in lista_params:
            self.execute(sql, params)
        return self

    def __len__(self):
        return len(self.sentencias)

    def confirmar(self):
        resultados = ejecutar_transaccion(self.conn, self.sentencias)
        self.sentencias = []
        return resultados
