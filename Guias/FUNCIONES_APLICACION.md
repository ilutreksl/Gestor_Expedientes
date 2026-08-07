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

La búsqueda global usa un único flujo (texto libre + filtros opcionales) y
muestra los resultados como un listado compacto (una fila fina por resultado),
no como tarjetas. Un clic en cualquier fila abre el expediente correspondiente
en una ventana aparte (`_abrir_editor_rma`).

#### `mostrar_busqueda_global(self)`
**Construye la interfaz**
- Barra de búsqueda de una sola fila (entry + Buscar + Limpiar + Filtros + Historial)
- Panel de filtros plegable (oculto por defecto, no reserva espacio en pantalla)
- Área de resultados (`CTkScrollableFrame`) a pantalla completa

#### `ejecutar_busqueda(self)`
**Búsqueda unificada (texto + filtros)**
- Valida fechas y que haya al menos un tipo de resultado incluido
- Llama `buscar_global(termino, filtros)`
- Muestra `mostrar_resultados()`
- Guarda en historial

#### `buscar_global(self, termino: str, filtros: dict) -> dict`
**Consulta las tablas seleccionadas en `filtros["tipos"]`**
- **Expedientes** (rma_maestro): búsqueda dinámica sobre todas las columnas
  de texto (vía `PRAGMA table_info`) + filtros por `estado`, `fecha_emision`,
  `cliente`, `numero_documento_cliente`, `rma_proveedor`
- **Productos** (rma_detalles, JOIN rma_maestro): búsqueda dinámica +
  filtros por `estado_producto`, `referencia_articulo` y los filtros del
  expediente padre
- **Historial** (rma_historial, JOIN rma_maestro)
- **Tareas** (tareas, LEFT JOIN rma_maestro por `codigo_rma`)
- **Returns**: `{expedientes: [], productos: [], historial: [], tareas: []}`

#### `mostrar_resultados(self, resultados: dict, termino: str, filtros: dict)`
**Renderiza resultados agrupados en filas compactas**
- Una sección por tipo con resultados, cada una con filas finas (icono,
  identificador, detalle, estado con color, fecha)
- Clic en una fila → abre el expediente en una ventana aparte

### Filtros avanzados

#### `crear_controles_filtros(self)`
**Panel de filtros (plegable, rejilla de 4 columnas)**
- Estado del expediente (dropdown, cargado dinámicamente desde la BD)
- Proveedor (entry, columna `rma_proveedor`)
- Rango de fechas de emisión (desde/hasta)
- Cliente y documento de cliente (entry)
- Estado del producto (dropdown, valores desde `OPCIONES["Estado_Producto"]`)
- Referencia del artículo (entry)
- Checkboxes "Incluir en resultados": Expedientes / Productos / Tareas / Historial
- Botones "Aplicar filtros" y "Limpiar filtros" (ambos llaman a `ejecutar_busqueda()` / `limpiar_filtros()`)

### Historial de búsquedas

#### `mostrar_historial_dropdown(self)`
Muestra un menú desplegable (no un panel fijo) con las últimas 10 búsquedas
- Llama `cargar_historial_busquedas()`
- Cada entrada ejecuta `usar_busqueda_historial()` al seleccionarla
- Incluye opción "Limpiar historial"

#### `usar_busqueda_historial(self, entrada: dict)`
**Repite una búsqueda guardada**
- Restaura término y filtros
- Ejecuta `ejecutar_busqueda()`

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
- Personas específicas de recepción (usadas también por el flujo de recepción por QR)
- Almacenadas en Turso (tabla `config_recepcion_qr`, columna `personas_recepcion`), no en JSON local — mismo interfaz pública que antes (`cargar_personas`, `guardar_personas`, `añadir_persona`, `eliminar_persona`, `editar_persona`)
- Import de `connect_db` diferido dentro de cada método (evita ciclo de importación con `lib/app_core.py`, que importa esta clase)

