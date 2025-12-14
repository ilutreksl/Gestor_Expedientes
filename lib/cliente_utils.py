"""
Utilidades para gestión de clientes
"""
from tkinter import messagebox
from lib.rma_editor_window import RmaEditorWindow


def obtener_años_rmas_cliente(cliente_id, conectar_db_func):
    """Obtiene los años disponibles en los RMAs del cliente."""
    try:
        conn, cursor = conectar_db_func()
        if not conn:
            return []
        
        # Obtener nombre del cliente
        cursor.execute("SELECT nombre FROM clientes WHERE cliente_id = ?", (cliente_id,))
        cliente_info = cursor.fetchone()
        if not cliente_info:
            return []
        
        nombre_cliente = cliente_info[0]
        
        # Obtener años únicos
        cursor.execute("""
            SELECT DISTINCT strftime('%Y', fecha_emision) as año
            FROM rma_maestro
            WHERE cliente = ? AND fecha_emision IS NOT NULL
            ORDER BY año DESC
        """, (nombre_cliente,))
        
        años = [row[0] for row in cursor.fetchall() if row[0]]
        conn.close()
        return años
        
    except Exception as e:
        print(f"Error obteniendo años: {e}")
        return []


def abrir_rma_por_codigo(codigo_rma, conectar_db_func, parent_window):
    """Abre un expediente RMA dado su código en una ventana nueva."""
    try:
        conn, cursor = conectar_db_func()
        if not conn:
            return
        
        # Buscar el ID del RMA por su código
        cursor.execute("SELECT id FROM rma_maestro WHERE codigo_rma = ?", (codigo_rma,))
        resultado = cursor.fetchone()
        conn.close()
        
        if resultado:
            rma_id = resultado[0]
            # Abrir en ventana nueva usando RmaEditorWindow
            RmaEditorWindow(parent_window, rma_id=rma_id)
        else:
            messagebox.showerror("Error", f"No se encontró el expediente RMA #{codigo_rma}")
            
    except Exception as e:
        print(f"Error abriendo RMA: {e}")
        messagebox.showerror("Error", f"Error al abrir el expediente: {str(e)}")


def obtener_historial_rmas_cliente(cliente_id, conectar_db_func, año=None, busqueda=None):
    """Obtiene el historial de RMAs de un cliente con filtros."""
    try:
        conn, cursor = conectar_db_func()
        if not conn: 
            return []
        
        # Primero obtener el nombre del cliente
        cursor.execute("SELECT nombre FROM clientes WHERE cliente_id = ?", (cliente_id,))
        cliente_info = cursor.fetchone()
        if not cliente_info:
            return []
        
        nombre_cliente = cliente_info[0]
        
        # Construir query con filtros
        query = """
            SELECT codigo_rma, fecha_emision, estado, motivo
            FROM rma_maestro 
            WHERE cliente = ?
        """
        params = [nombre_cliente]
        
        # Filtro por año
        if año:
            query += " AND strftime('%Y', fecha_emision) = ?"
            params.append(str(año))
        
        # Filtro por búsqueda
        if busqueda:
            query += " AND UPPER(codigo_rma) LIKE ?"
            params.append(f"%{busqueda}%")
        
        query += " ORDER BY fecha_emision DESC"
        
        cursor.execute(query, params)
        rmas = cursor.fetchall()
        conn.close()
        return rmas
        
    except Exception as e:
        print(f"Error obteniendo historial RMAs: {e}")
        return []
