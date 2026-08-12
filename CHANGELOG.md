Cambio V.1.2.10 - ✨ Últimas mejoras implementadas:

- La pestaña "Datos" del expediente en el móvil (QR) se ha convertido en 4 pestañas: Datos, Historial, Adjuntos y Artículos. Datos incluye ahora también el nº y fecha de albarán de reposición y de factura de abono. Adjuntos permite descargar los archivos que estén en la nube. Artículos muestra las líneas del expediente.
- Nuevo permiso "puede editar" por dispositivo móvil, concedido desde el panel de administración (📱 Dispositivos QR Recepción). Solo los dispositivos con permiso ven los botones de editar en Datos (fechas, albarán/factura, contacto) y en Artículos (cantidad entregada y estado del producto). El historial nunca es editable. Cada cambio queda registrado en el historial del expediente igual que si se hiciera desde el ordenador.
- Añadido el logo de la empresa a todas las páginas del móvil.
- Nuevo "Aviso de recepción por QR": en la ficha del expediente, pestaña "Tareas y Avisos" (antes solo "Tareas"), se puede configurar un mensaje y activar un pitido. Si se ha configurado, al confirmar la recepción desde el móvil aparece ese mensaje en pantalla y suena el pitido en el propio móvil — no hace falta tener el ordenador encendido. Si no se configura nada, no cambia nada.


Cambio V.1.2.03

- Al subir una foto por QR, si el expediente aún no tenía Fecha de Proceso, ahora se rellena junto con "Procesado Por" (la persona del móvil) y se actualiza el estado a "En Trámite". Solo ocurre la primera vez; si ya se había procesado antes desde el escritorio, no se toca.
- Revertido: guardar en la ficha de un expediente ya no refresca sola la ventana principal — vuelve a hacer falta pulsar F5, como antes de la v1.2.02.


Cambio V.1.2.02

- Corregido: al confirmar una recepción por QR, ahora se actualiza también el estado del expediente a "Recibido" (antes solo se guardaba la fecha de recepción, y el estado se quedaba desactualizado en la ventana principal y en las estadísticas).
- Corregido: al guardar cambios en la ficha de un expediente, la lista y el panel de estadísticas de la ventana principal se refrescan al momento, sin tener que cerrar la ficha.
- Corregido: el botón de Aplicar Filtros (F5) ahora también refresca el panel de estadísticas, no solo la lista.


Cambio V.1.2.01

- Ampliado el sistema de recepción de paquetes por QR: una vez el expediente ya está recepcionado, volver a escanear el mismo QR abre un menú con tres opciones nuevas: añadir un comentario al historial, revisar los datos del expediente en modo solo lectura, y añadir fotos.
- Las fotos se pueden hacer con la cámara del móvil o elegir de la galería, recortar y marcar (lápiz, flecha, rectángulo, texto) directamente ahí, y se suben ya comprimidas al expediente sin pasar por el ordenador.
- Se ha añadido a la guía de usuario la explicación completa de este menú nuevo.


Cambio V.1.2.00

- Nuevo sistema para la recepcion de paquetes.
Cuando se genera la autorizacion, en el documento se implementa un codigo QR, el cual si se escanea con un movil, automaticamente se registra su entrada en la app. Si ya esta registrado, sale mensaje de advertencia.
- Para este sistema se ha implementado un sistema de PINs, para registrar dispositivos moviles, dejando un dispositivo denominado Almacen, como dispositivo que siempre pregunta quien ha recepcionado el paquete. Si es otro dispositivo movil que este registrado, se guardar con ese nombre.
El usuario admin es el que puede generar los PINs y revocar dispositivos moviles.
- Se a añadido a la guia de usuario todo el sistema y como se usa y ejecuta.


Cambio V.1.1.09

- Rediseñada la ventana de la busqueda global avanzada.
- Añadido editor de imagenes en el editor de texto. Ahora cuando se va a adjuntar una imagen, te permitira editarla antes de embedirla. Las acciones que perimte son: Recortar, marcar, anotar y flecha.
- Añadido corrector ortografico en el editor de texto. Se debe de instalar la libreria pyspellchecker. Leer el archivo README.md para poder instalarlo. En caso de no instalarlo, el editor funciona pero sin esa funcion.
En ajustes de usuario, en la pestaña General, se puede cambiar el idioma.
- En el historial de los expedientes, ya se permite seleccionar texto para las funciones de copiar, cortar y pegar.
- Todo documentado en ayuda de la app.


Cambio V.1.1.06

- Añadido a la ventana de asociaciones de la ficha de los expedientes, el poder importar emails y asi asociarlos al expediente.
El email puede estar en formato .eml y .msg
Como se guarda como adjunto, es posible abrirlo desde la propia app.


Cambio V.1.1.05

- Añadida estadistica visible de articulos defectuosos contra las ventas y compras. Los archivos de ventas y compras deberan ser importados manualmente.


Cambio V.1.1.04

- Ventana autorellenable cuando se solicita numero de rma a Olfer para rellenar los campos de unidades afectadas y pedido de compra.



Cambio V.1.1.03

- (1.1.02)Añadidos dos nuevos campos en la pestaña General de la fichas de los expedientes.
Estos campos son para la Resolucion Provisional.
- (1.1.03)En el boton de enviar email dentro de la ficha de expedientes, ahora permite elegir otro destinatario y otro asunto, quedando reflejado en su historial.



Cambio V.1.1.01

- Refactorizacion de la aplicacion.
    * Mejorar mantenimiento a largo plazo.
    * Mejorar rendimiento de la app.
    * Mejorar agilidad de la app.
- Añadido listado de tareas y calendario en la columna de la derecha.
    * Se puede habilitar/deshabilitar desde los ajustes de usuario en la pestaña "Notificaciones"
