"""
Script de configuración inicial para la recepción de paquetes por QR.
Crea en Turso las tablas necesarias (dispositivos_qr, pins_qr,
config_recepcion_qr, auditoria_qr) y añade la columna metodo_recepcion
a rma_maestro. Es idempotente: se puede ejecutar varias veces sin
duplicar nada.

Si existe Diccionarios/personas_recepcion.json, su contenido se usa
para sembrar la fila inicial de config_recepcion_qr (no se pierde la
lista de personas de recepción ya configurada).

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
}


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


def main():
    if not (os.getenv("TURSO_DATABASE_URL") and os.getenv("TURSO_AUTH_TOKEN")):
        print("ERROR: TURSO_DATABASE_URL / TURSO_AUTH_TOKEN no configurados en el entorno (.env)")
        sys.exit(1)

    conn = connect_db()
    cursor = conn.cursor()

    crear_tablas(cursor, conn)
    anadir_columna_metodo_recepcion(cursor, conn)
    inicializar_config_por_defecto(cursor, conn)

    conn.close()
    print("\nEsquema de recepción por QR listo en Turso.")


if __name__ == "__main__":
    main()
