import sqlite3
import os
from pathlib import Path

DB_FILE = os.getenv("DB_FILE", "rma_app.db")
OUTPUT = os.getenv("OUTPUT", "turso_dump.sql")


def export_dump(db_path: str, out_path: str) -> None:
    if not Path(db_path).exists():
        raise FileNotFoundError(f"No existe la base de datos: {db_path}")
    con = sqlite3.connect(db_path)
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            for line in con.iterdump():
                f.write(f"{line}\n")
        print(f"Dump SQL exportado a: {out_path}")
    finally:
        con.close()


if __name__ == "__main__":
    export_dump(DB_FILE, OUTPUT)
