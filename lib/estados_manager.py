"""
Módulo para gestionar los estados de artículos
Permite cargar, guardar y gestionar los estados desde un archivo JSON
"""

import json
from pathlib import Path

class EstadosArticuloManager:
    """Clase para gestionar los estados de artículos"""
    
    def __init__(self, root_path=None):
        """
        Inicializa el gestor de estados
        
        Args:
            root_path: Ruta raíz del proyecto. Si es None, usa la ruta del script
        """
        if root_path is None:
            root_path = Path(__file__).parent.parent
        else:
            root_path = Path(root_path)
        
        self.archivo_estados = root_path / "Diccionarios" / "estados_articulo.json"
        self._asegurar_archivo_existe()
    
    def _asegurar_archivo_existe(self):
        """Crea el archivo de estados con valores por defecto si no existe"""
        if not self.archivo_estados.exists():
            # Crear directorio si no existe
            self.archivo_estados.parent.mkdir(parents=True, exist_ok=True)
            
            # Estados por defecto
            estados_default = {
                "estados": [
                    "",
                    "EN PERFECTO ESTADO ; ABONAR",
                    "FUNCIONA PERFECTAMENTE ; ABONAR",
                    "SOBRANTE DE OBRA ; ABONAR",
                    "NO FUNCIONA, ABONAR",
                    "FUNCIONA PERFECTAMENTE ; NO ABONAR",
                    "NO FUNCIONA ; NO ABONAR",
                    "REPOSICION FALLO PRODUCTO",
                    "REPOSICION ; ABONAR",
                    "MERCANCIA ENVIADA POR ERROR",
                    "MALA MANIPULACION ; NO ABONAR",
                    "EN PERFECTO ESTADO ; ABONAR 10% DEPRECIACION",
                    "FALLO SOLDADURA ; ABONAR",
                    "FALLO SOLDADURA ; NO ABONAR",
                    "FALLO MODULO ; ABONAR",
                    "MAL MANIPULACION ; ABONAR",
                    "DANA",
                    "CAMBIO DE PRODUCTO"
                ]
            }
            
            with open(self.archivo_estados, 'w', encoding='utf-8') as f:
                json.dump(estados_default, f, indent=2, ensure_ascii=False)
    
    def cargar_estados(self):
        """
        Carga los estados desde el archivo JSON
        
        Returns:
            list: Lista de estados
        """
        try:
            with open(self.archivo_estados, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('estados', [])
        except Exception as e:
            print(f"Error al cargar estados: {e}")
            return [""]  # Estado vacío por defecto
    
    def guardar_estados(self, estados):
        """
        Guarda los estados en el archivo JSON
        
        Args:
            estados (list): Lista de estados a guardar
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            data = {"estados": estados}
            with open(self.archivo_estados, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True, "Estados guardados correctamente"
        except Exception as e:
            return False, f"Error al guardar estados: {e}"
    
    def añadir_estado(self, nuevo_estado):
        """
        Añade un nuevo estado a la lista
        
        Args:
            nuevo_estado (str): Estado a añadir
            
        Returns:
            tuple: (success: bool, message: str)
        """
        if not nuevo_estado or not nuevo_estado.strip():
            return False, "El estado no puede estar vacío"
        
        estados = self.cargar_estados()
        
        if nuevo_estado in estados:
            return False, "Este estado ya existe"
        
        estados.append(nuevo_estado)
        return self.guardar_estados(estados)
    
    def eliminar_estado(self, estado):
        """
        Elimina un estado de la lista
        
        Args:
            estado (str): Estado a eliminar
            
        Returns:
            tuple: (success: bool, message: str)
        """
        estados = self.cargar_estados()
        
        if estado not in estados:
            return False, "El estado no existe"
        
        estados.remove(estado)
        return self.guardar_estados(estados)
    
    def editar_estado(self, estado_antiguo, estado_nuevo):
        """
        Edita un estado existente
        
        Args:
            estado_antiguo (str): Estado a modificar
            estado_nuevo (str): Nuevo valor del estado
            
        Returns:
            tuple: (success: bool, message: str)
        """
        if not estado_nuevo or not estado_nuevo.strip():
            return False, "El nuevo estado no puede estar vacío"
        
        estados = self.cargar_estados()
        
        if estado_antiguo not in estados:
            return False, "El estado original no existe"
        
        if estado_nuevo in estados and estado_nuevo != estado_antiguo:
            return False, "El nuevo estado ya existe"
        
        # Reemplazar el estado
        index = estados.index(estado_antiguo)
        estados[index] = estado_nuevo
        
        return self.guardar_estados(estados)
    
    def mover_estado(self, estado, direccion):
        """
        Mueve un estado arriba o abajo en la lista
        
        Args:
            estado (str): Estado a mover
            direccion (str): 'arriba' o 'abajo'
            
        Returns:
            tuple: (success: bool, message: str)
        """
        estados = self.cargar_estados()
        
        if estado not in estados:
            return False, "El estado no existe"
        
        index = estados.index(estado)
        
        if direccion == 'arriba':
            if index == 0:
                return False, "El estado ya está al principio"
            # Intercambiar con el anterior
            estados[index], estados[index - 1] = estados[index - 1], estados[index]
        elif direccion == 'abajo':
            if index == len(estados) - 1:
                return False, "El estado ya está al final"
            # Intercambiar con el siguiente
            estados[index], estados[index + 1] = estados[index + 1], estados[index]
        else:
            return False, "Dirección inválida"
        
        return self.guardar_estados(estados)
