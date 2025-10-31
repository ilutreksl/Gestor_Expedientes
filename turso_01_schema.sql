CREATE TABLE expedientes (
                    id_expediente INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha_creacion TEXT NOT NULL,
                    cliente TEXT NOT NULL,
                    contacto TEXT,
                    email TEXT,
                    telefono TEXT,
                    modelo TEXT,
                    n_serie TEXT,
                    descripcion_falla TEXT,
                    estado TEXT NOT NULL,
                    accion_correctiva TEXT,
                    tecnico_asignado TEXT,
                    fecha_cierre TEXT,
                    usuario_creacion TEXT
                );
CREATE TABLE rma_adjuntos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rma_id INTEGER NOT NULL,
                    nombre_archivo TEXT NOT NULL,
                    ruta_relativa TEXT NOT NULL,
                    fecha_subida TEXT,
                    usuario_subida TEXT,
                    FOREIGN KEY (rma_id) REFERENCES rma_maestro (id)
                );
CREATE TABLE rma_detalles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rma_id INTEGER, -- Clave Foránea a rma_maestro
            referencia_articulo TEXT NOT NULL,
            cantidad_segun_documento INTEGER,
            cantidad_entregada INTEGER,
            estado_producto TEXT, -- Seleccionable de 18 opciones
            precio_unitario REAL,
            FOREIGN KEY (rma_id) REFERENCES rma_maestro(id)
        );
CREATE TABLE rma_historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rma_id INTEGER, -- Clave Foránea a rma_maestro
            fecha_cambio TEXT NOT NULL,
            usuario TEXT NOT NULL,
            descripcion_cambio TEXT NOT NULL,
            FOREIGN KEY (rma_id) REFERENCES rma_maestro(id)
        );
CREATE TABLE rma_maestro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_rma TEXT UNIQUE, -- El formato RMA25001. Lo generamos con Python.
            cliente TEXT NOT NULL,
            numero_documento_cliente TEXT NOT NULL,
            autorizacion BOOLEAN, -- SI (1) o NO (0)
            fecha_emision TEXT NOT NULL,
            creado_por TEXT NOT NULL,
            fecha_autorizacion TEXT,
            autorizado_por TEXT,
            fecha_recepcion TEXT,
            recepcionado_por TEXT,
            fecha_gestion TEXT,
            gestionado_por TEXT,
            fecha_proceso TEXT,
            procesado_por TEXT,
            fecha_para_factura TEXT, -- Quincena
            numero_albaran TEXT,
            persona_de_contacto TEXT NOT NULL,
            email_de_contacto TEXT NOT NULL,
            fecha_doc_cliente TEXT,
            resultado_expediente TEXT, -- Seleccionable de 4 opciones
            precio_total_expediente REAL, -- Suma de los detalles
            estado TEXT DEFAULT 'Pendiente'
        , motivo TEXT, rma_proveedor TEXT DEFAULT '', modelo TEXT DEFAULT '', n_serie TEXT DEFAULT '', ref_proveedor TEXT DEFAULT '', obs_tecnica TEXT DEFAULT '');
CREATE TABLE rma_pasos (
                rma_id INTEGER,
                fecha_autorizacion TEXT,
                fecha_recepcion TEXT,
                fecha_gestion TEXT,
                FOREIGN KEY (rma_id) REFERENCES rma_maestro(id)
            );
CREATE TABLE tareas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo_rma TEXT,
                    titulo TEXT NOT NULL,
                    descripcion TEXT,
                    fecha_vencimiento TEXT,
                    estado TEXT DEFAULT 'Pendiente',
                    creado_por TEXT,
                    creado_en TEXT,
                    notificado INTEGER DEFAULT 0
                );
CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash BLOB NOT NULL
                );
CREATE TABLE usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_usuario TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            rol TEXT NOT NULL 
        );