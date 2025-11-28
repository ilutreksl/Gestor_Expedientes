Cambios V.0.1.05 - ✨ Últimas mejoras implementadas:

- Corregido error que no guardaba los resultados de los expedientes (Euros) en la BD.
- Corregida la estadistica de Rentabilidad por Cliente. Incluye exportacion a Excel.


Cambio V.0.1.04

Ajustado las columnas del listado de articulos.


Cambios V.0.1.03

🔄 Añadido boton para editar los articulos ya añadidos al expediente.
🔄 Pulsa INTRO permite añadir o actualizar articulos.


Cambios V.0.1.02

Correccion de errores.


Cambios V.0.1.01 

El campo de Numero Documento Cliente se mantiene editable si contiene las palabras: Email, Telefinica o Telefonico.
De esta manera se podra añadir mas adelante el numero correcto del cliente.


Cambios V.0.1.00

* Changelog Window: changelog_window.py: nueva ventana que muestra el historial de cambios.


🔄 Actualizar RMA: al actualizar un expediente solo se muestra un único mensaje de éxito y el formulario permanece abierto (no vuelve a la lista).


* Listado de expedientes: eliminada la columna Acciones; ahora un doble clic en cualquier punto de la fila abre el expediente; filas usan cursor hand2.

Atajo global F5: refresca el listado de expedientes desde la ventana principal.
Atajo global Ctrl + n: Crea un nuevo expediente.
Atajo global Ctrl + F: Abre la ventana de buscar avanzada.

💾 Backups: flujo “Turso-first” para volcados remotos cuando hay credenciales; logs de backup persistentes en logs/backups/.

🤖 Tareas: añadí filtro “Filtrar por Usuario” en la ventana de gestión de tareas para filtrar por creador.



Cambios V.0.0.94

🔄 Sistema de trazabilidad automática "En Trámite"
📊 Dashboard analítico con estadísticas en tiempo real
🤖 Confirmaciones inteligentes con validación de tareas
📊 Análisis de artículos problemáticos por períodos
💾 Soporte para decimales en cantidades de artículos
📤 Exportación Excel mejorada con formato profesional