- Correccion de bugs en la seccion de guardar los expedientes y las tareas.
- Añadido boton de crear tareas en el calendario del dashboard.



Cambio V.1.0.63

- Añadido poder adjuntar los albaranes automaticamente al expediente.
    - Hay que activarlo desde ajustes del usuario, y saldra un boton al lado del campo Numero de Albaran en la pestaña Contabilidad de los expediente.
- Mejorada la estadisticas de los articulos, para contemplar las mismas referencias en los mismos estados.



Cambio V.1.0.61

- Añadido check en el informe de quinceas para visualizar los entregados.
- Añadido dos nuevos iconos en el listado de expedientes.
    - Icono Reloj: Si un expediente tiene una tarea asociada.
    - Icono Mixto: Si esta entregado a Contabilidad.
- Se registra en el historial de los expedientes, cuando se entrega a Contabilidad, cuando se marca el check en el informe por quincenas.


Cambio V.1.0.60

- Renombrado de los adjuntos en la pestaña de adjuntos en la fichas de expedientes.
- Visualizado del espacio de cada archivo y el total de los adjutnos en las fichas de los expedientes.


Cambio V.1.0.59

- Remodelado de la seccion de articulos de dentro de las fichas de expediente. Ahora tambien solicita el albaran o factura de compra y el numero de ORDER.
- El informe de expedientes por quincena, tiene en cuanta este cambio y ahora al exportar el documento a excel, añade a cada expediente, los articulos relacionados y los albaranes/facturas de compra asociadas.


Cambio V.1.0.58

- Añadido icono en el listado de expedientes para saber si tiene albaran de reposicion y/o factura de abono. Muestra informacion del numero y de la ficha para facturar.
- Renombrado de adjuntos, añadiendo el numero de RMA automaticamente. (1.0.57)


Cambio V.1.0.56

- Correccion de bugs.


Cambio V.1.0.55

- Añadido editor de texto al campo Observacion tecnicas de la fichas de los expedientes.
- Boton de "Expandir" en el editor de texto, para abrir en una ventana de mayor tamaño el editor de texto.
- Integracion con el boton de "Generar Informe" añadiendo el texto+imagenes de este bloque.

Cambio V.1.0.54

- Nuevo boton cuando se cierra un expediente, para poder reabrir el expediente cerrado. Se debe de indicar el motivo de la reapertura del expediente. La informacion se guarda en el historial los cambios y el motivo.


Cambio V.1.0.53

- Ahora al crear un nuevo expediente, se necesita que el cliente este previamente creado. De esta manera se evitaran nombres de clientes errores.
Se abre una ventana de advertencia y desde esa ventana se puede crear el nuevo cliente.
- En la ficha de cliente, se puede desactivar. Si esta desactivado, no se puede crear un expediente hasta que vuelva a estar activo.


Cambio V.1.0.50

- Añadido rol de Administracion para boton de Autorizacion.


Cambio V.1.0.49

- Añadida nueva estadistica para contabilizar fallos en fabrica, para mantener una trazabilidad de los pedidos. (1.0.49)
- Añadido checkbox a la linea de los articulos de la ficha de expedientes, para incluirlo o no en la contabilizacion. Por defecto siempre lo incluye. (1.0.48)
- Ventana de ajustes de usuario mejorada por pestañas y añadidas nuevas funcionalidades. (1.0.46)
- Corregido bug de guardado  de usuario en menu contextual. (1.0.47)


Cambio V.1.0.45

- Sistema de Tareas mejorada. Asignacion de tareas y notificaciones sonoras. Se pueden deshabilitar desde los ajustes de cada usuario.
- Corregido bug al actualizar expediente cuando se generaba autorizacion, abria en ventana principal. (1.0.44)
- Correccion de bug a la hora de guardar y actualizar expedientes. (1.0.43)
- Añadido campo numero de ORDER a la ficha de expedientes en la pestaña Tecnica y creada tabla y campo en la BD.(1.0.42)


Cambio V.1.0.41

- Correccion de bug de adjuntar la firma para autorizar documento.
- Correccion de bug de actuaizar datos de autorizacion cuando se genera el documento de autorizacion.


Cambio V.1.0.40

- Sistema de gestion de Autorizacion.(Puede revisar en ayuda su funcionamiento).
- Sistema de firmas para la gestion de autorizacion. (Puede revisar la ayuda).
- Nuevas funciones añadidas al menu contextual del boton derecho del raton:
	* Asociar expedientes.
	* Generar autorizacion para el cliente.
	* Descargar la autorizacion, si esta generada.


Cambio V.1.0.32

- Funciones con el boton derecho del raton: Cambio de estado de los expedientes. (1.0.32)
- Añadida paginacion a la ventana principal. (1.0.31)
- La busqueda sencilla de laventana principal, ya no necesita año para buscar en el resto de años. (1.0.31)
- Añadida restauracion de backups de la BD. (1.0.30)
- Corregido error al generar informe.docx en la ficha de expedientes, no recogia el valor del numero de albaran. (1.0.29)
- Añadido paginacion a la ventana de backups para evitar la carga. (1.0.28)
- Corregido error cuando se generaba el excel de los RMP, lo guardaba tanto en local como en la nube. (1.0.27)
- Corregido error con el atajo rapido Ctrl+N, abria la anterior ventana de expedientes. (1.0.26)
- Cambiado color de botones no importantes, para que los gestione el color del tema en vigor. (1.0.25)
- Cambiado color del Header de las fichas de los RMP. (1.0.24)
- Corregido error de import de B2. (1.0.24)
- Modificado ubicacion de los backups de Turso a la nueva estructura de carpeta de B2. (1.0.23)
- Migracion de Dropbox a Backblaze B2 (1.0.22)


Cambio V.1.0.21

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