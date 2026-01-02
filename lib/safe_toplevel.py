"""
Ventana CTkToplevel mejorada que cancela automáticamente todos los callbacks pendientes al destruirse.
Esto previene errores de "bad window path name" cuando callbacks after() intentan acceder a ventanas destruidas.
"""

import customtkinter as ctk


class SafeCTkToplevel(ctk.CTkToplevel):
    """
    Extensión de CTkToplevel que mantiene registro de callbacks after() y los cancela al destruirse.
    """
    
    def __init__(self, *args, **kwargs):
        self._after_ids = []  # Lista de IDs de callbacks programados - DEBE ser ANTES de super().__init__
        super().__init__(*args, **kwargs)
        
    def after(self, ms, func=None, *args):
        """Override de after() para registrar el ID del callback"""
        after_id = super().after(ms, func, *args)
        if after_id:
            self._after_ids.append(after_id)
        return after_id
    
    def after_idle(self, func, *args):
        """Override de after_idle() para registrar el ID del callback"""
        after_id = super().after_idle(func, *args)
        if after_id:
            self._after_ids.append(after_id)
        return after_id
    
    def after_cancel(self, after_id):
        """Override de after_cancel() para remover el ID de la lista"""
        try:
            super().after_cancel(after_id)
            if after_id in self._after_ids:
                self._after_ids.remove(after_id)
        except:
            pass
    
    def destroy(self):
        """Override de destroy() para cancelar todos los callbacks pendientes primero"""
        # Cancelar todos los callbacks programados (si existen)
        if hasattr(self, '_after_ids'):
            for after_id in self._after_ids[:]:  # Copiar lista para iterar seguro
                try:
                    super().after_cancel(after_id)
                except:
                    pass
            
            self._after_ids.clear()
        
        # Liberar grab si existe
        try:
            self.grab_release()
        except:
            pass
        
        # Destruir la ventana
        try:
            super().destroy()
        except:
            pass
