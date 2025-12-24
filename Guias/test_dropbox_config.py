#!/usr/bin/env python3
"""
Script de prueba para verificar la configuración de Dropbox.
Ejecuta este script para verificar que las credenciales estén correctamente configuradas.
"""

import sys
import os

# Añadir el directorio actual al path para poder importar los módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_dropbox_config():
    """Prueba la configuración de Dropbox."""
    print("🔧 Verificando configuración de Dropbox...")
    print("=" * 50)
    
    # Test 1: Importar configuración
    try:
        from dropbox_config import DROPBOX_ACCESS_TOKEN, DROPBOX_ROOT_FOLDER
        print("✅ Archivo de configuración encontrado")
        print(f"   - Carpeta raíz: {DROPBOX_ROOT_FOLDER}")
        
        if DROPBOX_ACCESS_TOKEN and DROPBOX_ACCESS_TOKEN != "tu_access_token_aqui":
            print("✅ Access token configurado")
            # Mostrar solo los primeros y últimos caracteres por seguridad
            token_preview = f"{DROPBOX_ACCESS_TOKEN[:10]}...{DROPBOX_ACCESS_TOKEN[-10:]}"
            print(f"   - Token: {token_preview}")
        else:
            print("❌ Access token NO configurado")
            print("   - Edita dropbox_config.py y añade tu token real")
            return False
            
    except ImportError as e:
        print("❌ Error importando configuración de Dropbox:")
        print(f"   - {e}")
        print("   - Asegúrate de que dropbox_config.py existe y esté configurado")
        return False
    
    # Test 2: Importar librería dropbox
    try:
        import dropbox
        print("✅ Librería dropbox instalada")
    except ImportError:
        print("❌ Librería dropbox NO instalada")
        print("   - Ejecuta: pip install dropbox")
        return False
    
    # Test 3: Crear cliente y probar conexión
    try:
        from dropbox.exceptions import ApiError, AuthError
        
        dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
        account = dbx.users_get_current_account()
        
        print("✅ Conexión con Dropbox exitosa")
        print(f"   - Usuario: {account.name.display_name}")
        print(f"   - Email: {account.email}")
        
    except AuthError as e:
        print("❌ Error de autenticación:")
        print(f"   - {e}")
        print("   - Verifica que el access token sea correcto")
        print("   - Asegúrate de que la app tenga permisos suficientes")
        return False
        
    except Exception as e:
        print("❌ Error conectando con Dropbox:")
        print(f"   - {e}")
        print("   - Verifica tu conexión a internet")
        return False
    
    # Test 4: Probar creación de carpeta
    try:
        carpeta_test = f"{DROPBOX_ROOT_FOLDER}/TEST_CONEXION"
        
        # Intentar crear carpeta de prueba
        try:
            dbx.files_create_folder_v2(carpeta_test)
            print("✅ Carpeta de prueba creada")
        except ApiError as e:
            if e.error.is_path_conflict():
                print("✅ Carpeta de prueba ya existe (normal)")
            else:
                raise e
        
        # Intentar eliminar carpeta de prueba
        try:
            dbx.files_delete_v2(carpeta_test)
            print("✅ Carpeta de prueba eliminada")
        except ApiError:
            print("ℹ️  No se pudo eliminar carpeta de prueba (puede que no estuviera vacía)")
            
    except Exception as e:
        print("⚠️  Error probando operaciones de carpeta:")
        print(f"   - {e}")
        print("   - La conexión básica funciona, pero puede haber problemas de permisos")
    
    print("\n" + "=" * 50)
    print("🎉 ¡Configuración de Dropbox CORRECTA!")
    print("   - El sistema de adjuntos usará Dropbox automáticamente")
    print("   - Los archivos se guardarán en tu Dropbox")
    print("   - Puedes probar subiendo un adjunto en cualquier expediente")
    
    return True

if __name__ == "__main__":
    print("🧪 SCRIPT DE PRUEBA - CONFIGURACIÓN DROPBOX")
    print("Este script verificará si Dropbox está correctamente configurado.\n")
    
    try:
        success = test_dropbox_config()
        
        if success:
            print("\n✅ TODAS LAS PRUEBAS PASARON")
            print("Tu sistema está listo para usar Dropbox! 🚀")
        else:
            print("\n❌ ALGUNAS PRUEBAS FALLARON")
            print("Revisa los errores anteriores y corrige la configuración.")
            print("Consulta DROPBOX_MIGRATION_GUIDE.md para más detalles.")
            
    except KeyboardInterrupt:
        print("\n⚠️ Prueba interrumpida por el usuario")
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")
        print("Consulta DROPBOX_MIGRATION_GUIDE.md para ayuda.")
    
    input("\nPresiona Enter para cerrar...")