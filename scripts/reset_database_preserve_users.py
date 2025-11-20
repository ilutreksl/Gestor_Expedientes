"""
Script para limpiar la base de datos Turso y reiniciar los IDs, preservando usuarios.
Elimina todos los datos de prueba EXCEPTO los usuarios existentes.

USO:
    python scripts/reset_database_preserve_users.py

IMPORTANTE:
- Este script está diseñado para Turso Cloud Database
- Eliminará TODOS los datos EXCEPTO la tabla de usuarios
- Reiniciará los contadores de ID automáticos (excepto usuarios)
- PRESERVA todos los usuarios existentes y sus configuraciones
"""

import os
import sys
from datetime import datetime
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
    print("⚠️  ADVERTENCIA: OPERACIÓN DE LIMPIEZA (PRESERVANDO USUARIOS)")
    print("="*60)
    print("Este script va a:")
    print("  • Eliminar TODOS los datos EXCEPTO usuarios")
    print("  • Reiniciar contadores de ID automáticos (excepto usuarios)")
    print("  • Preservar todos los usuarios existentes")
    print("  • Dejar la base de datos lista para nuevo uso")
    print("\n✅ Los usuarios y sus configuraciones se mantendrán intactos")
    print("❌ Todos los expedientes RMA serán eliminados")
    
    respuesta = input("\n¿Estás seguro de que quieres continuar? (escriba 'SI' para confirmar): ")
    return respuesta.upper() == "SI"

def contar_usuarios_existentes():
    """Cuenta cuántos usuarios existen antes de la limpieza"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"⚠️  No se pudo contar usuarios: {e}")
        return 0

def limpiar_base_datos_preservando_usuarios():
    """Ejecuta la limpieza de la base de datos preservando usuarios"""
    try:
        # Contar usuarios existentes
        usuarios_count = contar_usuarios_existentes()
        print(f"\n👥 Usuarios existentes detectados: {usuarios_count}")
        
        # Conectar a la base de datos
        conn = connect_db()
        cursor = conn.cursor()
        
        print("\n🧹 Iniciando limpieza de base de datos (preservando usuarios)...")
        
        # Lista de tablas a limpiar (EXCLUYENDO usuarios)
        tablas_a_limpiar = [
            # Tablas dependientes (foreign keys)
            'rma_historial',
            'rma_detalles', 
            'rma_adjuntos',
            'tareas',
            'rma_proveedor_hist',
            'estadisticas_cliente',
            'notas_cliente',
            
            # Tablas principales (EXCEPTO usuarios)
            'rma_maestro',
            'rma_proveedor',
            'clientes'
            # NOTA: 'usuarios' intencionalmente excluida
        ]
        
        # 1. Eliminar datos de todas las tablas excepto usuarios
        print("\n📋 Eliminando datos de las tablas (preservando usuarios)...")
        for tabla in tablas_a_limpiar:
            try:
                cursor.execute(f"DELETE FROM {tabla}")
                print(f"  ✅ {tabla}: datos eliminados")
            except Exception as e:
                print(f"  ⚠️  {tabla}: {e}")
        
        # 2. Reiniciar secuencias de ID automáticos (EXCEPTO usuarios)
        print("\n🔄 Reiniciando contadores de ID automáticos (preservando usuarios)...")
        
        # Tablas con autoincrement (EXCLUYENDO usuarios)
        tablas_con_autoincrement = [
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
            # NOTA: 'usuarios' intencionalmente excluida
        ]
        
        for tabla in tablas_con_autoincrement:
            try:
                # Reiniciar el contador de autoincrement en sqlite_sequence
                cursor.execute("DELETE FROM sqlite_sequence WHERE name = ?", (tabla,))
                print(f"  ✅ {tabla}: contador ID reiniciado")
            except Exception as e:
                print(f"  ⚠️  {tabla}: {e}")
        
        # 3. Verificar que los usuarios se mantuvieron
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        usuarios_finales = cursor.fetchone()[0]
        
        # 4. Confirmar cambios
        conn.commit()
        conn.close()
        
        print("\n" + "="*60)
        print("🎉 LIMPIEZA COMPLETADA EXITOSAMENTE")
        print("="*60)
        print("✅ Datos de expedientes RMA eliminados")
        print("✅ Contadores de ID reiniciados a 1 (excepto usuarios)")
        print(f"✅ Usuarios preservados: {usuarios_finales}")
        
        if usuarios_finales != usuarios_count:
            print(f"⚠️  ADVERTENCIA: Conteo de usuarios cambió ({usuarios_count} → {usuarios_finales})")
        
        print("\n📋 Estado actual:")
        print("  • Tabla de usuarios: INTACTA")
        print("  • Expedientes RMA: ELIMINADOS")
        print("  • Contadores ID: REINICIADOS")
        print("  • Sistema: LISTO para nuevos datos")
        
    except Exception as e:
        print(f"\n❌ ERROR durante la limpieza: {e}")
        print("   Revisa la conexión a Turso y vuelve a intentar")
        return False
    
    return True

def main():
    """Función principal del script"""
    print("🗑️  SCRIPT DE LIMPIEZA (PRESERVANDO USUARIOS) - GESTOR RMA")
    print("="*60)
    print("📅 Fecha:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # Verificar que estamos usando Turso
    if not verificar_turso():
        return
    
    # Solicitar confirmación
    if not confirmar_accion():
        print("\n❌ Operación cancelada por el usuario")
        return
    
    # Ejecutar limpieza preservando usuarios
    if limpiar_base_datos_preservando_usuarios():
        print(f"\n🕒 Proceso completado: {datetime.now().strftime('%H:%M:%S')}")
    else:
        print(f"\n❌ Proceso falló: {datetime.now().strftime('%H:%M:%S')}")
        sys.exit(1)

if __name__ == "__main__":
    main()