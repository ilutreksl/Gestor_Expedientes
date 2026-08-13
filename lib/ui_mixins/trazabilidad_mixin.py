"""Mixin extraido automaticamente de VentanaPrincipal (app.py).

Estas clases NO son instanciables por si solas: solo aportan metodos que se
combinan con VentanaPrincipal via herencia multiple. Dependen de atributos de
instancia (self.conn, self.username, self.tree_rmas, etc.) inicializados en
VentanaPrincipal.__init__.

Contiene la ventana "Añadir Trazabilidad": punto único en la ficha del
expediente para adjuntar cualquier archivo (correo, foto, documento) y dejar
un comentario, enrutando cada cosa al sitio que ya existe en la app
(correos asociados, adjuntos o historial) sin que el usuario tenga que
pensar dónde va cada elemento.
"""
from lib.app_core import *  # noqa: F401,F403 - helpers/constantes/imports compartidos con app.py
from lib.safe_toplevel import SafeCTkToplevel
from lib.trazabilidad_manager import TrazabilidadManager

# Soporte opcional de arrastrar-y-soltar. Si la librería no está instalada,
# la ventana funciona igual de bien solo con el selector de archivos.
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _DND_DISPONIBLE = True
except ImportError:
    DND_FILES = None
    TkinterDnD = None
    _DND_DISPONIBLE = False
    logger.info("tkinterdnd2 no instalado; la ventana de Trazabilidad usará solo el selector de archivos")


