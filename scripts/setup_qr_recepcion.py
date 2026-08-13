"""
Script de configuración inicial para la recepción de paquetes por QR.
Crea en Turso las tablas necesarias (dispositivos_qr, pins_qr,
config_recepcion_qr, auditoria_qr), añade la columna metodo_recepcion
a rma_maestro, la columna puede_editar a dispositivos_qr, y la columna
estados_articulo a config_recepcion_qr. Es idempotente: se puede
ejecutar varias veces sin duplicar nada.

Si existen Diccionarios/personas_recepcion.json y
Diccionarios/estados_articulo.json, su contenido se usa para sembrar
la fila inicial de config_recepcion_qr (no se pierde lo ya configurado
localmente).

USO:
    python scripts/setup_qr_recepcion.py
"""

import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

try:
    from app import connect_db
except ImportError:
    print("Error: No se pudo importar connect_db desde app.py")
    sys.exit(1)


TABLAS = {
    "dispositivos_qr": """
        CREATE TABLE IF NOT EXISTS dispositivos_qr (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            tipo TEXT NOT NULL CHECK (tipo IN ('almacen', 'personal')),
            nombre_persona TEXT,
            fecha_registro TEXT NOT NULL,
            revocado INTEGER NOT NULL DEFAULT 0,
            fecha_revocado TEXT
        )
    """,
    "pins_qr": """
        CREATE TABLE IF NOT EXISTS pins_qr (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pin TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'usado', 'caducado', 'bloqueado')),
            creado_por TEXT NOT NULL,
            fecha_creacion TEXT NOT NULL,
            fecha_caducidad TEXT NOT NULL,
            intentos_fallidos INTEGER NOT NULL DEFAULT 0,
            dispositivo_id INTEGER REFERENCES dispositivos_qr(id)
        )
    """,
    "config_recepcion_qr": """
        CREATE TABLE IF NOT EXISTS config_recepcion_qr (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            personas_recepcion TEXT NOT NULL DEFAULT '[]',
            mensaje_incidencias TEXT NOT NULL DEFAULT '',
            pin_max_intentos INTEGER NOT NULL DEFAULT 5,
            pin_caducidad_minutos INTEGER NOT NULL DEFAULT 15
        )
    """,
    "auditoria_qr": """
        CREATE TABLE IF NOT EXISTS auditoria_qr (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            codigo_rma TEXT,
            resultado TEXT NOT NULL,
            dispositivo_id INTEGER,
            detalle TEXT
        )
    """,
    "config_trazabilidad": """
        CREATE TABLE IF NOT EXISTS config_trazabilidad (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            texto_ayuda TEXT NOT NULL DEFAULT ''
        )
    """,
}

_TEXTO_AYUDA_TRAZABILIDAD_DEFECTO = (
    "Adjunta el correo, foto o documento relacionado con esta incidencia y "
    "añade un comentario si lo necesitas. El sistema lo clasificará "
    "automáticamente: los correos (.eml/.msg) se asocian en la pestaña "
    "Asociados y el resto de archivos en Adjuntos."
)


def crear_tablas(cursor, conn):
    for nombre, sql in TABLAS.items():
        cursor.execute(sql)
        conn.commit()
        print(f"OK tabla '{nombre}' (creada o ya existente)")


def anadir_columna_metodo_recepcion(cursor, conn):
    try:
        cursor.execute("PRAGMA table_info('rma_maestro')")
        columnas = [row[1] for row in cursor.fetchall()]
    except Exception:
        columnas = []

    if 'metodo_recepcion' in columnas:
        print("OK columna 'metodo_recepcion' ya existe en rma_maestro")
        return

    try:
        cursor.execute("ALTER TABLE rma_maestro ADD COLUMN metodo_recepcion TEXT")
        conn.commit()
        print("OK columna 'metodo_recepcion' añadida a rma_maestro")
    except Exception as e:
        err = str(e).lower()
        if "duplicate" in err or "already exists" in err:
            print("OK columna 'metodo_recepcion' ya existe en rma_maestro (detectado por error)")
        else:
            raise


def anadir_columna_puede_editar(cursor, conn):
    try:
        cursor.execute("PRAGMA table_info('dispositivos_qr')")
        columnas = [row[1] for row in cursor.fetchall()]
    except Exception:
        columnas = []

    if 'puede_editar' in columnas:
        print("OK columna 'puede_editar' ya existe en dispositivos_qr")
        return

    try:
        cursor.execute("ALTER TABLE dispositivos_qr ADD COLUMN puede_editar INTEGER NOT NULL DEFAULT 0")
        conn.commit()
        print("OK columna 'puede_editar' añadida a dispositivos_qr")
    except Exception as e:
        err = str(e).lower()
        if "duplicate" in err or "already exists" in err:
            print("OK columna 'puede_editar' ya existe en dispositivos_qr (detectado por error)")
        else:
            raise


def anadir_columna_estados_articulo(cursor, conn):
    try:
        cursor.execute("PRAGMA table_info('config_recepcion_qr')")
        columnas = [row[1] for row in cursor.fetchall()]
    except Exception:
        columnas = []

    if 'estados_articulo' in columnas:
        print("OK columna 'estados_articulo' ya existe en config_recepcion_qr")
        return

    try:
        cursor.execute("ALTER TABLE config_recepcion_qr ADD COLUMN estados_articulo TEXT NOT NULL DEFAULT '[]'")
        conn.commit()
        print("OK columna 'estados_articulo' añadida a config_recepcion_qr")
    except Exception as e:
        err = str(e).lower()
        if "duplicate" in err or "already exists" in err:
            print("OK columna 'estados_articulo' ya existe en config_recepcion_qr (detectado por error)")
        else:
            raise


