"""
Script helper para procesar/normalizar iconos PNG que hayas descargado (p. ej. desde Freepik).

Qué hace:
- Busca en la carpeta `icons/` ficheros PNG cuyo nombre contenga palabras clave (list, articles, stats, tasks, reports, edit, info).
- Si encuentra coincidencias, redimensiona la imagen a 24x24 (manteniendo transparencia) y la guarda con el nombre esperado que usa la app:
    ic_list_outline_24.png
    ic_articles_outline_24.png
    ic_stats_outline_24.png
    ic_tasks_outline_24.png
    ic_reports_outline_24.png
    boton-de-informacion.png
    ic_edit_outline_24.png

Uso (PowerShell desde la raíz del repo):
    py .\scripts\import_icons_from_folder.py

Recomendación:
- Descarga desde Freepik PNGs con fondo transparente (preferible) y con tamaño >= 64x64. Nómbralos de forma descriptiva (por ejemplo `list.png`, `articulos.png`, `edit.png`) o deja el nombre original; el script intentará emparejarlos por palabra clave.
- El script hará copia de seguridad automática de los ficheros objetivo si existen.

"""
from PIL import Image
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(__file__))
ICONS_DIR = os.path.join(ROOT, "icons")
if not os.path.isdir(ICONS_DIR):
    print("Carpeta icons/ no encontrada. Creando...")
    os.makedirs(ICONS_DIR, exist_ok=True)

# Mapa de nombre objetivo -> lista de palabras clave que pueden aparecer en los ficheros descargados
TARGETS = {
    "ic_list_outline_24.png": ["list", "lista", "lista_rma", "listado"],
    "ic_articles_outline_24.png": ["article", "articulo", "artículos", "articulos", "article"],
    "ic_stats_outline_24.png": ["stat", "estad", "stats", "graf"],
    "ic_tasks_outline_24.png": ["task", "tarea", "tasks", "tareas"],
    "ic_reports_outline_24.png": ["report", "informe", "reports", "reportar"],
    "boton-de-informacion.png": ["info", "information", "ayuda", "help"],
    "ic_edit_outline_24.png": ["edit", "editar", "pencil", "lapiz", "pencil"]
}

# Tamaño objetivo
TARGET_SIZE = (24, 24)

# Buscar ficheros en icons/ que coincidan con palabras clave
found = {k: None for k in TARGETS.keys()}
all_files = [f for f in os.listdir(ICONS_DIR) if os.path.isfile(os.path.join(ICONS_DIR, f))]

candidates = {}
for f in all_files:
    name_low = f.lower()
    if not name_low.endswith(('.png', '.jpg', '.jpeg', '.webp')):
        continue
    for target, keywords in TARGETS.items():
        for kw in keywords:
            if kw in name_low:
                candidates.setdefault(target, []).append(f)
                break

# Mostrar coincidencias y elegir
for target in TARGETS:
    cands = candidates.get(target, [])
    if not cands:
        print(f"No se encontraron candidatos para {target}")
        continue
    # Si hay varios candidatos, toma el primero; el usuario puede renombrar manualmente si quiere otro
    src_fname = cands[0]
    src_path = os.path.join(ICONS_DIR, src_fname)
    dest_path = os.path.join(ICONS_DIR, target)

    try:
        # Hacer backup del destino si existe
        if os.path.exists(dest_path):
            bak = dest_path + ".bak"
            shutil.copy2(dest_path, bak)
            print(f"Backup creado: {bak}")

        # Abrir y redimensionar
        img = Image.open(src_path).convert("RGBA")
        img = img.resize(TARGET_SIZE, Image.LANCZOS)
        img.save(dest_path, format="PNG")
        print(f"Generado {target} desde {src_fname}")
    except Exception as e:
        print(f"Error procesando {src_fname} -> {target}: {e}")

print("Proceso terminado. Reinicia la app para ver los iconos actualizados.")
