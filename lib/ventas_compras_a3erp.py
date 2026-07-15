"""
Importación de ventas/compras exportadas desde a3ERP y comparativa contra incidencias (RMA).

Cada importación queda registrada como un "periodo" (histórico o incremental, con su
rango de fechas), de forma que las cargas semanales se acumulan en el tiempo en vez
de perderse, y la comparativa contra incidencias puede filtrarse por ventana temporal.
"""
import json
import os
import re
import unicodedata
from datetime import datetime, timedelta

import customtkinter as ctk
from tkinter import messagebox, filedialog, Listbox, Scrollbar, MULTIPLE, END, Toplevel
import pandas as pd

from CTkDatePicker import CTkDatePicker
from lib.app_core import parse_date_to_iso, logger, connect_db
from lib.estados_manager import EstadosArticuloManager
from lib.articulo_utils import VentanaEstadosArticulo


# --- Estados de rma_detalles que se consideran incidencia real de producto por defecto.
# El usuario puede cambiar esta selección desde la pestaña Comparativa; la lista completa
# de estados posibles sale de Diccionarios/estados_articulo.json (EstadosArticuloManager),
# porque esos estados pueden cambiar con el tiempo.
ESTADOS_PROBLEMATICOS_DEFECTO = [
    "NO FUNCIONA, ABONAR",
    "NO FUNCIONA ; NO ABONAR",
    "REPOSICION FALLO PRODUCTO",
    "REPOSICION ; ABONAR",
    "FALLO SOLDADURA ; ABONAR",
    "FALLO SOLDADURA ; NO ABONAR",
    "FALLO MODULO ; ABONAR",
]

# --- Mapeo de columnas del Excel de a3ERP (ventas y compras comparten formato) ---
_MAPA_COLUMNAS = {
    'alias': 'alias',
    'codigo': 'referencia',
    'descripcion': 'descripcion',
    'codigo de acabados': 'codigo_acabados',
    'codigo de cantidad': 'codigo_cantidad',
    'cod fam de acabados': 'familia_acabados',
    'cod fam de cantidad': 'familia_cantidad',
    'unidades': 'unidades',
    'bruto': 'bruto',
    'descuentos': 'descuentos',
    'neto': 'neto',
    'coste': 'coste',
    'margen': 'margen',
    'pct margen': 'porc_margen',
}
_COLUMNAS_NUMERICAS = ['unidades', 'bruto', 'descuentos', 'neto', 'coste', 'margen', 'porc_margen']


def _normalizar_columna(nombre):
    s = str(nombre).strip()
    s = s.replace('%', 'pct ')
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    s = s.lower()
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def _parsear_excel(ruta_archivo):
    """Lee un Excel exportado de a3ERP (ventas o compras) y devuelve un DataFrame normalizado."""
    df = pd.read_excel(ruta_archivo)

    columnas_renombradas = {}
    for col in df.columns:
        clave = _MAPA_COLUMNAS.get(_normalizar_columna(col))
        if clave:
            columnas_renombradas[col] = clave
    df = df.rename(columns=columnas_renombradas)
    df = df[[c for c in df.columns if c in _MAPA_COLUMNAS.values()]]

    if 'referencia' not in df.columns or 'unidades' not in df.columns:
        raise ValueError(
            "No se han reconocido las columnas 'Código' y/o 'Unidades' en el Excel.\n"
            "Verifica que sea una exportación de ventas/compras de a3ERP con fila de cabecera."
        )

    df['referencia'] = df['referencia'].astype(str).str.strip()
    df = df[(df['referencia'] != '') & (df['referencia'].str.lower() != 'nan')]

    for col in _COLUMNAS_NUMERICAS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if df.empty:
        raise ValueError("El archivo no contiene filas con referencia válida.")

    return df.reset_index(drop=True)


# --- Persistencia ---

