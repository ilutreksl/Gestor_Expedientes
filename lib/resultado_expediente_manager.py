"""
Gestor para la lista de resultados de expedientes.
Permite cargar, guardar y manipular la lista de resultados desde un archivo JSON.
"""

import json
from pathlib import Path


class ResultadoExpedienteManager:
    """Gestor para manejar los resultados de expedientes desde un archivo JSON"""
    
    def __init__(self, json_path=None):
        """
        Inicializa el gestor de resultados de expedientes
        
        Args:
            json_path: Ruta al archivo JSON. Si no se proporciona, usa la ruta por defecto.
        """
        if json_path is None:
            # Ruta por defecto: carpeta Diccionarios en el directorio raíz del proyecto
            base_dir = Path(__file__).parent.parent
            json_path = base_dir / "Diccionarios" / "resultado_expediente.json"
        
        self.json_path = Path(json_path)
        self._asegurar_archivo_existe()
    
    def _asegurar_archivo_existe(self):
        """Crea el archivo JSON con valores por defecto si no existe"""
        if not self.json_path.exists():
            # Crear directorio si no existe
            self.json_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Valores por defecto
            datos_defecto = {
                "resultados": [
                    "",
                    "ABONAR",
                    "NO ABONAR",
                    "REPOSICION"
                ]
            }
            
            self.guardar_resultados(datos_defecto["resultados"])
    
    def cargar_resultados(self):
        """
        Carga la lista de resultados desde el archivo JSON
        
        Returns:
            list: Lista de resultados de expedientes
        """
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                datos = json.load(f)
                return datos.get("resultados", [])
        except Exception as e:
            print(f"Error al cargar resultados: {e}")
            return ["", "ABONAR", "NO ABONAR", "REPOSICION"]
    
    def guardar_resultados(self, resultados):
        """
        Guarda la lista de resultados en el archivo JSON
        
        Args:
            resultados: Lista de resultados de expedientes
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            datos = {"resultados": resultados}
            
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(datos, f, ensure_ascii=False, indent=4)
            
            return True, "Resultados guardados correctamente"
        except Exception as e:
            return False, f"Error al guardar resultados: {e}"
    
    def añadir_resultado(self, nuevo_resultado):
        """
        Añade un nuevo resultado a la lista
        
        Args:
            nuevo_resultado: Resultado a añadir
            
        Returns:
            tuple: (success: bool, message: str)
        """
        nuevo_resultado = nuevo_resultado.strip().upper()
        
        if not nuevo_resultado:
            return False, "El resultado no puede estar vacío (use espacio para resultado en blanco)"
        
        resultados = self.cargar_resultados()
        
        # Verificar si ya existe
        if nuevo_resultado in resultados:
            return False, f"El resultado '{nuevo_resultado}' ya existe en la lista"
        
        resultados.append(nuevo_resultado)
        success, msg = self.guardar_resultados(resultados)
        
        if success:
            return True, f"Resultado '{nuevo_resultado}' añadido correctamente"
        else:
            return False, msg
    
    def eliminar_resultado(self, resultado):
        """
        Elimina un resultado de la lista
        
        Args:
            resultado: Resultado a eliminar
            
        Returns:
            tuple: (success: bool, message: str)
        """
        resultados = self.cargar_resultados()
        
        if resultado not in resultados:
            return False, f"El resultado '{resultado}' no existe en la lista"
        
        resultados.remove(resultado)
        success, msg = self.guardar_resultados(resultados)
        
        if success:
            return True, f"Resultado '{resultado}' eliminado correctamente"
        else:
            return False, msg
    
    def editar_resultado(self, resultado_actual, nuevo_resultado):
        """
        Edita un resultado existente
        
        Args:
            resultado_actual: Resultado a editar
            nuevo_resultado: Nuevo valor del resultado
            
        Returns:
            tuple: (success: bool, message: str)
        """
        nuevo_resultado = nuevo_resultado.strip().upper()
        
        if not nuevo_resultado:
            return False, "El resultado no puede estar vacío"
        
        resultados = self.cargar_resultados()
        
        if resultado_actual not in resultados:
            return False, f"El resultado '{resultado_actual}' no existe en la lista"
        
        # Verificar si el nuevo resultado ya existe (y no es el mismo)
        if nuevo_resultado != resultado_actual and nuevo_resultado in resultados:
            return False, f"El resultado '{nuevo_resultado}' ya existe en la lista"
        
        # Reemplazar el resultado
        indice = resultados.index(resultado_actual)
        resultados[indice] = nuevo_resultado
        
        success, msg = self.guardar_resultados(resultados)
        
        if success:
            return True, f"Resultado actualizado de '{resultado_actual}' a '{nuevo_resultado}'"
        else:
            return False, msg
    
    def mover_resultado(self, resultado, direccion):
        """
        Mueve un resultado hacia arriba o abajo en la lista
        
        Args:
            resultado: Resultado a mover
            direccion: 'arriba' o 'abajo'
            
        Returns:
            tuple: (success: bool, message: str)
        """
        resultados = self.cargar_resultados()
        
        if resultado not in resultados:
            return False, f"El resultado '{resultado}' no existe en la lista"
        
        indice = resultados.index(resultado)
        
        if direccion == "arriba":
            if indice == 0:
                return False, "El resultado ya está en la primera posición"
            resultados[indice], resultados[indice - 1] = resultados[indice - 1], resultados[indice]
        elif direccion == "abajo":
            if indice == len(resultados) - 1:
                return False, "El resultado ya está en la última posición"
            resultados[indice], resultados[indice + 1] = resultados[indice + 1], resultados[indice]
        else:
            return False, "Dirección inválida. Use 'arriba' o 'abajo'"
        
        success, msg = self.guardar_resultados(resultados)
        
        if success:
            return True, "Resultado movido correctamente"
        else:
            return False, msg
