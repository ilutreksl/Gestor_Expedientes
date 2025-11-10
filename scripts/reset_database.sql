-- ========================================================
-- SCRIPT SQL PARA LIMPIAR BASE DE DATOS TURSO
-- Gestor de Expedientes RMA - ILUTREK S.L.
-- ========================================================
-- 
-- PROPÓSITO: Eliminar todos los datos de prueba y reiniciar 
--           los IDs automáticos para uso en producción
--
-- USO: Ejecutar directamente en la consola de Turso o 
--      a través de turso db shell
--
-- ⚠️  ADVERTENCIA: Esta operación eliminará TODOS los datos
--     y NO se puede deshacer
-- ========================================================

-- Mostrar información inicial
.echo on
.headers on

-- ========================================================
-- PASO 1: ELIMINAR TODOS LOS DATOS
-- ========================================================

-- Eliminar datos de tablas dependientes primero (foreign keys)
DELETE FROM rma_historial;
DELETE FROM rma_detalles; 
DELETE FROM rma_adjuntos;
DELETE FROM tareas;
DELETE FROM rma_proveedor_hist;
DELETE FROM estadisticas_cliente;
DELETE FROM notas_cliente;

-- Eliminar datos de tablas principales
DELETE FROM rma_maestro;
DELETE FROM rma_proveedor;
DELETE FROM clientes;
DELETE FROM usuarios;

-- ========================================================
-- PASO 2: REINICIAR CONTADORES DE ID AUTOMÁTICOS
-- ========================================================

-- Reiniciar secuencias AUTOINCREMENT en libSQL/Turso
DELETE FROM sqlite_sequence WHERE name = 'usuarios';
DELETE FROM sqlite_sequence WHERE name = 'rma_maestro';
DELETE FROM sqlite_sequence WHERE name = 'rma_detalles';
DELETE FROM sqlite_sequence WHERE name = 'rma_historial';
DELETE FROM sqlite_sequence WHERE name = 'rma_adjuntos';
DELETE FROM sqlite_sequence WHERE name = 'tareas';
DELETE FROM sqlite_sequence WHERE name = 'rma_proveedor';
DELETE FROM sqlite_sequence WHERE name = 'rma_proveedor_hist';
DELETE FROM sqlite_sequence WHERE name = 'clientes';
DELETE FROM sqlite_sequence WHERE name = 'estadisticas_cliente';
DELETE FROM sqlite_sequence WHERE name = 'notas_cliente';

-- ========================================================
-- PASO 3: CREAR USUARIO ADMINISTRADOR POR DEFECTO
-- ========================================================

-- Insertar usuario administrador con contraseña hasheada
-- Contraseña: "admin123" (CAMBIAR EN PRODUCCIÓN)
INSERT INTO usuarios (nombre_usuario, password_hash, rol) 
VALUES ('admin', '$2b$12$rQJ1VxU5XYJmhLhd5hSMHe5Nh3jYvPHNKmHtqoFyQdYpXcU8VnPZW', 'administrador');

-- ========================================================
-- VERIFICACIÓN: MOSTRAR ESTADO FINAL
-- ========================================================

-- Verificar que las tablas están vacías (excepto usuarios)
SELECT 'Usuarios restantes:' as info, COUNT(*) as total FROM usuarios;
SELECT 'RMAs restantes:' as info, COUNT(*) as total FROM rma_maestro;
SELECT 'Detalles restantes:' as info, COUNT(*) as total FROM rma_detalles;
SELECT 'Historial restante:' as info, COUNT(*) as total FROM rma_historial;
SELECT 'Adjuntos restantes:' as info, COUNT(*) as total FROM rma_adjuntos;
SELECT 'Tareas restantes:' as info, COUNT(*) as total FROM tareas;
SELECT 'Proveedores restantes:' as info, COUNT(*) as total FROM rma_proveedor;
SELECT 'Clientes restantes:' as info, COUNT(*) as total FROM clientes;
SELECT 'Estadísticas cliente restantes:' as info, COUNT(*) as total FROM estadisticas_cliente;
SELECT 'Notas cliente restantes:' as info, COUNT(*) as total FROM notas_cliente;

-- Verificar que los IDs se reiniciaron
SELECT 'Próximo ID usuarios:' as info, COALESCE(MAX(seq), 0) + 1 as next_id 
FROM sqlite_sequence WHERE name = 'usuarios';

SELECT 'Próximo ID RMA:' as info, COALESCE(MAX(seq), 0) + 1 as next_id 
FROM sqlite_sequence WHERE name = 'rma_maestro';

-- ========================================================
-- RESULTADO ESPERADO
-- ========================================================
-- ✅ Todas las tablas vacías excepto 1 usuario administrador
-- ✅ Contadores de ID reiniciados a 1
-- ✅ Base de datos lista para producción
-- 
-- PRÓXIMOS PASOS:
-- 1. Cambiar contraseña del usuario 'admin'
-- 2. Crear usuarios reales del equipo
-- 3. Comenzar a usar la aplicación en producción
-- ========================================================