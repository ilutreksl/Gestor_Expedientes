"""
Divide el dump SQL en archivos más pequeños para facilitar la importación en Turso.
Genera:
1. turso_01_schema.sql - Solo CREATE TABLE
2. turso_02_data.sql - Solo INSERT INTO
"""
import os
from pathlib import Path

INPUT = "turso_dump.sql"
OUTPUT_SCHEMA = "turso_01_schema.sql"
OUTPUT_DATA = "turso_02_data.sql"


def split_dump():
    if not Path(INPUT).exists():
        print(f"Error: No existe {INPUT}")
        return
    
    with open(INPUT, "r", encoding="utf-8") as f:
        content = f.read()
    
    lines = content.splitlines()
    
    schema_lines = []
    data_lines = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped:  # Línea vacía
            continue
        
        if stripped.startswith('CREATE TABLE'):
            # CREATE TABLE puede ser multilínea, agregar toda la definición
            schema_lines.append(line)
        elif stripped.startswith('INSERT INTO'):
            data_lines.append(line)
        elif schema_lines and not stripped.startswith('INSERT INTO'):
            # Continuar con la definición del CREATE TABLE
            schema_lines.append(line)
    
    # Escribir archivo de schema
    with open(OUTPUT_SCHEMA, "w", encoding="utf-8") as f:
        f.write("\n".join(schema_lines))
    
    print(f"✅ Generado: {OUTPUT_SCHEMA} ({len(schema_lines)} líneas)")
    
    # Escribir archivo de datos
    with open(OUTPUT_DATA, "w", encoding="utf-8") as f:
        f.write("\n".join(data_lines))
    
    print(f"✅ Generado: {OUTPUT_DATA} ({len(data_lines)} líneas)")
    print("\n📋 Instrucciones:")
    print("1. Ejecuta primero turso_01_schema.sql en Turso")
    print("2. Luego ejecuta turso_02_data.sql en Turso")


if __name__ == "__main__":
    split_dump()
