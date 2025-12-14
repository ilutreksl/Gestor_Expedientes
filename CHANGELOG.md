Cambios V.0.1.23 - ✨ Últimas mejoras implementadas:

- 📦 Mejorada la ficha de estado de producto. Permite filtrar por estado y por periodo de fecha. Añadido boton de imprimir.   Crea un HTML para la previsualizacion.
- 📦 Añadido boton de articulo dentro de la ficha de expedientes. Abre la ventana de los estados del articulo.
- 👤 Añadido boton en la ficha de expedientes, para acceder a la ficha de cliente.
- 👤 Mejorada la ficha de cliente.
- 📊 Añadida nueva estadistica: Por estado de expediente, rentabilidad y exportacion a excel.
- 📊 Añadida nueva estadistica: Por articulo y estado de articulo. Permite filtrar por estado y por estado de expediente. Ademas se puede exportar a excel los resultados.
      Permite ademas importar un excel, traido de otro programa para realizar comparativas de productos entre las ventas y los defectuosos.
- Añadido campo [[FECHA_RECEPCION]] a la plantilla de Generar Informe.
- 📊 Añadida estadisticas de calculo de dias por expediente. 
- 📊 Añadido dashboard dentro de la ventana de estadisticas para el calculo promedio por cliente. Se calcula solo, sobre los expedientes cerrados para un calculo seguro.
- 🤖 Añadida nueva columna en la ventana principal, mostrando la ultima actualizacion con prefijo para mostrar en que estado esta.
- 🤖 Corregido bug del boton de guardar nuevo expediente, no cambiaba de color naranja a verde.
- 🤖 El buscador global incluye busquedas en historial, tareas y resto de campos del expediente.
- 🔄 La creacion y edicion de los expedientes se realizan en una nueva ventana.
- 🔄 Se pueden abrir varios expedientes para poder trabajar simultaneamente.


Cambios V.0.1.10

💾 Cuando se guarda un nuevo expediente, si el campo documento cliente contiene las palabras e-mail, email, telefonico o telefonica, permite el guardado.


Cambios V.0.1.09

- Se ha eliminado las filas estilo cebra, para dejarlas en defecto por tema.


Cambios V.0.1.08

🤖 En la pestaña General de los expedientes, el campo Autorizacion permite seleccionar SI o NO, teniendo las siguientes condiciones:
    - Si se selecciona SI, se marca la fecha actual y sale ventana modal para seleccionar la persona que autoriza.
    - Si se selecciona NO, borra la fecha de Fecha Autorizacion y pone en valor por defecto en Autorizado Por.


Cambios V.0.1.07

- Ahora en la ventana de articulos, al pinchar en la referencia, se abre una nueva ventana donde muestra un listado del articulo con las cantidades por estado.
- Pinchando en el estado, se abre una nueva ventana mostrando los expdeientes asociados a dicho estado por articulo. Desde dicha ventana se puede editar el expediente.


Cambios V.0.1.05

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