def _ensure_tablas(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS a3erp_periodos (
            id INTEGER PRIMARY KEY,
            tipo_movimiento TEXT NOT NULL,
            tipo_carga TEXT NOT NULL,
            fecha_inicio TEXT NOT NULL,
            fecha_fin TEXT NOT NULL,
            nombre_archivo TEXT,
            usuario TEXT,
            fecha_importacion TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS a3erp_lineas (
            id INTEGER PRIMARY KEY,
            periodo_id INTEGER NOT NULL,
            alias TEXT,
            referencia TEXT NOT NULL,
            descripcion TEXT,
            codigo_acabados TEXT,
            codigo_cantidad TEXT,
            familia_acabados TEXT,
            familia_cantidad TEXT,
            unidades REAL NOT NULL DEFAULT 0,
            bruto REAL,
            descuentos REAL,
            neto REAL,
            coste REAL,
            margen REAL,
            porc_margen REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS a3erp_config (
            clave TEXT PRIMARY KEY,
            valor TEXT
        )
    """)
    conn.commit()


UMBRAL_ALARMA_DEFECTO = 3.0


def _obtener_umbral_alarma(conn):
    cur = conn.cursor()
    cur.execute("SELECT valor FROM a3erp_config WHERE clave = 'umbral_alarma_pct'")
    row = cur.fetchone()
    if not row or row[0] in (None, ''):
        return UMBRAL_ALARMA_DEFECTO
    try:
        return float(row[0])
    except (TypeError, ValueError):
        return UMBRAL_ALARMA_DEFECTO


def _guardar_umbral_alarma(conn, valor):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO a3erp_config (clave, valor) VALUES ('umbral_alarma_pct', ?) "
        "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
        (str(valor),)
    )
    conn.commit()


def _obtener_estados_problematicos(conn):
    """Estados de producto que cuentan como incidencia, elegidos por el usuario.

    Se guardan como JSON en a3erp_config. Si nunca se han configurado, se inicializan
    con ESTADOS_PROBLEMATICOS_DEFECTO filtrado a los estados que existan actualmente
    en Diccionarios/estados_articulo.json (por si alguno se ha eliminado con el tiempo).
    """
    cur = conn.cursor()
    cur.execute("SELECT valor FROM a3erp_config WHERE clave = 'estados_problematicos'")
    row = cur.fetchone()
    if row and row[0]:
        try:
            return json.loads(row[0])
        except (TypeError, ValueError):
            pass

    estados_disponibles = EstadosArticuloManager().cargar_estados()
    estados_iniciales = [e for e in ESTADOS_PROBLEMATICOS_DEFECTO if e in estados_disponibles]
    _guardar_estados_problematicos(conn, estados_iniciales)
    return estados_iniciales


def _guardar_estados_problematicos(conn, estados):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO a3erp_config (clave, valor) VALUES ('estados_problematicos', ?) "
        "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
        (json.dumps(estados),)
    )
    conn.commit()


def _guardar_periodo(conn, tipo_movimiento, tipo_carga, fecha_inicio, fecha_fin, nombre_archivo, usuario, df):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO a3erp_periodos (tipo_movimiento, tipo_carga, fecha_inicio, fecha_fin, nombre_archivo, usuario) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (tipo_movimiento, tipo_carga, fecha_inicio, fecha_fin, nombre_archivo, usuario)
    )
    periodo_id = cur.lastrowid
    if not periodo_id:
        cur.execute(
            "SELECT id FROM a3erp_periodos WHERE tipo_movimiento=? AND tipo_carga=? AND fecha_inicio=? AND fecha_fin=? "
            "ORDER BY id DESC LIMIT 1",
            (tipo_movimiento, tipo_carga, fecha_inicio, fecha_fin)
        )
        periodo_id = cur.fetchone()[0]

    filas = []
    for _, row in df.iterrows():
        filas.append((
            periodo_id,
            row.get('alias', '') or '',
            row['referencia'],
            row.get('descripcion', '') or '',
            row.get('codigo_acabados', '') or '',
            row.get('codigo_cantidad', '') or '',
            row.get('familia_acabados', '') or '',
            row.get('familia_cantidad', '') or '',
            float(row.get('unidades', 0) or 0),
            float(row.get('bruto', 0) or 0),
            float(row.get('descuentos', 0) or 0),
            float(row.get('neto', 0) or 0),
            float(row.get('coste', 0) or 0),
            float(row.get('margen', 0) or 0),
            float(row.get('porc_margen', 0) or 0),
        ))
    sql_insert_linea = (
        "INSERT INTO a3erp_lineas (periodo_id, alias, referencia, descripcion, codigo_acabados, codigo_cantidad, "
        "familia_acabados, familia_cantidad, unidades, bruto, descuentos, neto, coste, margen, porc_margen) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    try:
        # Se envía en lotes en vez de un único executemany: un Excel histórico puede traer
        # miles de filas, y un solo pipeline con todas ellas puede superar el timeout de la
        # conexión remota (Turso). Lotes pequeños mantienen cada petición HTTP rápida.
        TAM_LOTE = 200
        for i in range(0, len(filas), TAM_LOTE):
            cur.executemany(sql_insert_linea, filas[i:i + TAM_LOTE])
        conn.commit()
    except Exception:
        # Si falla a mitad de la carga, no dejar un periodo a medio importar: se borra
        # (y lo que se hubiera insertado hasta ese punto) para que el usuario pueda reintentar.
        try:
            _eliminar_periodo(conn, periodo_id)
        except Exception:
            pass
        raise

    return periodo_id


def _eliminar_periodo(conn, periodo_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM a3erp_lineas WHERE periodo_id = ?", (periodo_id,))
    cur.execute("DELETE FROM a3erp_periodos WHERE id = ?", (periodo_id,))
    conn.commit()


def _periodos_solapados(conn, tipo_movimiento, tipo_carga, fecha_inicio, fecha_fin):
    """Periodos ya importados del mismo tipo de movimiento y de carga cuyo rango se solapa con el indicado.

    Solo se compara dentro del mismo tipo_carga: el bloque histórico y las cargas
    incrementales se solapan a propósito (el histórico es el fondo de referencia),
    así que cruzarlos aquí generaría un aviso falso en cada importación semanal.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT tipo_carga, fecha_inicio, fecha_fin FROM a3erp_periodos "
        "WHERE tipo_movimiento = ? AND tipo_carga = ? AND fecha_inicio <= ? AND fecha_fin >= ?",
        (tipo_movimiento, tipo_carga, fecha_fin, fecha_inicio)
    )
    return cur.fetchall()


def _periodos_incluidos(conn, tipo_movimiento, incluir_historico, fecha_desde, fecha_hasta):
    """IDs de periodo a incluir en una comparativa, según filtros de histórico/ventana temporal."""
    cur = conn.cursor()
    ids = []

    if incluir_historico:
        cur.execute(
            "SELECT id FROM a3erp_periodos WHERE tipo_movimiento = ? AND tipo_carga = 'historico'",
            (tipo_movimiento,)
        )
        ids.extend(r[0] for r in cur.fetchall())

    sql = "SELECT id FROM a3erp_periodos WHERE tipo_movimiento = ? AND tipo_carga = 'incremental'"
    params = [tipo_movimiento]
    if fecha_desde:
        sql += " AND fecha_fin >= ?"
        params.append(fecha_desde)
    if fecha_hasta:
        sql += " AND fecha_inicio <= ?"
        params.append(fecha_hasta)
    cur.execute(sql, params)
    ids.extend(r[0] for r in cur.fetchall())
    return ids


def _sumar_unidades_por_referencia(conn, periodo_ids):
    """Unidades y totales en € (neto, coste, margen) por referencia para los periodos indicados.

    En compras 'coste' y 'margen' siempre valen 0 (el Excel de compras no trae esas
    columnas) — el coste de la compra es directamente 'neto'.
    """
    if not periodo_ids:
        return pd.DataFrame(columns=['referencia', 'unidades', 'neto', 'coste', 'margen'])
    cur = conn.cursor()
    placeholders = ','.join(['?'] * len(periodo_ids))
    cur.execute(
        f"SELECT referencia, SUM(unidades), SUM(neto), SUM(coste), SUM(margen) "
        f"FROM a3erp_lineas WHERE periodo_id IN ({placeholders}) GROUP BY referencia",
        periodo_ids
    )
    rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=['referencia', 'unidades', 'neto', 'coste', 'margen'])
    df['referencia'] = df['referencia'].astype(str).str.strip()
    return df


def _obtener_incidencias_por_referencia(conn, estados_problematicos):
    if not estados_problematicos:
        return pd.DataFrame(columns=['referencia', 'num_incidencias', 'cantidad_incidencias'])
    cur = conn.cursor()
    placeholders = ','.join(['?' for _ in estados_problematicos])
    cur.execute(f"""
        SELECT
            referencia_articulo,
            COUNT(*) as num_incidencias,
            SUM(cantidad_entregada) as cantidad_incidencias
        FROM rma_detalles
        WHERE referencia_articulo IS NOT NULL
        AND referencia_articulo != ''
        AND estado_producto IN ({placeholders})
        AND COALESCE(contabilizar, 1) = 1
        GROUP BY referencia_articulo
    """, estados_problematicos)
    rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=['referencia', 'num_incidencias', 'cantidad_incidencias'])
    df['referencia'] = df['referencia'].astype(str).str.strip()
    return df


