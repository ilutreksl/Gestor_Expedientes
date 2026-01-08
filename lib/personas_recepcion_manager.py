"""
Módulo para gestionar las personas de recepción del sistema
Permite cargar, guardar y gestionar las personas de recepción desde un archivo JSON
"""

import json
from pathlib import Path
from lib.logger_config import get_logger

logger = get_logger()


class PersonasRecepcionManager:
    """Clase para gestionar las personas de recepción del sistema"""
    
    def __init__(self, root_path=None):
        """
        Inicializa el gestor de personas de recepción
        
        Args:
            root_path: Ruta raíz del proyecto. Si es None, usa la ruta del script
        """
        if root_path is None:
            root_path = Path(__file__).parent.parent
        else:
            root_path = Path(root_path)
        
        self.archivo_personas = root_path / "Diccionarios" / "personas_recepcion.json"
        self._asegurar_archivo_existe()
        logger.info("PersonasRecepcionManager inicializado")
    
    def _asegurar_archivo_existe(self):
        """Crea el archivo de personas de recepción con valores por defecto si no existe"""
        if not self.archivo_personas.exists():
            # Crear directorio si no existe
            self.archivo_personas.parent.mkdir(parents=True, exist_ok=True)
            
            # Personas por defecto
            personas_default = {
                "personas_recepcion": [
                    "RAQUEL",
                    "SILVIA",
                    "CARLOS",
                    "IVAN",
                    "ANDRES",
                    "JOSE ANTONIO",
                    "JUANVI",
                    "JOSE LUIS"
                ]
            }
            
            with open(self.archivo_personas, 'w', encoding='utf-8') as f:
                json.dump(personas_default, f, indent=2, ensure_ascii=False)
            logger.info("Archivo personas_recepcion.json creado con valores por defecto")
    
    def cargar_personas(self):
        """
        Carga las personas de recepción desde el archivo JSON
        
        Returns:
            list: Lista de personas de recepción
        """
        try:
            with open(self.archivo_personas, 'r', encoding='utf-8') as f:
                data = json.load(f)
                personas = data.get('personas_recepcion', [])
                logger.debug(f"Cargadas {len(personas)} personas de recepción")
                return personas
        except Exception as e:
            logger.error(f"Error al cargar personas de recepción: {e}")
            return []
    
    def guardar_personas(self, personas):
        """
        Guarda las personas de recepción en el archivo JSON
        
        Args:
            personas (list): Lista de personas a guardar
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            data = {"personas_recepcion": personas}
            with open(self.archivo_personas, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Guardadas {len(personas)} personas de recepción")
            return True, "Personas de recepción guardadas correctamente"
        except Exception as e:
            logger.error(f"Error al guardar personas de recepción: {e}")
            return False, f"Error al guardar personas de recepción: {e}"
    
    def añadir_persona(self, nueva_persona):
        """
        Añade una nueva persona de recepción a la lista
        
        Args:
            nueva_persona (str): Persona a añadir
            
        Returns:
            tuple: (success: bool, message: str)
        """
        if not nueva_persona or not nueva_persona.strip():
            logger.warning("Intento de añadir persona de recepción vacía")
            return False, "El nombre no puede estar vacío"
        
        personas = self.cargar_personas()
        
        # Normalizar a mayúsculas para evitar duplicados
        nueva_persona_upper = nueva_persona.strip().upper()
        
        if nueva_persona_upper in personas:
            logger.warning(f"Intento de añadir persona de recepción duplicada: {nueva_persona_upper}")
            return False, "Esta persona ya existe"
        
        personas.append(nueva_persona_upper)
        success, message = self.guardar_personas(personas)
        
        if success:
            logger.info(f"Persona de recepción añadida: {nueva_persona_upper}")
        
        return success, message
    
    def eliminar_persona(self, persona):
        """
        Elimina una persona de recepción de la lista
        
        Args:
            persona (str): Persona a eliminar
            
        Returns:
            tuple: (success: bool, message: str)
        """
        personas = self.cargar_personas()
        
        if persona not in personas:
            logger.warning(f"Intento de eliminar persona de recepción inexistente: {persona}")
            return False, "La persona no existe en la lista"
        
        personas.remove(persona)
        success, message = self.guardar_personas(personas)
        
        if success:
            logger.info(f"Persona de recepción eliminada: {persona}")
        
        return success, message
    
    def editar_persona(self, persona_antigua, persona_nueva):
        """
        Edita el nombre de una persona de recepción
        
        Args:
            persona_antigua (str): Nombre actual
            persona_nueva (str): Nombre nuevo
            
        Returns:
            tuple: (success: bool, message: str)
        """
        if not persona_nueva or not persona_nueva.strip():
            logger.warning("Intento de editar persona de recepción con nombre vacío")
            return False, "El nombre no puede estar vacío"
        
        personas = self.cargar_personas()
        
        if persona_antigua not in personas:
            logger.warning(f"Intento de editar persona de recepción inexistente: {persona_antigua}")
            return False, "La persona original no existe"
        
        # Normalizar a mayúsculas
        persona_nueva_upper = persona_nueva.strip().upper()
        
        # Verificar si el nuevo nombre ya existe (y no es el mismo)
        if persona_nueva_upper in personas and persona_nueva_upper != persona_antigua:
            logger.warning(f"Intento de editar a persona de recepción duplicada: {persona_nueva_upper}")
            return False, "Ya existe una persona con ese nombre"
        
        # Reemplazar
        index = personas.index(persona_antigua)
        personas[index] = persona_nueva_upper
        
        success, message = self.guardar_personas(personas)
        
        if success:
            logger.info(f"Persona de recepción editada: {persona_antigua} → {persona_nueva_upper}")
        
        return success, message
