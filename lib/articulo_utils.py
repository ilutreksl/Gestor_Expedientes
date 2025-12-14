"""
Utilidades para gestión de artículos
"""
import customtkinter as ctk


def mostrar_selector_referencias(articulos_data, parent_window, callback):
    """
    Muestra un diálogo para seleccionar un artículo de la lista en memoria
    
    Args:
        articulos_data: Lista de artículos en memoria
        parent_window: Ventana padre
        callback: Función a llamar con la referencia del artículo seleccionado
    """
    ventana = ctk.CTkToplevel(parent_window)
    ventana.title("Seleccionar Artículo")
    ventana.geometry("600x400")
    ventana.transient(parent_window)
    ventana.grab_set()
    
    # Centrar ventana
    ventana.update_idletasks()
    x = parent_window.winfo_x() + (parent_window.winfo_width() // 2) - (600 // 2)
    y = parent_window.winfo_y() + (parent_window.winfo_height() // 2) - (400 // 2)
    ventana.geometry(f"600x400+{x}+{y}")
    
    # Título
    ctk.CTkLabel(
        ventana, 
        text="Seleccione el artículo que desea ver:",
        font=ctk.CTkFont(size=14, weight="bold")
    ).pack(pady=10)
    
    # Frame con scroll para la lista
    frame_lista = ctk.CTkScrollableFrame(ventana, width=550, height=250)
    frame_lista.pack(padx=10, pady=5, fill="both", expand=True)
    
    # Crear botones para cada artículo
    for articulo in articulos_data:
        referencia = articulo.get('referencia_articulo', 'N/A')
        estado = articulo.get('estado_producto', 'N/A')
        cantidad = articulo.get('cantidad_entregada', 0)
        precio = articulo.get('precio_unitario', 0.0)
        
        try:
            texto = f"{referencia} - {estado} (Cant: {cantidad}, €{float(precio):.2f})"
        except:
            texto = f"{referencia} - {estado} (Cant: {cantidad})"
        
        btn = ctk.CTkButton(
            frame_lista,
            text=texto,
            width=520,
            height=40,
            anchor="w",
            command=lambda ref=referencia: seleccionar_y_cerrar(ref)
        )
        btn.pack(pady=2, padx=5)
    
    def seleccionar_y_cerrar(referencia):
        ventana.destroy()
        callback(referencia)
    
    # Botón cancelar
    ctk.CTkButton(
        ventana,
        text="Cancelar",
        command=ventana.destroy,
        width=100
    ).pack(pady=10)
