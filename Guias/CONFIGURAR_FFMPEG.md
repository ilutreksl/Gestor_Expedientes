# Configurar FFmpeg para Compresión de Videos

## ¿Qué hace?
Permite comprimir automáticamente los videos antes de adjuntarlos a los expedientes, reduciendo su tamaño sin perder mucha calidad.

## Opción 1: FFmpeg Portable (RECOMENDADO) ✅
**No requiere instalación para cada usuario**

### Pasos:

1. **Descargar FFmpeg:**
   - Ve a: https://www.gyan.dev/ffmpeg/builds/
   - Descarga: `ffmpeg-release-essentials.zip` (versión más ligera, ~80MB)
   
2. **Extraer archivos:**
   - Abre el ZIP descargado
   - Dentro verás una carpeta `ffmpeg-X.X.X-essentials_build`
   - Entra en esa carpeta y luego en `bin/`
   - Encontrarás 3 archivos: `ffmpeg.exe`, `ffprobe.exe`, `ffplay.exe`

3. **Copiar a tu aplicación:**
   ```
   Gestor_Expedientes/
   ├── app.py
   ├── lib/
   └── bin/                    ← Crear esta carpeta
       └── ffmpeg/             ← Crear esta carpeta
           ├── ffmpeg.exe      ← Copiar aquí
           ├── ffprobe.exe     ← Copiar aquí
           └── ffplay.exe      ← Copiar aquí (opcional)
   ```

4. **¡Listo!** 
   - La aplicación detectará automáticamente FFmpeg en `bin/ffmpeg/`
   - Funciona para todos los usuarios sin instalación adicional
   - Solo distribuyes la carpeta completa con tu aplicación

## Opción 2: Sin FFmpeg
Si no configuras FFmpeg:
- ✅ La aplicación seguirá funcionando normalmente
- ⚠️ Los videos se subirán sin comprimir (ocuparán más espacio)
- 📝 Verás un mensaje: "FFmpeg no disponible - el video se subirá sin comprimir"

## ¿Cuánto espacio ocupa?
- FFmpeg portable: ~80-100 MB
- Ahorro promedio por video: 50-70% del tamaño original

## Prueba si funciona
Después de configurar, adjunta un video a un expediente. Deberías ver:
- Ventana "🎬 Optimizando video"
- Progreso en porcentaje
- Mensaje final con la reducción de tamaño

## Licencia
FFmpeg es software libre bajo licencias LGPL/GPL. Es legal redistribuirlo con tu aplicación.