def _calcular_metricas_economicas(df, tipo_movimiento):
    """Añade columnas de impacto económico a un DataFrame de comparativa ya fusionado
    (requiere 'unidades', 'neto', 'coste', 'margen', 'cantidad_incidencias').

    - precio_unitario: € medio por unidad (precio de venta, o precio de compra si tipo_movimiento='compra')
    - coste_unitario: € medio de coste de compra por unidad. En ventas sale de la columna
      'Coste' del Excel de a3ERP; en compras el Excel no separa coste/margen, así que el
      coste de la unidad ES su precio de compra (precio_unitario).
    - coste_incidencias: lo que le ha costado a la empresa comprar/producir las unidades
      que han acabado en una incidencia, independientemente de si se abonaron o no.
    - margen_perdido: beneficio dejado de ganar por esas unidades (solo tiene sentido en
      ventas; en compras se deja a 0 porque no hay margen de venta que perder).
    - ingresos_en_riesgo: valor de venta de las unidades con incidencia (solo ventas).
    """
    df = df.copy()
    unidades_seguras = df['unidades'].where(df['unidades'] != 0)

    df['precio_unitario'] = (df['neto'] / unidades_seguras).fillna(0).round(2)
    if tipo_movimiento == 'venta':
        df['coste_unitario'] = (df['coste'] / unidades_seguras).fillna(0).round(2)
        df['margen_unitario'] = (df['margen'] / unidades_seguras).fillna(0).round(2)
    else:
        df['coste_unitario'] = df['precio_unitario']
        df['margen_unitario'] = 0.0

    df['coste_incidencias'] = (df['cantidad_incidencias'] * df['coste_unitario']).round(2)
    df['margen_perdido'] = (df['cantidad_incidencias'] * df['margen_unitario']).round(2)
    df['ingresos_en_riesgo'] = (df['cantidad_incidencias'] * df['precio_unitario']).round(2)
    return df


def _calcular_alarmas(conn, tipo_movimiento, umbral):
    """Referencias cuyo % de incidencia iguala o supera el umbral.

    Usa siempre la vista global (histórico + todos los periodos incrementales),
    porque una alarma debe reflejar la situación real acumulada de la referencia,
    no un recorte temporal puntual.
    """
    periodo_ids = _periodos_incluidos(conn, tipo_movimiento, True, '', '')
    if not periodo_ids:
        return pd.DataFrame(columns=['referencia', 'unidades', 'num_incidencias', 'cantidad_incidencias', 'porcentaje_incidencia'])

    df_movimientos = _sumar_unidades_por_referencia(conn, periodo_ids)
    estados_problematicos = _obtener_estados_problematicos(conn)
    df_incidencias = _obtener_incidencias_por_referencia(conn, estados_problematicos)

    df = pd.merge(df_movimientos, df_incidencias, on='referencia', how='inner')
    if df.empty:
        return df.assign(porcentaje_incidencia=[])

    df['porcentaje_incidencia'] = (df['cantidad_incidencias'] / df['unidades'] * 100).round(2)
    df = df[df['porcentaje_incidencia'] >= umbral].sort_values('porcentaje_incidencia', ascending=False)
    return df.reset_index(drop=True)


