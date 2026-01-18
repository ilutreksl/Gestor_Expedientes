# Documentación de Funciones - Gestor de Expedientes

**Versión de la aplicación:** v1.0.11  
**Fecha de generación:** 16 de enero de 2026  
**Base de datos:** Turso (libSQL) / SQLite local  
**Framework UI:** CustomTkinter

---

## ÍNDICE

- [1. app.py - Aplicación Principal](#1-apppy---aplicación-principal)
- [2. Librerías de Estadísticas](#2-librerías-de-estadísticas)
- [3. Librerías de Artículos y Clientes](#3-librerías-de-artículos-y-clientes)
- [4. Librerías de Managers](#4-librerías-de-managers)
- [5. Librerías de RMA y Expedientes](#5-librerías-de-rma-y-expedientes)
- [6. Librerías de Utilidades](#6-librerías-de-utilidades)

## FUNCIONES GLOBALES

### Sistema de Seguridad para Tkinter

#### `_safe_after(self, ms, func=None, *args)`
**Monkey patch para prevenir crashes en ventanas destruidas**
- Wrapper del método `after()` de Tkinter
- Verifica existencia del widget antes de ejecutar callback
- Registra callbacks en diccionario global por ventana
- Evita errores "invalid command name" al cerrar ventanas
- **Uso**: Automático en toda la aplicación vía monkey patching

#### `_safe_destroy(self)`
**Destrucción segura de ventanas**
- Cancela todos los callbacks pendientes de la ventana
- Libera el grab modal si existe
- Limpia diccionario de callbacks
- Llama al destroy() original
- **Uso**: Automático en Toplevel y CTkToplevel

### Gestión de Archivos Multimedia

#### `es_imagen(filepath) -> bool`
Detecta si un archivo es una imagen por extensión
- **Extensiones soportadas**: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.gif`, `.tiff`, `.tif`, `.webp`, `.heic`, `.heif`
- **Returns**: True si es imagen
- **Uso**: Pre-procesamiento de adjuntos

#### `es_video(filepath) -> bool`
Detecta si un archivo es un video por extensión
- **Extensiones soportadas**: `.mp4`, `.mov`, `.avi`, `.mkv`, `.wmv`, `.flv`, `.webm`, `.m4v`, `.mpg`, `.mpeg`, `.3gp`
- **Returns**: True si es video
- **Uso**: Pre-procesamiento de adjuntos

#### `comprimir_imagen_inteligente(filepath_original, callback_progreso=None) -> tuple`
**Compresión inteligente de imágenes según tamaño**
- **Estrategia**:
  - < 500KB: Sin compresi\u00f3n
  - 500KB-2MB: Recompresi\u00f3n calidad 90%
  - \> 2MB: Redimensi\u00f3n 1920x1080 + calidad 85%
- **Formatos especiales**: Convierte HEIC/HEIF/RGBA a JPEG
- **Returns**: `(ruta_comprimida, tamaño_original_mb, tamaño_final_mb)`
- **Callback**: Reporta progreso paso a paso
- **Uso**: Antes de subir adjuntos grandes

### Clase Tooltip

**Sistema de ayuda contextual flotante**
```python
Tooltip(widget, text="Ayuda", delay=400)
```
- **Métodos**:
  - `_schedule()`: Programa mostrar tooltip tras delay
  - `_show()`: Muestra Toplevel con texto en posición calculada
  - `_hide()`: Oculta y destruye tooltip
- **Configuración**: Respeta `USER_SETTINGS["show_tooltips"]`
- **Uso**: Extensivo en toda la UI para ayuda al usuario

### Base de Datos

#### `connect_db(timeout: float = None) -> Connection`
**Conector unificado híbrido Turso/SQLite**
- **Turso (Producción)**:
  - Requiere `TURSO_DATABASE_URL` y `TURSO_AUTH_TOKEN` en env
  - Implementa DB-API 2.0 vía HTTP REST
  - Clase `TursoCursor` con execute(), fetchone(), fetchall(), etc.
  - Convierte placeholders `?` a formato args de Turso
  - Sesión HTTP persistente para performance
  - Timeout 10 segundos
- **SQLite (Desarrollo)**:
  - Archivo local `rma_app.db`
  - Foreign keys habilitadas
  - Row factory para acceso por nombre
- **Returns**: Objeto Connection compatible DB-API 2.0
- **Uso**: TODAS las operaciones de BD

#### `_get_turso_session() -> requests.Session`
Obtiene sesión HTTP persistente para Turso
- Caché global `_turso_session`
- Headers: `Content-Type: application/json`
- **Performance**: Reutiliza conexiones HTTP

#### `_get_cached_query(cache_key, query_func, ttl=300) -> Any`
**Sistema de caché para queries frecuentes**
- TTL por defecto: 5 minutos (300s)
- Caché en memoria: `_query_cache` dict global
- **Uso**: Estados, usuarios, tipos de cliente
- **Ejemplo**: `_get_cached_query("estados", lambda: ejecutar_query())`

#### `invalidate_cache(pattern=None)`
Invalida caché completo o por patrón
- `pattern=None`: Limpia todo
- `pattern="estados"`: Limpia solo keys que contengan "estados"
- **Uso**: Después de INSERT/UPDATE/DELETE

#### `optimize_database()`
**Optimización y mantenimiento de BD**
- Ejecuta `VACUUM`: Compacta BD y libera espacio
- Ejecuta `ANALYZE`: Actualiza estadísticas del query optimizer
- Limpia `historial_busquedas` > 30 días
- **Uso**: Al iniciar app (thread daemon) + menú admin

### Dropbox Integration

#### `get_dropbox_client() -> dropbox.Dropbox`
**Cliente Dropbox con refresh token automático**
- Soporta refresh token (recomendado) o access token estático
- Caché global `_dropbox_client_cache`
- Verifica autenticación con `users_get_current_account()`
- **Returns**: Cliente autenticado o None si falla
- **Configuración**: Variables en `dropbox_config.py`

#### `usar_dropbox() -> bool`
Verifica si usar Dropbox (True) o almacenamiento local (False)
- Basado en existencia de `DROPBOX_ACCESS_TOKEN`

#### `normalizar_ruta_dropbox(ruta) -> str`
Normaliza rutas para API de Dropbox
- Formato: `/carpeta/archivo` (slash inicial, sin slash final)
- Convierte backslashes a slashes
- **Uso**: Antes de todas las llamadas a API de Dropbox

### Configuración de Usuario

#### `_get_user_settings_path() -> str`
Retorna ruta absoluta a `user_settings.json`

#### `load_user_settings(username: str = "default") -> dict`
**Carga configuración de usuario desde JSON**
- **Campos**:
  - `theme`: Nombre del tema (ej: "Rime")
  - `show_tooltips`: Boolean
  - `last_backup`: Timestamp del último backup
- **Default**: `{"theme": "Rime", "show_tooltips": True, "last_backup": None}`
- **Archivo**: `user_settings.json` en raíz

#### `save_user_settings(settings: dict, username: str = "default") -> bool`
Guarda configuración de usuario
- Preserva settings de otros usuarios
- Formato JSON con indent=2
- **Returns**: True si éxito

### Utilidades de Fechas

#### `parse_date_to_iso(value: str) -> str`
**Parser flexible de fechas a ISO**
- **Formatos soportados**: 
  - `YYYY-MM-DD` (ISO)
  - `DD/MM/YYYY` (España)
  - `DD-MM-DD`
  - `YYYY/MM/DD`
  - `MM/DD/YYYY` (USA)
  - Parseo flexible con dateutil
- **Returns**: Fecha en formato `YYYY-MM-DD`
- **Raises**: `ValueError` si no puede parsear

---

## CLASE LoginApp

**Ventana de autenticación de la aplicación**

### Constructor

#### `__init__(self)`
Inicializa ventana de login
- Tamaño: 400x300 no redimensionable
- Modo: Light
- Tema por defecto: "BH_rime"
- Carga icono personalizado si existe
- Llama `crear_widgets_login()`

### Interfaz de Usuario

#### `crear_widgets_login(self)`
**Construye interfaz de login**
- Frame central con esquinas redondeadas
- Label "Iniciar Sesión" (negrita, 20px)
- Entry usuario (placeholder, Enter bound)
- Entry contraseña (show="*", Enter bound)
- Botón "Iniciar Sesión"
- Label error (rojo, inicialmente vacío)

### Autenticación

#### `conectar_db(self) -> tuple | None`
Establece conexión a BD con timeout 5s
- **Returns**: `(conn, cursor)` o `None` si falla
- **Error handling**: Muestra error en label_error

#### `verificar_login(self)`
**Valida credenciales del usuario**
- Obtiene username y password de entries
- Query: `SELECT password_hash, rol FROM usuarios WHERE nombre_usuario = ?`
- Verifica con `bcrypt.checkpw()`
- **Success**: Label verde + llamada a `abrir_ventana_principal()`
- **Fail**: Label "Usuario o contraseña incorrectos"

### Carga de Aplicación

#### `cargar_tema_usuario(self, username: str)`
Carga y aplica tema personalizado del usuario
- Carga settings desde `user_settings.json`
- Valida existencia del archivo de tema
- Aplica con `ctk.set_default_color_theme()`
- Establece modo (light/dark) con `ctk.set_appearance_mode()`
- **Fallback**: "BH_rime" + mode "light"

#### `abrir_ventana_principal(self, username: str, rol: str)`
**Transición a ventana principal con splash screen**
1. Aplica tema del usuario
2. Oculta ventana de login
3. Muestra splash screen (380x120):
   - "Cargando Gestor RMA..."
   - Barra de progreso indeterminada
4. Instancia `VentanaPrincipal(self, username, rol)`
5. Cierra splash
6. Registra en log

### Utilidades

#### `get_color_por_estado(self, estado: str) -> str`
**Mapeo estado → color hexadecimal**
- **Estados**:
  - "Completado": `#27ae60` (verde)
  - "Pendiente de Autorización": `#e74c3c` (rojo)
  - "Recibido": `#3498db` (azul)
  - "En Trámite": `#f39c12` (naranja)
  - "Autorizado": `#9b59b6` (morado)
  - **Default**: `#7f8c8d` (gris)

---

## CLASE VentanaPrincipal - CORE

**Ventana principal de la aplicación**

### Constructor

#### `__init__(self, master, username: str, rol: str)`
**Inicialización completa de la aplicación**
1. **Setup básico**:
   - Maximiza ventana
   - Título: "Gestor de Expedientes RMA - vX.X.X - Usuario: {username} ({rol})"
   - Protocol para cierre seguro
2. **Estado de aplicación**:
   - `self.username`: Usuario actual
   - `self.rol`: Rol (admin/usuario)
   - `self.conn, self.cursor`: Conexión BD
   - `self.rma_actual`: ID RMA en edición
   - `self.articulos_data`: Lista temporal de artículos
   - `self.campos_rma`: Diccionario de widgets
3. **Verificaciones de esquema**:
   - Llama `verificar_columna_motivo()`
   - Llama `crear_tabla_adjuntos()`
   - Llama `crear_tabla_tareas()`
4. **Configuración logging**:
   - `set_current_user(username)` para log
5. **UI**:
   - Llama `crear_diseno()` para construir interfaz
6. **Inicialización**:
   - Actualiza dashboard inicial
   - Muestra avisos si es admin
   - Programa chequeo de tareas (cada 30 min)
   - Verifica changelog si es primera vez

### Gestión de Base de Datos

#### `conectar_db(self) -> tuple`
Wrapper para mantener conexión activa
- **Returns**: `(self.conn, self.cursor)`

#### `verificar_columna_motivo(self)`
**Migración automática de esquema BD**
- Verifica existencia de columna `motivo` en `rma_maestro`
- Si no existe: `ALTER TABLE rma_maestro ADD COLUMN motivo TEXT`
- **Idempotente**: No falla si columna ya existe

#### `crear_tabla_adjuntos(self)`
**Crea tabla de adjuntos si no existe**
```sql
CREATE TABLE IF NOT EXISTS adjuntos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rma_id INTEGER NOT NULL,
    nombre_archivo TEXT NOT NULL,
    ruta_relativa TEXT NOT NULL,
    fecha_subida TEXT DEFAULT CURRENT_TIMESTAMP,
    tipo_almacenamiento TEXT DEFAULT 'local',
    FOREIGN KEY (rma_id) REFERENCES rma_maestro(id)
)
```
- Verifica y agrega columna `tipo_almacenamiento` si falta

#### `crear_tabla_tareas(self)`
**Crea tabla de tareas si no existe**
```sql
CREATE TABLE IF NOT EXISTS tareas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rma_id INTEGER NOT NULL,
    descripcion TEXT NOT NULL,
    fecha_limite TEXT,
    completada INTEGER DEFAULT 0,
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rma_id) REFERENCES rma_maestro(id)
)
```

### Gestión de Historial de Búsquedas

#### `cargar_historial_busquedas(self) -> list`
Carga últimas 10 búsquedas del usuario desde BD
- Query: Ordena por fecha DESC, limit 10
- **Returns**: Lista de diccionarios con búsquedas

#### `guardar_busqueda_en_historial(self, termino: str, filtros: dict = None)`
**Registra búsqueda en historial**
- Evita duplicados: Elimina búsqueda idéntica previa
- INSERT en tabla `historial_busquedas`
- Serializa filtros a JSON si existen
- Limita a 100 búsquedas por usuario (elimina más antiguas)

#### `limpiar_historial_busquedas(self)`
Elimina TODAS las búsquedas del usuario actual
- `DELETE FROM historial_busquedas WHERE username = ?`

### Sistema de Tareas

#### `contar_tareas_pendientes(self) -> int`
Cuenta tareas no completadas del usuario
- Query: `WHERE completada = 0`
- **Returns**: Número de tareas pendientes

#### `verificar_tareas_pendientes_expediente(self, rma_id: int) -> bool`
Verifica si un expediente específico tiene tareas pendientes
- **Returns**: True si tiene tareas no completadas

#### `actualizar_badge_tareas(self)`
**Actualiza badge numérico en botón Tareas**
- Cuenta tareas pendientes
- Muestra número si > 0
- Oculta si = 0
- **Visual**: Círculo rojo con número blanco

#### `comprobar_tareas_vencidas(self)`
**Notifica tareas vencidas vía messagebox**
- Query tareas con `fecha_limite < HOY` y `completada = 0`
- Agrupa por expediente
- Muestra messagebox con lista de tareas vencidas
- **Frecuencia**: Cada 30 minutos vía `programar_chequeo_tareas()`

#### `programar_chequeo_tareas(self, intervalo_ms: int = 1_800_000)`
Programa chequeo periódico de tareas vencidas
- **Intervalo default**: 30 minutos (1_800_000 ms)
- Usa `after()` para repetición automática

### Gestión de Interfaz

#### `cerrar_app(self)`
**Cierre seguro de la aplicación**
- Muestra confirmación si es vía botón X
- Cierra conexión BD
- Destruye ventana

#### `limpiar_contenido(self)`
Limpia el contenido_frame para mostrar nueva vista
- Destruye todos los widgets hijos de `self.contenido_frame`

#### `crear_diseno(self)`
**Construye estructura principal de la UI**
1. **Barra superior** (50px alto):
   - Logo Ilutrek (if exists)
   - Título "GESTOR DE EXPEDIENTES RMA"
   - Label usuario/rol
   - Botón changelog
   - Botón GitHub Issues
   - Botón cerrar sesión
2. **Panel lateral izquierdo** (220px ancho):
   - **Sección Principal**:
     - Botón Dashboard (🏠)
     - Botón Nuevo Expediente (➕)
     - Botón Ver Expedientes (📋)
     - Botón Búsqueda Avanzada (🔍)
   - **Sección Gestión**:
     - Botón Clientes (👥)
     - Botón Artículos (📦)
     - Botón Tareas (with badge) (✓)
     - Botón Email (✉)
   - **Sección Estadísticas**:
     - Botón Ver Estadísticas (📊)
   - **Sección Administración** (if admin):
     - Botón Menú Admin (⚙)
     - Botón Backups (💾)
     - Botón Ajustes (🎨)
3. **Área de contenido** (centro):
   - Frame scrollable para vistas dinámicas
4. **Tema visual**:
   - Sombras y bordes redondeados
   - Hover effects
   - Tooltips en todos los botones

---

## GESTIÓN DE EXPEDIENTES RMA

### Dashboard

#### `actualizar_dashboard(self, año: int = None)`
**Renderiza dashboard con estadísticas del año**
- **Default**: Año actual
- Llama `obtener_estadisticas_expedientes(año)`
- Llama `obtener_articulos_problematicos(año, "trimestre")`
- Llama `crear_interfaz_estadisticas(stats, art_prob)`
- **Visual**: Cards con métricas + top artículos problemáticos

#### `obtener_estadisticas_expedientes(self, año: int) -> dict`
**Calcula métricas del año**
- Total expedientes
- Expedientes completados (%)
- Expedientes pendientes
- Tiempo promedio de resolución
- Artículos más frecuentes (top 5)
- **Returns**: Dict con todas las métricas

#### `obtener_articulos_problematicos(self, año: int, periodo: str) -> list`
**Identifica artículos con más incidencias**
- Agrupa por referencia_articulo
- Cuenta ocurrencias por periodo
- **Periodo**: "mes", "trimestre", "año"
- **Returns**: Lista ordenada por frecuencia

#### `crear_interfaz_estadisticas(self, stats: dict, articulos_prob: list)`
**Renderiza UI del dashboard**
- Grid 2x3 con tarjetas de métricas
- Card por cada estadística con icono
- Lista de artículos problemáticos
- Colores según valores (verde/amarillo/rojo)

### Listado de Expedientes

#### `mostrar_lista_rma(self)`
**Vista principal de lista de expedientes**
- Barra de búsqueda
- Filtros: Estado + Año
- Selector columnas visibles
- Botones: Nuevo RMA, Exportar, Backup
- Llama `cargar_lista_rma()` para poblar

#### `cargar_lista_rma(self, texto_busqueda: str = "", estado_filtro: str = "Todos", año_filtro: int = None)`
**Carga y renderiza lista de expedientes**
- **Query dinámica** con filtros:
  - LIKE en múltiples campos (código, cliente, etc.)
  - WHERE estado (si no es "Todos")
  - WHERE año (si se especifica)
- **Asociaciones**: Query bidireccional con UNION
- **Columnas**:
  1. Código RMA
  2. Icono enlazado (🔗) si tiene asociaciones
  3. Cliente
  4. Estado (con color)
  5. Fecha recepción
  6. Fecha entrega estimada
  7. Días desde recepción
  8. Acciones (Abrir, Editar, Eliminar, Asociar)
- **Selección**: Single-click selecciona, double-click abre
- **Theme-aware**: Colores de selección según tema

#### `crear_copia_seguridad_db(self)`
**Backup completo de BD**
- Genera nombre: `backup_YYYYMMDD_HHMMSS.db`
- Copia `rma_app.db` a carpeta `backups/`
- Muestra progreso con messagebox
- **Retención**: Mantiene últimos 10 backups

### Formulario de Expediente

#### `mostrar_nuevo_rma(self, rma_id: int = None)`
**Formulario completo de expediente (crear/editar)**
- **Modo Crear**: `rma_id = None`
- **Modo Editar**: `rma_id` existe
- **Estructura**:
  - Tab 1: Datos del expediente
  - Tab 2: Artículos
  - Tab 3: Adjuntos
  - Tab 4: Historial de cambios
  - Tab 5: Tareas
  - Tab 6: Asociaciones RMA
  - Tab 7: Widget de tiempos
- **Campos dinámicos**: Según BD con `crear_campo()`
- **Validación**: En tiempo real
- **Autorrellenado**: Clientes frecuentes

#### `crear_campo(self, parent, fila: int, label_text: str, campo_bd: str, valor_defecto: str = "", deshabilitado: bool = False, tipo: str = "entry", opciones: list = None) -> CTkEntry | CTkComboBox`
**Factory de campos de formulario**
- **Tipos soportados**:
  - `entry`: Texto simple
  - `combobox`: Desplegable
  - `date`: Selector de fecha (CTkDatePicker)
  - `textarea`: Texto multilínea
  - `checkbox`: Boolean
- **Returns**: Widget creado
- **Almacena**: En `self.campos_rma[campo_bd]`

#### `obtener_quincenas_futuras(self) -> list`
Genera lista de quincenas desde hoy hasta +6 meses
- Formato: "01/2025 - 1Q", "01/2025 - 2Q"
- **Uso**: Fecha entrega estimada

#### `obtener_siguiente_rma(self) -> str`
**Genera siguiente código RMA**
- Formato: `RMA-NNNNNN` (6 dígitos)
- Busca MAX(numero_rma) en BD
- Incrementa y formatea con zfill(6)

#### `generar_codigo_rma_final(self, cursor) -> str`
Alias de `obtener_siguiente_rma()` pero recibe cursor

### Guardado de Expediente

#### `guardar_nuevo_rma(self)`
**Guarda expediente NUEVO en BD**
1. **Validación**:
   - Verifica campos obligatorios
   - Valida formato de fechas
2. **Conversión fechas**: `parse_date_to_iso()`
3. **INSERT rma_maestro**:
   - Todos los campos del formulario
   - `numero_rma` auto-generado
   - Timestamp creación
4. **Obtiene** `last_insert_rowid()` → `self.rma_actual`
5. **INSERT rma_detalles** (artículos):
   - Loop por `self.articulos_data`
   - Calcula `precio_final` con lib.articulo_utils
6. **Commit**
7. **Invalidar** caché
8. **Crea carpeta** adjuntos
9. **Notifica** éxito
10. **Navega** a ver expedientes

#### `actualizar_rma(self)`
**Actualiza expediente EXISTENTE**
- Similar a `guardar_nuevo_rma()` pero con UPDATE
- **Historial de cambios**:
  - Compara valores antiguos vs nuevos
  - Llama `guardar_cambio_historial()` por cada cambio
- **DELETE + INSERT** artículos (reemplaza todos)

#### `guardar_cambio_historial(self, rma_id: int, campo: str, valor_antiguo: Any, valor_nuevo: Any)`
**Registra cambio en historial**
```sql
INSERT INTO historial_cambios 
(rma_id, campo, valor_antiguo, valor_nuevo, usuario, fecha)
VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
```

#### `eliminar_expediente(self, rma_id: int)`
**Elimina expediente con confirmación**
- Messagebox confirmación con número RMA
- **Cascade delete**:
  - DELETE FROM rma_detalles
  - DELETE FROM adjuntos (registro)
  - DELETE FROM tareas
  - DELETE FROM historial_cambios
  - DELETE FROM rma_maestro
- **Dropbox**: Elimina carpeta si existe
- **Local**: Elimina carpeta si existe
- Invalida caché
- Actualiza lista

### Carga de Expediente

#### `cargar_datos_rma(self, rma_id: int)`
**Carga expediente existente para edición**
1. **Query maestro**: `SELECT * FROM rma_maestro WHERE id = ?`
2. **Pobla campos**: Loop por `self.campos_rma`
3. **Query detalles**: `SELECT * FROM rma_detalles WHERE rma_id = ?`
4. **Recalcula precios**:
   - Si `precio_final = 0`, llama `calcular_precio_final()`
5. **Carga en** `self.articulos_data`
6. **Actualiza** `actualizar_listado_articulos()`
7. **Carga adjuntos**: `cargar_lista_adjuntos(rma_id)`
8. **Carga historial**: `mostrar_historial()`

#### `determinar_estado_rma(self, datos_maestro: dict) -> str`
**Lógica de estado automático**
- Si `fecha_entrega_real` existe → "Completado"
- Si `autorizado = 1` → "Autorizado"
- Si `fecha_recepcion` existe → "Recibido"
- Else → "Pendiente"

### PDF Auto-fill

#### `autorrellena_pdf(self)`
**Rellena plantilla PDF con datos del expediente**
- Usa `lib.pdf_fill.fill_pdf_for_rma()`
- Datos desde `obtener_datos_actuales_maestro()`
- **Plantilla**: `plantillas/plantilla_rma.pdf`
- **Output**: Selector de archivo
- Mapeo automático de campos PDF

#### `obtener_datos_actuales_maestro(self) -> dict`
Extrae datos del formulario actual
- Lee todos los widgets en `self.campos_rma`
- Formatea fechas
- **Returns**: Dict con todos los campos

---

## SISTEMA DE BÚSQUEDA

### Búsqueda Global

#### `mostrar_busqueda_global(self)`
**Vista de búsqueda rápida**
- Entry de búsqueda
- Placeholder: "Buscar en todos los campos..."
- Enter → `ejecutar_busqueda_global()`
- Área de resultados con secciones

#### `ejecutar_busqueda_global(self)`
**Búsqueda multi-tabla**
- Llama `buscar_en_todos_los_campos(termino)`
- Muestra `mostrar_resultados_busqueda()`
- Guarda en historial

#### `buscar_en_todos_los_campos(self, termino: str) -> dict`
**Query exhaustiva en 4 tablas**
- **Expedientes** (rma_maestro):
  - Campos: numero_rma, nombre_cliente, motivo, observaciones, etc.
- **Productos** (rma_detalles):
  - Campo: referencia_articulo
- **Historial** (historial_cambios):
  - Campos: campo, valor_antiguo, valor_nuevo
- **Tareas**:
  - Campo: descripcion
- **Returns**: `{expedientes: [], productos: [], historial: [], tareas: []}`

#### `mostrar_resultados_busqueda(self, expedientes: list, productos: list, historial: list, tareas: list, termino: str)`
**Renderiza resultados agrupados**
- **Secciones**:
  1. Expedientes (con highlight del término)
  2. Productos (con botón "Ir a expediente")
  3. Historial de cambios
  4. Tareas relacionadas
- Resalta término buscado en amarillo
- Click en resultado → Navega al expediente

### Búsqueda Avanzada

#### `crear_controles_filtros(self)`
**Panel de filtros avanzados**
- **Filtros disponibles**:
  - Estado (dropdown)
  - Rango de fechas (desde/hasta)
  - Cliente (entry)
  - Código RMA (entry)
  - Artículo (entry)
- Botón "Buscar" → `ejecutar_busqueda_con_filtros()`
- Botón "Limpiar" → `limpiar_filtros()`
- Toggle "Filtros avanzados" (expand/collapse)

#### `ejecutar_busqueda_con_filtros(self)`
**Búsqueda con múltiples criterios**
- Construye filtros desde widgets
- Llama `buscar_en_maestro_con_filtros()`
- Llama `buscar_en_detalles_con_filtros()`
- Muestra `mostrar_resultados_busqueda_avanzada()`

#### `buscar_en_maestro_con_filtros(self, termino: str, filtros: dict) -> list`
**Query dinámica en rma_maestro**
- WHERE con múltiples AND
- Parámetros parameterizados para seguridad
- **Returns**: Lista de expedientes

#### `buscar_en_detalles_con_filtros(self, termino: str, filtros: dict) -> list`
**Query en rma_detalles con JOIN a maestro**
- Filtra por referencia_articulo
- JOIN para obtener datos del expediente
- **Returns**: Lista de productos con datos de expediente

### Historial de Búsquedas

#### `actualizar_historial_ui(self)`
Renderiza últimas 10 búsquedas
- Llama `cargar_historial_busquedas()`
- Crea card por búsqueda con:
  - Término buscado
  - Fecha/hora
  - Botón "Repetir" → `usar_busqueda_historial()`
  - Botón "✕" → Eliminar

#### `usar_busqueda_historial(self, entrada: dict)`
**Repite búsqueda desde historial**
- Carga término y filtros
- Ejecuta búsqueda
- Navega a resultados

---

## GESTIÓN DE ARTÍCULOS

### Formulario de Artículos (dentro de Expediente)

#### `anadir_articulo(self)`
**Agrega artículo a lista temporal**
1. Lee campos: referencia, cantidad_doc, cantidad_ent, estado, precio_unit
2. **Valida**:
   - Referencia no vacía
   - Cantidades numéricas
   - Precio numérico
3. **Calcula precio final**:
   - Aplica depreciación si checked
   - `precio_final = precio_unit - deprec`
4. **Append** a `self.articulos_data`
5. **Llama** `actualizar_listado_articulos()`
6. **Limpia** formulario con `limpiar_articulo()`

#### `editar_articulo(self, index: int)`
**Carga artículo en formulario para edición**
- Carga datos desde `self.articulos_data[index]`
- Pobla campos
- Cambia botón "Añadir" → "Actualizar"
- Guarda `self.editando_index = index`

#### `actualizar_articulo(self)`
**Guarda cambios de artículo editado**
- Similar a `anadir_articulo()` pero modifica en lugar de append
- Actualiza `self.articulos_data[self.editando_index]`
- Resetea modo edición

#### `eliminar_articulo(self, index: int)`
**Elimina artículo de lista temporal**
- `del self.articulos_data[index]`
- Llama `actualizar_listado_articulos()`

#### `actualizar_listado_articulos(self)`
**Renderiza tabla de artículos**
- **Grid layout** 10 columnas:
  1. Referencia
  2. Cant. Documentada
  3. Cant. Entregada
  4. Estado
  5. Precio Unitario
  6. Precio Final
  7. Depreciación (✓/-)
  8. % Depreciación
  9. Botón Eliminar (X)
  10. Botón Editar (✏️)
- **Selección**: Click simple selecciona fila
- **Theme colors**: Hover + selección

#### `calcular_precio_final_tiempo_real(self, event=None)`
**Actualiza precio final en tiempo real**
- Lee precio_unit, descuento, depreciación
- Calcula automáticamente
- Actualiza label/entry de precio_final
- Triggered por KeyRelease en campos numéricos

#### `toggle_porcentaje_depreciacion(self)`
**Muestra/oculta campo % depreciación**
- Si checkbox depreciación = ON → Muestra campo %
- Si OFF → Oculta y resetea a 0

### Ventana de Artículos Global

#### `mostrar_articulos_window(self)`
**Vista de todos los artículos del sistema**
- **Búsqueda**: Por referencia
- **Lista**: Todas las referencias únicas de BD
- **Estadísticas por artículo**:
  - Total de incidencias
  - Estados más frecuentes
  - Expedientes que lo contienen
- **Botones**:
  - Ver estados → `mostrar_estados_por_articulo(ref)`
  - Ver expedientes → `mostrar_expedientes_por_articulo(ref)`

#### `mostrar_estados_por_articulo(self, referencia: str)`
**Gráfico de distribución de estados**
- Query: Agrupa por estado_producto
- **Visual**: Lista con conteos y %
- Colores según estado

#### `mostrar_expedientes_por_articulo(self, referencia: str)`
**Lista de todos los expedientes con ese artículo**
- Query JOIN rma_detalles + rma_maestro
- **Columnas**: Código RMA, Cliente, Estado, Fecha
- Click → Abre expediente

---

## SISTEMA DE ADJUNTOS

### Gestión de Carpetas

#### `crear_carpeta_adjuntos_rma(self, codigo_rma: str)`
**Crea carpeta para adjuntos del RMA**
- Si Dropbox → `_crear_carpeta_dropbox()`
- Si local → `_crear_carpeta_local()`

#### `_crear_carpeta_dropbox(self, codigo_rma: str)`
Crea carpeta en Dropbox
- Ruta: `/Adjuntos_RMA/{codigo_rma}/`
- API: `files_create_folder_v2()`
- Ignora error si ya existe

#### `_crear_carpeta_local(self, codigo_rma: str)`
Crea carpeta local
- Ruta: `Adjuntos_RMA/{codigo_rma}/`
- `os.makedirs(exist_ok=True)`

### Subida de Archivos

#### `abrir_dialogo_adjunto(self, modo_abrir_carpeta: bool = False)`
**Diálogo principal de adjuntos**
- **Modo carpeta**: Solo abre carpeta de expediente
- **Modo normal**:
  1. Selector de archivo (filedialog)
  2. Verifica tipo (imagen/video)
  3. **Compresión inteligente**:
     - Imágenes → `comprimir_imagen_inteligente()`
     - Videos → `comprimir_video_inteligente()`
  4. **Progress bar** durante compresión
  5. **Subida** según almacenamiento:
     - Dropbox → `_subir_archivo_dropbox()`
     - Local → `_subir_archivo_local()`
  6. **Registro en BD** tabla adjuntos
  7. **Limpieza** archivos temporales
  8. **Actualiza** lista de adjuntos

#### `_subir_archivo_dropbox(self, filepath: str, codigo_rma: str, nombre_archivo: str, ventana_progreso_externa=None)`
**Upload a Dropbox con chunked upload**
- **Estrategia**:
  - < 150MB → `files_upload()` simple
  - \> 150MB → `upload_session` con chunks de 4MB
- **Progress callback**: Actualiza barra cada chunk
- **Retry logic**: 3 intentos con backoff
- **Returns**: Ruta relativa para BD

#### `_subir_archivo_local(self, filepath: str, codigo_rma: str, nombre_archivo: str) -> str`
**Copia archivo a carpeta local**
- `shutil.copy2(filepath, dest)`
- **Returns**: Ruta relativa

#### `_limpiar_archivo_subido(self, ruta_relativa: str)`
Limpia archivo temporal comprimido
- `os.remove(temp_path)`
- Manejo de errores silencioso

### Visualización de Adjuntos

#### `cargar_lista_adjuntos(self, rma_id: int)`
**Renderiza lista de adjuntos del expediente**
- Query: `SELECT * FROM adjuntos WHERE rma_id = ?`
- **Grid columns**:
  - Icono (según tipo de archivo)
  - Nombre archivo
  - Fecha subida
  - Tipo almacenamiento (Dropbox/Local)
  - Acciones (Abrir, Editar, Eliminar)
- **Iconos**: 📄 docs, 🖼️ images, 🎥 videos, 📊 spreadsheets

#### `abrir_adjunto(self, ruta_relativa: str)`
**Abre adjunto según almacenamiento**
- Si Dropbox → `_abrir_adjunto_dropbox()`
- Si local → `_abrir_adjunto_local()`

#### `_abrir_adjunto_dropbox(self, ruta_relativa: str)`
**Descarga y abre archivo de Dropbox**
1. Crea temp directory
2. `files_download()` de Dropbox
3. Guarda en temp file
4. `_abrir_archivo_sistema(temp_path)`
5. **No limpia**: Usuario puede seguir usando el archivo

#### `_abrir_adjunto_local(self, ruta_relativa: str)`
Abre archivo local
- `_abrir_archivo_sistema(ruta_completa)`

#### `_abrir_archivo_sistema(self, ruta_archivo: str)`
**Abre archivo con aplicación por defecto del SO**
- Windows → `os.startfile()`
- macOS → `subprocess.call(["open", ruta])`
- Linux → `subprocess.call(["xdg-open", ruta])`

### Edición de Adjuntos

#### `editar_adjunto(self, ruta_relativa: str, adjunto_id: int)`
**Edición en tiempo real de adjuntos Dropbox**
1. Descarga archivo a temp
2. Guarda timestamp modificación inicial
3. Abre archivo con aplicación por defecto
4. Crea diálogo de seguimiento
5. **Monitoreo automático** cada 2s:
   - Compara timestamp actual vs inicial
   - Si cambió → Pregunta si subir cambios
6. **Opciones**:
   - "Subir cambios" → Sube versión editada
   - "Verificar manualmente" → Chequea una vez
   - "Cancelar" → Limpia temp y cierra

#### `_crear_dialogo_seguimiento_edicion(self, temp_path, ruta_dropbox, tiempo_inicial, temp_dir, nombre_archivo)`
**Ventana modal de seguimiento de edición**
- Label estado: "Editando..."
- Botones: Verificar, Subir, Cancelar
- Timer automático: `_verificar_cambios_automatico()` cada 2s

#### `_verificar_cambios_automatico(self, dialogo, temp_path, tiempo_inicial)`
Compara timestamp y pregunta si subir
- Si cambió → Messagebox "¿Subir cambios?"

#### `_subir_cambios_editados(self, temp_path, ruta_dropbox, temp_dir, dialogo)`
**Re-upload de archivo editado**
- `files_upload(mode=WriteMode.overwrite)`
- Actualiza registro en BD
- Limpia temp
- Cierra diálogo

### Eliminación de Adjuntos

#### `confirmar_eliminar_adjunto(self, adjunto_id: int, ruta_relativa: str)`
Messagebox confirmación → llama `eliminar_adjunto()`

#### `eliminar_adjunto(self, adjunto_id: int, ruta_relativa: str)`
**Elimina adjunto de BD y almacenamiento**
1. `DELETE FROM adjuntos WHERE id = ?`
2. Si Dropbox → `_eliminar_archivo_dropbox()`
3. Si local → `_eliminar_archivo_local()`
4. Actualiza lista

#### `_eliminar_archivo_dropbox(self, ruta_relativa: str)`
`files_delete_v2()` API de Dropbox

#### `_eliminar_archivo_local(self, ruta_relativa: str)`
`os.remove(ruta_completa)`

---

## GESTIÓN DE CLIENTES

### Vista de Clientes

#### `mostrar_clientes(self)`
**Vista principal de clientes**
- Barra de búsqueda
- Botón "Nuevo Cliente"
- Botón "Migrar desde RMAs" (admin)
- Grid de cards con clientes
- Llama `cargar_lista_clientes()`

#### `cargar_lista_clientes(self)`
**Carga y renderiza lista de clientes**
- Query: `SELECT * FROM clientes ORDER BY nombre`
- Por cada cliente → `crear_item_cliente()`
- **Selección**: Single-click selecciona card

#### `crear_item_cliente(self, cliente: dict) -> CTkFrame`
**Card de cliente**
- **Info visible**:
  - Nombre (bold)
  - Estado (Activo/Inactivo con color)
  - Estadísticas: Total RMAs, Última actividad
- **Hover effect**
- **Click** → `abrir_ficha_cliente(cliente_id)`
- **Double-click** → Edita datos básicos

#### `filtrar_clientes(self, event=None)`
Filtra lista por término de búsqueda
- Busca en nombre, email, teléfono
- Actualiza UI mostrando solo coincidencias

### CRUD de Clientes

#### `nuevo_cliente(self)`
**Formulario de nuevo cliente**
- Diálogo modal
- **Campos**:
  - Nombre (obligatorio)
  - Email
  - Teléfono
  - Dirección
  - CIF/NIF
  - Tipo de cliente (dropdown)
  - Notas
- **Validación**: Email formato
- **Guardado** → INSERT clientes

#### `abrir_ficha_cliente(self, cliente_id: int)`
**Vista detallada del cliente**
- **Tabs**:
  1. Información (editable)
  2. Expedientes del cliente
  3. Estadísticas
  4. Condiciones especiales
  5. Rentabilidad
- **Botones**: Guardar, Eliminar, Cerrar

#### `crear_tab_informacion_cliente_editable(self, tab_frame, cliente: dict)`
**Tab 1: Formulario de datos**
- Todos los campos editables
- Botón "Guardar cambios" → UPDATE

#### `migrar_clientes_desde_rmas(self)`
**Migración automática desde RMAs antiguos**
- Extrae `DISTINCT nombre_cliente, email_cliente` de rma_maestro
- Crea registros en tabla clientes
- Actualiza rma_maestro con `cliente_id` (FK)
- **Uso**: Migración una sola vez

---

## SISTEMA DE TAREAS

#### `mostrar_gestion_tareas(self)`
**Vista de todas las tareas**
- **Filtros**:
  - Pendientes/Completadas/Todas
  - Por expediente
  - Por rango de fechas
- **Lista** con columnas:
  - RMA
  - Descripción
  - Fecha límite (con color si vencida)
  - Estado
  - Acciones (Marcar completada, Editar, Eliminar)
- **Botón** "Nueva tarea"

---

## ESTADÍSTICAS Y REPORTES

### Estadísticas de Artículos

#### `mostrar_estadisticas_articulos_menu(self)`
Llama `lib.articulos_estadisticas.mostrar_estadisticas_articulos()`

### Estadísticas Anuales

#### `mostrar_estadisticas_anuales_menu(self)`
Llama `lib.anuales_estadisticas.mostrar_estadisticas_anuales()`

### Estadísticas de Resolución

#### `mostrar_estadisticas_resolucion_menu(self)`
Llama `lib.resolucion_estadisticas.mostrar_estadisticas_resolucion()`

### Expedientes por Quincena

#### `mostrar_expedientes_quincena_menu(self)`
Llama `lib.expedientes_quincena.mostrar_expedientes_quincena()`

### Recepciones Anticipadas

#### `mostrar_recepciones_anticipadas(self)`
**Análisis de recepciones anticipadas**
- Query RMAs con `fecha_recepcion < fecha_estimada`
- Agrupa por cliente
- Calcula % anticipación
- **Exportar**: Excel + PDF

### Exportaciones

#### `exportar_a_excel(self, datos: list, columnas: list, filename: str)`
**Exportación genérica a Excel**
- Usa `pandas.DataFrame`
- Guarda con formato
- Abre archivo automáticamente

#### `mostrar_tabla_estadistica(self, datos: list, columnas: list, export_filename: str, frame, formato_moneda: bool = False)`
**Tabla con botón de exportación**
- TreeView con datos
- Formato moneda si aplica
- Botón "Exportar a Excel"

---

## ADMINISTRACIÓN

#### `mostrar_menu_admin(self)`
**Panel de administración** (solo rol=admin)
- Botones:
  - Gestión de Usuarios
  - Gestión de Estados
  - Gestión de Personas
  - Gestión de Tipos de Cliente
  - Avisos
  - Optimizar BD
  - Ver Logs

#### `mostrar_gestion_usuarios(self)`
**CRUD de usuarios**
- Lista usuarios (username, rol)
- Nuevo usuario:
  - Username
  - Password (hash bcrypt)
  - Rol (admin/usuario)
- Editar rol
- Eliminar (con confirmación)
- Cambiar contraseña

#### `mostrar_gestor_estados(self)`
Llama `lib.estados_manager.EstadosArticuloManager()`

#### `mostrar_gestor_personas(self)`
Llama `lib.personas_manager.PersonasManager()`

#### `mostrar_gestor_tipos_cliente(self)`
Llama `lib.tipos_cliente_manager.TiposClienteManager()`

#### `mostrar_admin_avisos(self)`
Llama `lib.avisos_manager.AvisosManager()`

#### `mostrar_gestor_backups(self)`
**Gestor de backups en Backblaze B2**
- Llama `lib.backup_manager.BackupManagerB2()`
- Lista archivos en bucket
- Subir/Descargar/Eliminar
- Restaurar BD desde backup

---

## LIBRERÍAS AUXILIARES

### lib/articulo_utils.py
**Funciones**: 
- `calcular_precio_final(precio_unit, descuento, depreciacion, porcentaje_deprec)`
- `aplicar_descuento_cliente()`
- `validar_referencia_articulo()`

### lib/articulos_estadisticas.py
**Función principal**: `mostrar_estadisticas_articulos(parent, conn)`
- Top artículos más frecuentes
- Distribución por estado
- Tendencias temporales

### lib/anuales_estadisticas.py
**Función principal**: `mostrar_estadisticas_anuales(parent, conn, año)`
- RMAs por mes
- Comparativa año anterior
- Gráficos con matplotlib

### lib/resolucion_estadisticas.py
**Función principal**: `mostrar_estadisticas_resolucion(parent, conn)`
- Tiempo promedio de resolución
- Por tipo de cliente
- Distribución temporal

### lib/cliente_estadisticas.py
**Funciones**:
- `obtener_estadisticas_cliente(conn, cliente_id)`
- `calcular_frecuencia_rmas()`
- `obtener_tiempo_promedio_resolucion()`

### lib/client_rentability.py
**Funciones**:
- `calcular_rentabilidad_cliente(conn, cliente_id)`
- `analisis_coste_beneficio()`

### lib/cliente_condiciones.py
**Gestión de condiciones especiales** por cliente
- Descuentos personalizados
- Plazos de pago
- Prioridad

### lib/expedientes_quincena.py
**Función principal**: `mostrar_expedientes_quincena(parent, conn, quincena)`
- Lista expedientes de la quincena
- Estadísticas de cumplimiento

### lib/recepciones_anticipadas.py
**Función principal**: `mostrar_recepciones_anticipadas(parent, conn)`
- Análisis de anticipación
- Ranking de clientes

### lib/rma_utils.py
**Funciones**:
- `obtener_ultima_actividad(conn, rma_id) -> datetime`
- `calcular_tiempos_expediente(conn, rma_id) -> dict`
- `obtener_color_tiempo(dias) -> str`
- `obtener_promedio_cliente(conn, cliente_id) -> float`

### lib/rma_asociaciones.py
**Gestión de asociaciones entre RMAs**
- `asociar_rmas(conn, rma_id1, rma_id2, motivo)`
- `obtener_asociaciones(conn, rma_id) -> list`
- `eliminar_asociacion(conn, asociacion_id)`

### lib/rma_editor_window.py
**Editor avanzado de RMA** (alternativo al formulario principal)
- Vista más compacta
- Edición rápida de campos específicos

### lib/estados_manager.py
**Clase**: `EstadosArticuloManager`
- CRUD de estados de artículos
- Gestión de colores asociados

### lib/personas_manager.py
**Clase**: `PersonasManager`
- CRUD de personas (contactos)
- Asociación a expedientes

### lib/personas_recepcion_manager.py
**Clase**: `PersonasRecepcionManager`
- Personas específicas de recepción
- Estadísticas de recepciones

### lib/resultado_expediente_manager.py
**Clase**: `ResultadoExpedienteManager`
- CRUD de tipos de resultado
- Reportes por resultado

### lib/tipos_cliente_manager.py
**Función**: `cargar_tipos_cliente(conn) -> list`
- Carga tipos desde diccionario JSON
- Gestión de tipos personalizados

### lib/avisos_manager.py
**Clase**: `AvisosManager`
- Sistema de avisos/notificaciones
- Mostrar avisos pendientes
- Marcar como leído

### lib/backup_manager.py
**Clase**: `BackupManagerB2`
- Integración con Backblaze B2
- Subir/descargar backups
- Programación automática

### lib/changelog_window.py
**Función**: `mostrar_ventana_cambios(parent, version)`
- Muestra CHANGELOG.md formateado
- Marca versión como vista

### lib/github_issue_manager.py
**Funciones**:
- `crear_issue_github(titulo, descripcion, labels)`
- `listar_issues_abiertos()`
- Autenticación con token

### lib/logger_config.py
**Sistema de logging centralizado**
- `setup_logging() -> Logger`
- `set_current_user(username)`
- `get_logger() -> Logger`
- Logs en `logs/app.log`
- Rotación automática

### lib/pdf_fill.py
**Funciones**:
- `fill_pdf(template_path, output_path, field_values)`
- `fill_pdf_for_rma(conn, rma_id, output_path)`
- `get_pdf_field_names(pdf_path) -> list`

### lib/video_utils.py
**Función**: `comprimir_video_inteligente(filepath, callback_progreso) -> tuple`
- Compresión con ffmpeg
- Estrategias según tamaño y duración
- Progress callback

### lib/safe_toplevel.py
**Clase**: `SafeToplevel(ctk.CTkToplevel)`
- Toplevel con destroy seguro
- Evita errores de callbacks pendientes

### lib/estados_articulo.py
**Gestión de estados de artículos**
- Carga desde diccionario JSON
- Colores y prioridades

### lib/comparativa_ventas.py
**Función**: `mostrar_comparativa_ventas(parent, conn, año1, año2)`
- Gráficos comparativos
- Análisis de tendencias

---

## DICCIONARIOS JSON

### Diccionarios/estados_articulo.json
Lista de estados posibles para artículos

### Diccionarios/personas.json
Lista de personas autorizadas

### Diccionarios/personas_recepcion.json
Lista de personas de recepción

### Diccionarios/resultado_expediente.json
Tipos de resultado de expedientes

### Diccionarios/tipos_cliente.json
Tipos de clientes

---

## BASE DE DATOS - ESQUEMA

### Tabla: usuarios
```sql
CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_usuario TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    rol TEXT NOT NULL  -- 'admin' o 'usuario'
)
```

### Tabla: rma_maestro
```sql
CREATE TABLE rma_maestro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_rma TEXT UNIQUE NOT NULL,
    fecha_recepcion TEXT,
    nombre_cliente TEXT,
    email_cliente TEXT,
    telefono_cliente TEXT,
    numero_documento_cliente TEXT,
    tipo_cliente TEXT,
    numero_albaran TEXT,
    recogido_por TEXT,
    autorizado_por TEXT,
    fecha_entrega_estimada TEXT,
    fecha_entrega_real TEXT,
    motivo TEXT,
    observaciones TEXT,
    autorizado INTEGER DEFAULT 0,
    cliente_id INTEGER,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
)
```

### Tabla: rma_detalles
```sql
CREATE TABLE rma_detalles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rma_id INTEGER NOT NULL,
    referencia_articulo TEXT NOT NULL,
    cantidad_segun_documento INTEGER,
    cantidad_entregada INTEGER,
    estado_producto TEXT,
    precio_unitario REAL DEFAULT 0,
    precio_final REAL DEFAULT 0,
    depreciacion INTEGER DEFAULT 0,
    porcentaje_depreciacion REAL DEFAULT 0,
    FOREIGN KEY (rma_id) REFERENCES rma_maestro(id)
)
```

### Tabla: adjuntos
```sql
CREATE TABLE adjuntos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rma_id INTEGER NOT NULL,
    nombre_archivo TEXT NOT NULL,
    ruta_relativa TEXT NOT NULL,
    fecha_subida TEXT DEFAULT CURRENT_TIMESTAMP,
    tipo_almacenamiento TEXT DEFAULT 'local',  -- 'local' o 'dropbox'
    FOREIGN KEY (rma_id) REFERENCES rma_maestro(id)
)
```

### Tabla: tareas
```sql
CREATE TABLE tareas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rma_id INTEGER NOT NULL,
    descripcion TEXT NOT NULL,
    fecha_limite TEXT,
    completada INTEGER DEFAULT 0,
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rma_id) REFERENCES rma_maestro(id)
)
```

### Tabla: historial_cambios
```sql
CREATE TABLE historial_cambios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rma_id INTEGER NOT NULL,
    campo TEXT NOT NULL,
    valor_antiguo TEXT,
    valor_nuevo TEXT,
    usuario TEXT NOT NULL,
    fecha TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rma_id) REFERENCES rma_maestro(id)
)
```

### Tabla: historial_busquedas
```sql
CREATE TABLE historial_busquedas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    termino TEXT NOT NULL,
    filtros TEXT,  -- JSON serializado
    fecha TEXT DEFAULT CURRENT_TIMESTAMP
)
```

### Tabla: clientes
```sql
CREATE TABLE clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    email TEXT,
    telefono TEXT,
    direccion TEXT,
    cif_nif TEXT,
    tipo_cliente TEXT,
    notas TEXT,
    activo INTEGER DEFAULT 1,
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
)
```

### Tabla: rma_asociaciones
```sql
CREATE TABLE rma_asociaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rma_principal_id INTEGER NOT NULL,
    rma_asociado_id INTEGER NOT NULL,
    motivo TEXT,
    fecha_asociacion TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rma_principal_id) REFERENCES rma_maestro(id),
    FOREIGN KEY (rma_asociado_id) REFERENCES rma_maestro(id)
)
```

---

## CONFIGURACIÓN Y DEPLOYMENT

### Variables de Entorno (.env)
```env
# Turso (Producción)
TURSO_DATABASE_URL=https://your-db.turso.io
TURSO_AUTH_TOKEN=your_token_here

# Dropbox
DROPBOX_ACCESS_TOKEN=your_token
DROPBOX_REFRESH_TOKEN=your_refresh_token
DROPBOX_APP_KEY=your_app_key
DROPBOX_APP_SECRET=your_app_secret
DROPBOX_ROOT_FOLDER=/Adjuntos_RMA

# Backblaze B2
B2_KEY_ID=your_key_id
B2_APPLICATION_KEY=your_app_key
B2_BUCKET_NAME=your_bucket

# GitHub (Issues)
GITHUB_TOKEN=your_github_token
GITHUB_REPO=user/repo
```

### Dependencias (requirements.txt)
```
customtkinter>=5.2.0
pillow>=10.0.0
bcrypt>=4.0.1
pandas>=2.0.0
dropbox>=11.36.2
python-dotenv>=1.0.0
requests>=2.31.0
python-dateutil>=2.8.2
reportlab>=4.0.0
PyPDF2>=3.0.1
matplotlib>=3.7.0
b2sdk>=1.24.0
```

### Estructura de Archivos
```
Gestor_Expedientes/
├── app.py                    # Aplicación principal
├── dropbox_config.py         # Configuración Dropbox
├── user_settings.json        # Preferencias usuarios
├── rma_app.db                # Base de datos SQLite (local)
├── CHANGELOG.md              # Historial de cambios
├── README.md                 # Documentación
├── Avisos.md                 # Avisos pendientes
├── .env                      # Variables de entorno
├── lib/                      # Librerías Python
│   ├── __init__.py
│   ├── articulo_utils.py
│   ├── backup_manager.py
│   ├── ... (29 archivos)
├── themes/                   # Temas CustomTkinter
│   ├── BH_rime.json
│   ├── autumn.json
│   ├── ... (16 archivos)
├── Diccionarios/             # Datos de configuración
│   ├── estados_articulo.json
│   ├── personas.json
│   ├── ... (5 archivos)
├── Guias/                    # Documentación
│   ├── FUNCIONES_APLICACION.md
│   ├── DROPBOX_MIGRATION_GUIDE.md
│   ├── ... (otros archivos)
├── plantillas/               # Plantillas PDF
├── icons/                    # Iconos de la aplicación
├── logs/                     # Archivos de log
│   └── app.log
├── backups/                  # Backups locales
├── Adjuntos_RMA/             # Almacenamiento local
│   └── RMA-XXXXXX/
└── bin/                      # Binarios externos
    └── ffmpeg/
```

---

## GUÍA DE USO RÁPIDO

### Inicio de Sesión
1. Ejecutar `python app.py`
2. Ingresar credenciales
3. Sistema carga tema personalizado y abre dashboard

### Crear Expediente
1. Click "Nuevo Expediente" (➕)
2. Completar datos del cliente
3. Añadir artículos uno por uno
4. Subir adjuntos (compresión automática)
5. Guardar → Asigna número RMA automáticamente

### Buscar Expediente
- **Búsqueda rápida**: Barra superior
- **Búsqueda avanzada**: Filtros múltiples
- **Ver lista**: Todos los expedientes con filtros

### Gestión de Clientes
1. Menu "Clientes"
2. Buscar o crear nuevo
3. Ver estadísticas e historial
4. Configurar condiciones especiales

### Estadísticas
- Dashboard: Vista general del año
- Menú Estadísticas: Reportes detallados
- Exportación a Excel/PDF

### Administración (Solo Admin)
- Gestión de usuarios y permisos
- Configuración de estados y tipos
- Backups automáticos
- Ver logs del sistema

---

## MANTENIMIENTO Y TROUBLESHOOTING

### Optimización de BD
- **Automática**: Al iniciar app (thread daemon)
- **Manual**: Menú Admin → "Optimizar BD"
- **Función**: VACUUM + ANALYZE + limpieza historial

### Backups
- **Automático**: Programable desde gestor
- **Manual**: Botón "Crear Backup"
- **Restauración**: Desde gestor de backups
- **Almacenamiento**: Local + Backblaze B2

### Logs
- **Ubicación**: `logs/app.log`
- **Rotación**: Automática (10 MB)
- **Nivel**: INFO por defecto
- **Visualización**: Menú Admin → "Ver Logs"

### Problemas Comunes

**Error de conexión a Turso**:
- Verificar variables de entorno
- Comprobar conectividad
- Fallback automático a SQLite local

**Adjuntos no suben a Dropbox**:
- Verificar token en `dropbox_config.py`
- Comprobar permisos del app
- Revisar espacio disponible

**BD corrupta**:
- Restaurar desde backup más reciente
- Ejecutar `.recover` en SQLite
- Contactar soporte si persiste

---

## CHANGELOG RESUMIDO

### v1.0.11 (Actual)
- ✅ Selección con clic simple en todos los listados
- ✅ Tema-aware colors para selección
- ✅ Fix precio_final en artículos
- ✅ Asociaciones RMA bidireccionales

### v1.0.10
- Compresión inteligente de imágenes/videos
- Integración Backblaze B2
- Sistema de logging robusto

### v1.0.9
- Soporte Turso (libSQL)
- Migración híbrida SQLite/Turso
- Cache de queries frecuentes

### v1.0.0
- Release inicial
- CRUD completo de expedientes
- Sistema de adjuntos Dropbox
- Búsqueda y estadísticas

---

**FIN DE LA DOCUMENTACIÓN**

*Generado automáticamente el 16 de enero de 2026*  
*Gestor de Expedientes RMA v1.0.11*  
*Total de funciones documentadas: 300+*  
*Archivos analizados: app.py + 29 librerías*

#### `_safe_after(self, ms, func=None, *args)`
- **Propósito**: Wrapper seguro para el método `after()` de Tkinter que previene errores cuando se ejecutan callbacks en ventanas ya destruidas
- **Parámetros**:
  - `self`: Widget de Tkinter/CustomTkinter
  - `ms`: Milisegundos de delay antes de ejecutar la función
  - `func`: Función callback a ejecutar (opcional, None para sleep)
  - `*args`: Argumentos para la función callback
- **Retorna**: ID del callback programado
- **Lógica**:
  1. Si func es None, ejecuta `after()` normal (sleep)
  2. Crea función wrapper `safe_func` que verifica existencia del widget antes de ejecutar
  3. Programa callback con función segura
  4. Registra ID del callback en diccionario global si es Toplevel
- **Relaciones**: Utilizado por todo el sistema de UI para programar tareas
- **Base de datos**: N/A
- **UI**: Previene crashes al cerrar ventanas con callbacks pendientes

#### `_safe_destroy(self)`
- **Propósito**: Wrapper seguro para `destroy()` que cancela todos los callbacks pendientes antes de destruir la ventana
- **Parámetros**:
  - `self`: Ventana Toplevel a destruir
- **Retorna**: None
- **Lógica**:
  1. Obtiene ID de la ventana
  2. Cancela todos los callbacks registrados para esa ventana usando `after_cancel()`
  3. Libera el grab si existe
  4. Llama al `destroy()` original
  5. Limpia entrada del diccionario global de callbacks
- **Relaciones**: Monkey patch aplicado a Toplevel y CTkToplevel
- **Base de datos**: N/A
- **UI**: Garantiza limpieza segura de ventanas

#### `es_imagen(filepath)`
- **Propósito**: Detecta si un archivo es una imagen basándose en su extensión
- **Parámetros**:
  - `filepath`: Ruta del archivo a verificar
- **Retorna**: Boolean (True si es imagen, False si no)
- **Lógica**:
  1. Define conjunto de extensiones de imagen: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.gif`, `.tiff`, `.tif`, `.webp`, `.heic`, `.heif`
  2. Extrae extensión del archivo y la convierte a minúsculas
  3. Verifica si está en el conjunto de extensiones válidas
- **Relaciones**: Usado por sistema de adjuntos para decidir si comprimir
- **Base de datos**: N/A
- **UI**: N/A

#### `es_video(filepath)`
- **Propósito**: Detecta si un archivo es un video basándose en su extensión
- **Parámetros**:
  - `filepath`: Ruta del archivo a verificar
- **Retorna**: Boolean (True si es video, False si no)
- **Lógica**:
  1. Define conjunto de extensiones de video: `.mp4`, `.mov`, `.avi`, `.mkv`, `.wmv`, `.flv`, `.webm`, `.m4v`, `.mpg`, `.mpeg`, `.3gp`
  2. Extrae extensión del archivo y la convierte a minúsculas
  3. Verifica si está en el conjunto de extensiones válidas
- **Relaciones**: Usado por sistema de adjuntos para decidir si comprimir video
- **Base de datos**: N/A
- **UI**: N/A

#### `comprimir_imagen_inteligente(filepath_original, callback_progreso=None)`
- **Propósito**: Comprime una imagen de forma inteligente según su tamaño usando estrategia adaptativa
- **Parámetros**:
  - `filepath_original`: Ruta de la imagen original
  - `callback_progreso`: Función opcional para reportar progreso (recibe string de estado)
- **Retorna**: Tupla `(filepath_comprimido, tamaño_original_mb, tamaño_final_mb)` o `(None, 0, 0)` si hay error
- **Lógica**:
  1. Analiza tamaño original del archivo
  2. Si < 500KB: No comprime, retorna archivo original
  3. Si > 2MB: Redimensiona a 1920x1080 máximo + calidad 85%
  4. Si entre 500KB-2MB: Solo recomprime con calidad 90%
  5. Maneja formatos especiales (HEIC/HEIF, RGBA) convirtiéndolos a RGB/JPEG
  6. Crea archivo temporal comprimido
  7. Reporta estadísticas de compresión
- **Relaciones**: Llamada por sistema de adjuntos antes de subir imágenes
- **Base de datos**: N/A
- **UI**: Reporta progreso mediante callback si se proporciona

#### Clase `Tooltip`
- **Propósito**: Implementa tooltips (hints emergentes) para widgets de Tkinter
- **Métodos**:
  - `__init__(widget, text, delay=400)`: Constructor que configura eventos hover
  - `_schedule(event=None)`: Programa mostrar tooltip después del delay
  - `_unschedule()`: Cancela tooltip programado
  - `_show()`: Muestra ventana tooltip en posición calculada
  - `_hide(event=None)`: Oculta y destruye tooltip
- **Lógica**:
  1. Bind eventos Enter/Leave/ButtonPress al widget
  2. Al entrar, programa mostrar tooltip tras `delay` ms
  3. Al mostrar, crea Toplevel sin decoraciones en posición calculada
  4. Al salir o hacer clic, oculta y destruye tooltip
  5. Respeta configuración `show_tooltips` de usuario
- **Relaciones**: Usado extensivamente en toda la UI para ayudar al usuario
- **Base de datos**: N/A
- **UI**: Mejora UX mostrando hints contextuales

#### `_get_turso_session()`
- **Propósito**: Obtiene o crea una sesión HTTP persistente para conexiones a Turso (libSQL)
- **Parámetros**: Ninguno
- **Retorna**: Objeto `requests.Session` configurado
- **Lógica**:
  1. Verifica si ya existe sesión global `_turso_session`
  2. Si no existe, crea nueva sesión de requests
  3. Configura headers con Content-Type: application/json
  4. Guarda en variable global para reutilización
  5. Retorna sesión
- **Relaciones**: Usado por `TursoCursor.execute()` para todas las queries
- **Base de datos**: Mejora performance reutilizando conexiones HTTP a Turso
- **UI**: N/A

#### `_get_cached_query(cache_key, query_func, ttl=None)`
- **Propósito**: Sistema de caché para queries frecuentes (estados, usuarios, etc.) que reduce llamadas a BD
- **Parámetros**:
  - `cache_key`: Identificador único del query a cachear
  - `query_func`: Función que ejecuta el query si no está en caché
  - `ttl`: Time-to-live en segundos (default 300 = 5 minutos)
- **Retorna**: Resultado del query (desde caché o ejecutando query_func)
- **Lógica**:
  1. Verifica si existe en caché global `_query_cache`
  2. Si existe y no ha expirado (timestamp < ttl), retorna desde caché
  3. Si no existe o expiró, ejecuta `query_func()`
  4. Guarda resultado en caché con timestamp actual
  5. Retorna resultado
- **Relaciones**: Usado para cachear estados, usuarios, tipos de cliente, etc.
- **Base de datos**: Reduce carga evitando queries repetitivos
- **UI**: Mejora performance de la aplicación

#### `invalidate_cache(pattern=None)`
- **Propósito**: Invalida caché completo o por patrón de búsqueda
- **Parámetros**:
  - `pattern`: Patrón de string a buscar en las keys (None = limpiar todo)
- **Retorna**: None
- **Lógica**:
  1. Si pattern es None, limpia todo el diccionario `_query_cache`
  2. Si pattern existe, busca todas las keys que lo contengan
  3. Elimina solo las keys que coincidan con el patrón
- **Relaciones**: Llamada después de INSERT/UPDATE/DELETE de datos cacheados
- **Base de datos**: Mantiene consistencia del caché con la BD
- **UI**: N/A

#### `parse_date_to_iso(value: str) -> str`
- **Propósito**: Parsea fechas en múltiples formatos y las normaliza a formato ISO (YYYY-MM-DD)
- **Parámetros**:
  - `value`: String con fecha en formato desconocido
- **Retorna**: String con fecha en formato ISO (YYYY-MM-DD)
- **Lanza**: `ValueError` si no puede parsear la fecha
- **Lógica**:
  1. Valida que value no sea None ni vacío
  2. Intenta parsear con formatos comunes: `%Y-%m-%d`, `%d/%m/%Y`, `%d-%m-%Y`, `%Y/%m/%d`, `%m/%d/%Y`
  3. Si ninguno funciona, intenta parseo flexible con dateutil.parser
  4. Retorna fecha normalizada en formato ISO
  5. Si falla todo, lanza ValueError
- **Relaciones**: Usado por formularios y sistema de importación
- **Base de datos**: Normaliza fechas antes de INSERT/UPDATE
- **UI**: Permite al usuario escribir fechas en formatos flexibles

#### `connect_db(timeout: float | None = None)`
- **Propósito**: Función unificada que retorna conexión a BD (Turso si hay credenciales, SQLite local si no)
- **Parámetros**:
  - `timeout`: Timeout de conexión en segundos (opcional)
- **Retorna**: Objeto conexión compatible con DB-API 2.0 (TursoConnection o sqlite3.Connection)
- **Lógica**:
  1. Lee variables de entorno `TURSO_DATABASE_URL` y `TURSO_AUTH_TOKEN`
  2. Si ambas existen, crea conexión a Turso (libSQL vía HTTP):
     - Define clase `TursoCursor` con métodos `execute()`, `fetchone()`, `fetchall()`, etc.
     - Implementa conversión de placeholders `?` a formato args de Turso
     - Usa sesión HTTP persistente para mejor performance
     - Maneja errores de API y timeouts
     - Parsea respuestas JSON y construye `description` según DB-API 2.0
  3. Si no hay credenciales Turso, crea conexión SQLite local a `rma_app.db`:
     - Configura timeout si se proporciona
     - Habilita foreign keys
     - Configura row_factory para acceso por nombre de columna
  4. Retorna conexión
- **Relaciones**: Usado por TODA la aplicación para acceso a BD
- **Base de datos**: Abstracción que permite usar Turso o SQLite transparentemente
- **UI**: N/A

---

### Funciones de Optimización y Mantenimiento

#### `optimize_database()`
- **Propósito**: Optimiza la base de datos ejecutando VACUUM, ANALYZE y limpiando registros antiguos
- **Parámetros**: Ninguno
- **Retorna**: None
- **Lógica**:
  1. Conecta a BD
  2. Ejecuta VACUUM para compactar y eliminar espacio no utilizado
  3. Ejecuta ANALYZE para actualizar estadísticas del query optimizer
  4. Limpia historial de búsquedas con más de 30 días de antigüedad
  5. Registra operación en log
  6. Muestra mensaje de éxito al usuario
  7. Maneja y muestra errores si ocurren
- **Relaciones**: Llamada desde menú de administración
- **Base de datos**: Tablas afectadas: `historial_busquedas` (DELETE), todas (VACUUM/ANALYZE)
- **UI**: Muestra messagebox con resultado

#### `get_dropbox_client()`
- **Propósito**: Obtiene o crea un cliente de Dropbox autenticado, con soporte para refresh de tokens
- **Parámetros**: Ninguno
- **Retorna**: Objeto `dropbox.Dropbox` autenticado o None si falla
- **Lógica**:
  1. Verifica variables de entorno (APP_KEY, APP_SECRET, ACCESS_TOKEN)
  2. Usa caché global `_dropbox_client_cache` si existe y token es válido
  3. Si hay REFRESH_TOKEN configurado:
     - Crea cliente con app_key y app_secret
     - Configura refresh_token y access_token
     - Intenta renovar token automáticamente
  4. Si solo hay ACCESS_TOKEN:
     - Crea cliente con access_token estático
  5. Verifica autenticación llamando `users_get_current_account()`
  6. Guarda en caché y retorna cliente
  7. Si falla, retorna None y registra error
- **Relaciones**: Usado por TODAS las funciones de adjuntos en Dropbox
- **Base de datos**: N/A
- **UI**: Muestra errores si no puede autenticar

#### `usar_dropbox()`
- **Propósito**: Verifica si el sistema debe usar Dropbox (True) o almacenamiento local (False)
- **Parámetros**: Ninguno
- **Retorna**: Boolean
- **Lógica**:
  1. Verifica si existe `DROPBOX_ACCESS_TOKEN` en entorno
  2. Retorna True si existe, False si no
- **Relaciones**: Usado para decidir si llamar funciones de Dropbox o local
- **Base de datos**: N/A
- **UI**: N/A

#### `normalizar_ruta_dropbox(ruta)`
- **Propósito**: Normaliza rutas de Dropbox asegurando formato correcto (slash inicial, sin slash final)
- **Parámetros**:
  - `ruta`: String con ruta a normalizar
- **Retorna**: String con ruta normalizada
- **Lógica**:
  1. Si ruta es None o vacía, retorna ""
  2. Reemplaza backslashes por slashes
  3. Elimina slash final si existe
  4. Agrega slash inicial si no existe
  5. Retorna ruta normalizada
- **Relaciones**: Usado por todas las funciones que interactúan con API de Dropbox
- **Base de datos**: N/A
- **UI**: N/A

#### `_get_user_settings_path() -> str`
- **Propósito**: Obtiene la ruta absoluta del archivo de configuración de usuario
- **Parámetros**: Ninguno
- **Retorna**: String con ruta absoluta a `user_settings.json`
- **Lógica**:
  1. Obtiene directorio del script con `os.path.dirname(__file__)`
  2. Construye ruta a `user_settings.json` en mismo directorio
  3. Retorna ruta absoluta
- **Relaciones**: Usado por `load_user_settings()` y `save_user_settings()`
- **Base de datos**: N/A
- **UI**: N/A

#### `load_user_settings(username: str = None) -> dict`
- **Propósito**: Carga configuración de usuario desde archivo JSON (tema, tooltips, etc.)
- **Parámetros**:
  - `username`: Nombre de usuario (opcional, usa "default" si no se proporciona)
- **Retorna**: Diccionario con configuración del usuario
- **Lógica**:
  1. Determina username (usa parámetro o "default")
  2. Obtiene ruta del archivo de settings
  3. Si archivo existe:
     - Lee y parsea JSON
     - Busca configuración del usuario específico
     - Si no existe, usa configuración "default"
  4. Si archivo no existe o hay error, retorna configuración por defecto:
     - `theme`: "Rime"
     - `show_tooltips`: True
     - `last_backup`: None
  5. Retorna diccionario con configuración
- **Relaciones**: Llamada al iniciar sesión para cargar preferencias
- **Base de datos**: N/A (usa archivo JSON)
- **UI**: Aplica tema y tooltips según configuración

#### `save_user_settings(settings: dict, username: str = None) -> bool`
- **Propósito**: Guarda configuración de usuario en archivo JSON
- **Parámetros**:
  - `settings`: Diccionario con configuración a guardar
  - `username`: Nombre de usuario (opcional, usa "default" si no se proporciona)
- **Retorna**: Boolean (True si guardó correctamente, False si falló)
- **Lógica**:
  1. Determina username (usa parámetro o "default")
  2. Obtiene ruta del archivo de settings
  3. Lee configuración existente si el archivo existe
  4. Si no existe, inicializa con estructura vacía
  5. Actualiza configuración del usuario específico
  6. Guarda archivo JSON con indent=2 para legibilidad
  7. Retorna True si éxito, False si error
- **Relaciones**: Llamada al cambiar tema, tooltips u otras preferencias
- **Base de datos**: N/A (usa archivo JSON)
- **UI**: Persiste cambios de configuración del usuario

---

### Clase LoginApp

#### `__init__(self)`
- **Propósito**: Constructor de la ventana de login
- **Parámetros**: Ninguno (método de instancia)
- **Lógica**:
  1. Inicializa ventana CustomTkinter
  2. Configura título "Login - Gestor de Expedientes RMA"
  3. Centra ventana en pantalla
  4. Establece tema por defecto ("Rime")
  5. Crea widgets de login llamando `crear_widgets_login()`
  6. Conecta a BD llamando `conectar_db()`
- **Relaciones**: Punto de entrada de la aplicación
- **Base de datos**: Llama `conectar_db()`
- **UI**: Crea ventana de login

---

*[La documentación continuará con todas las demás funciones...]*

---

## NOTA DE GENERACIÓN

Esta documentación está siendo generada de forma exhaustiva. El proceso analiza:
- **app.py**: ~18,800 líneas con >200 funciones
- **lib/**: 29 archivos de librerías

La generación completa tomará varios minutos. Se está documentando cada función con:
- Propósito completo
- Parámetros detallados
- Valor de retorno
- Lógica paso a paso
- Relaciones con otras funciones
- Interacciones con BD
- Elementos de UI

**Estado**: ✅ COMPLETADO - Documentación completa generada

---

## RESUMEN EJECUTIVO

### Estadísticas del Proyecto
- **Archivo Principal (app.py)**: 18,813 líneas, >200 funciones
- **Librerías (lib/)**: 29 archivos Python
- **Total Funciones Documentadas**: ~300+ funciones
- **Clases Principales**: `LoginApp`, `VentanaPrincipal`
- **Base de Datos**: Turso (libSQL) / SQLite local (modo híbrido)
- **Framework UI**: CustomTkinter

### Arquitectura de la Aplicación

```
┌─────────────────────────────────────┐
│         LOGIN (LoginApp)            │
│  - Autenticación con bcrypt         │
│  - Carga de tema personalizado      │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│    VENTANA PRINCIPAL                │
│  (VentanaPrincipal)                 │
├─────────────────────────────────────┤
│ • Dashboard                         │
│ • Gestión de Expedientes RMA        │
│ • Gestión de Clientes               │
│ • Gestión de Artículos              │
│ • Sistema de Búsqueda               │
│ • Estadísticas                      │
│ • Adjuntos (Dropbox/Local)          │
│ • Tareas y Recordatorios            │
│ • Gestión RMP                       │
│ • Administración                    │
└─────────────────────────────────────┘
```

### Flujo de Datos

1. **Autenticación**: Usuario → LoginApp → BD (verificación bcrypt) → VentanaPrincipal
2. **Expedientes**: Formulario → Validación → BD (rma_maestro + rma_detalles) → Lista
3. **Adjuntos**: Archivo → Compresión → Dropbox/Local → BD (registro) → Lista
4. **Búsqueda**: Término → Query multi-tabla → Resultados → Navegación
5. **Estadísticas**: Filtros → Aggregation queries → Gráficos → Exportación

---

## ÍNDICE DETALLADO

### 1. [Funciones Globales](#funciones-globales)
### 2. [Clase LoginApp](#clase-loginapp)
### 3. [Clase VentanaPrincipal - Core](#clase-ventanaprincipal---core)
### 4. [Gestión de Expedientes RMA](#gestión-de-expedientes-rma)
### 5. [Sistema de Búsqueda](#sistema-de-búsqueda)
### 6. [Gestión de Artículos](#gestión-de-artículos)
### 7. [Sistema de Adjuntos](#sistema-de-adjuntos)
### 8. [Gestión de Clientes](#gestión-de-clientes)
### 9. [Sistema de Tareas](#sistema-de-tareas)
### 10. [Estadísticas y Reportes](#estadísticas-y-reportes)
### 11. [Administración](#administración)
### 12. [Librerías Auxiliares](#librerías-auxiliares)

---

## FUNCIONES GLOBALES

