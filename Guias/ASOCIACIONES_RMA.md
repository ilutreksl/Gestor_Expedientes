# Sistema de Asociación de Expedientes RMA

## 📋 Descripción

El sistema de asociación de expedientes permite vincular múltiples RMAs entre sí, facilitando la gestión de casos relacionados (mismo cliente, misma incidencia, piezas relacionadas, etc.).

## 🗂️ Estructura de Base de Datos

### Tabla: `rma_asociaciones`

```sql
CREATE TABLE rma_asociaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rma_id INTEGER NOT NULL,
    rma_asociado_id INTEGER NOT NULL,
    motivo TEXT DEFAULT '',
    fecha_asociacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usuario TEXT,
    UNIQUE(rma_id, rma_asociado_id),
    FOREIGN KEY (rma_id) REFERENCES rma_maestro(id) ON DELETE CASCADE,
    FOREIGN KEY (rma_asociado_id) REFERENCES rma_maestro(id) ON DELETE CASCADE
);

CREATE INDEX idx_rma_asociaciones_rma_id ON rma_asociaciones(rma_id);
CREATE INDEX idx_rma_asociaciones_rma_asociado_id ON rma_asociaciones(rma_asociado_id);
```

**Características:**
- **Bidireccional**: Una sola entrada asocia ambos expedientes
- **Sin duplicados**: UNIQUE constraint previene asociaciones repetidas
- **Cascada**: Si se elimina un RMA, se eliminan automáticamente sus asociaciones
- **Auditoría**: Registra quién y cuándo creó la asociación

## 📁 Archivos del Sistema

### 1. `lib/rma_asociaciones.py`
Módulo principal con funciones de gestión:

#### Funciones principales:

**`obtener_asociaciones(rma_id, conn)`**
- Obtiene todos los expedientes asociados a un RMA
- Retorna lista de diccionarios con información completa
- Consulta bidireccional automática

**`asociar_expedientes(rma_id, rma_asociado_id, motivo, usuario, conn)`**
- Crea una nueva asociación entre dos expedientes
- Validaciones:
  - No puede asociar un expediente consigo mismo
  - Ambos RMAs deben existir
  - No permite duplicados
- Retorna (success: bool, message: str)

**`desasociar_expedientes(rma_id, rma_asociado_id, conn)`**
- Elimina la asociación entre dos expedientes
- Retorna (success: bool, message: str)

**`buscar_rmas_para_asociar(termino_busqueda, rma_id_excluir, conn)`**
- Busca expedientes por código o cliente
- Excluye el RMA actual y los ya asociados
- Límite de 50 resultados

**`contar_asociaciones(rma_id, conn)`**
- Cuenta cuántos expedientes están asociados
- Útil para badges/indicadores

### 2. UI en `app.py`

#### Nueva Pestaña: 🔗 Asociados
Solo visible en modo edición (expedientes guardados).

**Componentes:**
- **Encabezado**: Botón "➕ Asociar Expediente"
- **Lista**: Tabla con asociaciones actuales
  - Código RMA
  - Cliente
  - Estado
  - Motivo
  - Acciones (👁️ Abrir, ❌ Desasociar)

#### Métodos principales:

**`crear_tab_asociaciones(tab_frame, rma_id)`**
- Crea la pestaña de asociaciones
- Inicializa la lista

**`cargar_lista_asociaciones()`**
- Recarga la lista de asociaciones
- Se llama después de crear/eliminar asociaciones

**`mostrar_dialogo_asociar_rma(rma_id)`**
- Diálogo de búsqueda y selección
- Búsqueda en tiempo real (delay 500ms)
- Campo de motivo opcional

**`abrir_rma_asociado(rma_id)`**
- Abre el expediente asociado en nueva ventana
- ⚠️ En desarrollo

**`desasociar_expediente(rma_asociado_id)`**
- Elimina asociación con confirmación
- Refresca la lista automáticamente

## 🚀 Uso del Sistema

### Asociar Expedientes

1. Abrir un expediente en modo edición
2. Ir a la pestaña **🔗 Asociados**
3. Clic en **➕ Asociar Expediente**
4. Buscar por código RMA o nombre de cliente
5. Seleccionar el expediente deseado
6. (Opcional) Escribir motivo de asociación
7. Clic en **✓ Asociar**

