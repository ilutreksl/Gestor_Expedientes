"""
Módulo para gestionar la confirmación de cierre de la aplicación.
"""

import customtkinter as ctk
from tkinter import messagebox
import logging

logger = logging.getLogger("GestorExpedientes")


def confirmar_cierre_aplicacion(parent_window):
    """
    Muestra un diálogo de confirmación antes de cerrar la aplicación.
    
    Args:
        parent_window: Ventana principal de la aplicación
        
    Returns:
        bool: True si el usuario confirma el cierre, False en caso contrario
    """
    try:
        respuesta = messagebox.askyesno(
            "Confirmar cierre",
            "¿Está seguro de que desea cerrar la aplicación?\n\nSe cerrarán todas las ventanas abiertas.",
            parent=parent_window
        )
        
        if respuesta:
            logger.info("Usuario confirmó el cierre de la aplicación")
            return True
        else:
            logger.debug("Usuario canceló el cierre de la aplicación")
            return False
            
    except Exception as e:
        logger.error(f"Error en confirmación de cierre: {e}", exc_info=True)
        # En caso de error, permitir el cierre
        return True
