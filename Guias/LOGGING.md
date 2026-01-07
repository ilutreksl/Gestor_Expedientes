# Sistema de Logging - Gestor de Expedientes

## 📋 Descripción

Sistema centralizado de logging que captura automáticamente:
- ✅ Todos los `print()` de la aplicación
- ✅ Excepciones no capturadas
- ✅ Errores y advertencias
- ✅ Información del usuario que ejecuta cada acción

## 📁 Ubicación de Logs

Los archivos de log se guardan en la carpeta `logs/` con el formato:
```
logs/app_YYYY-MM-DD.log
```

Ejemplo: `logs/app_2026-01-07.log`

## 📝 Formato de Registro

Cada entrada de log sigue este formato:
```
[FECHA HORA] [USUARIO] [NIVEL] [archivo:linea] mensaje
```

### Ejemplo:
```
[2026-01-07 14:30:25] [admin] [INFO] [app.py:1234] Usuario 'admin' con rol 'admin' ha iniciado sesión
[2026-01-07 14:30:27] [admin] [ERROR] [app.py:5678] Error al guardar: SQLite error...
[2026-01-07 14:31:10] [usuario1] [DEBUG] [PRINT] Guardando expediente RMA25001
```

## 🎯 Niveles de Log

- **DEBUG**: Mensajes de depuración (incluye todos los prints)
- **INFO**: Información general de operaciones
- **WARNING**: Advertencias que no detienen la ejecución
- **ERROR**: Errores capturados y manejados
- **CRITICAL**: Errores críticos y excepciones no capturadas

## 🔧 Uso en el Código

### Logging automático de prints

Todos los `print()` se capturan automáticamente. No necesitas cambiar nada:

```python
print("Guardando expediente...")  # Automáticamente registrado
```

### Logging manual

Para registrar mensajes específicos con niveles:

```python
from lib.logger_config import get_logger

logger = get_logger()

logger.debug("Mensaje de depuración")
logger.info("Operación completada")
logger.warning("Advertencia: campo vacío")
logger.error("Error al procesar")
logger.critical("Error crítico del sistema")
```

### Logging con contexto de excepción

```python
try:
    # código que puede fallar
    resultado = operacion_riesgosa()
except Exception as e:
    logger.error(f"Error en operación: {e}", exc_info=True)
```

## 👤 Usuario en Logs

El sistema registra automáticamente el usuario que ejecuta cada acción:
- Al iniciar sesión, se configura el usuario actual
- Todas las operaciones posteriores se registran con ese usuario
- Si no hay usuario logueado, aparece como "SYSTEM"

## 📦 Rotación de Archivos

Los logs se rotan automáticamente por día:
- Cada día se crea un nuevo archivo
- Los archivos antiguos se conservan para auditoría
- Recomendación: limpiar logs antiguos manualmente cada 3-6 meses

## 🔒 Seguridad

**IMPORTANTE**: Los archivos de log contienen información sensible:
- Nombres de usuarios
- Operaciones realizadas
- Posibles datos de clientes/expedientes
- Mensajes de error con contexto

**Los logs están excluidos del control de versiones (.gitignore)**

## 🛠️ Mantenimiento

### Limpieza manual de logs antiguos

```powershell
# Eliminar logs de hace más de 90 días
Get-ChildItem logs/*.log | Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-90)} | Remove-Item
```

### Búsqueda en logs

```powershell
# Buscar errores de un usuario específico
Select-String -Path "logs/*.log" -Pattern "\[usuario1\].*ERROR"

# Buscar logs de un día específico
Get-Content "logs/app_2026-01-07.log" | Select-String "ERROR"
```

## 📊 Análisis de Logs

Los logs son útiles para:
- 🔍 Depuración de errores
- 📈 Auditoría de acciones de usuarios
- 🔒 Seguridad y detección de problemas
- 📋 Cumplimiento normativo
- 🎯 Análisis de uso de la aplicación

## ⚙️ Configuración Avanzada

Para modificar el comportamiento del logging, edita `lib/logger_config.py`:

- Cambiar nivel de logging
- Modificar formato de mensajes
- Añadir handlers adicionales (email, base de datos, etc.)
- Configurar rotación de archivos por tamaño

## 🚀 Activación

El sistema de logging se activa automáticamente al iniciar la aplicación.
No requiere configuración adicional.
