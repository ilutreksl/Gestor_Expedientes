"""
Utilidades para procesamiento de videos.
Compresión inteligente usando FFmpeg.
"""

import os
import subprocess
import tempfile
import shutil


def obtener_ruta_ffmpeg():
    """
    Obtiene la ruta al ejecutable de FFmpeg.
    Busca primero en la carpeta de la aplicación (bin/ffmpeg/ffmpeg.exe),
    luego en el PATH del sistema.
    
    Returns: Ruta al ejecutable de FFmpeg o 'ffmpeg' si está en PATH, o None si no se encuentra.
    """
    # 1. Buscar en la carpeta de la aplicación
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Subir dos niveles desde lib/
    ffmpeg_local = os.path.join(script_dir, 'bin', 'ffmpeg', 'ffmpeg.exe')
    
    if os.path.exists(ffmpeg_local):
        return ffmpeg_local
    
    # 2. Buscar en el PATH del sistema
    try:
        resultado = subprocess.run(
            ['ffmpeg', '-version'], 
            capture_output=True, 
            text=True,
            timeout=5
        )
        if resultado.returncode == 0:
            return 'ffmpeg'
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    return None


def verificar_ffmpeg():
    """
    Verifica si FFmpeg está disponible.
    Returns: True si FFmpeg está disponible, False en caso contrario.
    """
    return obtener_ruta_ffmpeg() is not None


def obtener_duracion_video(filepath, ffmpeg_path):
    """
    Obtiene la duración del video en segundos usando FFprobe.
    Returns: duración en segundos (float) o None si hay error.
    """
    try:
        # Si ffmpeg_path es una ruta completa, obtener ffprobe del mismo directorio
        if os.path.isfile(ffmpeg_path):
            ffprobe_path = os.path.join(os.path.dirname(ffmpeg_path), 'ffprobe.exe')
            if not os.path.exists(ffprobe_path):
                ffprobe_path = 'ffprobe'  # Fallback al PATH
        else:
            ffprobe_path = 'ffprobe'
        
        comando = [
            ffprobe_path,
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            filepath
        ]
        resultado = subprocess.run(comando, capture_output=True, text=True, timeout=10)
        if resultado.returncode == 0:
            return float(resultado.stdout.strip())
    except:
        pass
    return None


