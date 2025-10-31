"""
Reordena turso_02_data.sql para que rma_maestro se inserte primero.
"""

INPUT = "turso_02_data.sql"
OUTPUT = "turso_02_data_ordered.sql"

# Leer todas las líneas
with open(INPUT, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Clasificar las líneas por tabla
maestro_lines = []
usuarios_lines = []
other_lines = []

for line in lines:
    if 'INSERT INTO "rma_maestro"' in line:
        maestro_lines.append(line)
    elif 'INSERT INTO "usuarios"' in line:
        usuarios_lines.append(line)
    else:
        other_lines.append(line)

# Escribir en orden correcto: usuarios, maestro, luego el resto
with open(OUTPUT, "w", encoding="utf-8") as f:
    # Primero usuarios (para el login)
    for line in usuarios_lines:
        f.write(line)
    # Luego rma_maestro (tabla padre)
    for line in maestro_lines:
        f.write(line)
    # Finalmente el resto (tablas hijas)
    for line in other_lines:
        f.write(line)

print(f"✅ Archivo reordenado creado: {OUTPUT}")
print(f"   - Usuarios: {len(usuarios_lines)} líneas")
print(f"   - RMA Maestro: {len(maestro_lines)} líneas")
print(f"   - Otras tablas: {len(other_lines)} líneas")