### Ver Asociaciones

En la pestaña **🔗 Asociados** se muestran:
- Código del expediente asociado
- Cliente
- Estado actual
- Motivo de la asociación
- Botones de acción

### Desasociar Expedientes

1. En la lista de asociaciones
2. Clic en botón **❌** de la asociación a eliminar
3. Confirmar en el diálogo
4. La lista se actualiza automáticamente

## 🔍 Casos de Uso

### 1. Mismo Cliente, Múltiples Incidencias
```
RMA-2024-001 ← → RMA-2024-015
Motivo: "Mismo cliente, problemas recurrentes"
```

### 2. Piezas Relacionadas
```
RMA-2024-050 ← → RMA-2024-051 ← → RMA-2024-052
Motivo: "Piezas del mismo lote defectuoso"
```

### 3. Evolución de Casos
```
RMA-2023-999 ← → RMA-2024-001
Motivo: "Continuación del caso anterior"
```

## ⚙️ Configuración

No requiere configuración adicional. El sistema:
- ✅ Tabla creada automáticamente
- ✅ Integrado en la UI existente
- ✅ Logging automático en `logs/`
- ✅ Validaciones incorporadas

## 📊 Estadísticas

Para obtener estadísticas de asociaciones:

```python
from lib import rma_asociaciones

# Total de asociaciones de un RMA
conn = connect_db()
total = rma_asociaciones.contar_asociaciones(rma_id, conn)
conn.close()

# Expedientes más asociados (consulta SQL directa)
SELECT rma_id, COUNT(*) as total_asociaciones
FROM (
    SELECT rma_id FROM rma_asociaciones
    UNION ALL
    SELECT rma_asociado_id FROM rma_asociaciones
) 
GROUP BY rma_id
ORDER BY total_asociaciones DESC
LIMIT 10
```

## 🐛 Solución de Problemas

### Error: "No se puede asociar un expediente consigo mismo"
**Causa**: Intentando asociar un RMA con su propio ID  
**Solución**: Seleccionar un expediente diferente

### Error: "Estos expedientes ya están asociados"
**Causa**: La asociación ya existe  
**Solución**: La asociación es bidireccional, verificar en la lista

### No aparece la pestaña de Asociados
**Causa**: Expediente en modo creación (no guardado)  
**Solución**: Guardar el expediente primero

### Error de conexión a base de datos
**Causa**: Problema con credenciales de Turso  
**Solución**: Verificar `.env` con TURSO_DATABASE_URL y TURSO_AUTH_TOKEN

## 📝 Logging

Todas las operaciones se registran en `logs/app.log`:

```
INFO - Se obtuvieron 3 asociaciones para RMA ID 25
INFO - Asociación creada exitosamente: RMA 25 <-> 30 por admin
WARNING - Intento de asociar un RMA consigo mismo: 25
ERROR - Error al asociar expedientes 25 y 999: RMA ID 999 no encontrado
```

## 🔐 Seguridad

- ✅ Validación de IDs de RMA
- ✅ Prevención de inyección SQL (parámetros preparados)
- ✅ Auditoría completa (usuario + timestamp)
- ✅ Restricciones de integridad referencial

## 🔄 Mantenimiento

### Limpiar asociaciones huérfanas (si fuera necesario)
```sql
DELETE FROM rma_asociaciones 
WHERE rma_id NOT IN (SELECT id FROM rma_maestro)
   OR rma_asociado_id NOT IN (SELECT id FROM rma_maestro);
```

### Ver todas las asociaciones
```sql
SELECT 
    a.id,
    r1.codigo_rma as rma_principal,
    r2.codigo_rma as rma_asociado,
    a.motivo,
    a.fecha_asociacion,
    a.usuario
FROM rma_asociaciones a
INNER JOIN rma_maestro r1 ON a.rma_id = r1.id
INNER JOIN rma_maestro r2 ON a.rma_asociado_id = r2.id
ORDER BY a.fecha_asociacion DESC;
```

## 📚 Referencias

- Documentación CustomTkinter: https://customtkinter.tomschimansky.com/
- Turso Documentation: https://docs.turso.tech/
- Python DB-API 2.0: https://peps.python.org/pep-0249/

---

**Versión**: 1.0.0  
**Fecha**: 2024  
**Autor**: Sistema de Gestión RMA