### lib/qr_recepcion.py
**Funciones**: `generar_url_recepcion(codigo_rma) -> str`, `generar_imagen_qr(codigo_rma, ruta_destino=None) -> str`
- Genera la URL firmada (HMAC-SHA256, `QR_RECEPCION_HMAC_SECRET`) que se codifica en el QR de recepción
- Genera la imagen PNG del QR (librería `qrcode`)
- Usado por `lib/autorizacion_docx.py` para insertar el QR en el cuadro de texto `[[QR]]` de la plantilla

### lib/dispositivos_qr_manager.py
**Clase**: `DispositivosQRManager`
- Genera y cancela PINs de un solo uso (`generar_pin`, `cancelar_pin`, `listar_pins_pendientes`)
- Lista y revoca dispositivos registrados (`listar_dispositivos`, `revocar_dispositivo`)
- Lee/edita configuración de recepción por QR: mensaje de Incidencias, intentos máximos de PIN, caducidad del PIN (`obtener_config`, `actualizar_config`)
- El registro real del dispositivo (validación del PIN, alta en `dispositivos_qr`) lo hace el Worker de Cloudflare, no esta clase — aquí solo se administra desde la app de escritorio

### lib/ui_mixins/dispositivos_qr_mixin.py
**Clase**: `DispositivosQRMixin`
- Pantalla de administración (`mostrar_gestor_dispositivos_qr`), solo accesible con rol admin/administrador
- Pestaña "Dispositivos y PINs": generar PIN, cancelar PIN pendiente, revocar dispositivo
- Pestaña "Configuración": mensaje de Incidencias, intentos máximos y caducidad del PIN
- Registrado en `mostrar_menu_admin` (`lib/ui_mixins/admin_mixin.py`) y en la herencia múltiple de `VentanaPrincipal` (`app.py`)

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

### lib/rich_text_editor.py
**Clase**: `RichTextEditor(tk.Frame)` — editor de texto enriquecido usado en el
campo "Observaciones Técnicas" de la ficha de expedientes (pestaña
Información Técnica).

- **Formato**: negrita, cursiva, subrayado, tachado, tamaño, familia de
  fuente, color de fuente, resaltado, alineación, sangría.
  - Fuente y tamaño por defecto: **Verdana Pro, 12pt** (`DEFAULT_FAMILY` /
    `DEFAULT_SIZE`).
- **Imágenes**: inserción desde archivo o desde los adjuntos del expediente
  (descarga de Backblaze B2 si aplica). Antes de insertarse, cada imagen pasa
  por el **editor de imágenes** (`lib/image_editor_dialog.py`) para poder
  recortarla o marcarla; se puede pulsar "Insertar imagen" sin tocar nada
  para insertarla tal cual.
- **Corrector ortográfico** (`lib/spellcheck_utils.py`): subraya en rojo las
  palabras no reconocidas mientras se escribe (con debounce). Botón
  "✓ Ortografía" en la barra de herramientas para activar/desactivar. Clic
  derecho sobre una palabra marcada → sugerencias de corrección o "Añadir al
  diccionario" (persiste en
  `Diccionarios/diccionario_personalizado_ortografia.json`).
  Requiere `pip install pyspellchecker`; si no está instalado, el botón no
  aparece y el editor funciona igual sin corrector.
  - **Idioma**: configurable en Ajustes de Usuario → pestaña "📋 General" →
    "Idioma del corrector ortográfico" (`user_settings["idioma_ortografia"]`,
    por defecto `"es"`). El cambio se aplica al momento, sin reiniciar la
    app. Idiomas disponibles: los que trae pyspellchecker de fábrica (es, en,
    fr, pt, de, it, nl, ru, ar, eu, fa, lv) — ver
    `spellcheck_utils.IDIOMAS_DISPONIBLES`. Solo español tiene el diccionario
    ampliado propio (tildes); el resto usa el diccionario básico de
    pyspellchecker.
- **Almacenamiento**: `get_content()` serializa todo (texto, formato,
  imágenes) como JSON en el campo `obs_tecnica` de `rma_maestro`. Las marcas
  de ortografía son solo visuales: nunca se guardan ni se exportan.
- **Ventana expandida**: botón "⛶ Expandir" abre una ventana grande con una
  segunda barra de herramientas (resaltado, alineación, tachado, sangría).