def comprimir_video_inteligente(filepath_original, callback_progreso=None):
    """
    Comprime un video siguiendo una estrategia inteligente similar a imágenes:
    - Si > 50MB: Comprimir a H.264 CRF 28, resolución máx 1920x1080, 30fps
    - Si > 20MB: Comprimir a H.264 CRF 23, resolución máx 1920x1080, mantener fps
    - Si < 20MB: No modificar
    
    Args:
        filepath_original: Ruta del video original
        callback_progreso: Función callback(mensaje: str) para reportar progreso
    
    Returns: 
        ffmpeg_path = obtener_ruta_ffmpeg()
        if not ffmpeg_pathaño_original_mb, tamaño_final_mb) 
        o (None, 0, 0) si hay error
    """
    try:
        if callback_progreso:
            callback_progreso("🔍 Analizando video...")
        
        # Verificar que FFmpeg esté disponible
        if not verificar_ffmpeg():
            if callback_progreso:
                callback_progreso("⚠️ FFmpeg no disponible - el video se subirá sin comprimir")
            tamaño_original = os.path.getsize(filepath_original)
            tamaño_original_mb = tamaño_original / (1024 * 1024)
            return filepath_original, tamaño_original_mb, tamaño_original_mb
        
        # Obtener tamaño original
        tamaño_original = os.path.getsize(filepath_original)
        tamaño_original_mb = tamaño_original / (1024 * 1024)
        
        # Si es muy pequeño, no comprimir
        if tamaño_original < 20 * 1024 * 1024:  # 20MB
            if callback_progreso:
                callback_progreso(f"✅ Video pequeño ({tamaño_original_mb:.1f}MB), no necesita compresión")
            return filepath_original, tamaño_original_mb, tamaño_original_mb
        
        if callback_progreso:
            callback_progreso(f"📏 Video {tamaño_original_mb:.1f}MB - iniciando compresión...")
        
        # Obtener duración para calcular progreso, ffmpeg_path
        duracion = obtener_duracion_video(filepath_original)
        
        # Determinar parámetros de compresión según tamaño
        if tamaño_original > 50 * 1024 * 1024:  # > 50MB
            # Compresión agresiva
            crf = '28'
            fps_max = '30'
            escala = 'scale=1920:1080:force_original_aspect_ratio=decrease'
            if callback_progreso:
                callback_progreso("🎯 Compresión agresiva: CRF 28, 1080p, 30fps máx")
        else:
            # Compresión moderada
            crf = '23'
            fps_max = None  # Mantener fps original
            escala = 'scale=1920:1080:force_original_aspect_ratio=decrease'
            if callback_progreso:
                callback_progreso("🔧 Compresión moderada: CRF 23, 1080p")
        
        # Crear archivo temporal para el video comprimido
        temp_fd, temp_path = tempfile.mkstemp(suffix='.mp4')
        os.close(temp_fd)
        
        # Construir comando FFmpeg
        comando = [
            ffmpeg_path,
            '-i', filepath_original,
            '-c:v', 'libx264',           # Codec H.264
            '-crf', crf,                  # Factor de calidad
            '-preset', 'medium',          # Balance velocidad/calidad
            '-vf', escala,                # Escalar a máx 1080p
            '-c:a', 'aac',                # Codec audio AAC
            '-b:a', '128k',               # Bitrate audio 128kbps
            '-movflags', '+faststart',    # Optimizar para streaming
            '-y',                         # Sobrescribir sin preguntar
        ]
        
        # Añadir limitación de fps si es necesario
        if fps_max:
            comando.extend(['-r', fps_max])
        
        comando.append(temp_path)
        
        if callback_progreso:
            callback_progreso("⚙️ Procesando video con FFmpeg...")
        
        # Ejecutar FFmpeg
        proceso = subprocess.Popen(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Monitorear progreso leyendo stderr de FFmpeg
        ultima_actualizacion = 0
        for linea in proceso.stderr:
            # FFmpeg reporta progreso en stderr con formato "time=HH:MM:SS.MS"
            if 'time=' in linea and duracion:
                try:
                    # Extraer tiempo actual
                    time_str = linea.split('time=')[1].split()[0]
                    h, m, s = time_str.split(':')
                    tiempo_actual = int(h) * 3600 + int(m) * 60 + float(s)
                    progreso = (tiempo_actual / duracion) * 100
                    
                    # Actualizar cada 10% para no saturar
                    if progreso - ultima_actualizacion >= 10:
                        ultima_actualizacion = int(progreso)
                        if callback_progreso:
                            callback_progreso(f"⏳ Procesando: {int(progreso)}%")
                except:
                    pass
        
        # Esperar a que termine
        proceso.wait()
        
        if proceso.returncode != 0:
            # Error en FFmpeg
            if callback_progreso:
                callback_progreso("❌ Error al comprimir video")
            try:
                os.unlink(temp_path)
            except:
                pass
            return None, 0, 0
        
        # Verificar resultado
        tamaño_final = os.path.getsize(temp_path)
        tamaño_final_mb = tamaño_final / (1024 * 1024)
        
        # Si el archivo comprimido es más grande que el original, usar el original
        if tamaño_final >= tamaño_original:
            if callback_progreso:
                callback_progreso(f"ℹ️ Video optimizado es igual de grande - usando original")
            try:
                os.unlink(temp_path)
            except:
                pass
            return filepath_original, tamaño_original_mb, tamaño_original_mb
        
        reduccion = ((tamaño_original - tamaño_final) / tamaño_original) * 100
        
        if callback_progreso:
            callback_progreso(f"✅ Compresión completada: {tamaño_original_mb:.1f}MB → {tamaño_final_mb:.1f}MB ({reduccion:.1f}% reducción)")
        
        return temp_path, tamaño_original_mb, tamaño_final_mb
        
    except Exception as e:
        if callback_progreso:
            callback_progreso(f"❌ Error en compresión: {e}")
        return None, 0, 0
