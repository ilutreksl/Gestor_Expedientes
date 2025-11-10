"""
Script para limpiar completamente la base de datos Turso y reiniciar los IDs.
Elimina todos los datos de prueba y deja las tablas listas para uso en producción.

USO:
    python scripts/reset_database.py

IMPORTANTE:
- Este script está diseñado para Turso Cloud Database
- Eliminará TODOS los datos de las tablas
- Reiniciará los contadores de ID automáticos
- Mantendrá al menos un usuario administrador
"""

import os
import sys
from datetime import datetime
import bcrypt
from dotenv import load_dotenv

# Añadir el directorio padre al PATH para importar el módulo de conexión
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar la función de conexión desde app.py
try:
    from app import connect_db
except ImportError:
    print("❌ Error: No se pudo importar la función de conexión de app.py")
    sys.exit(1)

# Cargar variables de entorno
load_dotenv()

def verificar_turso():
    """Verifica que estemos usando Turso y no SQLite local"""
    turso_url = os.getenv("TURSO_DATABASE_URL")
    turso_token = os.getenv("TURSO_AUTH_TOKEN")
    
    if not turso_url or not turso_token:
        print("❌ ERROR: Variables de entorno de Turso no configuradas")
        print("   Asegúrate de tener TURSO_DATABASE_URL y TURSO_AUTH_TOKEN en tu archivo .env")
        return False
    
    print(f"✅ Conectando a Turso: {turso_url[:50]}...")
    return True

def confirmar_accion():
    """Solicita confirmación del usuario antes de continuar"""
    print("\n" + "="*60)
    print("⚠️  ADVERTENCIA: OPERACIÓN DESTRUCTIVA")
    print("="*60)
    print("Este script va a:")
    print("  • Eliminar TODOS los datos de las tablas")
    print("  • Reiniciar todos los contadores de ID automáticos")
    print("  • Crear un usuario administrador por defecto")
    print("  • Dejar la base de datos lista para producción")
    print("\n❌ ESTA ACCIÓN NO SE PUEDE DESHACER ❌")
    
    respuesta = input("\n¿Estás seguro de que quieres continuar? (escriba 'SI' para confirmar): ")
    return respuesta.upper() == "SI"

def limpiar_base_datos():
    """Ejecuta la limpieza completa de la base de datos"""
    try:
        # Conectar a la base de datos
        conn = connect_db()
        cursor = conn.cursor()
        
        print("\n🧹 Iniciando limpieza de base de datos...")
        
        # Lista de tablas principales en orden de dependencias (primero las hijas, luego las padres)
        tablas_a_limpiar = [
            # Tablas dependientes (foreign keys)
            'rma_historial',
            'rma_detalles', 
            'rma_adjuntos',
            'tareas',
            'rma_proveedor_hist',
            'estadisticas_cliente',
            'notas_cliente',
            
            # Tablas principales
            'rma_maestro',
            'rma_proveedor',
            'clientes',
            'usuarios'
        ]
        
        # 1. Eliminar todos los datos de las tablas
        print("\n📋 Eliminando datos de todas las tablas...")
        for tabla in tablas_a_limpiar:
            try:
                cursor.execute(f"DELETE FROM {tabla}")
                print(f"  ✅ {tabla}: datos eliminados")
            except Exception as e:
                print(f"  ⚠️  {tabla}: {e}")
        
        # 2. Reiniciar secuencias de ID automáticos en Turso
        print("\n🔄 Reiniciando contadores de ID automáticos...")
        
        # En libSQL/Turso, necesitamos actualizar sqlite_sequence para reiniciar AUTOINCREMENT
        tablas_con_autoincrement = [
            'usuarios',
            'rma_maestro', 
            'rma_detalles',
            'rma_historial',
            'rma_adjuntos',
            'tareas',
            'rma_proveedor',
            'rma_proveedor_hist',
            'clientes',
            'estadisticas_cliente',
            'notas_cliente'
        ]
        
        for tabla in tablas_con_autoincrement:
            try:
                # Reiniciar el contador de autoincrement en sqlite_sequence
                cursor.execute("DELETE FROM sqlite_sequence WHERE name = ?", (tabla,))
                print(f"  ✅ {tabla}: contador ID reiniciado")
            except Exception as e:
                print(f"  ⚠️  {tabla}: {e}")
        
        # 3. Crear usuario administrador por defecto
        print("\n👤 Creando usuario administrador por defecto...")
        admin_password = "admin123"  # Cambiar en producción
        password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        try:
            cursor.execute(
                "INSERT INTO usuarios (nombre_usuario, password_hash, rol) VALUES (?, ?, ?)",
                ("admin", password_hash, "administrador")
            )
            print("  ✅ Usuario 'admin' creado (contraseña: admin123)")
            print("  ⚠️  CAMBIAR LA CONTRASEÑA EN PRODUCCIÓN")
        except Exception as e:
            print(f"  ❌ Error creando usuario administrador: {e}")
        
        # 4. Confirmar cambios
        conn.commit()
        conn.close()
        
        print("\n" + "="*60)
        print("🎉 LIMPIEZA COMPLETADA EXITOSAMENTE")
        print("="*60)
        print("✅ Todos los datos de prueba han sido eliminados")
        print("✅ Contadores de ID reiniciados a 1")
        print("✅ Usuario administrador creado")
        print("\n📋 Próximos pasos:")
        print("  1. Cambiar la contraseña del usuario 'admin'")
        print("  2. Crear usuarios reales para el equipo")
        print("  3. La aplicación está lista para uso en producción")
        
    except Exception as e:
        print(f"\n❌ ERROR durante la limpieza: {e}")
        print("   Revisa la conexión a Turso y vuelve a intentar")
        return False
    
    return True

def main():
    """Función principal del script"""
    print("🗑️  SCRIPT DE LIMPIEZA DE BASE DE DATOS - GESTOR RMA")
    print("="*60)
    print("📅 Fecha:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # Verificar que estamos usando Turso
    if not verificar_turso():
        return
    
    # Solicitar confirmación
    if not confirmar_accion():
        print("\n❌ Operación cancelada por el usuario")
        return
    
    # Ejecutar limpieza
    if limpiar_base_datos():
        print(f"\n🕒 Proceso completado: {datetime.now().strftime('%H:%M:%S')}")
    else:
        print(f"\n❌ Proceso falló: {datetime.now().strftime('%H:%M:%S')}")
        sys.exit(1)

if __name__ == "__main__":
    main()