### lib/image_editor_dialog.py
**Clase**: `ImageEditorDialog(tk.Toplevel)` — ventana modal para recortar y
marcar una imagen antes de insertarla en `RichTextEditor`.

- **Herramientas**: recortar, rectángulo, flecha, lápiz (trazo libre), texto.
- Color y grosor configurables; deshacer (hasta 8 pasos) y restablecer a la
  imagen original.
- Devuelve la imagen resultante (`dlg.result`) en el atributo `result` tras
  cerrarse; `None` si se cancela.
- Si se edita una imagen que venía "desde adjuntos" (por nombre, no
  embebida), el resultado editado se guarda embebido en base64 en vez de
  como referencia, para no perder el recorte/las marcas al reabrir el
  expediente.

### lib/spellcheck_utils.py
**Corrector ortográfico en español** (envoltorio sobre `pyspellchecker`).

- `get_spellchecker()`: instancia compartida (se crea una sola vez). Combina
  el diccionario básico de `pyspellchecker` con
  `Diccionarios/es_palabras_frecuentes.txt` (~143.000 palabras, generado una
  única vez a partir de `wordfreq` — no hace falta tener `wordfreq`
  instalado para usar la app, solo se usó para generar ese fichero). Esto
  reduce mucho los falsos positivos frente al diccionario básico, que no
  reconocía formas verbales conjugadas de uso corriente (p.ej. "tiene").
- **Tildes**: al generar `es_palabras_frecuentes.txt` se podó a propósito la
  forma sin tilde de cada palabra que en el corpus real aparece claramente
  con más frecuencia acentuada (p.ej. "recepcion", "numero", "articulo",
  "codigo", "albaran", "gestion" quedan fuera del diccionario; solo se
  aceptan "recepción", "número", "artículo"...), así que un error de tilde en
  ese tipo de palabras sí se marca. Se respeta una lista de excepciones con
  los pares clásicos de "tilde diacrítica" del español donde ambas formas son
  palabras legítimas con significado distinto (el/él, tu/tú, mi/mí, se/sé,
  de/dé, si/sí, mas/más, aun/aún, solo/sólo, este/esté,
  que/qué, como/cómo, cuando/cuándo, donde/dónde, quien/quién, cual/cuál,
  cuanto/cuánto, porque/porqué...) y con conjugaciones verbales de uso muy
  frecuente que coinciden con la forma sin tilde de otra palabra (p.ej.
  "trabajo", "cambio", "espero", "abandono" no se marcan). El criterio usado
  para decidir qué podar: se compara la frecuencia de uso real (vía
  `wordfreq.zipf_frequency`) de la forma con tilde y sin tilde; si la que no
  lleva tilde es notablemente menos frecuente, se considera un error y se
  quita del diccionario.
- `detectar_palabras_incorrectas(texto)`: devuelve posiciones de palabras no
  reconocidas.
- `obtener_sugerencias(palabra)`: sugerencias de corrección, con la más
  probable primero (usa `SpellChecker.correction()`, que prioriza la misma
  palabra con la tilde correcta cuando aplica).
- `añadir_palabra_personalizada(palabra)`: persiste una excepción en
  `Diccionarios/diccionario_personalizado_ortografia.json`.
- **Limitación conocida**: fuera de la lista de excepciones y de las
  conjugaciones verbales muy frecuentes, algunas palabras poco comunes que
  coinciden con la forma sin tilde de otra (homógrafos) podrían no detectarse
  o, más raramente, marcarse cuando no tocaba. Para esos casos puntuales,
  "Añadir al diccionario" soluciona el problema para siempre.

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

### Diccionarios/diccionario_personalizado_ortografia.json
Palabras añadidas por los usuarios al corrector ortográfico del editor de
Observaciones Técnicas (ver `lib/spellcheck_utils.py`). Se crea la primera
vez que alguien usa "Añadir al diccionario".

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

### Recepción de paquetes por QR

Añadido en `rma_maestro`: columna `metodo_recepcion TEXT` (`NULL` / `'QR'` / `'Manual'`). Reutiliza las columnas ya existentes `fecha_recepcion` y `recepcionado_por` — el Worker las rellena igual que lo haría el flujo manual, solo añade `metodo_recepcion` para poder diferenciarlos en estadísticas.

