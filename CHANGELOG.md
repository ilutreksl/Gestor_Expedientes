- Migracion de Dropbox a Backblaze B2 (1.0.22)


Cambio V.1.0.21 - ✨ Últimas mejoras implementadas:

- Añadida en la columna de estadisticas, el almacenamiento de las nubes utilizadas por la aplicacion.
- Modificado titulos de la ventana de expedientes.
- Añadido boton "Descargar" en la pestaña de adjuntos de la ficha de expedientes.
- Se han recortado los botones de los adjuntos a solo iconos para dejar mas espacio al titulo del archivo.
- Cambios visuales:
    * Ventana de Login centrada a la pantalla.
    * Añadido padding de 15px entre el titulo y las pestañas en la ventana de expedientes.
    * Eliminada estadisticas de articulos problematicos de la ventana principal.
    * Añadida confirmacion de cierre de la aplicacion.
- Las referencias de los articulos en los expedientes, siempre se guardan en mayusculas.


Cambio V.1.0.15

- Añadido filtros y busqueda en el historial de cada expediente.
- Mejorada la ventana de RMP. Ahora separada por ventanas y añadidas las funciones de gestion de adjuntos y treas.
- Añadido boton de ayuda en los ajustes de usuario. Abre una nueva ventana mostrando el uso de la aplicacion.
- Corregido bug en el cual esde la ventana de RMP abria una ficha de expediente, lo abria en la ventana principal y no en una nueva ventana.


Cambio V.1.0.10

- Sistema de asociacion de expedientes bidireccional.
- Añadido tipo de cliente a los clientes. Gestion de tipo de cliente desde el menu admin del usuario admin.
- Calculo automatico del precio final del articulo, teniendo en cuenta si el cliente tiene descuento o no y si hay depreciacion.
- Añadido campo depreciacion en los articulos de los expedientes.
- Añadida pestaña Condiciones a la ficha de clientes.
- Corregido fallo que duplicaba contacto cuando se migraban los clientes.


Cambio V.1.0.9

- Nueva estadistica de expedientes completados por quincenas. Se puede exportar a excel.
- Añadido desplegable en el campo de Recepcionado_Por con un listado de usuarios.
- El listado de usuarios de Recepcionado_Por es administrable desde el menu Admin del usuario admin.
- Añadido orden de fecha mas reciente en el listado de archivos de Backups.
- Añadido poder ordenar por nombre y por fecha en la ventana de backups.


Cambio V.1.0.7

- Implementado sistema de logging.


Cambios V.1.0.5

- 📊 Añadida estadistica de expedientes anual.
- Cuando se introduzca una Fecha Gestion, se necesita un Resultado Expediente para poder cerrar y guardar un expediente. En caso de no introducirlo, saldra mensaje de advertencia.
- Rediseñado la ficha de expedientes para mostrar en una primera vista toda la informacion.
- Los diccionarios de seleccion de estados de productos y de personas en las fechas, ahora estan en JSON y son configurables desde el menu ADMIN del usuario admin.


V.1.0.1

- Gestion de las copias de BD desde el usuario admin.


V.1.0.0 - Inicio de la aplicacion.

Cambios V.0.1.36

- Corregido fallo con el valor de fecha para facturar. No mostraba el valor correcto, mostrando siempre el mismo valor, aunque en la BD hubiese otro distinto.


Cambios V.0.1.35

- Añadido sistema de avisos del sistema. Administrable desde usuario admin.
    * Sale cada vez que se inicia la aplicacion a cada usuario, deben confirmar para que se les quite.
    * Sale siempre mientras este activado el checkbox.
- Cmbiado los iconos de Copia de BD y Reportar por iconos mas adecuados.
- Añadido sistema de copia de BD automatico diario.
- Mejorada la gestion de errores en la conexion a Turso.
    * Se ejecuta los dias laborables a las 17:00h y sube las copias a Blackblaze automaticamente.
    * Mantiene visibles las ultimas 30 copias, a partir de esa las mueve a una carpeta denominada "Archivo" para mantenerlas el tiempo necesario.
    * Envia correo al administrados informando de la copia y de la informacion copiada.


Cambios V.0.1.28

- 📊 Añadida estadistica para el control de clientes que presentan el material antes de la autorizacion.
- Añadidos los campos en la pestaña de Contabilidad de la ficha de los expedientes:
    * Numero Albaran Reposicion
    * Fecha Albaran Reposicion
    * Numero Factura Abono
    * Fecha Factura Abono
- Cambiada la ubicacion de PRECIO TOTAL EXPEDIENTE a la parte superior, para que este siempre visible.
- Añadido compresion de videos en los adjuntos de los expedientes.
- Visualizacion en los slash sobre que BD se usa y si se conecta a Dropbox.
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