def cargar_estados_articulo_json():
    ruta = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "Diccionarios", "estados_articulo.json"
    )
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("estados", [])
    except Exception:
        return []


def sembrar_estados_articulo(cursor, conn):
    cursor.execute("SELECT estados_articulo FROM config_recepcion_qr WHERE id = 1")
    row = cursor.fetchone()
    if row and row[0] and row[0] != '[]':
        print("OK 'estados_articulo' ya tiene datos, no se resiembra")
        return

    estados = cargar_estados_articulo_json()
    estados_json = json.dumps(estados, ensure_ascii=False)
    cursor.execute("UPDATE config_recepcion_qr SET estados_articulo = ? WHERE id = 1", (estados_json,))
    conn.commit()
    print(f"OK estados_articulo sembrado desde JSON local ({len(estados)} estados)")


def cargar_personas_recepcion_json():
    ruta = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "Diccionarios", "personas_recepcion.json"
    )
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("personas_recepcion", [])
    except Exception:
        return []


def anadir_columnas_aviso_recepcion(cursor, conn):
    try:
        cursor.execute("PRAGMA table_info('rma_maestro')")
        columnas = [row[1] for row in cursor.fetchall()]
    except Exception:
        columnas = []

    if 'aviso_recepcion_mensaje' not in columnas:
        try:
            cursor.execute("ALTER TABLE rma_maestro ADD COLUMN aviso_recepcion_mensaje TEXT")
            conn.commit()
            print("OK columna 'aviso_recepcion_mensaje' añadida a rma_maestro")
        except Exception as e:
            err = str(e).lower()
            if "duplicate" in err or "already exists" in err:
                print("OK columna 'aviso_recepcion_mensaje' ya existe en rma_maestro (detectado por error)")
            else:
                raise
    else:
        print("OK columna 'aviso_recepcion_mensaje' ya existe en rma_maestro")

    if 'aviso_recepcion_sonido' not in columnas:
        try:
            cursor.execute("ALTER TABLE rma_maestro ADD COLUMN aviso_recepcion_sonido INTEGER NOT NULL DEFAULT 1")
            conn.commit()
            print("OK columna 'aviso_recepcion_sonido' añadida a rma_maestro")
        except Exception as e:
            err = str(e).lower()
            if "duplicate" in err or "already exists" in err:
                print("OK columna 'aviso_recepcion_sonido' ya existe en rma_maestro (detectado por error)")
            else:
                raise
    else:
        print("OK columna 'aviso_recepcion_sonido' ya existe en rma_maestro")


def inicializar_config_por_defecto(cursor, conn):
    cursor.execute("SELECT id FROM config_recepcion_qr WHERE id = 1")
    if cursor.fetchone():
        print("OK fila de configuración ya existe en config_recepcion_qr")
        return

    personas = cargar_personas_recepcion_json()
    personas_json = json.dumps(personas, ensure_ascii=False)

    mensaje_por_defecto = (
        "El nombre introducido no coincide con el personal autorizado. "
        "Por favor, contacta con el Departamento de Incidencias."
    )
    cursor.execute(
        "INSERT INTO config_recepcion_qr (id, personas_recepcion, mensaje_incidencias, pin_max_intentos, pin_caducidad_minutos) "
        "VALUES (1, ?, ?, 5, 15)",
        (personas_json, mensaje_por_defecto)
    )
    conn.commit()
    print(f"OK fila de configuración inicial creada en config_recepcion_qr (personas migradas: {len(personas)})")


def inicializar_config_trazabilidad(cursor, conn):
    cursor.execute("SELECT id FROM config_trazabilidad WHERE id = 1")
    if cursor.fetchone():
        print("OK fila de configuración ya existe en config_trazabilidad")
        return

    cursor.execute(
        "INSERT INTO config_trazabilidad (id, texto_ayuda) VALUES (1, ?)",
        (_TEXTO_AYUDA_TRAZABILIDAD_DEFECTO,)
    )
    conn.commit()
    print("OK fila de configuración inicial creada en config_trazabilidad")


def main():
    if not (os.getenv("TURSO_DATABASE_URL") and os.getenv("TURSO_AUTH_TOKEN")):
        print("ERROR: TURSO_DATABASE_URL / TURSO_AUTH_TOKEN no configurados en el entorno (.env)")
        sys.exit(1)

    conn = connect_db()
    cursor = conn.cursor()

    crear_tablas(cursor, conn)
    anadir_columna_metodo_recepcion(cursor, conn)
    anadir_columna_puede_editar(cursor, conn)
    anadir_columna_estados_articulo(cursor, conn)
    anadir_columnas_aviso_recepcion(cursor, conn)
    inicializar_config_por_defecto(cursor, conn)
    sembrar_estados_articulo(cursor, conn)
    inicializar_config_trazabilidad(cursor, conn)

    conn.close()
    print("\nEsquema de recepción por QR listo en Turso.")


if __name__ == "__main__":
    main()