class VentanaVentasComprasA3ERP(ctk.CTkToplevel):
    """Ventana para importar Excel de ventas/compras de a3ERP y compararlos con incidencias."""

    def __init__(self, ventana_principal):
        super().__init__(ventana_principal)

        self.ventana_principal = ventana_principal
        self.datos_comparativa = None
        self._comp_tipo_actual = None

        self.title("Ventas y Compras (a3ERP)")
        self.geometry("1200x750")

        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 1200) // 2
        y = (screen_height - 750) // 2
        self.geometry(f"1200x750+{x}+{y}")

        logger.info(f"Abriendo ventana de Ventas/Compras (a3ERP) para usuario: {getattr(ventana_principal, 'username', '')}")

        conn, cur = self.ventana_principal.conectar_db()
        if conn:
            try:
                _ensure_tablas(conn)
            finally:
                conn.close()

        self._crear_interfaz()

    def _crear_interfaz(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=15)

        self.tab_comparativa = self.tabview.add("📊 Comparativa vs Incidencias")
        self.tab_periodos = self.tabview.add("🗂️ Periodos cargados")
        self.tab_importar = self.tabview.add("📥 Importar")

        self._construir_tab_comparativa()
        self._construir_tab_periodos()
        self._construir_tab_importar()

        self._refrescar_periodos()

    # ------------------------------------------------------------------ #
    # Tab: Importar
    # ------------------------------------------------------------------ #
    def _construir_tab_importar(self):
        tab = self.tab_importar

        ctk.CTkLabel(
            tab, text="Importar Excel de a3ERP", font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(10, 5))
        ctk.CTkLabel(
            tab,
            text="El Excel debe ser la exportación de a3ERP con cabecera (Alias, Código, Descripción, ..., Unidades, ...).\n"
                 "Indica el tipo de movimiento y de carga, y el rango de fechas que filtraste en a3ERP para este archivo\n"
                 "(el fichero no trae fecha por línea, así que ese rango solo lo sabes tú).",
            justify="left", text_color="gray"
        ).pack(pady=(0, 15))

        form = ctk.CTkFrame(tab)
        form.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(form, text="Tipo de movimiento:").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.var_tipo_movimiento = ctk.StringVar(value="venta")
        ctk.CTkSegmentedButton(
            form, values=["venta", "compra"], variable=self.var_tipo_movimiento
        ).grid(row=0, column=1, sticky="w", padx=10, pady=10)

        ctk.CTkLabel(form, text="Tipo de carga:").grid(row=1, column=0, sticky="w", padx=10, pady=10)
        self.var_tipo_carga = ctk.StringVar(value="incremental")
        ctk.CTkSegmentedButton(
            form, values=["incremental", "historico"], variable=self.var_tipo_carga,
            command=self._al_cambiar_tipo_carga
        ).grid(row=1, column=1, sticky="w", padx=10, pady=10)

        ctk.CTkLabel(form, text="Fecha inicio del periodo:").grid(row=2, column=0, sticky="w", padx=10, pady=10)
        self.picker_inicio = CTkDatePicker(form, width=180)
        self.picker_inicio.set_date_format('%Y-%m-%d')
        self.picker_inicio.grid(row=2, column=1, sticky="w", padx=10, pady=10)

        ctk.CTkLabel(form, text="Fecha fin del periodo:").grid(row=3, column=0, sticky="w", padx=10, pady=10)
        self.picker_fin = CTkDatePicker(form, width=180)
        self.picker_fin.set_date_format('%Y-%m-%d')
        self.picker_fin.grid(row=3, column=1, sticky="w", padx=10, pady=10)

        self._al_cambiar_tipo_carga("incremental")

        self.btn_importar = ctk.CTkButton(
            tab, text="📁 Seleccionar Excel e Importar", command=self._importar, width=260
        )
        self.btn_importar.pack(pady=20)

        self.lbl_estado_importar = ctk.CTkLabel(tab, text="", text_color="gray")
        self.lbl_estado_importar.pack(pady=5)

    def _al_cambiar_tipo_carga(self, valor):
        hoy = datetime.now()
        inicio = hoy - timedelta(days=730) if valor == "historico" else hoy - timedelta(days=7)
        self.picker_inicio.set_date(inicio)
        self.picker_fin.set_date(hoy)

    def _importar(self):
        tipo_movimiento = self.var_tipo_movimiento.get()
        tipo_carga = self.var_tipo_carga.get()

        try:
            fecha_inicio = parse_date_to_iso(self.picker_inicio.get_date())
            fecha_fin = parse_date_to_iso(self.picker_fin.get_date())
        except ValueError as e:
            messagebox.showerror("Fecha inválida", str(e))
            return

        if fecha_inicio > fecha_fin:
            messagebox.showerror("Error", "La fecha de inicio no puede ser posterior a la fecha de fin.")
            return

        archivo = filedialog.askopenfilename(
            title=f"Seleccionar Excel de {tipo_movimiento}s",
            filetypes=[("Archivos Excel", "*.xlsx *.xls"), ("Todos los archivos", "*.*")]
        )
        if not archivo:
            return

        try:
            df = _parsear_excel(archivo)
        except Exception as e:
            logger.error(f"Error al leer Excel a3ERP '{archivo}': {e}", exc_info=True)
            messagebox.showerror("Error al leer el Excel", str(e))
            return

        conn, cur = self.ventana_principal.conectar_db()
        if not conn:
            logger.error("Error importando a3ERP: no se pudo conectar a la base de datos")
            messagebox.showerror("Error", "No se pudo conectar a la base de datos")
            return

        importacion_ok = False
        try:
            _ensure_tablas(conn)

            cur.execute(
                "SELECT id FROM a3erp_periodos WHERE tipo_movimiento=? AND tipo_carga=? AND fecha_inicio=? AND fecha_fin=?",
                (tipo_movimiento, tipo_carga, fecha_inicio, fecha_fin)
            )
            existente = cur.fetchone()

            if existente:
                if not messagebox.askyesno(
                    "Periodo ya importado",
                    "Ya existe una carga con el mismo tipo y exactamente el mismo rango de fechas.\n"
                    "¿Deseas reemplazarla por los datos de este nuevo archivo?"
                ):
                    return
                _eliminar_periodo(conn, existente[0])
            else:
                solapes = _periodos_solapados(conn, tipo_movimiento, tipo_carga, fecha_inicio, fecha_fin)
                if solapes:
                    detalle = "\n".join(f"- {tc} ({fi} a {ff})" for tc, fi, ff in solapes)
                    if not messagebox.askyesno(
                        "Periodo solapado",
                        f"El rango indicado se solapa con periodos ya importados:\n{detalle}\n\n"
                        "Si sumas ambos periodos en la comparativa, esas unidades se contarían dos veces. "
                        "¿Deseas continuar igualmente?"
                    ):
                        return

            _guardar_periodo(
                conn, tipo_movimiento, tipo_carga, fecha_inicio, fecha_fin,
                os.path.basename(archivo), getattr(self.ventana_principal, 'username', ''), df
            )

            self.lbl_estado_importar.configure(
                text=f"✅ Importadas {len(df)} referencias de {tipo_movimiento}s ({fecha_inicio} a {fecha_fin})",
                text_color="#22c55e"
            )
            messagebox.showinfo("Importación completada", f"Se han importado {len(df)} referencias correctamente.")
            importacion_ok = True
            logger.info(
                f"Importación a3ERP OK: tipo={tipo_movimiento}, carga={tipo_carga}, "
                f"periodo={fecha_inicio}..{fecha_fin}, referencias={len(df)}, archivo={os.path.basename(archivo)}, "
                f"usuario={getattr(self.ventana_principal, 'username', '')}"
            )
        except Exception as e:
            logger.error(f"Error al importar Excel a3ERP: {e}", exc_info=True)
            messagebox.showerror("Error al importar", str(e))
        finally:
            conn.close()

        self._refrescar_periodos()
        if importacion_ok:
            self._comprobar_alarmas_post_importacion(tipo_movimiento)

    # ------------------------------------------------------------------ #
    # Tab: Periodos cargados
    # ------------------------------------------------------------------ #
    def _construir_tab_periodos(self):
        tab = self.tab_periodos

        header = ctk.CTkFrame(tab, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header, text="Periodos importados", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="🔄 Refrescar", width=120, command=self._refrescar_periodos).pack(side="right")

        self.frame_periodos = ctk.CTkScrollableFrame(tab)
        self.frame_periodos.pack(fill="both", expand=True, padx=10, pady=10)

    def _refrescar_periodos(self):
        for widget in self.frame_periodos.winfo_children():
            widget.destroy()

        conn, cur = self.ventana_principal.conectar_db()
        if not conn:
            return
        try:
            _ensure_tablas(conn)
            cur.execute("""
                SELECT p.id, p.tipo_movimiento, p.tipo_carga, p.fecha_inicio, p.fecha_fin,
                       p.nombre_archivo, p.fecha_importacion, COUNT(l.id)
                FROM a3erp_periodos p
                LEFT JOIN a3erp_lineas l ON l.periodo_id = p.id
                GROUP BY p.id
                ORDER BY p.fecha_fin DESC, p.id DESC
            """)
            periodos = cur.fetchall()
        finally:
            conn.close()

        if not periodos:
            ctk.CTkLabel(
                self.frame_periodos, text="Todavía no se ha importado ningún periodo.", text_color="gray"
            ).pack(pady=20)
            return

        headers = [
            ("TIPO", 80), ("CARGA", 100), ("DESDE", 100), ("HASTA", 100),
            ("REFS.", 70), ("ARCHIVO", 220), ("IMPORTADO", 150), ("", 90)
        ]
        header_frame = ctk.CTkFrame(self.frame_periodos)
        header_frame.pack(fill="x", pady=(0, 5))
        for texto, ancho in headers:
            ctk.CTkLabel(header_frame, text=texto, font=ctk.CTkFont(weight="bold"), width=ancho).pack(side="left", padx=5)

        for (pid, tipo_mov, tipo_carga, f_ini, f_fin, archivo, f_imp, n_lineas) in periodos:
            fila = ctk.CTkFrame(self.frame_periodos, fg_color="transparent")
            fila.pack(fill="x", pady=2)
            ctk.CTkLabel(fila, text=tipo_mov, width=80).pack(side="left", padx=5)
            ctk.CTkLabel(fila, text=tipo_carga, width=100).pack(side="left", padx=5)
            ctk.CTkLabel(fila, text=f_ini, width=100).pack(side="left", padx=5)
            ctk.CTkLabel(fila, text=f_fin, width=100).pack(side="left", padx=5)
            ctk.CTkLabel(fila, text=str(n_lineas), width=70).pack(side="left", padx=5)
            ctk.CTkLabel(fila, text=(archivo or ''), width=220).pack(side="left", padx=5)
            ctk.CTkLabel(fila, text=str(f_imp or ''), width=150).pack(side="left", padx=5)
            ctk.CTkButton(
                fila, text="🗑️ Eliminar", width=90, fg_color="#ef4444", hover_color="#dc2626",
                command=lambda pid=pid: self._eliminar_periodo_ui(pid)
            ).pack(side="left", padx=5)

    def _eliminar_periodo_ui(self, periodo_id):
        if not messagebox.askyesno(
            "Confirmar", "¿Eliminar este periodo y todas sus líneas importadas?\nEsta acción no se puede deshacer."
        ):
            return
        conn, cur = self.ventana_principal.conectar_db()
        if not conn:
            messagebox.showerror("Error", "No se pudo conectar a la base de datos")
            return
        try:
            _eliminar_periodo(conn, periodo_id)
            logger.info(
                f"Periodo a3ERP eliminado: id={periodo_id}, usuario={getattr(self.ventana_principal, 'username', '')}"
            )
        finally:
            conn.close()
        self._refrescar_periodos()

    # ------------------------------------------------------------------ #
    # Tab: Comparativa vs Incidencias
    # ------------------------------------------------------------------ #
    def _construir_tab_comparativa(self):
        tab = self.tab_comparativa

        cabecera = ctk.CTkFrame(tab, fg_color="transparent")
        cabecera.pack(fill="x", padx=15, pady=(8, 2))
        ctk.CTkLabel(
            cabecera, text="📊 Comparativa: Movimientos vs Incidencias", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left")
        ctk.CTkButton(
            cabecera, text="ℹ️", width=30, fg_color="transparent", border_width=1,
            command=self._mostrar_info_comparativa
        ).pack(side="left", padx=8)

        filtros = ctk.CTkFrame(tab)
        filtros.pack(fill="x", padx=15, pady=4)

        PADY = 4

        # Fila 0: fuente de datos
        ctk.CTkLabel(filtros, text="Movimiento:").grid(row=0, column=0, padx=(10, 4), pady=PADY, sticky="w")
        self.var_comp_tipo = ctk.StringVar(value="venta")
        ctk.CTkSegmentedButton(
            filtros, values=["venta", "compra"], variable=self.var_comp_tipo
        ).grid(row=0, column=1, padx=4, pady=PADY, sticky="w")

        self.var_comp_historico = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            filtros, text="Incluir histórico", variable=self.var_comp_historico
        ).grid(row=0, column=2, padx=15, pady=PADY, sticky="w")

        ctk.CTkLabel(filtros, text="Desde:").grid(row=0, column=3, padx=(15, 4), pady=PADY, sticky="w")
        self.picker_comp_desde = CTkDatePicker(filtros, width=140)
        self.picker_comp_desde.set_date_format('%Y-%m-%d')
        self.picker_comp_desde.grid(row=0, column=4, padx=4, pady=PADY, sticky="w")

        ctk.CTkLabel(filtros, text="Hasta:").grid(row=0, column=5, padx=(10, 4), pady=PADY, sticky="w")
        self.picker_comp_hasta = CTkDatePicker(filtros, width=140)
        self.picker_comp_hasta.set_date_format('%Y-%m-%d')
        self.picker_comp_hasta.grid(row=0, column=6, padx=4, pady=PADY, sticky="w")

        # Fila 1: acciones + orden + estado
        ctk.CTkButton(
            filtros, text="🔄 Calcular", command=self._calcular_comparativa, width=140
        ).grid(row=1, column=0, columnspan=2, padx=10, pady=PADY, sticky="w")
        self.btn_exportar_comp = ctk.CTkButton(
            filtros, text="💾 Exportar", command=self._exportar_comparativa, width=140, state="disabled"
        )
        self.btn_exportar_comp.grid(row=1, column=2, padx=4, pady=PADY, sticky="w")

        ctk.CTkLabel(filtros, text="Ordenar por:").grid(row=1, column=3, padx=(15, 4), pady=PADY, sticky="w")
        self.var_orden_comp = ctk.StringVar(value="% incidencia")
        ctk.CTkSegmentedButton(
            filtros, values=["% incidencia", "Coste incidencias (€)"], variable=self.var_orden_comp,
            command=self._al_cambiar_orden_comparativa
        ).grid(row=1, column=4, columnspan=2, padx=4, pady=PADY, sticky="w")

        self.lbl_estado_comp = ctk.CTkLabel(filtros, text="", text_color="gray", font=ctk.CTkFont(size=11))
        self.lbl_estado_comp.grid(row=1, column=6, padx=10, pady=PADY, sticky="w")

        # Fila 2: alarmas
        ctk.CTkLabel(filtros, text="🔔 Umbral alarma (%):").grid(row=2, column=0, padx=(10, 4), pady=PADY, sticky="w")
        self.entry_umbral = ctk.CTkEntry(filtros, width=60)
        self.entry_umbral.grid(row=2, column=1, padx=4, pady=PADY, sticky="w")
        ctk.CTkButton(
            filtros, text="💾 Guardar", width=100, command=self._guardar_umbral_ui
        ).grid(row=2, column=2, padx=4, pady=PADY, sticky="w")
        ctk.CTkButton(
            filtros, text="🔔 Comprobar Alarmas Ahora", width=200, command=self._comprobar_alarmas_ui
        ).grid(row=2, column=3, columnspan=2, padx=(15, 4), pady=PADY, sticky="w")
        self._cargar_umbral_ui()

        # Fila 3: estados problemáticos + buscador
        ctk.CTkButton(
            filtros, text="⚙️ Estados que cuentan como incidencia", width=260,
            command=self._seleccionar_estados_problematicos_ui
        ).grid(row=3, column=0, columnspan=2, padx=10, pady=PADY, sticky="w")
        self.lbl_estados_problematicos = ctk.CTkLabel(filtros, text="", text_color="gray", font=ctk.CTkFont(size=11))
        self.lbl_estados_problematicos.grid(row=3, column=2, padx=4, pady=PADY, sticky="w")
        self._refrescar_lbl_estados_problematicos()

        ctk.CTkLabel(filtros, text="🔍 Buscar:").grid(row=3, column=3, padx=(15, 4), pady=PADY, sticky="w")
        self.var_buscar_referencia = ctk.StringVar()
        self.var_buscar_referencia.trace_add("write", self._on_buscar_referencia_changed)
        ctk.CTkEntry(
            filtros, textvariable=self.var_buscar_referencia, width=220,
            placeholder_text="Filtra por referencia..."
        ).grid(row=3, column=4, columnspan=2, padx=4, pady=PADY, sticky="w")

        self.frame_resultados_comp = ctk.CTkScrollableFrame(tab)
        self.frame_resultados_comp.pack(fill="both", expand=True, padx=15, pady=(4, 10))

    def _mostrar_info_comparativa(self):
        messagebox.showinfo(
            "Cómo funciona la comparativa",
            "Solo se cuentan incidencias con los estados de producto marcados como problemáticos "
            "(configurables con \"⚙️ Estados que cuentan como incidencia\").\n\n"
            "El bloque histórico agrega varios años sin fecha por línea: inclúyelo como volumen de "
            "referencia, pero para comparar tasas de fallo por antigüedad usa el filtro de fechas, "
            "que solo aplica a periodos semanales (incrementales).\n\n"
            "Haz clic en una referencia de la tabla para ver sus estados y expedientes asociados."
        )

    def _calcular_comparativa(self):
        tipo_movimiento = self.var_comp_tipo.get()
        incluir_historico = self.var_comp_historico.get()

        try:
            desde_txt = (self.picker_comp_desde.get_date() or '').strip()
            hasta_txt = (self.picker_comp_hasta.get_date() or '').strip()
            fecha_desde = parse_date_to_iso(desde_txt) if desde_txt else ''
            fecha_hasta = parse_date_to_iso(hasta_txt) if hasta_txt else ''
        except ValueError as e:
            messagebox.showerror("Fecha inválida", str(e))
            return

        conn, cur = self.ventana_principal.conectar_db()
        if not conn:
            messagebox.showerror("Error", "No se pudo conectar a la base de datos")
            return

        try:
            _ensure_tablas(conn)
            periodo_ids = _periodos_incluidos(conn, tipo_movimiento, incluir_historico, fecha_desde, fecha_hasta)
            if not periodo_ids:
                messagebox.showwarning("Sin datos", "No hay periodos importados que cumplan estos filtros.")
                return
            df_movimientos = _sumar_unidades_por_referencia(conn, periodo_ids)
            estados_problematicos = _obtener_estados_problematicos(conn)
            df_incidencias = _obtener_incidencias_por_referencia(conn, estados_problematicos)
        finally:
            conn.close()

        if not estados_problematicos:
            messagebox.showwarning(
                "Sin estados seleccionados",
                "No hay ningún estado marcado como incidencia. Configúralos con "
                "\"⚙️ Estados que cuentan como incidencia\" antes de calcular la comparativa."
            )
            return

        df_comparativa = pd.merge(df_movimientos, df_incidencias, on='referencia', how='inner')
        if df_comparativa.empty:
            messagebox.showwarning(
                "Sin coincidencias",
                "No se encontraron referencias comunes entre los movimientos filtrados y las incidencias."
            )
            return

        df_comparativa['porcentaje_incidencia'] = (
            df_comparativa['cantidad_incidencias'] / df_comparativa['unidades'] * 100
        ).round(2)
        df_comparativa = _calcular_metricas_economicas(df_comparativa, tipo_movimiento)

        self.datos_comparativa = df_comparativa
        self._comp_tipo_actual = tipo_movimiento
        self.var_buscar_referencia.set("")
        self._refrescar_tabla_comparativa()
        self.btn_exportar_comp.configure(state="normal")
        self.lbl_estado_comp.configure(
            text=f"✅ Comparativa calculada: {len(df_comparativa)} referencias coincidentes ({len(periodo_ids)} periodos incluidos)",
            text_color="#22c55e"
        )

    def _on_buscar_referencia_changed(self, *_args):
        self._refrescar_tabla_comparativa()

    def _al_cambiar_orden_comparativa(self, _valor=None):
        self._refrescar_tabla_comparativa()

    def _refrescar_tabla_comparativa(self):
        """Aplica el filtro de búsqueda y el criterio de orden actuales y repinta la tabla."""
        if self.datos_comparativa is None:
            return
        df = self.datos_comparativa
        texto = self.var_buscar_referencia.get().strip().lower()
        if texto:
            df = df[df['referencia'].str.lower().str.contains(texto, regex=False)]

        campo_orden = 'coste_incidencias' if self.var_orden_comp.get() == 'Coste incidencias (€)' else 'porcentaje_incidencia'
        if campo_orden not in df.columns:
            campo_orden = 'porcentaje_incidencia'
        df = df.sort_values(campo_orden, ascending=False)

        self._mostrar_resultados_comparativa(self._comp_tipo_actual, df)

    def _abrir_estados_articulo(self, referencia):
        """Abre la ventana ya existente de estados por artículo (con acceso a expedientes).

        VentanaEstadosArticulo espera una función que devuelva solo la conexión (con
        .cursor()), no la tupla (conn, cursor) que devuelve VentanaPrincipal.conectar_db().
        """
        VentanaEstadosArticulo(self.ventana_principal, referencia, connect_db)

    def _mostrar_resultados_comparativa(self, tipo_movimiento, df):
        for widget in self.frame_resultados_comp.winfo_children():
            widget.destroy()

        if df.empty:
            ctk.CTkLabel(
                self.frame_resultados_comp, text="Ninguna referencia coincide con la búsqueda.", text_color="gray"
            ).pack(pady=20)
            return

        hay_datos_economicos = 'coste_incidencias' in df.columns

        total_refs = len(df)
        promedio = df['porcentaje_incidencia'].mean()
        maximo = df['porcentaje_incidencia'].max()

        resumen = ctk.CTkFrame(self.frame_resultados_comp, fg_color="#f0f0f0")
        resumen.pack(fill="x", pady=(0, 8))
        texto_resumen = f"📈 Referencias: {total_refs} | Promedio incidencia: {promedio:.2f}% | Máximo: {maximo:.2f}%"
        if hay_datos_economicos:
            texto_resumen += f" | 💰 Coste incidencias: {df['coste_incidencias'].sum():,.2f} €"
            if tipo_movimiento == 'venta':
                texto_resumen += f" | Margen perdido: {df['margen_perdido'].sum():,.2f} €"
        ctk.CTkLabel(
            resumen, text=texto_resumen,
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#2c3e50"
        ).pack(pady=6)

        headers = [
            ("REFERENCIA", 190),
            (f"CANT. {tipo_movimiento.upper()}", 85),
            ("INCID.", 60),
            ("CANT. INCID.", 85),
            ("% INCID.", 80),
        ]
        if hay_datos_economicos:
            headers.append(("COSTE/UD", 80))
            headers.append(("COSTE INCID.", 110))
            if tipo_movimiento == 'venta':
                headers.append(("MARGEN PERDIDO", 120))
                headers.append(("INGRESO EN RIESGO", 130))

        header_frame = ctk.CTkFrame(self.frame_resultados_comp)
        header_frame.pack(fill="x", pady=(0, 3))
        for texto, ancho in headers:
            ctk.CTkLabel(
                header_frame, text=texto, font=ctk.CTkFont(size=11, weight="bold"), width=ancho
            ).pack(side="left", padx=4)

        for _, row in df.iterrows():
            fila = ctk.CTkFrame(self.frame_resultados_comp, fg_color="transparent")
            fila.pack(fill="x", pady=1)

            porcentaje = row['porcentaje_incidencia']
            if porcentaje < 1:
                color = "#22c55e"
            elif porcentaje < 3:
                color = "#eab308"
            elif porcentaje < 5:
                color = "#f97316"
            else:
                color = "#ef4444"

            referencia = str(row['referencia'])
            lbl_ref = ctk.CTkLabel(fila, text=referencia, width=190, text_color="#2b6cb0", cursor="hand2", font=ctk.CTkFont(size=11))
            lbl_ref.pack(side="left", padx=4)
            lbl_ref.bind("<Button-1>", lambda e, ref=referencia: self._abrir_estados_articulo(ref))
            ctk.CTkLabel(fila, text=f"{row['unidades']:.0f}", width=85, font=ctk.CTkFont(size=11)).pack(side="left", padx=4)
            ctk.CTkLabel(fila, text=f"{int(row['num_incidencias'])}", width=60, font=ctk.CTkFont(size=11)).pack(side="left", padx=4)
            ctk.CTkLabel(fila, text=f"{row['cantidad_incidencias']:.0f}", width=85, font=ctk.CTkFont(size=11)).pack(side="left", padx=4)
            ctk.CTkLabel(
                fila, text=f"{porcentaje:.2f}%", width=80, text_color=color, font=ctk.CTkFont(size=11, weight="bold")
            ).pack(side="left", padx=4)

            if hay_datos_economicos:
                ctk.CTkLabel(fila, text=f"{row['coste_unitario']:.2f} €", width=80, font=ctk.CTkFont(size=11)).pack(side="left", padx=4)
                ctk.CTkLabel(
                    fila, text=f"{row['coste_incidencias']:,.2f} €", width=110,
                    font=ctk.CTkFont(size=11, weight="bold"), text_color="#b45309"
                ).pack(side="left", padx=4)
                if tipo_movimiento == 'venta':
                    ctk.CTkLabel(
                        fila, text=f"{row['margen_perdido']:,.2f} €", width=120, font=ctk.CTkFont(size=11)
                    ).pack(side="left", padx=4)
                    ctk.CTkLabel(
                        fila, text=f"{row['ingresos_en_riesgo']:,.2f} €", width=130, font=ctk.CTkFont(size=11)
                    ).pack(side="left", padx=4)

        leyenda = ctk.CTkFrame(self.frame_resultados_comp, fg_color="#f0f0f0")
        leyenda.pack(fill="x", pady=10)
        ctk.CTkLabel(leyenda, text="Leyenda: ", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        ctk.CTkLabel(leyenda, text="🟢 <1%", text_color="#22c55e").pack(side="left", padx=5)
        ctk.CTkLabel(leyenda, text="🟡 1-3%", text_color="#eab308").pack(side="left", padx=5)
        ctk.CTkLabel(leyenda, text="🟠 3-5%", text_color="#f97316").pack(side="left", padx=5)
        ctk.CTkLabel(leyenda, text="🔴 >5%", text_color="#ef4444").pack(side="left", padx=5)

    def _cargar_umbral_ui(self):
        conn, cur = self.ventana_principal.conectar_db()
        if not conn:
            self.entry_umbral.insert(0, str(UMBRAL_ALARMA_DEFECTO))
            return
        try:
            _ensure_tablas(conn)
            umbral = _obtener_umbral_alarma(conn)
        finally:
            conn.close()
        self.entry_umbral.delete(0, "end")
        self.entry_umbral.insert(0, str(umbral))

    def _leer_umbral_entry(self):
        try:
            valor = float(self.entry_umbral.get().replace(',', '.').strip())
        except ValueError:
            messagebox.showerror("Umbral inválido", "Introduce un número válido para el umbral (ej. 3 o 3.5).")
            return None
        if valor <= 0:
            messagebox.showerror("Umbral inválido", "El umbral debe ser mayor que 0.")
            return None
        return valor

    def _guardar_umbral_ui(self):
        valor = self._leer_umbral_entry()
        if valor is None:
            return
        conn, cur = self.ventana_principal.conectar_db()
        if not conn:
            messagebox.showerror("Error", "No se pudo conectar a la base de datos")
            return
        try:
            _ensure_tablas(conn)
            _guardar_umbral_alarma(conn, valor)
        finally:
            conn.close()
        logger.info(
            f"Umbral de alarma a3ERP actualizado a {valor}%, usuario={getattr(self.ventana_principal, 'username', '')}"
        )
        messagebox.showinfo("Umbral guardado", f"El umbral de alarma se ha fijado en {valor}%.")

    def _refrescar_lbl_estados_problematicos(self):
        conn, cur = self.ventana_principal.conectar_db()
        if not conn:
            return
        try:
            _ensure_tablas(conn)
            estados = _obtener_estados_problematicos(conn)
        finally:
            conn.close()
        self.lbl_estados_problematicos.configure(text=f"{len(estados)} estado(s) seleccionado(s) como incidencia")

    def _seleccionar_estados_problematicos_ui(self):
        conn, cur = self.ventana_principal.conectar_db()
        if not conn:
            messagebox.showerror("Error", "No se pudo conectar a la base de datos")
            return
        try:
            _ensure_tablas(conn)
            estados_seleccionados_actual = _obtener_estados_problematicos(conn)
        finally:
            conn.close()

        estados_disponibles = [e for e in EstadosArticuloManager().cargar_estados() if e]

        dialogo = Toplevel(self)
        dialogo.title("Estados que cuentan como incidencia")
        dialogo.geometry("520x460")
        dialogo.transient(self)
        dialogo.grab_set()

        dialogo.update_idletasks()
        x = (dialogo.winfo_screenwidth() - 520) // 2
        y = (dialogo.winfo_screenheight() - 460) // 2
        dialogo.geometry(f"520x460+{x}+{y}")

        frame_principal = ctk.CTkFrame(dialogo)
        frame_principal.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            frame_principal,
            text="Selecciona qué estados de producto (Diccionarios/estados_articulo.json)\n"
                 "cuentan como incidencia para el % de incidencia y las alarmas:",
            font=ctk.CTkFont(size=12, weight="bold"), justify="left"
        ).pack(pady=10)

        frame_lista = ctk.CTkFrame(frame_principal)
        frame_lista.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar = Scrollbar(frame_lista)
        scrollbar.pack(side="right", fill="y")

        listbox = Listbox(frame_lista, selectmode=MULTIPLE, yscrollcommand=scrollbar.set, height=15, exportselection=False)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        for estado in estados_disponibles:
            listbox.insert(END, estado)
            if estado in estados_seleccionados_actual:
                listbox.selection_set(estados_disponibles.index(estado))

        frame_botones = ctk.CTkFrame(frame_principal)
        frame_botones.pack(fill="x", pady=10)

        def seleccionar_todos():
            listbox.selection_set(0, END)

        def deseleccionar_todos():
            listbox.selection_clear(0, END)

        def aplicar_seleccion():
            indices = listbox.curselection()
            nuevos_estados = [listbox.get(i) for i in indices]

            conn2, cur2 = self.ventana_principal.conectar_db()
            if not conn2:
                messagebox.showerror("Error", "No se pudo conectar a la base de datos")
                return
            try:
                _ensure_tablas(conn2)
                _guardar_estados_problematicos(conn2, nuevos_estados)
            finally:
                conn2.close()

            logger.info(
                f"Estados problemáticos a3ERP actualizados a {nuevos_estados}, "
                f"usuario={getattr(self.ventana_principal, 'username', '')}"
            )
            self._refrescar_lbl_estados_problematicos()
            dialogo.destroy()

        ctk.CTkButton(frame_botones, text="✓ Seleccionar Todos", command=seleccionar_todos, width=140).pack(side="left", padx=5)
        ctk.CTkButton(frame_botones, text="✗ Deseleccionar Todos", command=deseleccionar_todos, width=140).pack(side="left", padx=5)
        ctk.CTkButton(frame_botones, text="Aplicar", command=aplicar_seleccion, width=100).pack(side="right", padx=5)
        ctk.CTkButton(
            frame_botones, text="Cancelar", command=dialogo.destroy, fg_color="#ef4444", width=100
        ).pack(side="right", padx=5)

    def _comprobar_alarmas_ui(self):
        """Comprobación manual del umbral para el movimiento seleccionado en el combo de comparativa."""
        valor = self._leer_umbral_entry()
        if valor is None:
            return
        tipo_movimiento = self.var_comp_tipo.get()
        self._ejecutar_comprobacion_alarmas(tipo_movimiento, valor, silencioso_si_vacio=False)

    def _comprobar_alarmas_post_importacion(self, tipo_movimiento):
        """Comprobación automática tras importar un Excel, con el umbral guardado en BD."""
        conn, cur = self.ventana_principal.conectar_db()
        if not conn:
            return
        try:
            _ensure_tablas(conn)
            umbral = _obtener_umbral_alarma(conn)
        finally:
            conn.close()
        self._ejecutar_comprobacion_alarmas(tipo_movimiento, umbral, silencioso_si_vacio=True)

    def _ejecutar_comprobacion_alarmas(self, tipo_movimiento, umbral, silencioso_si_vacio):
        conn, cur = self.ventana_principal.conectar_db()
        if not conn:
            messagebox.showerror("Error", "No se pudo conectar a la base de datos")
            return
        try:
            _ensure_tablas(conn)
            df_alarmas = _calcular_alarmas(conn, tipo_movimiento, umbral)
        finally:
            conn.close()

        if df_alarmas.empty:
            if not silencioso_si_vacio:
                messagebox.showinfo(
                    "Sin alarmas",
                    f"Ninguna referencia de {tipo_movimiento}s supera el {umbral}% de incidencia."
                )
            return

        logger.warning(
            f"Alarma de incidencia a3ERP: {len(df_alarmas)} referencia(s) de {tipo_movimiento}s >= {umbral}% "
            f"(referencias: {', '.join(df_alarmas['referencia'].astype(str).tolist())})"
        )
        self._mostrar_dialogo_alarmas(df_alarmas, tipo_movimiento, umbral)

    def _mostrar_dialogo_alarmas(self, df_alarmas, tipo_movimiento, umbral):
        dialogo = ctk.CTkToplevel(self)
        dialogo.title("🔔 Alarmas de incidencia")
        dialogo.geometry("800x500")
        dialogo.attributes('-topmost', True)

        ctk.CTkLabel(
            dialogo,
            text=f"⚠️ {len(df_alarmas)} referencia(s) de {tipo_movimiento}s igualan o superan el {umbral}% de incidencia",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#ef4444", wraplength=760
        ).pack(pady=(15, 5))
        ctk.CTkLabel(
            dialogo,
            text="Cálculo sobre el total acumulado (histórico + periodos semanales importados). "
                 "Haz clic en una referencia para ver sus estados y expedientes asociados.",
            text_color="gray", wraplength=760
        ).pack(pady=(0, 10))

        frame = ctk.CTkScrollableFrame(dialogo)
        frame.pack(fill="both", expand=True, padx=15, pady=10)

        headers = [
            ("REFERENCIA", 220), (f"TOTAL {tipo_movimiento.upper()}S", 150),
            ("INCIDENCIAS", 120), ("% INCIDENCIA", 130)
        ]
        header_frame = ctk.CTkFrame(frame)
        header_frame.pack(fill="x", pady=(0, 5))
        for texto, ancho in headers:
            ctk.CTkLabel(header_frame, text=texto, font=ctk.CTkFont(weight="bold"), width=ancho).pack(side="left", padx=5)

        for _, row in df_alarmas.iterrows():
            fila = ctk.CTkFrame(frame, fg_color="transparent")
            fila.pack(fill="x", pady=2)
            referencia = str(row['referencia'])
            lbl_ref = ctk.CTkLabel(fila, text=referencia, width=220, text_color="#2b6cb0", cursor="hand2")
            lbl_ref.pack(side="left", padx=5)
            lbl_ref.bind("<Button-1>", lambda e, ref=referencia: self._abrir_estados_articulo(ref))
            ctk.CTkLabel(fila, text=f"{row['unidades']:.0f}", width=150).pack(side="left", padx=5)
            ctk.CTkLabel(fila, text=f"{int(row['num_incidencias'])} ({row['cantidad_incidencias']:.0f} uds.)", width=120).pack(side="left", padx=5)
            ctk.CTkLabel(
                fila, text=f"{row['porcentaje_incidencia']:.2f}%", width=130,
                text_color="#ef4444", font=ctk.CTkFont(weight="bold")
            ).pack(side="left", padx=5)

        ctk.CTkButton(dialogo, text="Cerrar", command=dialogo.destroy, width=120).pack(pady=15)

    def _exportar_comparativa(self):
        if self.datos_comparativa is None:
            messagebox.showwarning("Advertencia", "Primero debe calcular la comparativa")
            return

        archivo = filedialog.asksaveasfilename(
            title="Guardar resultados",
            defaultextension=".xlsx",
            filetypes=[("Archivos Excel", "*.xlsx"), ("Todos los archivos", "*.*")],
            initialfile="comparativa_a3erp_incidencias.xlsx"
        )
        if not archivo:
            return

        try:
            columnas = {
                'referencia': 'Referencia',
                'unidades': f'Cantidad {self._comp_tipo_actual}s',
                'num_incidencias': 'Número de Incidencias',
                'cantidad_incidencias': 'Cantidad en Incidencias',
                'porcentaje_incidencia': 'Porcentaje de Incidencia (%)',
                'coste_unitario': 'Coste por Unidad (€)',
                'coste_incidencias': 'Coste de las Incidencias (€)',
            }
            if self._comp_tipo_actual == 'venta':
                columnas['margen_perdido'] = 'Margen Perdido (€)'
                columnas['ingresos_en_riesgo'] = 'Ingreso en Riesgo (€)'

            columnas_presentes = [c for c in columnas if c in self.datos_comparativa.columns]
            df_exportar = self.datos_comparativa[columnas_presentes].rename(columns=columnas)
            df_exportar.to_excel(archivo, index=False, sheet_name='Comparativa')
            messagebox.showinfo("Exportación exitosa", f"Los resultados se han exportado correctamente a:\n{archivo}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar los resultados:\n{e}")
