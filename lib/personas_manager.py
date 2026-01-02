"""
Módulo para gestionar las personas/usuarios del sistema
Permite cargar, guardar y gestionar las personas desde un archivo JSON
"""

import json
from pathlib import Path

class PersonasManager:
    """Clase para gestionar las personas del sistema"""
    
    def __init__(self, root_path=None):
        """
        Inicializa el gestor de personas
        
        Args:
            root_path: Ruta raíz del proyecto. Si es None, usa la ruta del script
        """
        if root_path is None:
            root_path = Path(__file__).parent.parent
        else:
            root_path = Path(root_path)
        
        self.archivo_personas = root_path / "Diccionarios" / "personas.json"
        self._asegurar_archivo_existe()
    
    def _asegurar_archivo_existe(self):
        """Crea el archivo de personas con valores por defecto si no existe"""
        if not self.archivo_personas.exists():
            # Crear directorio si no existe
            self.archivo_personas.parent.mkdir(parents=True, exist_ok=True)
            
            # Personas por defecto
            personas_default = {
                "personas": [
                    "RAQUEL",
                    "SILVIA",
                    "CARLOS",
                    "IVAN",
                    "ANDRES"
                ]
            }
            
            with open(self.archivo_personas, 'w', encoding='utf-8') as f:
                json.dump(personas_default, f, indent=2, ensure_ascii=False)
    
    def cargar_personas(self):
        """
        Carga las personas desde el archivo JSON
        
        Returns:
            list: Lista de personas
        """
        try:
            with open(self.archivo_personas, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('personas', [])
        except Exception as e:
            print(f"Error al cargar personas: {e}")
            return []
    
    def guardar_personas(self, personas):
        """
        Guarda las personas en el archivo JSON
        
        Args:
            personas (list): Lista de personas a guardar
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            data = {"personas": personas}
            with open(self.archivo_personas, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True, "Personas guardadas correctamente"
        except Exception as e:
            return False, f"Error al guardar personas: {e}"
    
    def añadir_persona(self, nueva_persona):
        """
        Añade una nueva persona a la lista
        
        Args:
            nueva_persona (str): Persona a añadir
            
        Returns:
            tuple: (success: bool, message: str)
        """
        if not nueva_persona or not nueva_persona.strip():
            return False, "El nombre no puede estar vacío"
        
        personas = self.cargar_personas()
        
        # Normalizar a mayúsculas para evitar duplicados
        nueva_persona_upper = nueva_persona.strip().upper()
        
        if nueva_persona_upper in personas:
            return False, "Esta persona ya existe"
        
        personas.append(nueva_persona_upper)
        return self.guardar_personas(personas)
    
    def eliminar_persona(self, persona):
        """
        Elimina una persona de la lista
        
        Args:
            persona (str): Persona a eliminar
            
        Returns:
            tuple: (success: bool, message: str)
        """
        personas = self.cargar_personas()
        
        if persona not in personas:
            return False, "La persona no existe"
        
        personas.remove(persona)
        return self.guardar_personas(personas)
    
    def editar_persona(self, persona_antigua, persona_nueva):
        """
        Edita una persona existente
        
        Args:
            persona_antigua (str): Persona a modificar
            persona_nueva (str): Nuevo nombre de la persona
            
        Returns:
            tuple: (success: bool, message: str)
        """
        if not persona_nueva or not persona_nueva.strip():
            return False, "El nuevo nombre no puede estar vacío"
        
        personas = self.cargar_personas()
        
        if persona_antigua not in personas:
            return False, "La persona original no existe"
        
        # Normalizar a mayúsculas
        persona_nueva_upper = persona_nueva.strip().upper()
        
        if persona_nueva_upper in personas and persona_nueva_upper != persona_antigua:
            return False, "El nuevo nombre ya existe"
        
        # Reemplazar la persona
        index = personas.index(persona_antigua)
        personas[index] = persona_nueva_upper
        
        return self.guardar_personas(personas)
    
    def mover_persona(self, persona, direccion):
        """
        Mueve una persona arriba o abajo en la lista
        
        Args:
            persona (str): Persona a mover
            direccion (str): 'arriba' o 'abajo'
            
        Returns:
            tuple: (success: bool, message: str)
        """
        personas = self.cargar_personas()
        
        if persona not in personas:
            return False, "La persona no existe"
        
        index = personas.index(persona)
        
        if direccion == 'arriba':
            if index == 0:
                return False, "La persona ya está al principio"
            # Intercambiar con el anterior
            personas[index], personas[index - 1] = personas[index - 1], personas[index]
        elif direccion == 'abajo':
            if index == len(personas) - 1:
                return False, "La persona ya está al final"
            # Intercambiar con el siguiente
            personas[index], personas[index + 1] = personas[index + 1], personas[index]
        else:
            return False, "Dirección inválida"
        
        return self.guardar_personas(personas)