class TrazabilidadMixin:
    def abrir_ventana_trazabilidad(self, rma_id):
        """Abre la ventana para adjuntar archivos/comentarios de trazabilidad a un expediente ya guardado."""
        if not rma_id:
            messagebox.showwarning("Guardar primero", "Guarda el expediente antes de añadir trazabilidad.")
            return

        ventana = SafeCTkToplevel(self)
        ventana.title("➕ Añadir Trazabilidad")
        ventana.geometry("560x640")
        ventana.transient(self)
        ventana.grab_set()

        ventana.update_idletasks()
        x = (ventana.winfo_screenwidth() // 2) - (560 // 2)
        y = (ventana.winfo_screenheight() // 2) - (640 // 2)
        ventana.geometry(f"560x640+{x}+{y}")

        main_frame = ctk.CTkFrame(ventana)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        texto_ayuda = TrazabilidadManager().cargar_texto_ayuda()
        ctk.CTkLabel(main_frame, text=texto_ayuda, font=ctk.CTkFont(size=12),
                     text_color="gray", wraplength=500, justify="left").pack(anchor="w", pady=(0, 10))

        archivos_pendientes = []

        zona_drop = ctk.CTkFrame(main_frame, height=70, fg_color=("gray85", "gray20"), corner_radius=8)
        zona_drop.pack(fill="x", pady=(0, 8))
        zona_drop.pack_propagate(False)
        lbl_zona_drop = ctk.CTkLabel(zona_drop, text="Arrastra archivos aquí", text_color="gray")
        lbl_zona_drop.pack(expand=True)

        lista_frame = ctk.CTkScrollableFrame(main_frame, label_text="Archivos a adjuntar", height=140)
        lista_frame.pack(fill="both", pady=(0, 8))

        def refrescar_lista_archivos():
            for widget in lista_frame.winfo_children():
                widget.destroy()
            if not archivos_pendientes:
                ctk.CTkLabel(lista_frame, text="Ningún archivo seleccionado todavía",
                             text_color="gray").pack(pady=10)
                return
            for filepath in list(archivos_pendientes):
                fila = ctk.CTkFrame(lista_frame, fg_color="transparent")
                fila.pack(fill="x", pady=2)
                ctk.CTkLabel(fila, text=os.path.basename(filepath), anchor="w").pack(
                    side="left", fill="x", expand=True)
                ctk.CTkButton(fila, text="✕", width=28, fg_color="gray40", hover_color="gray30",
                              command=lambda f=filepath: quitar_archivo(f)).pack(side="right")

        def anadir_archivos(filepaths):
            anadidos = 0
            invalidos = 0
            for f in filepaths:
                if not f:
                    continue
                if os.path.isfile(f):
                    if f not in archivos_pendientes:
                        archivos_pendientes.append(f)
                        anadidos += 1
                else:
                    invalidos += 1
            refrescar_lista_archivos()
            if invalidos and anadidos == 0:
                # Caso típico: se ha soltado un correo arrastrado directamente desde
                # Outlook. Outlook lo ofrece como "archivo virtual" (OLE), un formato
                # que tkinterdnd2 no sabe materializar en una ruta real, así que no
                # llega ningún archivo válido y sin este aviso no pasaría nada visible.
                messagebox.showwarning(
                    "No se ha podido añadir",
                    "No se ha reconocido ningún archivo válido en lo soltado.\n\n"
                    "Si intentabas arrastrar un correo directamente desde Outlook, "
                    "guárdalo antes como archivo (Archivo > Guardar como > .eml o .msg, "
                    "o arrástralo a una carpeta del explorador) y luego arrastra o "
                    "selecciona ese archivo ya guardado."
                )

        def quitar_archivo(filepath):
            if filepath in archivos_pendientes:
                archivos_pendientes.remove(filepath)
            refrescar_lista_archivos()

        def seleccionar_archivos():
            filepaths = filedialog.askopenfilenames(
                title="Seleccionar archivo(s) para el expediente",
                filetypes=(("Todos los archivos", "*.*"),)
            )
            if filepaths:
                anadir_archivos(filepaths)

        ctk.CTkButton(main_frame, text="📁 Seleccionar archivos",
                      command=seleccionar_archivos).pack(fill="x", pady=(0, 10))

        # --- Intento de drag & drop, aislado y con degradación elegante ---
        # tkinterdnd2 no está pensado para "engancharse" a una ventana que no es
        # TkinterDnD.Tk (esta app usa CTk como raíz). Se inyecta el paquete Tcl
        # 'tkdnd' en esta ventana en concreto (TkinterDnD._require) y se añaden
        # los métodos de destino de arrastre directamente al frame de destino.
        # Es una API interna de la librería: si algo no encaja (versión distinta,
        # entorno sin tkdnd, etc.) se captura y sencillamente no se activa la
        # zona de arrastre, sin afectar al resto de la ventana ni de la app.
        dnd_activo = False
        if _DND_DISPONIBLE:
            try:
                TkinterDnD._require(ventana)
                zona_drop.drop_target_register = TkinterDnD.DnDWrapper.drop_target_register.__get__(zona_drop)
                zona_drop.dnd_bind = TkinterDnD.DnDWrapper.dnd_bind.__get__(zona_drop)

                def _on_drop_archivos(event):
                    try:
                        rutas = ventana.tk.splitlist(event.data)
                    except Exception:
                        rutas = [event.data]
                    anadir_archivos(rutas)

                zona_drop.drop_target_register(DND_FILES)
                zona_drop.dnd_bind('<<Drop>>', _on_drop_archivos)
                dnd_activo = True
            except Exception as e:
                logger.warning(f"Drag&drop no disponible en la ventana de Trazabilidad: {e}")
        if not dnd_activo:
            lbl_zona_drop.configure(text="Arrastrar y soltar no disponible en este equipo — usa el botón de abajo")

        refrescar_lista_archivos()

        ctk.CTkLabel(main_frame, text="Comentario (opcional):",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        textbox_comentario = ctk.CTkTextbox(main_frame, height=100, wrap="word")
        textbox_comentario.pack(fill="x", pady=(0, 10))

        botones_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        botones_frame.pack(fill="x")

        def guardar():
            comentario = textbox_comentario.get("1.0", "end-1c").strip()
            if not archivos_pendientes and not comentario:
                messagebox.showwarning("Nada que guardar",
                                        "Selecciona al menos un archivo o escribe un comentario.")
                return

            btn_guardar.configure(state="disabled", text="Guardando...")
            btn_cancelar.configure(state="disabled")
            ventana.update()

            self._guardar_trazabilidad(rma_id, list(archivos_pendientes), comentario, ventana)

        btn_guardar = ctk.CTkButton(botones_frame, text="✅ Guardar", command=guardar, height=38,
                                     font=ctk.CTkFont(weight="bold"))
        btn_guardar.pack(side="left", fill="x", expand=True, padx=(0, 5))

        btn_cancelar = ctk.CTkButton(botones_frame, text="❌ Cancelar", width=100,
                                      fg_color="gray40", hover_color="gray30", command=ventana.destroy)
        btn_cancelar.pack(side="right")

    def _guardar_trazabilidad(self, rma_id, archivos, comentario, ventana):
        """Enruta cada archivo por extensión (.eml/.msg -> correos asociados, resto ->
        adjuntos) y registra el comentario en el historial. Todo en una sola transacción."""
        texto_completo = self.lbl_codigo_rma.cget("text")
        codigo_rma = texto_completo.split(": ")[1].strip()

        avisos = []
        archivos_ok = 0

        conn, cursor = self.master.conectar_db()
        if not conn:
            ventana.destroy()
            messagebox.showerror("Error de conexión", "No se pudo conectar con la base de datos.")
            return

        try:
            for filepath in archivos:
                nombre_original = os.path.basename(filepath)
                extension = os.path.splitext(filepath)[1].lower()

                if extension in ('.eml', '.msg'):
                    if extension == '.msg' and not self._puede_importar_msg():
                        avisos.append(f"Omitido (sin permiso para .msg): {nombre_original}")
                        continue
                    try:
                        datos_correo = correo_parser.parsear_correo_archivo(filepath)
                    except Exception as e:
                        avisos.append(f"No se pudo leer el correo '{nombre_original}': {e}")
                        continue

                    marca_tiempo = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    nombre_archivo = f"{codigo_rma}_CORREO_{marca_tiempo}{extension}"
                    if usar_b2():
                        exito, ruta_relativa = self._subir_archivo_b2(filepath, codigo_rma, nombre_archivo, None)
                        tipo_almacenamiento = 'backblaze'
                    else:
                        exito, ruta_relativa = self._subir_archivo_local(filepath, codigo_rma, nombre_archivo)
                        tipo_almacenamiento = 'local'
                    if not exito:
                        avisos.append(f"No se pudo subir el correo '{nombre_original}'")
                        continue

                    datos = {
                        'asunto': datos_correo.get('asunto', ''),
                        'remitente': datos_correo.get('remitente', ''),
                        'fecha_correo': datos_correo.get('fecha', ''),
                        'cuerpo': datos_correo.get('cuerpo_sin_firma') or datos_correo.get('cuerpo_completo', ''),
                        'nombre_archivo_original': nombre_original,
                        'ruta_relativa_adjunto': ruta_relativa,
                        'tipo_almacenamiento': tipo_almacenamiento,
                        'fecha_importacion': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'usuario_importacion': self.username,
                    }
                    exito_bd, mensaje = rma_correos_asociados.insertar_correo_asociado(rma_id, datos, conn)
                    if not exito_bd:
                        self._limpiar_archivo_subido(ruta_relativa)
                        avisos.append(f"No se pudo asociar el correo '{nombre_original}': {mensaje}")
                        continue
                    archivos_ok += 1

                else:
                    nombre_archivo = f"{codigo_rma}_{nombre_original}"
                    if usar_b2():
                        exito, ruta_relativa = self._subir_archivo_b2(filepath, codigo_rma, nombre_archivo, None)
                        tipo_almacenamiento = 'backblaze'
                    else:
                        exito, ruta_relativa = self._subir_archivo_local(filepath, codigo_rma, nombre_archivo)
                        tipo_almacenamiento = 'local'
                    if not exito:
                        avisos.append(f"No se pudo subir el archivo '{nombre_original}'")
                        continue

                    self.crear_tabla_rma_orders()
                    self.crear_tabla_adjuntos()
                    try:
                        if getattr(self, '_usar_tipo_almacenamiento', False):
                            cursor.execute(
                                """INSERT INTO rma_adjuntos
                                   (rma_id, nombre_archivo, ruta_relativa, fecha_subida, usuario_subida, tipo_almacenamiento)
                                   VALUES (?, ?, ?, ?, ?, ?)""",
                                (rma_id, os.path.basename(ruta_relativa), ruta_relativa,
                                 datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                 self.username, tipo_almacenamiento)
                            )
                        else:
                            cursor.execute(
                                """INSERT INTO rma_adjuntos
                                   (rma_id, nombre_archivo, ruta_relativa, fecha_subida, usuario_subida)
                                   VALUES (?, ?, ?, ?, ?)""",
                                (rma_id, os.path.basename(ruta_relativa), ruta_relativa,
                                 datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                 self.username)
                            )
                    except Exception as e:
                        self._limpiar_archivo_subido(ruta_relativa)
                        avisos.append(f"No se pudo registrar el adjunto '{nombre_original}': {e}")
                        continue
                    archivos_ok += 1

            if comentario:
                cursor.execute(
                    """INSERT INTO rma_historial (rma_id, fecha_cambio, usuario, descripcion_cambio)
                       VALUES (?, ?, ?, ?)""",
                    (rma_id, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.username,
                     f"Trazabilidad añadida: {comentario}")
                )

            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error al guardar trazabilidad del expediente {rma_id}: {e}", exc_info=True)
            conn.close()
            ventana.destroy()
            messagebox.showerror("Error", f"No se pudo completar el guardado: {e}")
            return
        finally:
            conn.close()

        ventana.destroy()

        if avisos:
            messagebox.showwarning("Trazabilidad guardada con avisos",
                                    f"{archivos_ok} archivo(s) guardados correctamente.\n\n"
                                    "Avisos:\n" + "\n".join(avisos))
        else:
            messagebox.showinfo("Trazabilidad guardada", "✅ Se ha guardado correctamente.")

        try:
            self.refrescar_historial()
        except Exception:
            pass
        try:
            self.cargar_lista_adjuntos(self.current_rma_id)
        except Exception:
            pass
        try:
            self.cargar_lista_correos_asociados()
        except Exception:
            pass
