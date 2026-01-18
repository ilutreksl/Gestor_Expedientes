# Manual de Usuario - Gestor de Expedientes RMA

**Versión de la aplicación:** v1.0.11  
**Fecha:** Enero 2026  
**Destinado a:** Usuarios finales

---

## 📑 Índice

1. [Introducción](#introducción)
2. [Inicio de Sesión](#inicio-de-sesión)
3. [Pantalla Principal (Dashboard)](#pantalla-principal-dashboard)
4. [Trabajar con Expedientes RMA](#trabajar-con-expedientes-rma)
5. [Gestión de Clientes](#gestión-de-clientes)
6. [Gestión de Proveedores RMP](#gestión-de-proveedores-rmp)
7. [Búsqueda de Expedientes](#búsqueda-de-expedientes)
8. [Gestión de Artículos](#gestión-de-artículos)
9. [Adjuntar Archivos](#adjuntar-archivos)
10. [Tareas y Recordatorios](#tareas-y-recordatorios)
11. [Estadísticas e Informes](#estadísticas-e-informes)
12. [Configuración Personal](#configuración-personal)
13. [Preguntas Frecuentes](#preguntas-frecuentes)
14. [Consejos y Mejores Prácticas](#consejos-y-mejores-prácticas)

---

## Introducción

El **Gestor de Expedientes RMA** es una aplicación diseñada para facilitar la gestión completa de expedientes de devolución y reparación de productos (RMA = Return Merchandise Authorization).

### ¿Qué puedes hacer con esta aplicación?

- ✅ Crear y gestionar expedientes RMA
- ✅ Registrar clientes y su información
- ✅ Controlar artículos recibidos y su estado
- ✅ Adjuntar documentos, fotos y vídeos
- ✅ Buscar expedientes rápidamente
- ✅ Ver estadísticas y generar informes
- ✅ Gestionar tareas y recordatorios
- ✅ Enviar emails a clientes con adjuntos
- ✅ Asociar expedientes relacionados

### Requisitos previos

- Usuario y contraseña proporcionados por el administrador
- Conexión a internet (para almacenamiento en la nube)
- Recomendado: Pantalla de al menos 1366x768 píxeles

---

## Inicio de Sesión

### Paso 1: Abrir la aplicación

1. Haz doble clic en el icono de la aplicación
2. Espera a que aparezca la ventana de login

### Paso 2: Introducir credenciales

1. **Usuario**: Escribe tu nombre de usuario (sin espacios, sensible a mayúsculas)
2. **Contraseña**: Escribe tu contraseña (los caracteres se mostrarán como ●●●●)
3. Pulsa **Enter** o haz clic en el botón **"Iniciar Sesión"**

### ¿Qué pasa si olvido mi contraseña?

Contacta con el administrador del sistema para que te restablezca la contraseña.

### Problemas comunes al iniciar sesión

| Problema | Solución |
|----------|----------|
| "Usuario o contraseña incorrectos" | Verifica que estés escribiendo correctamente (mayúsculas/minúsculas) |
| La aplicación se queda pensando | Verifica tu conexión a internet |
| Error de conexión a la base de datos | Contacta con el administrador |

---

## Pantalla Principal (Dashboard)

Una vez iniciada la sesión, verás la pantalla principal dividida en tres partes:

### 1️⃣ Barra Superior
- **Logo de la empresa** (izquierda)
- **Título** "Gestor de Expedientes RMA"
- **Tu usuario y rol** (derecha)
- **Botones de utilidad**:
  - 📝 Ver cambios recientes
  - 🐛 Reportar problema
  - 🚪 Cerrar sesión

### 2️⃣ Panel Lateral (Menú Principal)

**Sección Principal:**
- 🏠 **Dashboard**: Volver a la pantalla de inicio
- ➕ **Nuevo Expediente**: Crear un nuevo RMA
- 📋 **Ver Expedientes**: Lista de todos los expedientes
- 🔍 **Búsqueda Avanzada**: Buscar con filtros

**Sección Gestión:**
- 👥 **Clientes**: Gestionar información de clientes
- 📦 **Artículos**: Ver artículos del sistema
- ✓ **Tareas**: Gestionar tareas pendientes (muestra número si hay pendientes)
- ✉ **Email**: Enviar emails a clientes

**Sección Estadísticas:**
- 📊 **Ver Estadísticas**: Informes y gráficos

**Sección Administración** (solo si eres administrador):
- ⚙ **Menú Admin**: Configuración avanzada
- 💾 **Backups**: Copias de seguridad
- 🎨 **Ajustes**: Personalización

### 3️⃣ Área Central (Contenido)

Aquí se muestra el contenido según la opción que hayas elegido del menú.

**Dashboard inicial muestra:**
- Tarjetas con estadísticas del año actual:
  - Total de expedientes
  - Expedientes completados
  - Expedientes pendientes
  - Tiempo promedio de resolución
  - Top 5 artículos más frecuentes
- Lista de artículos problemáticos

---

## Trabajar con Expedientes RMA

### Crear un Nuevo Expediente

#### Paso 1: Iniciar creación

1. Haz clic en el botón **➕ Nuevo Expediente** del menú lateral
2. Se abrirá un formulario con varias pestañas

#### Paso 2: Completar datos del expediente

En la pestaña **"Datos del Expediente"** encontrarás:

**Datos Generados Automáticamente:**
- **Número RMA**: Se genera automáticamente (no editable)
- **Fecha de Recepción**: Fecha actual por defecto

**Datos del Cliente:**
- **Nombre del Cliente** ⚠️ *Obligatorio*
- **Email del Cliente**: Para enviar notificaciones
- **Teléfono del Cliente**: Número de contacto
- **Número de Documento**: DNI/CIF del cliente
- **Tipo de Cliente**: Selecciona del desplegable (Particular, Empresa, etc.)

**Datos del Envío:**
- **Número de Albarán**: Número del documento de envío
- **Recogido Por**: Persona que recibió el envío
- **Autorizado Por**: Persona que autorizó la devolución

**Fechas:**
- **Fecha de Entrega Estimada**: Cuándo se espera devolver/reparar
  - *Consejo: Usa el selector de quincenas para facilitar la planificación*

**Información Adicional:**
- **Motivo**: Razón de la devolución (ej: "Producto defectuoso")
- **Observaciones**: Notas adicionales

**Estado:**
- ☑ **Marcar como autorizado**: Marca esta casilla si ya está autorizado

#### Paso 3: Añadir artículos

1. Cambia a la pestaña **"Artículos"**
2. En el formulario de artículos, completa:
   - **Referencia**: Código del artículo ⚠️ *Obligatorio*
   - **Cant. según documento**: Cantidad que indica el albarán
   - **Cant. entregada**: Cantidad realmente recibida
   - **Estado**: Selecciona el estado (Nuevo, Usado, Defectuoso, etc.)
   - **Precio Unitario**: Precio del artículo en euros
   - ☑ **Aplicar depreciación**: Marca si el artículo tiene depreciación
     - Si marcas esta opción, aparecerá un campo para el % de depreciación
   - **Precio Final**: Se calcula automáticamente según depreciación

3. Haz clic en **"Añadir Artículo"**
4. El artículo aparecerá en la lista inferior
5. Repite para añadir más artículos

**Gestión de artículos en la lista:**
- ✏️ **Editar**: Clic en el botón del lápiz para modificar
- ❌ **Eliminar**: Clic en la X roja para quitar de la lista

💡 **Consejo**: El precio final se actualiza automáticamente mientras escribes. Si aplicas depreciación del 20% a un artículo de 100€, el precio final será 80€.

#### Paso 4: Guardar el expediente

1. Haz clic en el botón **"Guardar RMA"** (parte inferior del formulario)
2. Verás un mensaje de confirmación
3. El sistema te llevará a la lista de expedientes

### Editar un Expediente Existente

1. Busca el expediente en la lista (botón **📋 Ver Expedientes**)
2. Haz clic en el botón **✏️ Editar** del expediente que quieres modificar
3. Se abrirá el mismo formulario pero con los datos ya cargados
4. Modifica lo que necesites
5. Haz clic en **"Actualizar RMA"**

⚠️ **Importante**: Todos los cambios quedan registrados en el historial (pestaña "Historial de Cambios")

### Ver Lista de Expedientes

1. Haz clic en **📋 Ver Expedientes** en el menú
2. Verás una tabla con todas las RMAs:
   - **Código RMA**: Número del expediente
   - 🔗 **Enlace**: Icono si tiene expedientes asociados
   - **Cliente**: Nombre del cliente
   - **Estado**: Estado actual con color
   - **Fecha Recepción**: Cuándo se recibió
   - **Fecha Entrega Est.**: Fecha estimada de entrega
   - **Días**: Días transcurridos desde la recepción
   - **Acciones**: Botones para abrir, editar, eliminar, etc.

#### Filtrar expedientes

Usa los controles superiores para filtrar:
- **Buscar**: Escribe cualquier término (nombre, código, etc.)
- **Estado**: Filtra por estado (Todos, Completado, Pendiente, etc.)
- **Año**: Filtra por año

💡 **Consejo**: Los filtros se aplican automáticamente al escribir o seleccionar

#### Seleccionar expedientes

- **Un clic**: Selecciona la fila (se marca con color)
- **Doble clic**: Abre el expediente para verlo completo

### Eliminar un Expediente

⚠️ **¡CUIDADO!** Esta acción no se puede deshacer.

1. Busca el expediente en la lista
2. Haz clic en el botón **🗑️ Eliminar**
3. Confirma la eliminación en el mensaje que aparece
4. El expediente y todos sus datos se borrarán (artículos, adjuntos, tareas, etc.)

### Asociar Expedientes Relacionados

A veces varios expedientes están relacionados entre sí (ej: devolución múltiple del mismo cliente).

1. Abre un expediente
2. Ve a la pestaña **"Asociaciones RMA"**
3. Haz clic en **"Nueva Asociación"**
4. Busca y selecciona el expediente a asociar
5. Escribe el motivo de la asociación
6. Guarda

**Beneficio**: Los expedientes asociados muestran el icono 🔗 en la lista y puedes navegar entre ellos fácilmente.

---

## Gestión de Clientes

### Ver Lista de Clientes

1. Haz clic en **👥 Clientes** en el menú
2. Verás tarjetas con la información de cada cliente:
   - Nombre
   - Estado (Activo/Inactivo)
   - Total de RMAs
   - Última actividad

### Buscar un Cliente

Usa la barra de búsqueda superior para filtrar por:
- Nombre
- Email
- Teléfono

### Crear un Nuevo Cliente

1. Haz clic en **"Nuevo Cliente"**
2. Completa el formulario:
   - **Nombre** ⚠️ *Obligatorio*
   - **Email**: Para enviar notificaciones
   - **Teléfono**: Número de contacto
   - **Dirección**: Dirección completa
   - **CIF/NIF**: Identificación fiscal
   - **Tipo de Cliente**: Selecciona del desplegable
   - **Notas**: Información adicional
3. Haz clic en **"Guardar"**

### Ver Ficha Completa de un Cliente

1. **Un clic** en la tarjeta del cliente para seleccionarlo
2. **Doble clic** para abrir su ficha completa

La ficha tiene varias pestañas:

**1. Información:**
- Datos generales (editables)
- Botón "Guardar cambios" tras modificar

**2. Expedientes:**
- Historial de todos los RMAs del cliente
- Estadísticas de sus expedientes

**3. Estadísticas:**
- Gráficos y métricas del cliente
- Frecuencia de RMAs
- Tiempo promedio de resolución

**4. Condiciones Especiales:**
- Descuentos personalizados
- Plazos especiales
- Prioridades

**5. Rentabilidad:**
- Análisis coste-beneficio
- Histórico de facturación

### Editar Datos de un Cliente

Desde la ficha del cliente:
1. Modifica los campos que necesites
2. Haz clic en **"Guardar cambios"**

### Desactivar un Cliente

Si un cliente ya no trabaja contigo pero quieres conservar su historial:
1. Abre su ficha
2. Desmarca **"Activo"**
3. Guarda cambios

Los clientes inactivos aparecen con color gris en la lista.

---

## Gestión de Proveedores RMP

El módulo de **Proveedores RMP** (Return to Manufacturer Proveedor) te permite gestionar las devoluciones a proveedores de forma organizada mediante pestañas.

### Acceder a la Ventana de Proveedores

1. Haz clic en el botón **📦 RMP** del menú lateral
2. Se abrirá una ventana con la lista de todos los proveedores

### Ver Detalle de un Proveedor

1. En la lista de proveedores, haz clic en el nombre del proveedor que quieres consultar
2. Se abrirá una ventana con 5 pestañas organizadas:

#### 📋 Pestaña "General"

Muestra todos los expedientes asociados al proveedor:

- **Listado de expedientes**: Código RMA, cliente, fecha y estado
- **Acciones disponibles**:
  - **Editar**: Abre el expediente en una ventana independiente
  - **Doble clic**: También abre el expediente
- **Exportar a Excel**: Genera un archivo Excel con todos los expedientes del proveedor
  - El archivo se guarda en: `Adjuntos_RMA/RMP/`
  - Se sube automáticamente a Dropbox (si está configurado)
  - Queda registrado en el historial

💡 **Consejo**: Usa la exportación a Excel para enviar listados al proveedor.

#### 💰 Pestaña "Contabilidad"

Gestiona la información contable del proveedor:

- **Factura de Abono**: Número de la factura recibida del proveedor
  - Escribe el número de factura
  - Haz clic en **💾 Guardar Factura**
  
💡 **Uso práctico**: Cuando el proveedor te envíe la factura de abono, regístrala aquí para tener todo centralizado.

#### 📎 Pestaña "Adjuntos"

Gestiona los archivos relacionados con el proveedor almacenados en Dropbox:

**Listar archivos**:
- La pestaña muestra automáticamente todos los archivos del proveedor que hay en Dropbox
- Se muestran archivos que empiezan con el nombre del proveedor
- Información visible: Nombre del archivo, tamaño, fecha de modificación

**Acciones con archivos**:
- **👁️ Visualizar**: Abre el archivo para verlo (se descarga temporalmente)
- **⬇️ Descargar**: Guarda el archivo en tu ordenador
  - Elige la ubicación donde guardarlo
  - El archivo se descarga con su nombre original
- **🗑️ Eliminar**: Borra el archivo de Dropbox
  - ⚠️ Pide confirmación antes de eliminar
  - Esta acción no se puede deshacer

**Subir nuevos archivos**:
1. Haz clic en **📤 Subir Archivo**
2. Selecciona el archivo de tu ordenador
3. El archivo se sube a Dropbox con el formato: `{NombreProveedor}_{NombreArchivo}`
4. Haz clic en **🔄 Actualizar** para ver el nuevo archivo en la lista

💡 **Tipos de archivos comunes**:
- Facturas de abono del proveedor (.pdf)
- Albaranes de envío (.pdf)
- Emails de comunicación (.eml, .pdf)
- Fotos de productos (.jpg, .png)
- Hojas de cálculo (.xlsx)

⚠️ **Importante**: 
- Los archivos deben estar en la carpeta `/RMP` de Dropbox
- El nombre del archivo debe empezar con el nombre del proveedor para aparecer aquí
- Necesitas tener Dropbox configurado correctamente

#### 📜 Pestaña "Historial"

Muestra un registro cronológico de todas las acciones realizadas con el proveedor:

**Información del historial**:
- 📅 Fecha y hora del evento
- 👤 Usuario que realizó la acción
- 🏷️ Estado relacionado (si aplica)
- 📝 Descripción del evento

**Eventos registrados automáticamente**:
- Cambios de estado del proveedor
- Exportaciones a Excel
- Modificaciones de datos

**Añadir comentarios manualmente**:
1. Escribe tu comentario en el cuadro de texto inferior
2. Haz clic en **💬 Añadir Comentario**
3. El comentario aparecerá inmediatamente en el historial

💡 **Usos del historial**:
- Seguimiento de comunicaciones con el proveedor
- Registro de incidencias
- Notas sobre acuerdos o condiciones especiales
- Documentar llamadas telefónicas

**Ejemplo de comentario útil**:
```
Llamada con el proveedor - Confirmaron recepción de 5 artículos.
Enviarán factura de abono la próxima semana. Referencia: FA2025-123
```

#### ✓ Pestaña "Tareas"

Gestiona las tareas y recordatorios relacionados con el proveedor:

**Ver tareas existentes**:
- **Listado de tareas**: Título, descripción, fecha de vencimiento y estado
- **Filtrar por estado**: Usa el desplegable para ver solo tareas pendientes, en progreso o completadas
- **Código de colores**:
  - 🟠 **Pendiente**: Tarea por hacer
  - 🔵 **En Progreso**: Tarea en curso
  - 🟢 **Completado**: Tarea finalizada

**Crear nueva tarea**:
1. Haz clic en **➕ Nueva Tarea**
2. Completa el formulario:
   - **Título** ⚠️ *Obligatorio*: Nombre corto de la tarea
   - **Descripción**: Detalles adicionales
   - **Fecha de vencimiento**: Formato DD/MM/AAAA (opcional)
3. Haz clic en **Guardar**

**Gestionar tareas**:
- **Cambiar estado**: Usa el desplegable en cada tarea para cambiar su estado
- **🗑️ Eliminar**: Borra la tarea (pide confirmación)

💡 **Ejemplos de tareas útiles**:
- "Llamar al proveedor para confirmar recepción"
- "Enviar albarán firmado al email del proveedor"
- "Revisar factura de abono cuando llegue"
- "Hacer seguimiento del envío - tracking XYZ123"

**Diferencia con tareas de expedientes**:
- Las tareas de proveedores son globales al proveedor
- Las tareas de expedientes son específicas de un RMA concreto

### Encabezado de la Ventana

En la parte superior de la ventana de detalle del proveedor verás:

- **Nombre del Proveedor**: Siempre visible
- **Estado del Proveedor**: Menú desplegable con opciones:
  - "" (Vacío)
  - En Progreso
  - Enviado
  - Completado
  - Exportado
  
Al cambiar el estado:
- Se guarda automáticamente
- Se registra en el historial
- Se actualiza en la lista principal

### Flujo de Trabajo Recomendado

1. **Crear/Recibir expedientes** con el mismo proveedor
2. **Abrir la ficha del proveedor** (botón RMP)
3. **Revisar expedientes** en la pestaña General
4. **Exportar a Excel** cuando tengas varios expedientes listos
5. **Subir documentos** del proveedor a la pestaña Adjuntos
6. **Crear tareas** para hacer seguimiento
7. **Actualizar estado** conforme avanza el proceso:
   - `En Progreso`: Estás preparando el envío
   - `Enviado`: Ya enviaste los artículos al proveedor
   - `Completado`: El proveedor procesó todo
   - `Exportado`: Ya generaste el Excel final
8. **Registrar factura** cuando llegue en Contabilidad
9. **Añadir comentarios** al historial con información relevante

### Preguntas Frecuentes - Proveedores

**P: ¿Por qué no veo archivos en la pestaña Adjuntos?**  
R: Los archivos deben estar en Dropbox, en la carpeta `/RMP`, y el nombre del archivo debe empezar con el nombre exacto del proveedor.

**P: ¿Puedo editar un expediente desde la ventana de proveedor?**  
R: Sí, haz clic en "Editar" o doble clic en el expediente. Se abrirá en una ventana independiente y la ventana del proveedor permanecerá abierta.

**P: ¿Se sincronizan las tareas de proveedores con las de expedientes?**  
R: No, son independientes. Las tareas de proveedores son para gestión global, las de expedientes para cada RMA específico.

**P: ¿Cómo sé si tengo tareas pendientes de un proveedor?**  
R: Cuando abras la ventana del proveedor y vayas a la pestaña Tareas, verás el contador de tareas por estado.

---

## Búsqueda de Expedientes

La aplicación tiene dos sistemas de búsqueda:

### 🔍 Búsqueda Rápida (Barra Superior)

Para búsquedas simples y rápidas:

1. Haz clic en la barra de búsqueda de la parte superior
2. Escribe cualquier término: nombre de cliente, código RMA, artículo, etc.
3. Pulsa **Enter**
4. Verás resultados agrupados en secciones:
   - **Expedientes**: RMAs que coinciden
   - **Productos**: Artículos que coinciden
   - **Historial**: Cambios registrados
   - **Tareas**: Tareas relacionadas

💡 **Consejo**: La búsqueda busca en TODOS los campos, así que puedes escribir cualquier dato que recuerdes.

### 🔍 Búsqueda Avanzada (Con Filtros)

Para búsquedas más precisas:

1. Haz clic en **🔍 Búsqueda Avanzada** en el menú
2. Completa los filtros que necesites:
   - **Término de búsqueda**: Palabra clave
   - **Estado**: Filtrar por estado específico
   - **Fecha desde/hasta**: Rango de fechas
   - **Cliente**: Nombre del cliente
   - **Código RMA**: Número específico
   - **Artículo**: Referencia de artículo
3. Haz clic en **"Buscar"**

**Botones útiles:**
- **Limpiar filtros**: Resetea todos los filtros
- **Expandir/Contraer filtros avanzados**: Muestra u oculta más opciones

### Historial de Búsquedas

La aplicación guarda tus últimas 10 búsquedas:

1. En la pantalla de búsqueda, mira el panel **"Historial de Búsquedas"**
2. Haz clic en **"Repetir"** para volver a ejecutar una búsqueda anterior
3. Haz clic en **"✕"** para eliminar una búsqueda del historial

**Limpiar todo el historial:**
- Haz clic en "Limpiar historial completo" en la parte inferior del panel

---

## Gestión de Artículos

### Ver Todos los Artículos del Sistema

1. Haz clic en **📦 Artículos** en el menú
2. Verás una lista de todas las referencias que han pasado por el sistema

### Buscar un Artículo Específico

Usa la barra de búsqueda para filtrar por referencia.

### Ver Información de un Artículo

Para cada artículo puedes ver:
- **Total de incidencias**: Cuántas veces ha aparecido en expedientes
- **Estados frecuentes**: En qué estados suele venir
- **Expedientes**: Lista de RMAs que lo incluyen

**Botones disponibles:**
- **Ver Estados**: Distribución de estados de ese artículo
- **Ver Expedientes**: Lista completa de RMAs con ese artículo

---

## Adjuntar Archivos

Los adjuntos te permiten guardar documentos, fotos y vídeos relacionados con cada expediente.

### Tipos de Archivos Soportados

- 📄 **Documentos**: PDF, Word, Excel, etc.
- 🖼️ **Imágenes**: JPG, PNG, HEIC, etc.
- 🎥 **Vídeos**: MP4, MOV, AVI, etc.
- 📊 **Otros**: Cualquier tipo de archivo

### Añadir un Adjunto

1. Abre el expediente que quieres editar
2. Ve a la pestaña **"Adjuntos"**
3. Haz clic en **"Añadir Adjunto"**
4. Selecciona el archivo de tu ordenador
5. **Espera mientras se procesa**:
   - 🖼️ Las imágenes grandes se comprimen automáticamente
   - 🎥 Los vídeos grandes se comprimen si es necesario
   - Verás una barra de progreso
6. Una vez completado, el archivo aparecerá en la lista

💡 **Ventaja**: La compresión automática ahorra espacio y tiempo de subida sin perder calidad apreciable.

### Ver un Adjunto

1. Ve a la pestaña "Adjuntos" del expediente
2. Haz clic en **📂 Abrir** junto al archivo que quieras ver
3. El archivo se descargará (si está en la nube) y se abrirá con su aplicación por defecto

### Editar un Adjunto (Solo Dropbox)

Si necesitas modificar un archivo que ya subiste:

1. Haz clic en **✏️ Editar** junto al archivo
2. El archivo se descargará y se abrirá automáticamente
3. Modifica el archivo con su aplicación (Word, Photoshop, etc.)
4. **Guarda los cambios** en la aplicación
5. Vuelve al Gestor RMA
6. La aplicación detecta los cambios y te pregunta: **"¿Subir cambios?"**
7. Confirma para actualizar el archivo en la nube

⚠️ **Importante**: Mantén abierta la ventana de seguimiento hasta que termines de editar.

### Eliminar un Adjunto

⚠️ **CUIDADO**: Esta acción no se puede deshacer.

1. Haz clic en **🗑️ Eliminar** junto al archivo
2. Confirma la eliminación
3. El archivo se borrará tanto de la nube como del registro

### Abrir la Carpeta del Expediente

Si quieres ver todos los archivos de golpe:

1. Haz clic en **"Abrir Carpeta"** en la pestaña de adjuntos
2. Se abrirá el explorador de archivos con la carpeta del expediente

---

## Tareas y Recordatorios

Las tareas te ayudan a recordar acciones pendientes para cada expediente.

### Ver Tareas Pendientes

En el menú lateral, el botón **✓ Tareas** muestra un **número rojo** si tienes tareas pendientes.

### Ver Todas las Tareas

1. Haz clic en **✓ Tareas** en el menú
2. Verás una lista de todas las tareas con:
   - **RMA**: Expediente relacionado
   - **Descripción**: Qué hay que hacer
   - **Fecha límite**: Cuándo vence
   - **Estado**: Pendiente o Completada

**Filtros disponibles:**
- Mostrar: Todas / Pendientes / Completadas
- Por expediente específico
- Por rango de fechas

### Crear una Nueva Tarea

Desde la vista de tareas:
1. Haz clic en **"Nueva Tarea"**
2. Completa:
   - **RMA**: Selecciona el expediente
   - **Descripción**: Qué hay que hacer
   - **Fecha límite**: Cuándo vence
3. Guarda

**Desde un expediente:**
1. Abre el expediente
2. Ve a la pestaña **"Tareas"**
3. Haz clic en **"Añadir Tarea"**
4. Completa descripción y fecha límite
5. Guarda

### Marcar una Tarea como Completada

- En la lista de tareas, haz clic en **☑️ Marcar completada**
- Las tareas completadas aparecen con una marca verde ✅

### Editar o Eliminar una Tarea

- **Editar**: Haz clic en el botón **✏️** para modificar
- **Eliminar**: Haz clic en **🗑️** para borrar

### Notificaciones de Tareas Vencidas

⏰ **Automático**: Cada 30 minutos, la aplicación comprueba si hay tareas vencidas y te avisa con un mensaje.

---

## Estadísticas e Informes

### Ver Dashboard General

1. Haz clic en **🏠 Dashboard** en el menú
2. Verás tarjetas con las estadísticas del año actual

**Para cambiar de año:**
- Usa el selector de año en la parte superior del dashboard

### Estadísticas Detalladas

1. Haz clic en **📊 Ver Estadísticas** en el menú
2. Selecciona el tipo de estadística que quieres ver:
   - **Artículos**: Productos más frecuentes, estados, tendencias
   - **Anuales**: Comparativa por años, evolución mensual
   - **Resolución**: Tiempos de respuesta, eficiencia
   - **Por Quincena**: Expedientes agrupados por quincenas
   - **Recepciones Anticipadas**: Análisis de anticipación

### Exportar Estadísticas

La mayoría de estadísticas tienen un botón **"Exportar a Excel"**:
1. Haz clic en el botón
2. Elige dónde guardar el archivo
3. Se abrirá automáticamente Excel con los datos

### Imprimir Informes PDF

Algunos informes tienen opción de **"Imprimir PDF"**:
1. Haz clic en el botón
2. Se genera un PDF con el informe formateado
3. Elige dónde guardarlo

---

## Configuración Personal

### Cambiar el Tema de la Aplicación

1. Haz clic en **🎨 Ajustes** en el menú
2. En la sección **"Tema"**, selecciona tu tema favorito:
   - **Rime**: Tema claro (por defecto)
   - **Midnight**: Tema oscuro
   - **Autumn**: Tonos otoñales
   - **Lavender**: Tonos morados
   - Y muchos más...
3. El cambio se aplica inmediatamente
4. Tu preferencia se guarda automáticamente

💡 **Consejo**: Si trabajas de noche, prueba un tema oscuro para reducir la fatiga visual.

### Activar/Desactivar Tooltips

Los **tooltips** son esos mensajes de ayuda que aparecen al pasar el ratón sobre los botones.

1. En **Ajustes**, busca la opción **"Mostrar tooltips"**
2. Marca o desmarca la casilla según prefieras
3. Se guarda automáticamente

### Configurar Backups Automáticos (Administradores)

Si eres administrador:
1. Ve a **💾 Backups**
2. Configura la frecuencia de backups automáticos
3. Selecciona dónde guardar las copias

---

## Preguntas Frecuentes

### ❓ ¿Cómo sé si un expediente tiene archivos adjuntos?

En la lista de expedientes, mira la columna de acciones. Si hay adjuntos, verás el icono 📎 junto al número de archivos.

### ❓ ¿Puedo trabajar sin conexión a internet?

**Depende del almacenamiento**:
- **Almacenamiento local**: Sí, funciona sin internet
- **Almacenamiento Dropbox**: No, necesitas internet para subir/descargar adjuntos

El resto de funciones (crear expedientes, artículos, etc.) funcionan sin internet si usas base de datos local.

### ❓ ¿Cuánto espacio ocupan los adjuntos?

- **Con compresión automática**: Las imágenes se reducen hasta un 80% y los vídeos hasta un 70%
- **Sin compresión**: Los archivos pequeños (<500KB) no se comprimen

💡 Puedes ver el espacio total usado en la sección de Backups (administradores).

### ❓ ¿Puedo recuperar un expediente eliminado?

Sí, si se hacen backups regularmente:
1. Contacta con el administrador
2. Él puede restaurar un backup anterior
3. ⚠️ Se perderán los cambios posteriores al backup

### ❓ ¿Por qué algunos botones están deshabilitados?

Depende de tu **rol de usuario**:
- **Usuario normal**: Acceso a funciones básicas
- **Administrador**: Acceso completo

Si necesitas más permisos, contacta con el administrador.

### ❓ ¿Cómo envío un email a un cliente?

1. Abre el expediente del cliente
2. Haz clic en **✉ Enviar Email**
3. Selecciona los adjuntos que quieres incluir
4. Se abrirá tu cliente de correo (Outlook, Gmail, etc.) con todo preparado
5. Revisa y envía

💡 El email incluye automáticamente el número de RMA en el asunto.

### ❓ ¿Qué hago si la aplicación se queda bloqueada?

1. Espera 30 segundos por si está procesando algo (compresión de archivo grande, etc.)
2. Si sigue bloqueada, cierra la aplicación con Ctrl+Alt+Supr → Administrador de tareas
3. Vuelve a abrirla
4. Si ocurre frecuentemente, contacta con el administrador

### ❓ ¿Puedo ver qué cambios se hicieron en un expediente?

Sí, cada expediente tiene un **Historial de Cambios**:
1. Abre el expediente
2. Ve a la pestaña **"Historial de Cambios"**
3. Verás una lista cronológica de todas las modificaciones:
   - Qué campo se cambió
   - Valor antiguo y nuevo
   - Quién lo cambió
   - Cuándo se cambió

---

## Consejos y Mejores Prácticas

### ✅ Organización de Expedientes

1. **Usa nombres descriptivos** para los clientes (ej: "Empresa ACME S.L." mejor que "ACME")
2. **Completa siempre el motivo** del RMA para futuras referencias
3. **Añade observaciones** si hay algo especial que recordar
4. **Asocia expedientes relacionados** para tener contexto completo

### ✅ Gestión de Artículos

1. **Usa referencias consistentes**: Decide un formato y úsalo siempre (ej: "ART-12345")
2. **Completa el estado** de cada artículo para estadísticas precisas
3. **Aplica depreciación** cuando corresponda para cálculos correctos

### ✅ Adjuntos

1. **Nombre descriptivo** a los archivos antes de subirlos (ej: "foto_producto_dañado_1.jpg")
2. **Sube fotos del estado** del producto recibido (protección legal)
3. **Organiza por tipo**: Primero docs, luego fotos, luego vídeos
4. **No subas archivos innecesarios** para ahorrar espacio

### ✅ Tareas

1. **Crea tareas para todo** lo que no puedas hacer inmediatamente
2. **Sé específico** en las descripciones (ej: "Llamar a cliente para confirmar dirección" mejor que "Llamar")
3. **Usa fechas límite realistas** para evitar estrés innecesario
4. **Revisa tareas diariamente** al iniciar la jornada

### ✅ Búsquedas

1. **Usa búsqueda rápida** para consultas puntuales
2. **Usa búsqueda avanzada** cuando busques combinaciones específicas
3. **Aprovecha el historial** para búsquedas recurrentes
4. **Prueba sinónimos** si no encuentras lo que buscas (ej: "defectuoso" vs "roto")

### ✅ Rendimiento

1. **Cierra expedientes completados** para liberar memoria
2. **Evita tener múltiples ventanas** de la aplicación abiertas
3. **Comprime imágenes grandes** antes de subirlas si tienes problemas de velocidad
4. **Limpia el historial de búsquedas** periódicamente

### ✅ Seguridad

1. **Cierra sesión** al terminar tu jornada
2. **No compartas tu contraseña** con nadie
3. **Verifica los datos** antes de eliminar expedientes
4. **Haz backups** regulares (administradores)

### ✅ Trabajo en Equipo

1. **Usa observaciones** para comunicarte con otros usuarios
2. **Marca expedientes autorizados** para que otros sepan el estado
3. **Actualiza fechas estimadas** si hay cambios para evitar confusiones
4. **Asocia RMAs relacionados** para que otros vean el contexto

---

## Atajos de Teclado

| Atajo | Acción |
|-------|--------|
| **Enter** | Confirmar / Buscar |
| **Esc** | Cancelar / Cerrar diálogo |
| **Ctrl + S** | Guardar (en formularios) |
| **Ctrl + F** | Ir a búsqueda rápida |
| **Tab** | Siguiente campo |
| **Shift + Tab** | Campo anterior |

---

## Soporte y Ayuda

### ¿Necesitas ayuda adicional?

1. **Consulta este manual** primero
2. **Pregunta a un compañero** con experiencia
3. **Contacta con el administrador** para problemas técnicos
4. **Reporta errores** usando el botón 🐛 en la barra superior

### Reportar un Problema

1. Haz clic en el botón **🐛** (parte superior derecha)
2. Describe el problema:
   - ¿Qué estabas intentando hacer?
   - ¿Qué pasó?
   - ¿Qué esperabas que pasara?
3. Añade capturas de pantalla si es posible
4. Envía el reporte

---

## Actualizaciones

### ¿Cómo sé si hay una nueva versión?

1. Haz clic en el botón **📝 Ver cambios** (parte superior derecha)
2. Si hay novedades, verás una lista de las nuevas funciones y mejoras
3. Las actualizaciones se instalan automáticamente

### ¿Qué hacer después de una actualización?

1. Lee los cambios en el CHANGELOG
2. Prueba las nuevas funciones
3. Reporta cualquier problema que encuentres

---

**¿Listo para empezar?** 🚀

Comienza por crear tu primer expediente RMA y explora las diferentes funciones. ¡La práctica hace al maestro!

---

*Versión del manual: 1.0 - Enero 2026*  
*Si encuentras errores en este manual o quieres sugerir mejoras, contacta con el administrador.*