### Tabla: dispositivos_qr
```sql
CREATE TABLE dispositivos_qr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT UNIQUE NOT NULL,       -- token opaco aleatorio, guardado como cookie en el móvil
    tipo TEXT NOT NULL CHECK (tipo IN ('almacen', 'personal')),
    nombre_persona TEXT,              -- solo si tipo = 'personal'
    fecha_registro TEXT NOT NULL,
    revocado INTEGER NOT NULL DEFAULT 0,
    fecha_revocado TEXT
)
```

### Tabla: pins_qr
```sql
CREATE TABLE pins_qr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pin TEXT NOT NULL,                -- 6 dígitos
    estado TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'usado', 'caducado', 'bloqueado')),
    creado_por TEXT NOT NULL,         -- usuario admin que lo generó
    fecha_creacion TEXT NOT NULL,
    fecha_caducidad TEXT NOT NULL,
    intentos_fallidos INTEGER NOT NULL DEFAULT 0,
    dispositivo_id INTEGER REFERENCES dispositivos_qr(id)
)
```

### Tabla: config_recepcion_qr
```sql
CREATE TABLE config_recepcion_qr (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- fila única
    personas_recepcion TEXT NOT NULL DEFAULT '[]',   -- JSON, gestionado por PersonasRecepcionManager
    mensaje_incidencias TEXT NOT NULL DEFAULT '',
    pin_max_intentos INTEGER NOT NULL DEFAULT 5,
    pin_caducidad_minutos INTEGER NOT NULL DEFAULT 15
)
```

### Tabla: auditoria_qr
```sql
CREATE TABLE auditoria_qr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    codigo_rma TEXT,
    resultado TEXT NOT NULL,   -- 'exito' | 'ya_registrado' | 'nombre_no_coincide' | 'firma_invalida' | 'expediente_no_encontrado'
    dispositivo_id INTEGER,
    detalle TEXT
)
```

Estas 4 tablas se crean con `scripts/setup_qr_recepcion.py` (idempotente, seguro de re-ejecutar).

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

# Recepción de paquetes por QR (Cloudflare Worker)
QR_RECEPCION_HMAC_SECRET=mismo_secreto_que_HMAC_SECRET_del_worker
QR_RECEPCION_WORKER_URL=https://tu-worker.tu-subdominio.workers.dev

# Cloudflare API (opcional, solo lectura de Analytics — panel de Storage)
CLOUDFLARE_API_TOKEN=token_con_permiso_account_analytics_read
CLOUDFLARE_ACCOUNT_ID=id_de_la_cuenta_cloudflare
```

### Worker de recepción por QR (Cloudflare)

Directorio `cloudflare-worker-recepcion/` (proyecto Node/Wrangler independiente, fuera del entorno Python):
```
cloudflare-worker-recepcion/
├── wrangler.toml       # name, main, compatibility_date
└── src/
    └── index.js        # Único archivo: rutas /r, /registro, /confirmar
```

- Se despliega con `wrangler deploy` desde ese directorio (requiere `wrangler login` una vez).
- Secretos configurados con `wrangler secret put <NOMBRE>` (nunca en el repo): `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN` (mismas credenciales que la app de escritorio), `HMAC_SECRET` (debe coincidir con `QR_RECEPCION_HMAC_SECRET` del `.env`), `DEVICE_TOKEN_SECRET` (reservado, no usado actualmente — los tokens de dispositivo son valores aleatorios opacos verificados por búsqueda en Turso, no firmados).
- Habla con Turso directamente por la misma API HTTP `v2/pipeline` que usa `lib/app_core.py::connect_db()` — no hay backend intermedio propio.
- **Precaución con `wrangler secret put` desde PowerShell**: `Write-Output $valor | wrangler secret put NOMBRE` puede colar un BOM UTF-8 al inicio del valor y romper la conexión a Turso (URL inválida). Usar redirección de archivo sin BOM (`wrangler secret put NOMBRE < archivo.txt`, con el archivo escrito en UTF-8 sin BOM) en su lugar — funciona sin problemas desde Git Bash.

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

