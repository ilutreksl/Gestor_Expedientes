"""Mixin extraido automaticamente de VentanaPrincipal (app.py).

Estas clases NO son instanciables por si solas: solo aportan metodos que se
combinan con VentanaPrincipal via herencia multiple. Dependen de atributos de
instancia (self.conn, self.username, self.tree_rmas, etc.) inicializados en
VentanaPrincipal.__init__.
"""
from lib.app_core import *  # noqa: F401,F403 - helpers/constantes/imports compartidos con app.py
from lib.app_core import _get_cached_query, invalidate_cache  # nombres "privados" que el wildcard import no trae

class BackupsMixin:
    def crear_copia_seguridad_db(self):
        """
        Crea una copia de seguridad completa de la base de datos principal
        usando el diálogo 'Guardar como' para que el usuario elija la ubicación.
        La base de datos se asume en la carpeta actual: rma_app.db.
        """
        
        # 1. Determinar la ruta de origen de la BD
        try:
            # Usamos os.getcwd() para obtener la ruta del directorio de trabajo actual
            # y os.path.join para construir la ruta completa de la base de datos.
            db_path_origen = os.path.join(os.getcwd(), DB_FILENAME)

            # Si se han configurado variables de TURSO, podemos intentar volcar desde Turso
            turso_url_check = os.getenv("TURSO_DATABASE_URL")
            turso_token_check = os.getenv("TURSO_AUTH_TOKEN")

            # Opcional: una verificación rápida para ver si el archivo existe.
            # Pero si hay credenciales de Turso, NO abortamos aquí: intentaremos volcar Turso.
            if not os.path.exists(db_path_origen) and not (turso_url_check and turso_token_check):
                messagebox.showerror(
                    "Error de Archivo",
                    f"No se encontró la base de datos local en la ruta esperada: {db_path_origen}\n"
                    f"Asegúrate de que el archivo '{DB_FILENAME}' está en la misma carpeta, o configura TURSO_DATABASE_URL/TURSO_AUTH_TOKEN para volcar desde Turso."
                )
                return

        except Exception as e:
            messagebox.showerror("Error de Ruta", f"No se pudo determinar la ruta de la base de datos: {e}")
            return

        # 2. Generar un nombre de archivo sugerido con fecha y hora
        fecha_actual = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_sugerido = f"backup_rma_app_{fecha_actual}.db"

        # 3. Abrir el diálogo para que el usuario seleccione la ruta de destino
        path_destino = filedialog.asksaveasfilename(
            defaultextension=".db", 
            filetypes=[
                ("Base de Datos SQLite", "*.db"), 
                ("Base de Datos SQLite", "*.sqlite"),
                ("Todos los archivos", "*.*")
            ],
            initialfile=nombre_sugerido,
            title="Guardar Copia de Seguridad de la Base de Datos"
        )

        if not path_destino:
            # El usuario canceló el diálogo
            return

        # 4. Realizar la copia de seguridad
        conn_origen = None
        conn_destino = None
        # Registro de operaciones para mostrar al final
        operations_log: list[str] = []

        def show_log_window(lines: list[str], title: str = "Registro de Copia de Seguridad"):
            """Muestra una ventana Toplevel con el log de operaciones."""
            try:
                win = ctk.CTkToplevel(self)
                win.title(title)
                win.geometry("700x400")
                win.grab_set()

                frame = ctk.CTkFrame(win)
                frame.pack(fill="both", expand=True, padx=10, pady=10)

                txt = ctk.CTkTextbox(frame, wrap="word")
                txt.pack(fill="both", expand=True)
                txt.configure(state="normal")
                txt.delete("1.0", "end")
                txt.insert("1.0", "\n".join(lines))
                txt.configure(state="disabled")

                btn_close = ctk.CTkButton(win, text="Cerrar", command=win.destroy)
                btn_close.pack(pady=8)
            except Exception:
                # Fallback simple si CustomTk no funciona por alguna razón
                try:
                    messagebox.showinfo(title, "\n".join(lines))
                except Exception:
                    print("Log:\n" + "\n".join(lines))

        # Si están definidas las variables de Turso, intentamos volcar la BD remota
        turso_url = os.getenv("TURSO_DATABASE_URL")
        turso_token = os.getenv("TURSO_AUTH_TOKEN")

        if turso_url and turso_token:
            try:
                operations_log.append(f"Intentando volcar Turso: {turso_url}")
                # Aviso al usuario: volcando desde Turso
                try:
                    messagebox.showinfo("Volcando desde Turso", "Se va a intentar volcar la base de datos desde Turso. Esta operación puede tardar varios minutos dependiendo del tamaño de las tablas.")
                except Exception:
                    # No bloquear si messagebox falla
                    pass
                # Conectamos a la BD (esto usará la implementación Turso si las env vars están)
                remote_conn = connect_db(timeout=30)
                remote_cursor = remote_conn.cursor()

                # Obtenemos los CREATE TABLE de la BD remota (evitar tablas internas sqlite_)
                remote_cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                tablas = remote_cursor.fetchall()

                # Crear la BD destino local y recrear tablas
                conn_destino = sqlite3.connect(path_destino)
                dest_cur = conn_destino.cursor()

                for tabla in tablas:
                    if len(tabla) < 2:
                        continue
                    nombre, create_sql = tabla[0], tabla[1]
                    if not create_sql:
                        continue
                    try:
                        dest_cur.execute(create_sql)
                        operations_log.append(f"CREATE TABLE ejecutado para: {nombre}")
                    except Exception:
                        # Si falla crear la tabla (por compatibilidad), intentar skip
                        operations_log.append(f"Advertencia: no se pudo crear tabla {nombre} (se omite)")
                        pass

                    # Copiar los datos de la tabla en bloques para no consumir mucha memoria
                    try:
                        chunk_size = 1000

                        # Intentar obtener el total de filas para poder mostrar progreso
                        total_rows = None
                        try:
                            remote_cursor.execute(f"SELECT COUNT(*) FROM \"{nombre}\"")
                            cnt = remote_cursor.fetchone()
                            total_rows = int(cnt[0]) if cnt and cnt[0] is not None else 0
                        except Exception:
                            # Si COUNT falla por permisos o particularidades, seguiremos sin total
                            total_rows = None

                        if total_rows == 0:
                            operations_log.append(f"Tabla {nombre}: 0 filas (omitida)")
                            continue

                        offset = 0
                        copied = 0
                        insert_sql = None

                        while True:
                            # Leer por bloques usando LIMIT/OFFSET
                            remote_cursor.execute(f"SELECT * FROM \"{nombre}\" LIMIT {chunk_size} OFFSET {offset}")
                            rows = remote_cursor.fetchall()
                            if not rows:
                                break

                            # Preparar placeholders la primera vez que tengamos descripción
                            if insert_sql is None:
                                colcount = len(remote_cursor.description) if remote_cursor.description else 0
                                placeholders = ",".join(["?" for _ in range(colcount)])
                                insert_sql = f"INSERT INTO \"{nombre}\" VALUES ({placeholders})"

                            # Insertar bloque en la DB destino
                            try:
                                dest_cur.executemany(insert_sql, rows)
                                conn_destino.commit()
                                copied += len(rows)
                                offset += len(rows)
                                if total_rows is None:
                                    operations_log.append(f"Tabla {nombre}: {copied} filas copiadas (progreso por bloques)")
                                else:
                                    operations_log.append(f"Tabla {nombre}: {copied}/{total_rows} filas copiadas")
                            except Exception:
                                conn_destino.rollback()
                                operations_log.append(f"Error insertando bloque en tabla {nombre} (omitida)")
                                # Saltar a la siguiente tabla
                                break

                        if copied > 0:
                            operations_log.append(f"Tabla {nombre}: copia finalizada, {copied} filas copiadas")
                        else:
                            operations_log.append(f"Tabla {nombre}: ninguna fila copiada")
                    except Exception as e:
                        # Ignorar errores de copia de datos de tablas concretas
                        try:
                            conn_destino.rollback()
                        except Exception:
                            pass
                        operations_log.append(f"Error copiando datos de tabla {nombre} (omitida): {e}")
                        continue

                # Cerrar conexión remota si existe
                try:
                    remote_conn.close()
                except Exception:
                    pass

                operations_log.append(f"Copia de Turso completada correctamente en: {path_destino}")
                # Intentar guardar el log en un archivo junto al .db de destino
                try:
                    # Guardar logs en carpeta centralizada: <project>/logs/backups/
                    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'backups')
                    os.makedirs(logs_dir, exist_ok=True)
                    log_name = os.path.splitext(os.path.basename(path_destino))[0] + '.log'
                    log_path = os.path.join(logs_dir, log_name)
                    with open(log_path, 'w', encoding='utf-8') as lf:
                        lf.write('\n'.join(operations_log))
                    operations_log.append(f"Registro guardado en: {log_path}")
                except Exception as e:
                    operations_log.append(f"No se pudo guardar el registro en disco: {e}")

                # Mostrar log detallado al usuario
                show_log_window(operations_log, title="Registro de copia (Turso)")
                return

            except Exception as e:
                # Si falla el volcado remoto, registramos y caeremos al backup local
                operations_log.append(f"Info: no se pudo volcar Turso directamente: {e}")
                try:
                    remote_conn.close()
                except Exception:
                    pass

        # Si no hay Turso o el volcado falló, intentamos el backup local tradicional
        try:
            # 4.1. Conectar a la base de datos de origen (solo lectura)
            if not os.path.exists(db_path_origen):
                raise FileNotFoundError(f"Archivo de BD local no encontrado: {db_path_origen}")

            conn_origen = sqlite3.connect(db_path_origen)
            # 4.2. Conectar a la base de datos de destino (se crea si no existe)
            conn_destino = sqlite3.connect(path_destino)

            # 4.3. Usar el método de backup integrado de SQLite
            with conn_destino:
                conn_origen.backup(conn_destino)

            operations_log.append(f"Copia local realizada correctamente en: {path_destino}")
            # Intentar guardar el log en un archivo junto al .db de destino
            try:
                # Guardar logs en carpeta centralizada: <project>/logs/backups/
                logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'backups')
                os.makedirs(logs_dir, exist_ok=True)
                log_name = os.path.splitext(os.path.basename(path_destino))[0] + '.log'
                log_path = os.path.join(logs_dir, log_name)
                with open(log_path, 'w', encoding='utf-8') as lf:
                    lf.write('\n'.join(operations_log))
                operations_log.append(f"Registro guardado en: {log_path}")
            except Exception as e:
                operations_log.append(f"No se pudo guardar el registro en disco: {e}")

            show_log_window(operations_log, title="Registro de copia (local)")

        except sqlite3.Error as e:
            messagebox.showerror("Error de Base de Datos", f"Ocurrió un error al crear la copia de seguridad: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error inesperado: {e}")
        finally:
            if conn_origen:
                conn_origen.close()
            if conn_destino:
                conn_destino.close()

    def mostrar_gestor_backups(self):
        """Muestra la ventana de gestión de backups en Backblaze B2"""
        try:
            from tkinter import filedialog
            import threading
            
            # Crear ventana
            ventana = ctk.CTkToplevel(self)
            ventana.title("Gestor de Backups - Backblaze B2")
            ventana.geometry("1000x600")
            ventana.transient(self)
            
            # Inicializar manager
            manager = BackupManagerB2()
            
            # Variable para almacenar archivos y criterios de ordenamiento
            archivos_actuales = []
            orden_actual = {"columna": "fecha", "ascendente": False}  # Por defecto: fecha descendente
            
            # Variables de paginación
            pagina_actual = 0
            elementos_por_pagina = 10  # Mostrar 10 archivos por página
            
            # Frame principal
            main_frame = ctk.CTkFrame(ventana)
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # ===== PARTE SUPERIOR: CONTROLES =====
            control_frame = ctk.CTkFrame(main_frame)
            control_frame.pack(fill="x", padx=5, pady=(5, 10))
            
            # Fila 1: Búsqueda y filtros
            filtros_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
            filtros_frame.pack(fill="x", padx=5, pady=5)
            
            # Búsqueda
            ctk.CTkLabel(filtros_frame, text="Buscar:").pack(side="left", padx=(0, 5))
            entry_busqueda = ctk.CTkEntry(filtros_frame, placeholder_text="Nombre de archivo...", width=250)
            entry_busqueda.pack(side="left", padx=5)
            
            # Filtro por tipo
            ctk.CTkLabel(filtros_frame, text="Tipo:").pack(side="left", padx=(20, 5))
            filtro_tipo = ctk.CTkOptionMenu(filtros_frame, values=["Todos", ".db", ".sql"], width=100)
            filtro_tipo.set("Todos")
            filtro_tipo.pack(side="left", padx=5)
            
            # Filtro por ubicación
            ctk.CTkLabel(filtros_frame, text="Ubicación:").pack(side="left", padx=(20, 5))
            filtro_ubicacion = ctk.CTkOptionMenu(filtros_frame, values=["Todos", "Raíz", "Archivo/"], width=120)
            filtro_ubicacion.set("Todos")
            filtro_ubicacion.pack(side="left", padx=5)
            
            # Fila 2: Botones de acción
            botones_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
            botones_frame.pack(fill="x", padx=5, pady=5)
            
            btn_crear_backup = ctk.CTkButton(botones_frame, text="🔄 Crear Backup Ahora", width=150)
            btn_crear_backup.pack(side="left", padx=5)
            Tooltip(btn_crear_backup, "Ejecuta el script de backup para crear una nueva copia de seguridad de la base de datos")
            
            btn_restaurar = ctk.CTkButton(botones_frame, text="📥 Restaurar Backup", width=140)
            btn_restaurar.pack(side="left", padx=5)
            Tooltip(btn_restaurar, "Restaura la base de datos desde un archivo de backup seleccionado (.db o .sql)")
            
            btn_actualizar = ctk.CTkButton(botones_frame, text="↻ Actualizar Lista", width=120)
            btn_actualizar.pack(side="left", padx=5)
            Tooltip(btn_actualizar, "Recarga la lista de archivos desde Backblaze B2")
            
            # Label de estado
            lbl_estado = ctk.CTkLabel(botones_frame, text="Listo", text_color="gray")
            lbl_estado.pack(side="left", padx=20)
            
            # ===== PARTE CENTRAL: LISTADO DE ARCHIVOS =====
            lista_frame = ctk.CTkFrame(main_frame)
            lista_frame.pack(fill="both", expand=True, padx=5, pady=5)
            
            # Header del listado con botones ordenables
            header_frame = ctk.CTkFrame(lista_frame, fg_color=("gray80", "gray25"), height=35)
            header_frame.pack(fill="x", padx=2, pady=(2, 0))
            header_frame.pack_propagate(False)
            
            # Botón Nombre (ordenable)
            btn_header_nombre = ctk.CTkButton(header_frame, text="Nombre ▼", font=ctk.CTkFont(weight="bold"), 
                                              width=350, fg_color="transparent", hover_color=("gray70", "gray30"),
                                              command=lambda: ordenar_por("nombre"))
            btn_header_nombre.pack(side="left", padx=10, pady=5)
            Tooltip(btn_header_nombre, "Click para ordenar por nombre")
            
            ctk.CTkLabel(header_frame, text="Tamaño", font=ctk.CTkFont(weight="bold"), width=100).pack(side="left", padx=5, pady=5)
            
            # Botón Fecha (ordenable)
            btn_header_fecha = ctk.CTkButton(header_frame, text="Fecha ▼", font=ctk.CTkFont(weight="bold"), 
                                             width=150, fg_color="transparent", hover_color=("gray70", "gray30"),
                                             command=lambda: ordenar_por("fecha"))
            btn_header_fecha.pack(side="left", padx=5, pady=5)
            Tooltip(btn_header_fecha, "Click para ordenar por fecha")
            
            ctk.CTkLabel(header_frame, text="Ubicación", font=ctk.CTkFont(weight="bold"), width=100).pack(side="left", padx=5, pady=5)
            ctk.CTkLabel(header_frame, text="Acciones", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5, pady=5)
            
            # Scrollable frame para archivos
            scroll_frame = ctk.CTkScrollableFrame(lista_frame)
            scroll_frame.pack(fill="both", expand=True, padx=2, pady=2)
            
            # ===== PAGINACIÓN =====
            paginacion_frame = ctk.CTkFrame(main_frame, height=40)
            paginacion_frame.pack(fill="x", padx=5, pady=(5, 2))
            paginacion_frame.pack_propagate(False)
            
            btn_anterior = ctk.CTkButton(paginacion_frame, text="◀ Anterior", width=100, state="disabled")
            btn_anterior.pack(side="left", padx=10, pady=5)
            
            lbl_pagina = ctk.CTkLabel(paginacion_frame, text="Página 1 de 1")
            lbl_pagina.pack(side="left", padx=20)
            
            btn_siguiente = ctk.CTkButton(paginacion_frame, text="Siguiente ▶", width=100, state="disabled")
            btn_siguiente.pack(side="left", padx=10, pady=5)
            
            # Selector de elementos por página
            ctk.CTkLabel(paginacion_frame, text="Elementos por página:").pack(side="left", padx=(40, 5))
            elementos_menu = ctk.CTkOptionMenu(paginacion_frame, values=["10", "20", "50", "100", "200"], 
                                               width=80, command=lambda val: cambiar_elementos_por_pagina(val))
            elementos_menu.set("10")
            elementos_menu.pack(side="left", padx=5)
            
            # ===== PARTE INFERIOR: INFORMACIÓN =====
            info_frame = ctk.CTkFrame(main_frame, height=40)
            info_frame.pack(fill="x", padx=5, pady=(2, 5))
            info_frame.pack_propagate(False)
            
            lbl_info = ctk.CTkLabel(info_frame, text="Total: 0 archivos | Espacio: 0 B")
            lbl_info.pack(side="left", padx=10, pady=10)
            
            # ===== FUNCIONES =====
            
            def actualizar_estado(mensaje, color="gray"):
                lbl_estado.configure(text=mensaje, text_color=color)
                ventana.update()
            
            def actualizar_indicadores_orden():
                """Actualiza las flechas en los encabezados según el orden actual"""
                # Nombre
                if orden_actual["columna"] == "nombre":
                    flecha = " ▲" if orden_actual["ascendente"] else " ▼"
                    btn_header_nombre.configure(text=f"Nombre{flecha}")
                else:
                    btn_header_nombre.configure(text="Nombre")
                
                # Fecha
                if orden_actual["columna"] == "fecha":
                    flecha = " ▲" if orden_actual["ascendente"] else " ▼"
                    btn_header_fecha.configure(text=f"Fecha{flecha}")
                else:
                    btn_header_fecha.configure(text="Fecha")
            
            def ordenar_por(columna):
                """Ordena la lista por la columna especificada"""
                nonlocal pagina_actual
                # Si es la misma columna, invertir el orden
                if orden_actual["columna"] == columna:
                    orden_actual["ascendente"] = not orden_actual["ascendente"]
                else:
                    # Nueva columna, orden ascendente por defecto (excepto fecha que es descendente)
                    orden_actual["columna"] = columna
                    orden_actual["ascendente"] = True if columna == "nombre" else False
                
                # Reiniciar a la primera página cuando se cambia el orden
                pagina_actual = 0
                actualizar_indicadores_orden()
                mostrar_archivos()
                logger.info(f"Lista ordenada por {columna} ({'ascendente' if orden_actual['ascendente'] else 'descendente'})")
            
            def cargar_archivos():
                """Carga la lista de archivos desde B2"""
                actualizar_estado("Conectando...", "blue")
                
                # Autenticar
                success, msg = manager.autenticar()
                if not success:
                    messagebox.showerror("Error", f"Error de autenticación: {msg}")
                    actualizar_estado(f"Error: {msg}", "red")
                    logger.error(f"Error de autenticación en backups: {msg}")
                    return
                
                actualizar_estado("Autenticando...", "blue")
                
                # Obtener bucket
                success, msg = manager.obtener_bucket_id()
                if not success:
                    messagebox.showerror("Error", f"Error al obtener bucket: {msg}")
                    actualizar_estado(f"Error: {msg}", "red")
                    logger.error(f"Error al obtener bucket: {msg}")
                    return
                
                actualizar_estado("Cargando lista de archivos...", "blue")
                
                # Listar archivos
                archivos, msg = manager.listar_archivos()
                if archivos is None:
                    messagebox.showerror("Error", f"Error al listar archivos: {msg}")
                    actualizar_estado(f"Error: {msg}", "red")
                    logger.error(f"Error al listar archivos: {msg}")
                    return
                
                nonlocal archivos_actuales
                archivos_actuales = archivos
                
                actualizar_estado(f"Cargados {len(archivos)} archivos", "green")
                logger.info(f"Cargados {len(archivos)} archivos de backup desde B2")
                actualizar_indicadores_orden()
                mostrar_archivos()
            
            def mostrar_archivos():
                """Muestra los archivos filtrados y ordenados en la lista con paginación"""
                nonlocal pagina_actual
                
                # Limpiar lista actual
                for widget in scroll_frame.winfo_children():
                    widget.destroy()
                
                # Aplicar filtros
                busqueda = entry_busqueda.get().lower()
                tipo = filtro_tipo.get()
                ubicacion = filtro_ubicacion.get()
                
                archivos_filtrados = []
                for archivo in archivos_actuales:
                    nombre = archivo['fileName']
                    
                    # Filtro de búsqueda
                    if busqueda and busqueda not in nombre.lower():
                        continue
                    
                    # Filtro de tipo
                    if tipo != "Todos":
                        if not nombre.endswith(tipo):
                            continue
                    
                    # Filtro de ubicación
                    if ubicacion == "Raíz" and nombre.startswith("Archivo/"):
                        continue
                    elif ubicacion == "Archivo/" and not nombre.startswith("Archivo/"):
                        continue
                    
                    archivos_filtrados.append(archivo)
                
                # Ordenar archivos según criterio actual
                if orden_actual["columna"] == "nombre":
                    archivos_filtrados.sort(key=lambda x: x['fileName'].lower(), reverse=not orden_actual["ascendente"])
                elif orden_actual["columna"] == "fecha":
                    archivos_filtrados.sort(key=lambda x: x['uploadTimestamp'], reverse=not orden_actual["ascendente"])
                
                # Calcular paginación
                total_archivos = len(archivos_filtrados)
                total_paginas = max(1, (total_archivos + elementos_por_pagina - 1) // elementos_por_pagina)
                
                # Asegurar que la página actual esté en rango válido
                if pagina_actual >= total_paginas:
                    pagina_actual = max(0, total_paginas - 1)
                
                # Calcular índices de inicio y fin para la página actual
                inicio = pagina_actual * elementos_por_pagina
                fin = min(inicio + elementos_por_pagina, total_archivos)
                
                archivos_pagina = archivos_filtrados[inicio:fin]
                
                # Mostrar archivos de la página actual
                if not archivos_pagina:
                    lbl_vacio = ctk.CTkLabel(scroll_frame, text="No hay archivos que coincidan con los filtros", 
                                             text_color="gray")
                    lbl_vacio.pack(pady=20)
                else:
                    # Crear filas solo para la página actual
                    for archivo in archivos_pagina:
                        crear_fila_archivo(archivo)
                
                # Actualizar controles de paginación
                lbl_pagina.configure(text=f"Página {pagina_actual + 1} de {total_paginas} ({inicio + 1}-{fin} de {total_archivos})")
                
                # Habilitar/deshabilitar botones de navegación
                btn_anterior.configure(state="normal" if pagina_actual > 0 else "disabled")
                btn_siguiente.configure(state="normal" if pagina_actual < total_paginas - 1 else "disabled")
                
                # Actualizar información
                total_tamano = sum(a['contentLength'] for a in archivos_filtrados)
                lbl_info.configure(text=f"Total: {len(archivos_filtrados)} archivos | Espacio: {manager.formatear_tamaño(total_tamano)}")
            
            def crear_fila_archivo(archivo):
                """Crea una fila para mostrar un archivo"""
                fila = ctk.CTkFrame(scroll_frame, fg_color=("gray90", "gray20"))
                fila.pack(fill="x", padx=2, pady=2)
                
                nombre = archivo['fileName'].replace("Archivo/", "") if archivo['fileName'].startswith("Archivo/") else archivo['fileName']
                tamaño = manager.formatear_tamaño(archivo['contentLength'])
                fecha = manager.formatear_fecha(archivo['uploadTimestamp'])
                ubicacion = "Archivo/" if archivo['fileName'].startswith("Archivo/") else "Raíz"
                
                lbl_nombre = ctk.CTkLabel(fila, text=nombre, width=350, anchor="w")
                lbl_nombre.pack(side="left", padx=10, pady=5)
                lbl_tamano = ctk.CTkLabel(fila, text=tamaño, width=100, anchor="w")
                lbl_tamano.pack(side="left", padx=5, pady=5)
                lbl_fecha = ctk.CTkLabel(fila, text=fecha, width=150, anchor="w")
                lbl_fecha.pack(side="left", padx=5, pady=5)
                lbl_ubicacion = ctk.CTkLabel(fila, text=ubicacion, width=100, anchor="w")
                lbl_ubicacion.pack(side="left", padx=5, pady=5)
                
                # Botones de acción
                acciones_frame = ctk.CTkFrame(fila, fg_color="transparent")
                acciones_frame.pack(side="left", padx=5, pady=2)
                
                btn_descargar = ctk.CTkButton(acciones_frame, text="⬇", width=30, height=25,
                                              command=lambda: descargar_archivo(archivo))
                btn_descargar.pack(side="left", padx=2)
                Tooltip(btn_descargar, "Descargar este archivo a tu ordenador")
                
                if not archivo['fileName'].startswith("Archivo/"):
                    btn_mover = ctk.CTkButton(acciones_frame, text="📁", width=30, height=25,
                                             command=lambda: mover_a_archivo(archivo))
                    btn_mover.pack(side="left", padx=2)
                    Tooltip(btn_mover, "Mover este archivo a la carpeta Archivo/ (backups antiguos)")
                
                btn_eliminar = ctk.CTkButton(acciones_frame, text="🗑", width=30, height=25,
                                            fg_color="red", hover_color="darkred",
                                            command=lambda: eliminar_archivo(archivo))
                btn_eliminar.pack(side="left", padx=2)
                Tooltip(btn_eliminar, "Eliminar permanentemente este archivo de Backblaze B2")
                
                # Eventos de selección
                file_id = archivo['fileId']
                
                def _seleccionar_backup(e):
                    if hasattr(ventana, 'fila_seleccionada_backup') and hasattr(ventana, 'frame_seleccionado_backup'):
                        try:
                            ventana.frame_seleccionado_backup.configure(fg_color=("gray90", "gray20"))
                        except:
                            pass
                    
                    try:
                        modo = ctk.get_appearance_mode()
                        color_sel = ("#D6EAF8" if modo == "Light" else "#2C5F8D")
                    except:
                        color_sel = "#D6EAF8"
                    
                    fila.configure(fg_color=color_sel)
                    ventana.fila_seleccionada_backup = file_id
                    ventana.frame_seleccionado_backup = fila
                
                def _on_enter_backup(e):
                    if not hasattr(ventana, 'fila_seleccionada_backup') or ventana.fila_seleccionada_backup != file_id:
                        try:
                            modo = ctk.get_appearance_mode()
                            hover_color = ("#F5F5F5" if modo == "Light" else "#2B2B2B")
                        except:
                            hover_color = "#F5F5F5"
                        fila.configure(fg_color=hover_color)
                
                def _on_leave_backup(e):
                    if not hasattr(ventana, 'fila_seleccionada_backup') or ventana.fila_seleccionada_backup != file_id:
                        fila.configure(fg_color=("gray90", "gray20"))
                
                fila.bind("<Button-1>", _seleccionar_backup)
                fila.bind("<Enter>", _on_enter_backup)
                fila.bind("<Leave>", _on_leave_backup)
                fila.configure(cursor="hand2")
                
                for lbl in [lbl_nombre, lbl_tamano, lbl_fecha, lbl_ubicacion]:
                    lbl.bind("<Button-1>", _seleccionar_backup)
                    lbl.configure(cursor="hand2")
            
            def descargar_archivo(archivo):
                """Descarga un archivo de B2"""
                destino = filedialog.asksaveasfilename(
                    defaultextension=os.path.splitext(archivo['fileName'])[1],
                    initialfile=archivo['fileName'].replace("Archivo/", ""),
                    title="Guardar archivo"
                )
                
                if not destino:
                    return
                
                actualizar_estado("Descargando...", "blue")
                success, msg = manager.descargar_archivo(archivo['fileId'], archivo['fileName'], destino)
                
                if success:
                    messagebox.showinfo("Éxito", f"Archivo descargado en:\n{destino}")
                    actualizar_estado("Descarga completada", "green")
                else:
                    messagebox.showerror("Error", f"Error al descargar: {msg}")
                    actualizar_estado(f"Error: {msg}", "red")
            
            def mover_a_archivo(archivo):
                """Mueve un archivo a la carpeta Archivo/"""
                if not messagebox.askyesno("Confirmar", f"¿Mover '{archivo['fileName']}' a Archivo/?"):
                    return
                
                actualizar_estado("Moviendo...", "blue")
                success, msg = manager.mover_a_archivo(archivo['fileId'], archivo['fileName'])
                
                if success:
                    messagebox.showinfo("Éxito", "Archivo movido a Archivo/")
                    actualizar_estado("Archivo movido", "green")
                    cargar_archivos()  # Recargar lista
                else:
                    messagebox.showerror("Error", f"Error al mover: {msg}")
                    actualizar_estado(f"Error: {msg}", "red")
            
            def eliminar_archivo(archivo):
                """Elimina un archivo de B2"""
                if not messagebox.askyesno("Confirmar Eliminación", 
                                          f"¿Estás seguro de eliminar '{archivo['fileName']}'?\n\nEsta acción no se puede deshacer."):
                    return
                
                actualizar_estado("Eliminando...", "blue")
                success, msg = manager.eliminar_archivo(archivo['fileId'], archivo['fileName'])
                
                if success:
                    messagebox.showinfo("Éxito", "Archivo eliminado")
                    actualizar_estado("Archivo eliminado", "green")
                    cargar_archivos()  # Recargar lista
                else:
                    messagebox.showerror("Error", f"Error al eliminar: {msg}")
                    actualizar_estado(f"Error: {msg}", "red")
            
            def crear_backup():
                """Ejecuta el script de backup"""
                if not messagebox.askyesno("Crear Backup", "¿Crear una nueva copia de seguridad?\n\nEsto puede tardar varios minutos."):
                    return
                
                actualizar_estado("Creando backup...", "blue")
                btn_crear_backup.configure(state="disabled", text="Creando...")
                
                def ejecutar():
                    success, msg = manager.ejecutar_backup()
                    
                    # Actualizar UI en el hilo principal
                    ventana.after(0, lambda: backup_completado(success, msg))
                
                threading.Thread(target=ejecutar, daemon=True).start()
            
            def backup_completado(success, msg):
                """Callback cuando el backup termina"""
                btn_crear_backup.configure(state="normal", text="🔄 Crear Backup Ahora")
                
                if success:
                    messagebox.showinfo("Éxito", "Backup creado correctamente")
                    actualizar_estado("Backup creado", "green")
                    cargar_archivos()  # Recargar lista
                else:
                    messagebox.showerror("Error", f"Error al crear backup:\n{msg}")
                    actualizar_estado(f"Error: {msg}", "red")
            
            def ir_pagina_anterior():
                """Navega a la página anterior"""
                nonlocal pagina_actual
                if pagina_actual > 0:
                    pagina_actual -= 1
                    mostrar_archivos()
            
            def ir_pagina_siguiente():
                """Navega a la página siguiente"""
                nonlocal pagina_actual
                # Calcular total de páginas
                total_archivos = len(archivos_actuales)
                total_paginas = max(1, (total_archivos + elementos_por_pagina - 1) // elementos_por_pagina)
                if pagina_actual < total_paginas - 1:
                    pagina_actual += 1
                    mostrar_archivos()
            
            def cambiar_elementos_por_pagina(valor):
                """Cambia la cantidad de elementos mostrados por página"""
                nonlocal elementos_por_pagina, pagina_actual
                elementos_por_pagina = int(valor)
                pagina_actual = 0  # Reiniciar a la primera página
                mostrar_archivos()
            
            def restaurar_backup_seleccionado():
                """Restaura un backup seleccionado desde B2"""
                from lib.backup_restauracion import restaurar_backup, obtener_info_backup
                import tempfile
                
                # Verificar que hay un archivo seleccionado
                if not hasattr(ventana, 'fila_seleccionada_backup'):
                    messagebox.showwarning("Selección requerida", 
                                          "Por favor, selecciona un archivo de backup del listado.\n\n" +
                                          "Solo se pueden restaurar archivos .db o .sql")
                    logger.warning("Intento de restauración sin archivo seleccionado")
                    return
                
                # Buscar el archivo seleccionado
                file_id = ventana.fila_seleccionada_backup
                archivo_seleccionado = None
                for archivo in archivos_actuales:
                    if archivo['fileId'] == file_id:
                        archivo_seleccionado = archivo
                        break
                
                if not archivo_seleccionado:
                    messagebox.showerror("Error", "No se pudo encontrar el archivo seleccionado")
                    logger.error("Archivo seleccionado no encontrado en la lista")
                    return
                
                nombre_archivo = archivo_seleccionado['fileName']
                
                # Validar que sea .db o .sql
                extension = os.path.splitext(nombre_archivo)[1].lower()
                if extension not in ['.db', '.sql']:
                    messagebox.showerror("Archivo no válido", 
                                       f"El archivo '{nombre_archivo}' no es un backup válido.\n\n" +
                                       "Solo se pueden restaurar archivos .db o .sql")
                    logger.error(f"Intento de restaurar archivo con extensión no válida: {extension}")
                    return
                
                # Crear ventana de confirmación personalizada
                ventana_confirmacion = ctk.CTkToplevel(ventana)
                ventana_confirmacion.title("⚠️ Confirmar Restauración de Backup")
                ventana_confirmacion.geometry("550x420")
                ventana_confirmacion.transient(ventana)
                ventana_confirmacion.grab_set()
                ventana_confirmacion.resizable(False, False)
                
                # Centrar ventana
                ventana_confirmacion.update_idletasks()
                x = ventana.winfo_x() + (ventana.winfo_width() - 550) // 2
                y = ventana.winfo_y() + (ventana.winfo_height() - 420) // 2
                ventana_confirmacion.geometry(f"550x420+{x}+{y}")
                
                # Contenido
                frame_contenido = ctk.CTkFrame(ventana_confirmacion)
                frame_contenido.pack(fill="both", expand=True, padx=20, pady=20)
                
                # Icono y título
                ctk.CTkLabel(frame_contenido, text="⚠️", font=ctk.CTkFont(size=40)).pack(pady=(10, 5))
                ctk.CTkLabel(frame_contenido, text="Restaurar Copia de Seguridad", 
                           font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)
                
                # Mensaje de advertencia
                mensaje = (
                    f"Estás a punto de restaurar la base de datos desde:\n\n"
                    f"📄 {nombre_archivo}\n\n"
                    f"⚠️ ADVERTENCIA:\n"
                    f"• Se reemplazarán TODOS los datos actuales\n"
                    f"• Se creará un backup de seguridad automático\n"
                    f"• La aplicación se cerrará después de la restauración\n\n"
                    f"¿Deseas continuar?"
                )
                
                lbl_mensaje = ctk.CTkLabel(frame_contenido, text=mensaje, 
                                          justify="left", wraplength=450)
                lbl_mensaje.pack(pady=10, padx=10)
                
                # Frame de botones
                frame_botones = ctk.CTkFrame(frame_contenido, fg_color="transparent")
                frame_botones.pack(side="bottom", pady=10)
                
                resultado = {"confirmar": False}
                
                def confirmar():
                    resultado["confirmar"] = True
                    ventana_confirmacion.destroy()
                
                def cancelar():
                    resultado["confirmar"] = False
                    ventana_confirmacion.destroy()
                
                btn_cancelar = ctk.CTkButton(frame_botones, text="❌ Cancelar", width=120,
                                            fg_color="#dc2626", hover_color="#b91c1c",
                                            command=cancelar)
                btn_cancelar.pack(side="left", padx=10)
                
                btn_confirmar = ctk.CTkButton(frame_botones, text="✅ Restaurar", width=120,
                                             command=confirmar)
                btn_confirmar.pack(side="left", padx=10)
                
                # Esperar a que se cierre la ventana
                ventana.wait_window(ventana_confirmacion)
                
                if not resultado["confirmar"]:
                    logger.info("Restauración cancelada por el usuario")
                    return
                
                # Proceder con la restauración
                actualizar_estado("Descargando backup...", "blue")
                logger.info(f"Iniciando restauración desde: {nombre_archivo}")
                
                try:
                    # Descargar archivo a temporal
                    temp_dir = tempfile.gettempdir()
                    temp_file = os.path.join(temp_dir, nombre_archivo.replace("Archivo/", ""))
                    
                    success, msg = manager.descargar_archivo(archivo_seleccionado['fileId'], 
                                                            archivo_seleccionado['fileName'], 
                                                            temp_file)
                    
                    if not success:
                        messagebox.showerror("Error de descarga", f"No se pudo descargar el backup:\n{msg}")
                        actualizar_estado(f"Error: {msg}", "red")
                        logger.error(f"Error al descargar backup: {msg}")
                        return
                    
                    actualizar_estado("Restaurando base de datos...", "blue")
                    logger.info("Archivo descargado, iniciando proceso de restauración")
                    
                    # Obtener ruta de la base de datos actual
                    ruta_db = self.master.database_path
                    
                    # Restaurar
                    exito, mensaje, ruta_backup_seguridad = restaurar_backup(temp_file, ruta_db)
                    
                    # Eliminar archivo temporal
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                    
                    if exito:
                        actualizar_estado("Restauración completada", "green")
                        logger.info(f"Restauración exitosa. Backup de seguridad en: {ruta_backup_seguridad}")
                        
                        messagebox.showinfo("Restauración Exitosa", 
                                          f"{mensaje}\n\n" +
                                          f"✅ Backup de seguridad creado en:\n{ruta_backup_seguridad}\n\n" +
                                          f"La aplicación se cerrará para aplicar los cambios.\n" +
                                          f"Vuelve a abrirla para continuar trabajando.")
                        
                        # Cerrar la aplicación
                        logger.info("Cerrando aplicación tras restauración exitosa")
                        self.master.quit()
                    else:
                        actualizar_estado("Error en restauración", "red")
                        logger.error(f"Error en la restauración: {mensaje}")
                        messagebox.showerror("Error de Restauración", 
                                           f"No se pudo restaurar el backup:\n\n{mensaje}")
                
                except Exception as e:
                    actualizar_estado("Error inesperado", "red")
                    logger.error(f"Error inesperado durante restauración: {str(e)}", exc_info=True)
                    messagebox.showerror("Error", f"Error inesperado:\n{str(e)}")
            
            # Conectar botones
            btn_actualizar.configure(command=lambda: threading.Thread(target=cargar_archivos, daemon=True).start())
            btn_crear_backup.configure(command=crear_backup)
            btn_restaurar.configure(command=restaurar_backup_seleccionado)
            btn_anterior.configure(command=ir_pagina_anterior)
            btn_siguiente.configure(command=ir_pagina_siguiente)
            
            # Conectar filtros para actualizar al cambiar (reiniciando a la primera página)
            def aplicar_filtros_y_reiniciar(*args):
                nonlocal pagina_actual
                pagina_actual = 0
                mostrar_archivos()
            
            entry_busqueda.bind("<KeyRelease>", lambda e: aplicar_filtros_y_reiniciar())
            filtro_tipo.configure(command=lambda _: aplicar_filtros_y_reiniciar())
            filtro_ubicacion.configure(command=lambda _: aplicar_filtros_y_reiniciar())
            
            # Cargar archivos inicialmente en un hilo
            threading.Thread(target=cargar_archivos, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al abrir gestor de backups: {e}")
            import traceback
            traceback.print_exc()
