"""Mixin extraido automaticamente de VentanaPrincipal (app.py).

Estas clases NO son instanciables por si solas: solo aportan metodos que se
combinan con VentanaPrincipal via herencia multiple. Dependen de atributos de
instancia (self.conn, self.username, self.tree_rmas, etc.) inicializados en
VentanaPrincipal.__init__.
"""
from lib.app_core import *  # noqa: F401,F403 - helpers/constantes/imports compartidos con app.py
from lib.app_core import _get_cached_query, invalidate_cache  # nombres "privados" que el wildcard import no trae

class EmailMixin:
    def abrir_cliente_correo_con_mailto(self, email_acontacto, asunto, cuerpo):
        """Prepara el enlace mailto y lo abre con el cliente de correo por defecto."""
        
        # Necesitamos la librería para codificar el Asunto y el Cuerpo para la URL
        import urllib.parse
        
        # Codificar el asunto y el cuerpo (necesario para URLs mailto con espacios o caracteres especiales)
        asunto_codificado = urllib.parse.quote(asunto)
        cuerpo_codificado = urllib.parse.quote(cuerpo)
        
        # Construir el enlace mailto
        mailto_link = f"mailto:{email_acontacto}?subject={asunto_codificado}&body={cuerpo_codificado}"
        
        try:
            # Abrir el enlace usando el cliente de correo/navegador por defecto
            import webbrowser
            webbrowser.open(mailto_link)
            return True # Éxito
        except Exception as e:
            messagebox.showerror("Error de Email", "No se pudo abrir el cliente de correo por defecto. Por favor, asegúrate de que tienes un cliente de correo configurado.")
            return False # Fallo

    def enviar_email_contacto(self):
        """Abre el cliente de correo para enviar un email al contacto registrado en el RMA actual."""
        
        # 1. Verificar que haya un RMA actual abierto
        if not self.rma_actual_id:
            messagebox.showwarning("Advertencia", "Debe seleccionar o tener abierto un expediente RMA para enviar un email.")
            return

        # 2. Mostrar diálogo para seleccionar adjuntos (si hay disponibles)
        self.mostrar_dialogo_adjuntos_email()

    def mostrar_dialogo_adjuntos_email(self):
        """Muestra un diálogo para seleccionar adjuntos antes de enviar el email."""
        
        conn = connect_db()
        cursor = conn.cursor()
        
        try:
            # Consultar datos del RMA
            cursor.execute("SELECT email_de_contacto, cliente, numero_documento_cliente, codigo_rma FROM rma_maestro WHERE id = ?", (self.rma_actual_id,))
            resultado = cursor.fetchone()
            
            if not resultado:
                messagebox.showerror("Error", f"No se encontró el expediente RMA: {self.rma_actual_id}")
                return
            
            email_acontacto, nombre_cliente, numero_documento_cliente, numero_rma = resultado
            
            # Verificar si el email_contacto está vacío o es nulo
            if not email_acontacto:
                messagebox.showwarning("Advertencia", f"El campo 'email_de_contacto' del expediente {self.rma_actual_id} está vacío.")
                return

            # Obtener lista de adjuntos disponibles
            cursor.execute("SELECT id, ruta_relativa, nombre_archivo FROM rma_adjuntos WHERE rma_id = ?", (self.rma_actual_id,))
            adjuntos_disponibles = cursor.fetchall()
            
            # Crear ventana de diálogo (oculta hasta que se calcule el tamaño real)
            dialogo = Toplevel(self)
            dialogo.withdraw()
            dialogo.title("📧 Preparar Email con Adjuntos")
            dialogo.resizable(True, True)
            dialogo.transient(self)

            # Frame principal
            main_frame = ctk.CTkFrame(dialogo)
            main_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Título
            titulo = ctk.CTkLabel(main_frame, text=f"📧 Email para: {nombre_cliente}", 
                                 font=ctk.CTkFont(size=18, weight="bold"))
            titulo.pack(pady=(10, 5))
            
            # Información del RMA
            info_frame = ctk.CTkFrame(main_frame)
            info_frame.pack(fill="x", pady=(0, 20))
            
            ctk.CTkLabel(info_frame, text=f"RMA: {numero_rma}", 
                        font=ctk.CTkFont(size=12, weight="bold")).pack(pady=5)
            ctk.CTkLabel(info_frame, text=f"Email: {email_acontacto}", 
                        font=ctk.CTkFont(size=12)).pack(pady=2)
            ctk.CTkLabel(info_frame, text=f"Doc. Cliente: {numero_documento_cliente}",
                        font=ctk.CTkFont(size=12)).pack(pady=2)

            # --- Sección Destinatario (contacto del expediente u otro email) ---
            destinatario_frame = ctk.CTkFrame(main_frame)
            destinatario_frame.pack(fill="x", pady=(0, 15))

            ctk.CTkLabel(destinatario_frame, text="📨 Destinatario:",
                        font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))

            destino_var = ctk.StringVar(value="contacto")
            entry_email_otro = ctk.CTkEntry(destinatario_frame, width=350, state="disabled",
                                             placeholder_text="Escribe el email del destinatario")

            def _on_destino_change():
                entry_email_otro.configure(state="normal" if destino_var.get() == "otro" else "disabled")

            ctk.CTkRadioButton(destinatario_frame, text=f"Contacto del expediente ({email_acontacto})",
                              variable=destino_var, value="contacto",
                              command=_on_destino_change).pack(anchor="w", padx=20, pady=2)
            ctk.CTkRadioButton(destinatario_frame, text="Otro destinatario:",
                              variable=destino_var, value="otro",
                              command=_on_destino_change).pack(anchor="w", padx=20, pady=2)
            entry_email_otro.pack(anchor="w", padx=40, pady=(0, 10))

            # --- Sección Asunto (editable) ---
            asunto_frame = ctk.CTkFrame(main_frame)
            asunto_frame.pack(fill="x", pady=(0, 15))

            ctk.CTkLabel(asunto_frame, text="📝 Asunto:",
                        font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))

            asunto_defecto = f"ILUTREK - Nº {numero_rma} ; DOCUMENTO CLIENTE: {numero_documento_cliente}"
            entry_asunto = ctk.CTkEntry(asunto_frame)
            entry_asunto.insert(0, asunto_defecto)
            entry_asunto.pack(fill="x", padx=10, pady=(0, 10))

            # Sección de adjuntos
            adjuntos_frame = ctk.CTkFrame(main_frame)
            adjuntos_frame.pack(fill="both", expand=True, pady=(0, 20))
            
            ctk.CTkLabel(adjuntos_frame, text="📎 Seleccionar adjuntos para el email:", 
                        font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 10))
            
            # Variables para almacenar selecciones
            self.adjuntos_seleccionados = []
            self.checkboxes_adjuntos = []
            
            if adjuntos_disponibles:
                # Frame scrollable para adjuntos
                scroll_frame = ctk.CTkScrollableFrame(adjuntos_frame, height=200)
                scroll_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
                
                for adjunto_id, ruta_relativa, nombre_archivo in adjuntos_disponibles:
                    # Frame para cada adjunto
                    adj_frame = ctk.CTkFrame(scroll_frame)
                    adj_frame.pack(fill="x", pady=2, padx=5)
                    
                    # Variable de checkbox
                    var_checkbox = ctk.BooleanVar()
                    
                    # Checkbox
                    checkbox = ctk.CTkCheckBox(
                        adj_frame, 
                        text="",
                        variable=var_checkbox,
                        width=20
                    )
                    checkbox.pack(side="left", padx=(10, 5), pady=10)
                    
                    # Información del archivo
                    info_label = ctk.CTkLabel(
                        adj_frame, 
                        text=f"{nombre_archivo or os.path.basename(ruta_relativa)}",
                        font=ctk.CTkFont(size=11)
                    )
                    info_label.pack(side="left", padx=(0, 10), pady=10, fill="x", expand=True)
                    
                    # Indicador de ubicación (Backblaze B2/Local)
                    ubicacion = "☁️ Backblaze B2" if usar_b2() else "💾 Local"
                    ubicacion_label = ctk.CTkLabel(
                        adj_frame,
                        text=ubicacion,
                        font=ctk.CTkFont(size=10),
                        text_color="gray"
                    )
                    ubicacion_label.pack(side="right", padx=(5, 10), pady=10)
                    
                    # Guardar referencia
                    self.checkboxes_adjuntos.append((var_checkbox, adjunto_id, ruta_relativa, nombre_archivo))
                
                # Botones de selección rápida
                botones_sel_frame = ctk.CTkFrame(adjuntos_frame)
                botones_sel_frame.pack(fill="x", padx=10, pady=(0, 10))
                
                ctk.CTkButton(botones_sel_frame, text="✅ Seleccionar todos",
                             command=self._seleccionar_todos_adjuntos,
                             width=120).pack(side="left", padx=5, pady=5)
                
                ctk.CTkButton(botones_sel_frame, text="❌ Deseleccionar todos",
                             command=self._deseleccionar_todos_adjuntos,
                             width=120).pack(side="left", padx=5, pady=5)
            else:
                # No hay adjuntos
                no_adj_label = ctk.CTkLabel(adjuntos_frame, 
                                           text="📋 No hay adjuntos disponibles en este RMA",
                                           font=ctk.CTkFont(size=12),
                                           text_color="gray")
                no_adj_label.pack(pady=20)
            
            # Frame de botones principales
            botones_frame = ctk.CTkFrame(main_frame)
            botones_frame.pack(fill="x", pady=(0, 10))
            
            # Botón para continuar con email
            def _click_continuar():
                if destino_var.get() == "otro":
                    email_final = entry_email_otro.get().strip()
                    if not email_final or not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email_final):
                        messagebox.showwarning("Email inválido", "Introduce un email de destinatario válido.")
                        return
                else:
                    email_final = email_acontacto

                asunto_final = entry_asunto.get().strip() or asunto_defecto

                self._procesar_email_con_adjuntos(dialogo, email_final, nombre_cliente, numero_documento_cliente, numero_rma, asunto_final)

            btn_email = ctk.CTkButton(
                botones_frame,
                text="📧 Abrir cliente de correo",
                command=_click_continuar,
                font=ctk.CTkFont(size=12, weight="bold"),
                height=40
            )
            btn_email.pack(side="left", padx=(10, 5), pady=10, fill="x", expand=True)
            
            # Botón cancelar
            btn_cancelar = ctk.CTkButton(
                botones_frame, 
                text="❌ Cancelar",
                command=dialogo.destroy,
                fg_color="#D32F2F", 
                hover_color="#B71C1C",
                width=100
            )
            btn_cancelar.pack(side="right", padx=(5, 10), pady=10)
            
            # Nota informativa
            nota_frame = ctk.CTkFrame(main_frame)
            nota_frame.pack(fill="x")
            
            nota_text = (
                "💡 Nota: Los archivos seleccionados se descargarán temporalmente para adjuntarlos al email.\n"
                "El cliente de correo se abrirá con el email preparado y los archivos listos para adjuntar."
            )
            
            ctk.CTkLabel(nota_frame, text=nota_text,
                        font=ctk.CTkFont(size=10),
                        text_color="gray",
                        wraplength=650).pack(pady=10, padx=10)

            # Calcular tamaño real necesario para mostrar todo el contenido sin recortes
            dialogo.update_idletasks()
            ancho = max(dialogo.winfo_reqwidth() + 20, 700)
            alto = min(dialogo.winfo_reqheight() + 20, dialogo.winfo_screenheight() - 100)
            x = (dialogo.winfo_screenwidth() // 2) - (ancho // 2)
            y = (dialogo.winfo_screenheight() // 2) - (alto // 2)
            dialogo.geometry(f"{ancho}x{alto}+{x}+{y}")
            dialogo.minsize(700, min(600, alto))
            dialogo.deiconify()
            dialogo.grab_set()

        except Exception as e:
            try:
                dialogo.destroy()
            except (NameError, UnboundLocalError, tk.TclError):
                pass
            messagebox.showerror("Error", f"Error preparando email: {e}")
        finally:
            conn.close()

    def _seleccionar_todos_adjuntos(self):
        """Selecciona todos los checkboxes de adjuntos."""
        for var_checkbox, _, _, _ in self.checkboxes_adjuntos:
            var_checkbox.set(True)

    def _deseleccionar_todos_adjuntos(self):
        """Deselecciona todos los checkboxes de adjuntos."""
        for var_checkbox, _, _, _ in self.checkboxes_adjuntos:
            var_checkbox.set(False)

    def _procesar_email_con_adjuntos(self, dialogo, email_acontacto, nombre_cliente, numero_documento_cliente, numero_rma, asunto=None):
        """Procesa los adjuntos seleccionados y abre el cliente de correo."""

        # Recopilar adjuntos seleccionados
        adjuntos_para_email = []
        for var_checkbox, adjunto_id, ruta_relativa, nombre_archivo in self.checkboxes_adjuntos:
            if var_checkbox.get():
                adjuntos_para_email.append((adjunto_id, ruta_relativa, nombre_archivo))

        # Cerrar diálogo
        dialogo.destroy()

        # Continuar con el proceso de email
        self._enviar_email_con_adjuntos_seleccionados(
            email_acontacto, nombre_cliente, numero_documento_cliente, numero_rma, adjuntos_para_email, asunto
        )

    def _enviar_email_con_adjuntos_seleccionados(self, email_acontacto, nombre_cliente, numero_documento_cliente, numero_rma, adjuntos_seleccionados, asunto=None):
        """Envía email con los adjuntos seleccionados."""
        
        try:
            # Lista para almacenar rutas temporales de archivos descargados
            archivos_temporales = []
            
            if adjuntos_seleccionados and usar_b2():
                # Descargar archivos seleccionados de Backblaze B2
                b2_api, bucket = get_b2_client()
                if not b2_api or not bucket:
                    messagebox.showerror("Error", "No se puede conectar con Backblaze B2 para descargar adjuntos.")
                    return
                
                # Crear directorio temporal
                temp_dir = tempfile.mkdtemp(prefix="email_attachments_")
                
                for adjunto_id, ruta_relativa, nombre_archivo in adjuntos_seleccionados:
                    try:
                        # Construir ruta en Backblaze B2
                        ruta_b2 = normalizar_ruta_b2(f"{B2_ROOT_FOLDER}/{ruta_relativa}")
                        
                        # Nombre del archivo temporal
                        nombre_archivo_final = nombre_archivo or os.path.basename(ruta_relativa)
                        temp_file_path = os.path.join(temp_dir, nombre_archivo_final)
                        
                        # Descargar archivo desde B2
                        print(f"Descargando {nombre_archivo_final} para adjuntar al email...")
                        downloaded_file = bucket.download_file_by_name(ruta_b2)
                        
                        # Guardar en archivo temporal
                        downloaded_file.save_to(temp_file_path)
                        
                        archivos_temporales.append(temp_file_path)
                        print(f"✓ Descargado: {nombre_archivo_final}")
                        
                    except B2Error as e:
                        print(f"Error descargando {nombre_archivo_final} desde B2: {e}")
                        messagebox.showwarning("Advertencia", f"No se pudo descargar el archivo '{nombre_archivo_final}': {e}")
                    except Exception as e:
                        print(f"Error descargando {nombre_archivo_final}: {e}")
                        messagebox.showwarning("Advertencia", f"No se pudo descargar el archivo '{nombre_archivo_final}': {e}")
            
            # Definir Asunto y Cuerpo del email
            asunto_base = asunto or f"ILUTREK - Nº {numero_rma} ; DOCUMENTO CLIENTE: {numero_documento_cliente}"
            
            # Texto base del email
            cuerpo_base = (
                f"Buenos dias,\n\n"
                f"Se adjunta resolución sobre el expediente abierto a su número de devolución:\n"
                f"{numero_documento_cliente}.\n"
                f"Para saber el estado de este informe, puede responder a este mismo correo.\n\n"
                f"Transcurridos 15 días del envío de este correo, se dará por cerrado el expediente, no aceptando ningún tipo de no conformidad a esta resolución.\n\n\n"
                f"Dpto. Tecnico Ilutrek."
            )
            
            # Añadir información sobre adjuntos al cuerpo del email
            if adjuntos_seleccionados:
                cuerpo_base += f"\n\n--- Adjuntos incluidos ---\n"
                for _, _, nombre_archivo in adjuntos_seleccionados:
                    archivo_nombre = nombre_archivo or "Archivo adjunto"
                    cuerpo_base += f"• {archivo_nombre}\n"
            
            # Mostrar diálogo informativo sobre los archivos descargados
            if archivos_temporales:
                archivos_list = "\n".join([f"• {os.path.basename(f)}" for f in archivos_temporales])
                info_message = (
                    f"✅ Archivos descargados y listos para adjuntar:\n\n{archivos_list}\n\n"
                    f"📁 Ubicación temporal: {os.path.dirname(archivos_temporales[0])}\n\n"
                    f"Se abrirá tu cliente de correo. Adjunta manualmente estos archivos al email."
                )
                
                respuesta = messagebox.askokcancel(
                    "Archivos preparados", 
                    info_message + "\n\n¿Abrir cliente de correo ahora?",
                    icon="info"
                )
                
                if not respuesta:
                    # Usuario canceló, limpiar archivos temporales
                    self._limpiar_archivos_temporales(archivos_temporales)
                    return
            
            # Abrir cliente de correo con mailto
            email_abierto_ok = self.abrir_cliente_correo_con_mailto(email_acontacto, asunto_base, cuerpo_base)
            
            if email_abierto_ok:
                # Mostrar información sobre archivos temporales si los hay
                if archivos_temporales:
                    # Crear ventana de información persistente
                    self._crear_ventana_archivos_temporales(archivos_temporales, temp_dir)
                
                # Registrar la acción en el historial
                self._registrar_accion_email_historial(numero_rma, email_acontacto, adjuntos_seleccionados, asunto_base)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error enviando email con adjuntos: {e}")

    def _crear_ventana_archivos_temporales(self, archivos_temporales, temp_dir):
        """Crea una ventana informativa sobre los archivos temporales descargados."""
        
        ventana_info = Toplevel(self)
        ventana_info.title("📎 Archivos temporales para email")
        ventana_info.geometry("500x400")
        ventana_info.resizable(False, False)
        
        # Mantener ventana siempre visible
        ventana_info.transient(self)
        ventana_info.lift()
        ventana_info.focus_force()
        
        # Centrar
        ventana_info.update_idletasks()
        x = (ventana_info.winfo_screenwidth() // 2) - (500 // 2)
        y = (ventana_info.winfo_screenheight() // 2) - (400 // 2)
        ventana_info.geometry(f"500x400+{x}+{y}")
        
        # Frame principal
        main_frame = ctk.CTkFrame(ventana_info)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        ctk.CTkLabel(main_frame, text="📎 Archivos listos para adjuntar", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 20))
        
        # Lista de archivos
        ctk.CTkLabel(main_frame, text="Archivos descargados:", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=10)
        
        scroll_frame = ctk.CTkScrollableFrame(main_frame, height=150)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        for archivo in archivos_temporales:
            archivo_frame = ctk.CTkFrame(scroll_frame)
            archivo_frame.pack(fill="x", pady=2)
            
            ctk.CTkLabel(archivo_frame, text=f"📄 {os.path.basename(archivo)}", 
                        font=ctk.CTkFont(size=11)).pack(side="left", padx=10, pady=5)
            
            # Botón para abrir carpeta
            ctk.CTkButton(archivo_frame, text="📁", width=30,
                         command=lambda f=archivo: self._abrir_carpeta_archivo(f)).pack(side="right", padx=5, pady=5)
        
        # Información
        info_text = (
            f"📁 Ubicación: {temp_dir}\n\n"
            f"💡 Instrucciones:\n"
            f"1. Ve a tu cliente de correo que se acaba de abrir\n"
            f"2. Adjunta manualmente los archivos mostrados arriba\n"
            f"3. Envía el email cuando esté listo\n"
            f"4. Los archivos temporales se eliminarán automáticamente"
        )
        
        ctk.CTkLabel(main_frame, text=info_text, 
                    font=ctk.CTkFont(size=10), 
                    text_color="gray",
                    justify="left").pack(pady=10, padx=10, anchor="w")
        
        # Botones
        botones_frame = ctk.CTkFrame(main_frame)
        botones_frame.pack(fill="x", pady=10)
        
        ctk.CTkButton(botones_frame, text="📁 Abrir carpeta",
                     command=lambda: self._abrir_carpeta_archivo(archivos_temporales[0])).pack(side="left", padx=10)
        
        ctk.CTkButton(botones_frame, text="🗑️ Limpiar archivos",
                     command=lambda: self._confirmar_limpiar_archivos(archivos_temporales, ventana_info),
                     fg_color="#D32F2F", hover_color="#B71C1C").pack(side="right", padx=10)

    def _abrir_carpeta_archivo(self, ruta_archivo):
        """Abre la carpeta que contiene el archivo."""
        try:
            folder_path = os.path.dirname(ruta_archivo)
            if sys.platform.startswith('win'):
                os.startfile(folder_path)
            elif sys.platform.startswith('darwin'):  # macOS
                os.system(f'open "{folder_path}"')
            else:  # Linux
                os.system(f'xdg-open "{folder_path}"')
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta: {e}")

    def _confirmar_limpiar_archivos(self, archivos_temporales, ventana):
        """Confirma y limpia los archivos temporales."""
        respuesta = messagebox.askyesno(
            "Limpiar archivos", 
            "¿Estás seguro de que quieres eliminar los archivos temporales?\n\n"
            "Solo hazlo después de haber adjuntado los archivos a tu email."
        )
        
        if respuesta:
            self._limpiar_archivos_temporales(archivos_temporales)
            ventana.destroy()
            messagebox.showinfo("Limpieza completada", "Archivos temporales eliminados correctamente.")

    def _limpiar_archivos_temporales(self, archivos_temporales):
        """Limpia los archivos temporales descargados."""
        for archivo in archivos_temporales:
            try:
                if os.path.exists(archivo):
                    os.remove(archivo)
            except Exception as e:
                print(f"Error eliminando archivo temporal {archivo}: {e}")
        
        # Intentar eliminar el directorio temporal si está vacío
        try:
            if archivos_temporales:
                temp_dir = os.path.dirname(archivos_temporales[0])
                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
        except Exception as e:
            print(f"Error eliminando directorio temporal: {e}")

    def _registrar_accion_email_historial(self, numero_rma, email_destinatario, adjuntos_seleccionados, asunto=None):
        """Registra la acción de envío de email en el historial con destinatario, asunto y adjuntos."""
        try:
            conn = connect_db()
            cursor = conn.cursor()

            descripcion = f"Email enviado a {email_destinatario}"

            if asunto:
                descripcion += f" (Asunto: {asunto})"

            if adjuntos_seleccionados:
                nombres_adjuntos = []
                for _, _, nombre_archivo in adjuntos_seleccionados:
                    nombre = nombre_archivo or "Archivo sin nombre"
                    nombres_adjuntos.append(nombre)
                
                if len(nombres_adjuntos) == 1:
                    descripcion += f" con adjunto: {nombres_adjuntos[0]}"
                else:
                    # Para múltiples adjuntos, mostrar lista
                    lista_adjuntos = ", ".join(nombres_adjuntos)
                    descripcion += f" con adjuntos: {lista_adjuntos}"
            
            cursor.execute("""
                INSERT INTO rma_historial (rma_id, fecha_cambio, usuario, descripcion_cambio)
                VALUES (?, ?, ?, ?)
            """, (self.rma_actual_id, datetime.datetime.now().isoformat(), self.username, descripcion))
            
            conn.commit()
            conn.close()
            
            # Actualizar historial en la interfaz si está visible
            if hasattr(self, 'historial_tab'):
                self.mostrar_historial(self.historial_tab)
                
        except Exception as e:
            print(f"Error registrando email en historial: {e}")

    def abrir_formulario_email(self):
        """Abre el cliente de correo por defecto con un enlace mailto preconfigurado."""
        
        # 🚨 ¡IMPORTANTE! Reemplaza 'tu.email@empresa.com' por la dirección correcta
        email_destino = "carlos@ilutrek.es"
        
        # Generamos un asunto útil que incluye el nombre de la aplicación y el usuario
        asunto = f"Bug/Sugerencia de {self.username} ({self.rol}) en Gestión RMA"
        
        # Creamos un cuerpo predefinido para guiar al compañero
        cuerpo = f"""
Hola,
        
Por favor, describe el problema o sugerencia a continuación:
        
----------------------------------------------------------------------
        
Tipo: [BUG / SUGERENCIA]
Página/Función: [Ej: Listado RMA / Formulario Edición]
Descripción: 
Pasos para reproducir (solo bugs):
        
----------------------------------------------------------------------
        
Información del Sistema (NO MODIFICAR):
Usuario: {self.username}
Versión de la App: {APP_VERSION}
"""
        
        # URL-encode el asunto y el cuerpo (necesario para URLs mailto)
        import urllib.parse
        asunto_codificado = urllib.parse.quote(asunto)
        cuerpo_codificado = urllib.parse.quote(cuerpo)
        
        # Construir el enlace mailto
        mailto_link = f"mailto:{email_destino}?subject={asunto_codificado}&body={cuerpo_codificado}"
        
        try:
            # Abrir el enlace usando el cliente de correo/navegador por defecto
            webbrowser.open(mailto_link)
        except Exception as e:
            # Si falla (ej. en un entorno sin navegador o cliente de correo configurado)
            print(f"Error al abrir el cliente de correo: {e}")
            messagebox.showerror("Error de Email", "No se pudo abrir el cliente de correo por defecto. Por favor, envía un email manualmente a " + email_destino)
