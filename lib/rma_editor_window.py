"""
Ventana independiente para crear/editar expedientes RMA.
REUTILIZA TODO EL CÓDIGO de app.py sin duplicación.
Usa la BD de Turso a través de VentanaPrincipal.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import datetime


class RmaEditorWindow(ctk.CTkToplevel):
    """
    Ventana independiente para crear/editar expedientes RMA.
    Reutiliza TODOS los métodos de VentanaPrincipal para garantizar funcionamiento exacto.
    """
    
    def __init__(self, parent_window, rma_id=None):
        """
        Args:
            parent_window: Instancia de VentanaPrincipal
            rma_id: ID del RMA a editar (None para crear nuevo)
        """
        super().__init__(parent_window)
        
        # Guardar referencia a la ventana principal
        self.parent_window = parent_window
        
        # Configurar ventana
        titulo = f"EDITAR EXPEDIENTE #{rma_id}" if rma_id else "CREAR NUEVO EXPEDIENTE"
        self.title(f"Gestor de Expedientes RMA - {titulo}")
        self.geometry("1400x900")
        
        # Habilitar botones de maximizar/minimizar/redimensionar
        self.resizable(True, True)
        self.attributes('-topmost', False)
        
        # NO hacer la ventana modal para permitir múltiples ventanas
        # NOTA: transient() se quita porque elimina los botones maximizar/minimizar en Windows
        # self.transient(parent_window)
        # NO usar grab_set() para permitir interacción con otras ventanas
        
        # Frame principal para el contenido de esta ventana
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.pack(fill="both", expand=True)
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        # TRUCO: Sobrescribir temporalmente el content_frame de la ventana principal
        # Guardamos el actual para restaurarlo INMEDIATAMENTE después
        saved_content_frame = parent_window.content_frame
        
        # Sobrescribir con el de esta ventana solo durante la renderización
        parent_window.content_frame = self.content_frame
        
        # Llamar al método original de la ventana principal
        # Esto ejecutará TODO el código exacto de mostrar_nuevo_rma
        parent_window.mostrar_nuevo_rma(rma_id)
        
        # IMPORTANTE: Restaurar INMEDIATAMENTE el content_frame original
        # Esto permite que otras ventanas puedan abrirse simultáneamente
        parent_window.content_frame = saved_content_frame
        
        # Configurar el cierre de ventana
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _on_closing(self):
        """Cierra la ventana y opcionalmente refresca la lista"""
        try:
            # Cerrar la ventana
            self.destroy()
            
            # Refrescar la lista de RMAs en la ventana principal
            # Esto actualizará la lista con cualquier cambio realizado
            try:
                if hasattr(self.parent_window, 'mostrar_lista_rma'):
                    # Contar cuántas ventanas de edición siguen abiertas
                    ventanas_abiertas = sum(1 for w in self.parent_window.master.winfo_children() 
                                          if isinstance(w, RmaEditorWindow) and w.winfo_exists())
                    
                    # Solo recargar si no quedan más ventanas de edición abiertas
                    if ventanas_abiertas == 0:
                        self.parent_window.after(100, self.parent_window.mostrar_lista_rma)
            except Exception as e:
                print(f"Error al programar recarga: {e}")
            
        except Exception as e:
            print(f"Error al cerrar ventana: {e}")
