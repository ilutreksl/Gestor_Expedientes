# 🚀 Migración de Adjuntos a Dropbox - Manual de Configuración

## ✅ ¿Qué se ha implementado?

He migrado completamente el sistema de adjuntos de almacenamiento local a **Dropbox Cloud Storage**. El sistema ahora funciona de manera híbrida:

- **Si Dropbox está configurado**: Los archivos se suben automáticamente a Dropbox
- **Si Dropbox NO está configurado**: Funciona como antes (almacenamiento local)

## 📋 Funcionalidades Migradas

### ✅ Completadas:
1. **Subida de archivos** → Se suben a Dropbox en lugar de carpeta local
2. **Apertura de archivos** → Se descargan temporalmente de Dropbox y se abren
3. **Eliminación de archivos** → Se eliminan tanto de la BD como de Dropbox
4. **Creación de carpetas** → Se crean automáticamente en Dropbox
5. **Base de datos** → Actualizada para registrar tipo de almacenamiento
6. **Interfaz** → Mantiene la misma interfaz, funciona transparentemente
7. **Seguridad** → Credenciales protegidas con .gitignore

### 🔧 Cambios Técnicos:
- **Nueva librería instalada**: `dropbox`
- **Funciones híbridas**: Detectan automáticamente si usar Dropbox o local
- **Gestión de errores**: Fallback automático a almacenamiento local si Dropbox falla
- **Archivos temporales**: Para abrir archivos de Dropbox se descargan temporalmente

## 🛠️ CONFIGURACIÓN PASO A PASO

### Paso 1: Crear App en Dropbox

1. Ve a https://www.dropbox.com/developers/apps
2. Haz clic en **"Create app"**
3. Selecciona:
   - **API**: Dropbox API
   - **Type**: Scoped access
   - **Access**: Full Dropbox
   - **Name**: `gestor-expedientes-adjuntos` (o el nombre que prefieras)
4. Haz clic en **"Create app"**


### Paso 2: Configurar Permisos

En la página de configuración de tu app:
1. Ve a la pestaña **"Permissions"**
2. Asegúrate de que estén marcados:
   - ✅ `files.content.read`
   - ✅ `files.content.write`  
   - ✅ `files.metadata.read`
   - ✅ `files.metadata.write`
3. Guarda los cambios

### Paso 3: Generar Access Token

1. Ve a la pestaña **"Settings"**
2. En la sección **"OAuth 2"**, busca **"Generated access token"**
3. Haz clic en **"Generate"**
4. **¡IMPORTANTE!** Copia el token generado (empieza con `sl.`)

### Paso 4: Configurar el Archivo de Credenciales

1. **IMPORTANTE**: El archivo `dropbox_config.py` está protegido y NO se subirá a GitHub
2. Copia el archivo plantilla: `dropbox_config.py.example` como `dropbox_config.py`
3. Abre el archivo `dropbox_config.py` (ya creado)
4. Reemplaza las credenciales:

```python
# Credenciales de Dropbox (completar con tus valores reales)
DROPBOX_APP_KEY = "tu_app_key_desde_settings"
DROPBOX_APP_SECRET = "tu_app_secret_desde_settings"  
DROPBOX_ACCESS_TOKEN = "sl.tu_access_token_generado"

# Configuración de rutas en Dropbox
DROPBOX_ROOT_FOLDER = "/Adjuntos_RMA"  # Esta carpeta se creará automáticamente
```

### 🔒 Seguridad de Credenciales

✅ **Protegido**: `dropbox_config.py` está en `.gitignore` - NO se subirá a GitHub  
✅ **Plantilla disponible**: `dropbox_config.py.example` muestra qué configurar  
✅ **Instrucciones claras**: Todo el proceso documentado paso a paso

### Paso 5: Probar la Configuración

1. Ejecuta la aplicación normalmente
2. Abre cualquier expediente RMA
3. Ve a la pestaña **"📎 Adjuntos"**
4. Intenta subir un archivo
5. Si funciona correctamente, verás: **"Archivo adjuntado correctamente"**
6. El archivo debería aparecer en tu Dropbox en `/Adjuntos_RMA/RMA25XXX/`

## 🔍 Verificación

### Indicadores de que funciona:
- ✅ Al subir archivo aparece mensaje de éxito
- ✅ En tu Dropbox aparece la carpeta `/Adjuntos_RMA/`
- ✅ Dentro hay subcarpetas por cada RMA (ej: `/Adjuntos_RMA/RMA25007/`)
- ✅ Los archivos se pueden abrir desde la aplicación
- ✅ Al hacer clic en "Abrir" se descarga y abre el archivo

### Si algo no funciona:
- ❌ Revisa que las credenciales sean correctas en `dropbox_config.py`
- ❌ Verifica que el access token no haya expirado
- ❌ Asegúrate de que los permisos estén bien configurados
- ❌ Revisa la consola por mensajes de error

## 📁 Estructura en Dropbox

```
📁 Tu Dropbox
└── 📁 Adjuntos_RMA/          (Carpeta raíz)
    ├── 📁 RMA25007/          (Por cada expediente)
    │   ├── 📄 documento1.pdf
    │   └── 📄 imagen1.jpg
    ├── 📁 RMA25008/
    │   └── 📄 factura.pdf
    └── 📁 RMA25009/
        ├── 📄 manual.doc
        └── 📄 foto.png
```

## ⚠️ IMPORTANTE

1. **Seguridad**: El archivo `dropbox_config.py` contiene credenciales sensibles. No lo compartas públicamente.

2. **Backup**: Los archivos existentes en la carpeta local `Adjuntos_RMA` NO se migrarán automáticamente. Si quieres migrarlos, puedes:
   - Subirlos manualmente a Dropbox en la estructura correcta
   - O mantener el sistema en modo híbrido

3. **Modo Híbrido**: El sistema puede trabajar con ambos:
   - Archivos nuevos → Dropbox (si configurado)
   - Archivos antiguos → Local (siguen funcionando)

## 🆘 Solución de Problemas

### Error: "No se pudo cargar dropbox_config.py"
- ✅ Asegúrate de que el archivo existe en la carpeta del proyecto
- ✅ Verifica que las credenciales estén completadas

### Error: "Error de autenticación con Dropbox"
- ✅ Revisa que el access token sea correcto
- ✅ Verifica que la app tenga los permisos necesarios

### Error: "No se pudo subir el archivo a Dropbox"
- ✅ Verifica tu conexión a internet
- ✅ Asegúrate de que tienes espacio en Dropbox
- ✅ El sistema automáticamente usará almacenamiento local como fallback

## 🎉 ¡Listo!

Una vez configurado, tu sistema de adjuntos estará completamente integrado con Dropbox. Los usuarios podrán:

- ✅ Subir archivos que se guardan automáticamente en Dropbox
- ✅ Abrir archivos que se descargan temporalmente
- ✅ Eliminar archivos tanto de la BD como de Dropbox
- ✅ Continuar usando la misma interfaz sin cambios

**¡El sistema está listo para usar con Dropbox! 🚀**