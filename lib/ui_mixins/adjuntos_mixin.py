"""Mixin extraido automaticamente de VentanaPrincipal (app.py).

Estas clases NO son instanciables por si solas: solo aportan metodos que se
combinan con VentanaPrincipal via herencia multiple. Dependen de atributos de
instancia (self.conn, self.username, self.tree_rmas, etc.) inicializados en
VentanaPrincipal.__init__.
"""
from lib.app_core import *  # noqa: F401,F403 - helpers/constantes/imports compartidos con app.py
from lib.app_core import _get_cached_query, invalidate_cache  # nombres "privados" que el wildcard import no trae

class AdjuntosMixin:
    def crear_carpeta_adjuntos_rma(self, codigo_rma):
        """
        Crea la carpeta específica para el RMA en Backblaze B2 o localmente.
        Retorna la ruta (para B2 será el prefijo, para local será la ruta física).
        """
        if usar_b2():
            return self._crear_carpeta_b2(codigo_rma)
        else:
            return self._crear_carpeta_local(codigo_rma)

    def _crear_carpeta_b2(self, codigo_rma):
        """Crea una carpeta (prefijo) en Backblaze B2 para el RMA."""
        b2_api, bucket = get_b2_client()
        if not b2_api or not bucket:
            # Fallback a almacenamiento local si B2 falla
            print("B2 no disponible, usando almacenamiento local")
            return self._crear_carpeta_local(codigo_rma)
        
        # Ruta en B2: Adjuntos_RMA/RMA25001
        # B2 no requiere crear carpetas explícitamente, usa prefijos en nombres de archivo
        carpeta_rma = f"{B2_ROOT_FOLDER}/{codigo_rma}"
        carpeta_rma = normalizar_ruta_b2(carpeta_rma)
        
        print(f"Prefijo B2 configurado para RMA: {carpeta_rma}")
        
        # En B2 no necesitamos crear carpetas, solo retornamos el prefijo
        # Los archivos se crearán con este prefijo automáticamente
        return carpeta_rma

    def _crear_carpeta_local(self, codigo_rma):
        """Crea una carpeta local para el RMA (implementación original)."""
        # 1. Asegurarse de que la carpeta raíz exista (Adjuntos_RMA)
        if not os.path.exists(ADJUNTOS_ROOT_DIR):
            os.makedirs(ADJUNTOS_ROOT_DIR)
            
        # 2. Crear la carpeta específica del RMA
        ruta_rma = os.path.join(ADJUNTOS_ROOT_DIR, codigo_rma)
        os.makedirs(ruta_rma, exist_ok=True)
        return ruta_rma

    def buscar_y_adjuntar_albaran(self):
        """Busca el PDF del albarán en la carpeta configurada y lo adjunta al expediente."""
        from lib.albaran_utils import extraer_nombre_pdf_desde_albaran, buscar_pdf_en_carpeta

        logger.info(f"Usuario {self.username} inicia búsqueda de albarán PDF")

        if not self.current_rma_id:
            logger.warning("Búsqueda de albarán cancelada: expediente no guardado")
            messagebox.showwarning(
                "Expediente no guardado",
                "Guarda el expediente al menos una vez antes de adjuntar archivos.")
            return

        # Leer el número de albarán del campo
        num_albaran = self.entry_Numero_Albaran.get().strip()
        if not num_albaran:
            logger.warning("Búsqueda de albarán cancelada: campo número de albarán vacío")
            messagebox.showwarning(
                "Campo vacío",
                "Introduce primero el número de albarán.")
            return

        # Leer configuración del usuario
        ruta = self.user_settings.get("ruta_carpeta_albaranes", "").strip()
        fmt_usuario = self.user_settings.get("formato_albaran_usuario", "{N}") or "{N}"
        fmt_pdf = self.user_settings.get("formato_archivo_pdf", "{N}.pdf") or "{N}.pdf"

        logger.debug(f"Búsqueda albarán: número='{num_albaran}', carpeta='{ruta}', "
                     f"fmt_usuario='{fmt_usuario}', fmt_pdf='{fmt_pdf}'")

        if not ruta or not os.path.isdir(ruta):
            logger.error(f"Carpeta de albaranes no configurada o inexistente: '{ruta}'")
            messagebox.showerror(
                "Carpeta no configurada",
                "La carpeta de albaranes no está configurada o no existe.\n"
                "Ve a Ajustes → pestaña 'Albaranes' para configurarla.")
            return

        # Construir el nombre esperado del archivo PDF
        try:
            nombre_pdf = extraer_nombre_pdf_desde_albaran(num_albaran, fmt_usuario, fmt_pdf)
            logger.debug(f"Nombre PDF calculado: '{nombre_pdf}'")
        except ValueError as e:
            logger.error(f"Error al interpretar número de albarán '{num_albaran}': {e}")
            messagebox.showerror(
                "Error en formato",
                f"No se pudo interpretar el número de albarán con los patrones configurados:\n{e}\n\n"
                "Ve a Ajustes → pestaña 'Albaranes' para revisar la configuración.")
            return

        # Buscar el archivo en la carpeta (recursivamente)
        ruta_pdf = buscar_pdf_en_carpeta(ruta, nombre_pdf)

        if not ruta_pdf:
            logger.warning(f"PDF '{nombre_pdf}' no encontrado en '{ruta}'")
            messagebox.showwarning(
                "PDF no encontrado",
                f"No se encontró el archivo '{nombre_pdf}' en:\n{ruta}\n\n"
                "Comprueba que el archivo existe y que los patrones de formato "
                "en Ajustes → Albaranes son correctos.")
            return

        logger.info(f"PDF encontrado: '{ruta_pdf}'")

        # Obtener el código RMA
        codigo_rma = self.lbl_codigo_rma.cget("text").split(": ")[1].strip()

        # Usar el nombre real del archivo encontrado (no el patrón, que puede tener *)
        nombre_real = os.path.basename(ruta_pdf)
        nombre_adjunto = f"{codigo_rma}_{nombre_real}"
        logger.debug(f"Nombre real del archivo: '{nombre_real}' → adjunto: '{nombre_adjunto}'")

        # Verificar si ya está adjuntado (evitar duplicados)
        try:
            conn, cursor = self.master.conectar_db()
            cursor.execute(
                "SELECT id FROM rma_adjuntos WHERE rma_id = ? AND nombre_archivo = ?",
                (self.current_rma_id, nombre_adjunto)
            )
            if cursor.fetchone():
                conn.close()
                logger.info(f"PDF '{nombre_adjunto}' ya estaba adjuntado al expediente {codigo_rma}")
                messagebox.showinfo(
                    "Ya adjuntado",
                    f"El archivo '{nombre_real}' ya está adjuntado a este expediente.")
                return
            conn.close()
        except Exception as e:
            logger.warning(f"Error al comprobar duplicado de adjunto: {e}")

        # Subir el archivo (local o B2)
        logger.debug(f"Subiendo adjunto '{nombre_adjunto}' para RMA '{codigo_rma}'")
        if usar_b2():
            exito, ruta_relativa = self._subir_archivo_b2(ruta_pdf, codigo_rma, nombre_adjunto, None)
        else:
            exito, ruta_relativa = self._subir_archivo_local(ruta_pdf, codigo_rma, nombre_adjunto)

        if not exito:
            logger.error(f"Fallo al subir el archivo '{nombre_adjunto}'")
            return

        # Registrar en base de datos
        self.crear_tabla_rma_orders()
        self.crear_tabla_adjuntos()
        conn, cursor = self.master.conectar_db()
        try:
            if getattr(self, '_usar_tipo_almacenamiento', False):
                tipo_almacenamiento = 'backblaze' if usar_b2() else 'local'
                cursor.execute(
                    """INSERT INTO rma_adjuntos
                       (rma_id, nombre_archivo, ruta_relativa, fecha_subida, usuario_subida, tipo_almacenamiento)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (self.current_rma_id, os.path.basename(ruta_relativa), ruta_relativa,
                     datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                     self.username, tipo_almacenamiento)
                )
            else:
                cursor.execute(
                    """INSERT INTO rma_adjuntos
                       (rma_id, nombre_archivo, ruta_relativa, fecha_subida, usuario_subida)
                       VALUES (?, ?, ?, ?, ?)""",
                    (self.current_rma_id, os.path.basename(ruta_relativa), ruta_relativa,
                     datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                     self.username)
                )
            conn.commit()
            logger.info(f"Albarán '{nombre_real}' adjuntado correctamente al expediente {codigo_rma} "
                        f"(rma_id={self.current_rma_id})")
        except Exception as e:
            logger.error(f"Error al registrar adjunto '{nombre_adjunto}' en BD: {e}", exc_info=True)
            messagebox.showerror("Error de BD", f"No se pudo registrar el adjunto: {e}")
            return
        finally:
            conn.close()

        messagebox.showinfo(
            "Albarán adjuntado",
            f"✅ El albarán '{nombre_real}' se ha adjuntado correctamente al expediente.")

        # Recargar la lista de adjuntos
        try:
            self.cargar_lista_adjuntos(self.current_rma_id)
        except Exception as e:
            logger.error(f"Error recargando adjuntos tras adjuntar albarán: {e}")

    def abrir_dialogo_adjunto(self, modo_abrir_carpeta=False):
        """Abre el diálogo de selección de archivo y lo sube al sistema."""
        # 1. Verificar si el RMA ya está guardado (si current_rma_id tiene valor)
        if not self.current_rma_id:
            messagebox.showwarning("Advertencia", "Debe guardar el RMA al menos una vez antes de adjuntar archivos.")
            return
        
        # Obtener el código RMA
        texto_completo = self.lbl_codigo_rma.cget("text") 
        codigo_rma = texto_completo.split(": ")[1] 
        
        # -----------------------------------------------------------------
        # LÓGICA DE ABRIR CARPETA (Modo Informe)
        # -----------------------------------------------------------------
        if modo_abrir_carpeta:
            if usar_b2():
                self._abrir_carpeta_b2(codigo_rma)
            else:
                self._abrir_carpeta_local(codigo_rma)
            return

        # -----------------------------------------------------------------
        # LÓGICA DE SUBIDA DE ARCHIVO
        # -----------------------------------------------------------------
        # 2. Abrir diálogo para seleccionar archivo(s) - MÚLTIPLE SELECCIÓN
        filepaths = filedialog.askopenfilenames(  # Cambio a askopenfilenames para múltiples
            title="Seleccionar Archivo(s) a Adjuntar - ¡Puedes seleccionar varias imágenes!",
            filetypes=(
                ("Todos los archivos", "*.*"), 
                ("Imágenes", "*.jpg;*.jpeg;*.png;*.bmp;*.gif;*.tiff;*.webp;*.heic"),
                ("Documentos PDF", "*.pdf")
            )
        )
        
        if not filepaths:
            return  # El usuario canceló

        # 3. Procesar cada archivo seleccionado
        total_archivos = len(filepaths)
        archivos_exitosos = 0
        
        # Crear una única ventana de progreso para múltiples archivos
        ventana_progreso_general = None
        if total_archivos > 1:
            ventana_progreso_general = ctk.CTkToplevel(self)
            ventana_progreso_general.title(f"📁 Procesando {total_archivos} archivos")
            ventana_progreso_general.geometry("450x130")
            ventana_progreso_general.transient(self)
            ventana_progreso_general.grab_set()
            
            # Centrar ventana
            ventana_progreso_general.update_idletasks()
            x = (ventana_progreso_general.winfo_screenwidth() // 2) - (450 // 2)
            y = (ventana_progreso_general.winfo_screenheight() // 2) - (130 // 2)
            ventana_progreso_general.geometry(f"450x130+{x}+{y}")
            
            label_archivo_actual = ctk.CTkLabel(ventana_progreso_general, text="", wraplength=420)
            label_archivo_actual.pack(pady=(10, 5))
            
            barra_general = ctk.CTkProgressBar(ventana_progreso_general, width=400)
            barra_general.pack(pady=5)
            barra_general.set(0)
        
        for i, filepath in enumerate(filepaths, 1):
            nombre_original = os.path.basename(filepath)
            
            # Añadir prefijo RMA al nombre si el archivo no lo lleva ya.
            # Si ya lo lleva (en cualquier capitalización), se normaliza a mayúsculas.
            match = re.match(r'^(rma\d+_)(.*)', nombre_original, re.IGNORECASE)
            if match:
                # Ya tiene prefijo RMA → normalizarlo a mayúsculas
                nombre_original = match.group(1).upper() + match.group(2)
            else:
                # No tiene prefijo → añadir el del expediente actual
                nombre_original = f"{codigo_rma}_{nombre_original}"
            
            # Actualizar progreso general si hay múltiples archivos
            if ventana_progreso_general:
                label_archivo_actual.configure(text=f"📁 Procesando {i}/{total_archivos}: {nombre_original}")
                barra_general.set((i-1) / total_archivos)
                ventana_progreso_general.update()
            else:
                # Mostrar progreso en consola para archivo único
                print(f"📁 Procesando archivo: {nombre_original}")
            
            # Subir archivo (Dropbox o local) con compresión automática para imágenes
            if usar_b2():
                exito, ruta_relativa = self._subir_archivo_b2(filepath, codigo_rma, nombre_original, ventana_progreso_general)
            else:
                exito, ruta_relativa = self._subir_archivo_local(filepath, codigo_rma, nombre_original)
            
            if not exito:
                continue  # Error ya mostrado, continuar con el siguiente archivo
            
            # 4. Insertar registro en la base de datos para este archivo
            self.crear_tabla_rma_orders()
            self.crear_tabla_adjuntos()
            
            conn, cursor = self.master.conectar_db()
            try:
                if getattr(self, '_usar_tipo_almacenamiento', False):
                    # Usar esquema nuevo con tipo_almacenamiento
                    tipo_almacenamiento = 'backblaze' if usar_b2() else 'local'
                    cursor.execute("""
                        INSERT INTO rma_adjuntos (rma_id, nombre_archivo, ruta_relativa, fecha_subida, usuario_subida, tipo_almacenamiento) 
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        self.current_rma_id, 
                        os.path.basename(ruta_relativa),  # Usar el nombre del archivo final (podría ser _optimizada.jpg)
                        ruta_relativa, 
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                        self.username,
                        tipo_almacenamiento
                    ))
                else:
                    # Usar esquema antiguo sin tipo_almacenamiento
                    cursor.execute("""
                        INSERT INTO rma_adjuntos (rma_id, nombre_archivo, ruta_relativa, fecha_subida, usuario_subida) 
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        self.current_rma_id, 
                        os.path.basename(ruta_relativa),  # Usar el nombre del archivo final
                        ruta_relativa, 
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                        self.username
                    ))
                
                conn.commit()
                archivos_exitosos += 1
                
            except Exception as e:
                print(f"Error insertando adjunto {nombre_original} en BD: {e}")
                messagebox.showerror("Error de BD", f"No se pudo registrar el adjunto {nombre_original}: {e}")
            finally:
                conn.close()
        
        # Cerrar ventana de progreso general y mostrar resumen
        if ventana_progreso_general:
            barra_general.set(1.0)
            label_archivo_actual.configure(text=f"✅ Completado: {archivos_exitosos}/{total_archivos} archivos procesados")
            ventana_progreso_general.update()
            ventana_progreso_general.after(2000, lambda: ventana_progreso_general.destroy())
        
        # 5. Mostrar mensaje final y recargar adjuntos
        if archivos_exitosos == total_archivos:
            if total_archivos == 1:
                messagebox.showinfo("Éxito", f"Archivo procesado y subido correctamente.")
            else:
                messagebox.showinfo("Éxito", f"¡Todos los archivos procesados correctamente!\n{archivos_exitosos} archivos subidos.")
        elif archivos_exitosos > 0:
            messagebox.showwarning("Parcialmente completado", f"Se procesaron {archivos_exitosos} de {total_archivos} archivos.\nRevisa los errores en la consola.")
        else:
            messagebox.showerror("Error", "No se pudo procesar ningún archivo.")
        
        # Recargar la lista de adjuntos
        try:
            self.cargar_lista_adjuntos(self.current_rma_id)
        except Exception as e:
            print(f"Error recargando adjuntos: {e}")
        
        # 5. Mostrar resultado final
        if total_archivos == 1:
            if archivos_exitosos == 1:
                mensaje = f"✅ Archivo adjuntado correctamente"
                if es_imagen(filepaths[0]):
                    mensaje += " (imagen optimizada automáticamente)"
                elif es_video(filepaths[0]):
                    mensaje += " (video optimizado automáticamente)"
                messagebox.showinfo("Éxito", mensaje)
            # Si falla, el error ya se mostró arriba
        else:
            # Múltiples archivos
            if archivos_exitosos == total_archivos:
                mensaje = f"✅ Todos los archivos ({total_archivos}) adjuntados correctamente"
                imagenes_count = sum(1 for fp in filepaths if es_imagen(fp))
                videos_count = sum(1 for fp in filepaths if es_video(fp))
                if imagenes_count > 0:
                    mensaje += f"\n🖼️ {imagenes_count} imagen(es) optimizada(s) automáticamente"
                if videos_count > 0:
                    mensaje += f"\n🎬 {videos_count} video(s) optimizado(s) automáticamente"
                messagebox.showinfo("Éxito", mensaje)
            elif archivos_exitosos > 0:
                messagebox.showwarning("Parcialmente exitoso", 
                    f"Se adjuntaron {archivos_exitosos} de {total_archivos} archivos.\n"
                    f"Revisa los mensajes de error anteriores.")
            else:
                messagebox.showerror("Error", "No se pudo adjuntar ningún archivo.")
        
        # 6. Recargar lista de adjuntos si hubo éxitos
        if archivos_exitosos > 0:
            self.cargar_lista_adjuntos(self.current_rma_id)

    def _abrir_carpeta_b2(self, codigo_rma):
        """Maneja la apertura de carpeta en modo Backblaze B2."""
        # Para B2, mostrar información ya que no hay carpeta física local
        messagebox.showinfo("Backblaze B2", 
            f"Los adjuntos están almacenados en Backblaze B2.\n"
            f"Bucket: {B2_BUCKET_NAME}\n"
            f"Prefijo: {B2_ROOT_FOLDER}/{codigo_rma}\n\n"
            f"Para acceder, usa la consola web de Backblaze B2 o descarga los archivos desde la pestaña de Adjuntos.")

    def _abrir_carpeta_local(self, codigo_rma):
        """Maneja la apertura de carpeta en modo local (implementación original)."""
        ruta_destino_base = self.crear_carpeta_adjuntos_rma(codigo_rma)
        
        try:
            if os.name == 'nt':
                os.startfile(ruta_destino_base)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', ruta_destino_base])
            else:
                subprocess.Popen(['xdg-open', ruta_destino_base])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta:\n{ruta_destino_base}\nError: {e}")

    def _subir_archivo_b2(self, filepath, codigo_rma, nombre_archivo, ventana_progreso_externa=None):
        """
        Sube un archivo a Backblaze B2 con compresión inteligente para imágenes.
        Retorna: (éxito: bool, ruta_relativa: str)
        """
        b2_api, bucket = get_b2_client()
        if not b2_api or not bucket:
            messagebox.showerror("Error", "No se puede conectar con Backblaze B2. Usando almacenamiento local.")
            return self._subir_archivo_local(filepath, codigo_rma, nombre_archivo)
        
        archivo_a_subir = filepath
        archivo_temporal = None
        nombre_archivo_final = nombre_archivo
        
        # ===== COMPRESIÓN DE IMÁGENES =====
        if es_imagen(filepath):
            try:
                ventana_progreso = None
                label_progreso = None
                barra_progreso = None
                
                # Solo crear ventana de progreso si no hay una externa (archivo único)
                if not ventana_progreso_externa:
                    ventana_progreso = ctk.CTkToplevel(self)
                    ventana_progreso.title("🖼️ Optimizando imagen")
                    ventana_progreso.geometry("400x120")
                    ventana_progreso.transient(self)
                    ventana_progreso.grab_set()
                    
                    # Centrar ventana
                    ventana_progreso.update_idletasks()
                    x = (ventana_progreso.winfo_screenwidth() // 2) - (400 // 2)
                    y = (ventana_progreso.winfo_screenheight() // 2) - (120 // 2)
                    ventana_progreso.geometry(f"400x120+{x}+{y}")
                    
                    label_progreso = ctk.CTkLabel(ventana_progreso, text="Preparando compresión...", wraplength=380)
                    label_progreso.pack(pady=(20, 10))
                    
                    barra_progreso = ctk.CTkProgressBar(ventana_progreso, width=350)
                    barra_progreso.pack(pady=10)
                    barra_progreso.set(0.1)
                
                # Función callback para actualizar progreso
                def actualizar_progreso(mensaje):
                    if ventana_progreso:
                        # Ventana individual
                        label_progreso.configure(text=mensaje)
                        ventana_progreso.update()
                        if barra_progreso.get() < 0.9:
                            barra_progreso.set(barra_progreso.get() + 0.15)
                    else:
                        # Solo log para ventana externa
                        print(f"  🎨 {mensaje}")
                
                if ventana_progreso:
                    ventana_progreso.update()
                
                # Comprimir imagen
                resultado = comprimir_imagen_inteligente(filepath, callback_progreso=actualizar_progreso)
                archivo_comprimido, tamaño_original, tamaño_final = resultado
                
                if archivo_comprimido and archivo_comprimido != filepath:
                    archivo_a_subir = archivo_comprimido
                    archivo_temporal = archivo_comprimido
                    
                    # Cambiar extensión a .jpg si se comprimió
                    nombre_base = os.path.splitext(nombre_archivo)[0]
                    nombre_archivo_final = f"{nombre_base}_optimizada.jpg"
                    
                    # Mostrar resultado final
                    if ventana_progreso:
                        barra_progreso.set(1.0)
                        if tamaño_original > tamaño_final:
                            actualizar_progreso(f"✅ ¡Imagen optimizada! {tamaño_original:.1f}MB → {tamaño_final:.1f}MB")
                        else:
                            actualizar_progreso(f"✅ Imagen procesada ({tamaño_original:.1f}MB)")
                
                # Cerrar ventana individual después de un tiempo
                if ventana_progreso:
                    ventana_progreso.after(1500, lambda: ventana_progreso.destroy())
                
            except Exception as e:
                # Si falla la compresión, usar archivo original
                print(f"Error en compresión de imagen: {e}")
                if ventana_progreso:
                    ventana_progreso.destroy()
        
        # ===== COMPRESIÓN DE VIDEOS =====
        if es_video(filepath):
            try:
                ventana_progreso = None
                label_progreso = None
                barra_progreso = None
                
                # Solo crear ventana de progreso si no hay una externa (archivo único)
                if not ventana_progreso_externa:
                    ventana_progreso = ctk.CTkToplevel(self)
                    ventana_progreso.title("🎬 Optimizando video")
                    ventana_progreso.geometry("450x120")
                    ventana_progreso.transient(self)
                    ventana_progreso.grab_set()
                    
                    # Centrar ventana
                    ventana_progreso.update_idletasks()
                    x = (ventana_progreso.winfo_screenwidth() // 2) - (450 // 2)
                    y = (ventana_progreso.winfo_screenheight() // 2) - (120 // 2)
                    ventana_progreso.geometry(f"450x120+{x}+{y}")
                    
                    label_progreso = ctk.CTkLabel(ventana_progreso, text="Preparando compresión...", wraplength=430)
                    label_progreso.pack(pady=(20, 10))
                    
                    barra_progreso = ctk.CTkProgressBar(ventana_progreso, width=400)
                    barra_progreso.pack(pady=10)
                    barra_progreso.set(0.1)
                
                # Función callback para actualizar progreso
                def actualizar_progreso_video(mensaje):
                    if ventana_progreso:
                        # Ventana individual
                        label_progreso.configure(text=mensaje)
                        ventana_progreso.update()
                        # Incrementar barra basándose en el mensaje
                        if "%" in mensaje:
                            try:
                                porcentaje = int(mensaje.split("%")[0].split()[-1])
                                barra_progreso.set(porcentaje / 100)
                            except:
                                pass
                        elif barra_progreso.get() < 0.9:
                            barra_progreso.set(barra_progreso.get() + 0.1)
                    else:
                        # Solo log para ventana externa
                        print(f"  🎬 {mensaje}")
                
                if ventana_progreso:
                    ventana_progreso.update()
                
                # Comprimir video
                resultado = comprimir_video_inteligente(filepath, callback_progreso=actualizar_progreso_video)
                
                # Verificar que el resultado sea válido
                if resultado and len(resultado) == 3:
                    archivo_comprimido, tamaño_original, tamaño_final = resultado
                    
                    if archivo_comprimido and archivo_comprimido != filepath:
                        archivo_a_subir = archivo_comprimido
                        archivo_temporal = archivo_comprimido
                        
                        # Cambiar extensión a .mp4 si se comprimió
                        nombre_base = os.path.splitext(nombre_archivo)[0]
                        nombre_archivo_final = f"{nombre_base}_optimizado.mp4"
                        
                        # Mostrar resultado final
                        if ventana_progreso:
                            barra_progreso.set(1.0)
                            if tamaño_original > tamaño_final:
                                actualizar_progreso_video(f"✅ ¡Video optimizado! {tamaño_original:.1f}MB → {tamaño_final:.1f}MB")
                            else:
                                actualizar_progreso_video(f"✅ Video procesado ({tamaño_original:.1f}MB)")
                
                # Cerrar ventana individual después de un tiempo
                if ventana_progreso:
                    ventana_progreso.after(2000, lambda: ventana_progreso.destroy())
                
            except Exception as e:
                # Si falla la compresión, usar archivo original
                print(f"Error en compresión de video: {e}")
                if 'ventana_progreso' in locals() and ventana_progreso:
                    try:
                        ventana_progreso.destroy()
                    except:
                        pass
        
        # ===== SUBIDA A BACKBLAZE B2 =====
        # Crear el prefijo (carpeta virtual) si no existe
        ruta_carpeta = self.crear_carpeta_adjuntos_rma(codigo_rma)
        
        # Ruta completa en B2 (file_name completo con prefijo)
        ruta_b2 = f"{ruta_carpeta}/{nombre_archivo_final}"
        ruta_b2 = normalizar_ruta_b2(ruta_b2)
        
        try:
            # Leer el archivo (original o comprimido) y subirlo
            bucket.upload_local_file(
                local_file=archivo_a_subir,
                file_name=ruta_b2
            )
            
            # Limpiar archivo temporal si existe
            if archivo_temporal:
                try:
                    os.unlink(archivo_temporal)
                except:
                    pass
            
            # La ruta relativa para BD será: RMA25001/archivo.pdf
            ruta_relativa = f"{codigo_rma}/{nombre_archivo_final}"
            return True, ruta_relativa
            
        except Exception as e:
            # Limpiar archivo temporal en caso de error
            if archivo_temporal:
                try:
                    os.unlink(archivo_temporal)
                except:
                    pass
            messagebox.showerror("Error Backblaze B2", f"No se pudo subir el archivo a Backblaze B2: {e}")
            return False, ""

    def _subir_archivo_local(self, filepath, codigo_rma, nombre_archivo):
        """
        Sube un archivo al almacenamiento local con compresión inteligente para imágenes y videos.
        Retorna: (éxito: bool, ruta_relativa: str)
        """
        archivo_a_subir = filepath
        archivo_temporal = None
        nombre_archivo_final = nombre_archivo
        
        # ===== COMPRESIÓN DE IMÁGENES =====
        if es_imagen(filepath):
            try:
                ventana_progreso = ctk.CTkToplevel(self)
                ventana_progreso.title("🖼️ Optimizando imagen")
                ventana_progreso.geometry("400x120")
                ventana_progreso.transient(self)
                ventana_progreso.grab_set()
                
                # Centrar ventana
                ventana_progreso.update_idletasks()
                x = (ventana_progreso.winfo_screenwidth() // 2) - (400 // 2)
                y = (ventana_progreso.winfo_screenheight() // 2) - (120 // 2)
                ventana_progreso.geometry(f"400x120+{x}+{y}")
                
                label_progreso = ctk.CTkLabel(ventana_progreso, text="Preparando compresión...", wraplength=380)
                label_progreso.pack(pady=(20, 10))
                
                barra_progreso = ctk.CTkProgressBar(ventana_progreso, width=350)
                barra_progreso.pack(pady=10)
                barra_progreso.set(0.1)
                
                # Función callback para actualizar progreso
                def actualizar_progreso(mensaje):
                    label_progreso.configure(text=mensaje)
                    ventana_progreso.update()
                    if barra_progreso.get() < 0.9:
                        barra_progreso.set(barra_progreso.get() + 0.15)
                
                ventana_progreso.update()
                
                # Comprimir imagen
                resultado = comprimir_imagen_inteligente(filepath, callback_progreso=actualizar_progreso)
                archivo_comprimido, tamaño_original, tamaño_final = resultado
                
                if archivo_comprimido and archivo_comprimido != filepath:
                    archivo_a_subir = archivo_comprimido
                    archivo_temporal = archivo_comprimido
                    
                    # Cambiar extensión a .jpg si se comprimió
                    nombre_base = os.path.splitext(nombre_archivo)[0]
                    nombre_archivo_final = f"{nombre_base}_optimizada.jpg"
                    
                    # Mostrar resultado final
                    barra_progreso.set(1.0)
                    if tamaño_original > tamaño_final:
                        actualizar_progreso(f"✅ ¡Imagen optimizada! {tamaño_original:.1f}MB → {tamaño_final:.1f}MB")
                    else:
                        actualizar_progreso(f"✅ Imagen procesada ({tamaño_original:.1f}MB)")
                
                # Cerrar ventana después de un tiempo
                ventana_progreso.after(1500, lambda: ventana_progreso.destroy())
                
            except Exception as e:
                print(f"Error en compresión de imagen: {e}")
                if 'ventana_progreso' in locals():
                    ventana_progreso.destroy()
        
        # ===== COMPRESIÓN DE VIDEOS =====
        if es_video(filepath):
            try:
                ventana_progreso = ctk.CTkToplevel(self)
                ventana_progreso.title("🎬 Optimizando video")
                ventana_progreso.geometry("450x120")
                ventana_progreso.transient(self)
                ventana_progreso.grab_set()
                
                # Centrar ventana
                ventana_progreso.update_idletasks()
                x = (ventana_progreso.winfo_screenwidth() // 2) - (450 // 2)
                y = (ventana_progreso.winfo_screenheight() // 2) - (120 // 2)
                ventana_progreso.geometry(f"450x120+{x}+{y}")
                
                label_progreso = ctk.CTkLabel(ventana_progreso, text="Preparando compresión...", wraplength=430)
                label_progreso.pack(pady=(20, 10))
                
                barra_progreso = ctk.CTkProgressBar(ventana_progreso, width=400)
                barra_progreso.pack(pady=10)
                barra_progreso.set(0.1)
                
                # Función callback para actualizar progreso
                def actualizar_progreso_video(mensaje):
                    label_progreso.configure(text=mensaje)
                    ventana_progreso.update()
                    # Incrementar barra basándose en el mensaje
                    if "%" in mensaje:
                        try:
                            porcentaje = int(mensaje.split("%")[0].split()[-1])
                            barra_progreso.set(porcentaje / 100)
                        except:
                            pass
                    elif barra_progreso.get() < 0.9:
                        barra_progreso.set(barra_progreso.get() + 0.1)
                
                ventana_progreso.update()
                
                # Comprimir video
                resultado = comprimir_video_inteligente(filepath, callback_progreso=actualizar_progreso_video)
                
                # Verificar que el resultado sea válido
                if resultado and len(resultado) == 3:
                    archivo_comprimido, tamaño_original, tamaño_final = resultado
                    
                    if archivo_comprimido and archivo_comprimido != filepath:
                        archivo_a_subir = archivo_comprimido
                        archivo_temporal = archivo_comprimido
                        
                        # Cambiar extensión a .mp4 si se comprimió
                        nombre_base = os.path.splitext(nombre_archivo)[0]
                        nombre_archivo_final = f"{nombre_base}_optimizado.mp4"
                        
                        # Mostrar resultado final
                        barra_progreso.set(1.0)
                        if tamaño_original > tamaño_final:
                            actualizar_progreso_video(f"✅ ¡Video optimizado! {tamaño_original:.1f}MB → {tamaño_final:.1f}MB")
                        else:
                            actualizar_progreso_video(f"✅ Video procesado ({tamaño_original:.1f}MB)")
                
                # Cerrar ventana después de un tiempo
                ventana_progreso.after(2000, lambda: ventana_progreso.destroy())
                
            except Exception as e:
                print(f"Error en compresión de video: {e}")
                if 'ventana_progreso' in locals() and ventana_progreso:
                    try:
                        ventana_progreso.destroy()
                    except:
                        pass
        
        # ===== COPIA AL ALMACENAMIENTO LOCAL =====
        try:
            ruta_destino_dir = self.crear_carpeta_adjuntos_rma(codigo_rma)
            ruta_destino_completa = os.path.join(ruta_destino_dir, nombre_archivo_final)
            
            # Copiar archivo (original o comprimido)
            shutil.copy2(archivo_a_subir, ruta_destino_completa)
            
            # Limpiar archivo temporal si existe
            if archivo_temporal:
                try:
                    os.unlink(archivo_temporal)
                except:
                    pass
            
            # Ruta relativa para BD
            ruta_relativa = os.path.join(codigo_rma, nombre_archivo_final)
            return True, ruta_relativa
            
        except Exception as e:
            # Limpiar archivo temporal en caso de error
            if archivo_temporal:
                try:
                    os.unlink(archivo_temporal)
                except:
                    pass
            messagebox.showerror("Error de Copia", f"No se pudo copiar el archivo: {e}")
            return False, ""

    def _limpiar_archivo_subido(self, ruta_relativa):
        """Intenta eliminar un archivo subido si falla la inserción en BD."""
        if usar_b2():
            b2_api, bucket = get_b2_client()
            if b2_api and bucket:
                try:
                    ruta_b2 = normalizar_ruta_b2(f"{B2_ROOT_FOLDER}/{ruta_relativa}")
                    # Listar versiones del archivo para obtener file_id
                    file_versions = bucket.ls(ruta_b2, latest_only=True, recursive=False)
                    for file_version, _ in file_versions:
                        if file_version.file_name == ruta_b2:
                            b2_api.delete_file_version(file_version.id_, file_version.file_name)
                            break
                except:
                    pass  # No importa si falla la limpieza
        else:
            try:
                ruta_completa = os.path.join(ADJUNTOS_ROOT_DIR, ruta_relativa)
                if os.path.exists(ruta_completa):
                    os.remove(ruta_completa)
            except:
                pass  # No importa si falla la limpieza

    def _get_adjuntos_imagenes(self):
        """
        Devuelve lista de adjuntos de imagen del expediente actual.
        Usada por el RichTextEditor para poblar el selector 'Desde adjuntos'.
        Incluye tipo_almacenamiento para que el editor sepa si descargar desde B2 o local.
        """
        if not getattr(self, 'current_rma_id', None):
            return []

        ext_img = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}

        try:
            conn, cursor = self.master.conectar_db()
            cursor.execute(
                "SELECT nombre_archivo, ruta_relativa, tipo_almacenamiento "
                "FROM rma_adjuntos WHERE rma_id = ?",
                (self.current_rma_id,)
            )
            filas = cursor.fetchall()
            conn.close()
        except Exception:
            return []

        resultado = []
        for nombre, ruta_rel, tipo_alm in filas:
            if os.path.splitext(nombre)[1].lower() not in ext_img:
                continue
            resultado.append({
                'nombre':              nombre,
                'ruta_relativa':       ruta_rel,
                'tipo_almacenamiento': tipo_alm or 'local',
                'adjuntos_root':       ADJUNTOS_ROOT_DIR,
            })
        return resultado

    def _formatear_tamano(self, bytes_size):
        """Convierte bytes a cadena legible (KB, MB, etc.)."""
        if bytes_size is None:
            return "—"
        if bytes_size < 1024:
            return f"{bytes_size} B"
        elif bytes_size < 1024 * 1024:
            return f"{bytes_size / 1024:.1f} KB"
        elif bytes_size < 1024 * 1024 * 1024:
            return f"{bytes_size / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_size / (1024 * 1024 * 1024):.2f} GB"

    def _obtener_tamanos_carpeta_b2(self, carpeta_rma):
        """
        Lista todos los archivos de una carpeta RMA en B2 en una sola llamada.
        Retorna dict {nombre_archivo: size_bytes}.
        """
        resultado = {}
        try:
            b2_api, bucket = get_b2_client()
            if not b2_api or not bucket:
                return resultado
            prefijo = normalizar_ruta_b2(f"{B2_ROOT_FOLDER}/{carpeta_rma}/")
            file_versions = bucket.ls(prefijo, latest_only=True, recursive=False)
            for file_version, _ in file_versions:
                nombre = file_version.file_name.split("/")[-1]
                resultado[nombre] = file_version.size
        except Exception as e:
            print(f"Error obteniendo tamaños de B2: {e}")
        return resultado

    def cargar_lista_adjuntos(self, rma_id):
        """Consulta y muestra el listado de adjuntos para un RMA específico."""
        
        # Verificar que el frame existe y la aplicación sigue activa
        try:
            if not hasattr(self, 'adjuntos_list_frame') or not self.adjuntos_list_frame.winfo_exists():
                return
        except Exception:
            return
        
        # Limpiar el frame antes de cargar la nueva lista
        try:
            for widget in self.adjuntos_list_frame.winfo_children():
                widget.destroy()
        except Exception as e:
            print(f"Error limpiando widgets: {e}")
            return

        try:
            conn, cursor = self.master.conectar_db()
            cursor.execute("SELECT id, nombre_archivo, ruta_relativa FROM rma_adjuntos WHERE rma_id = ?", (rma_id,))
            adjuntos = cursor.fetchall()
            conn.close()
        except Exception as e:
            print(f"Error cargando adjuntos: {e}")
            return

        # --- Obtener tamaños en una sola operación ---
        tamanos = {}
        if adjuntos:
            if usar_b2():
                primera_ruta = adjuntos[0][2].replace("\\", "/")
                carpeta_rma = primera_ruta.split("/")[0]
                tamanos_b2 = self._obtener_tamanos_carpeta_b2(carpeta_rma)
                for adjunto_id, nombre, ruta in adjuntos:
                    tamanos[adjunto_id] = tamanos_b2.get(nombre)
            else:
                for adjunto_id, nombre, ruta in adjuntos:
                    ruta_completa = os.path.join(ADJUNTOS_ROOT_DIR, ruta)
                    try:
                        tamanos[adjunto_id] = os.path.getsize(ruta_completa) if os.path.exists(ruta_completa) else None
                    except Exception:
                        tamanos[adjunto_id] = None

        # Actualizar stats
        if hasattr(self, 'lbl_adjuntos_stats'):
            if not adjuntos:
                self.lbl_adjuntos_stats.configure(text="Sin archivos adjuntos")
            else:
                total_bytes = sum(v for v in tamanos.values() if v is not None)
                n = len(adjuntos)
                plural = "archivos" if n != 1 else "archivo"
                total_str = self._formatear_tamano(total_bytes) if total_bytes > 0 else "—"
                self.lbl_adjuntos_stats.configure(
                    text=f"📎 {n} {plural} adjuntos  |  💾 Total: {total_str}"
                )

        if not adjuntos:
            ctk.CTkLabel(self.adjuntos_list_frame, text="No hay archivos adjuntos para este expediente.").pack(pady=10)
            return

        for i, adjunto in enumerate(adjuntos):
            adjunto_id, nombre, ruta = adjunto
            tamano_bytes = tamanos.get(adjunto_id)
            tamano_str = self._formatear_tamano(tamano_bytes)

            item_frame = ctk.CTkFrame(self.adjuntos_list_frame)
            item_frame.pack(fill='x', padx=5, pady=2)

            # Bloque izquierdo: nombre + tamaño
            info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            info_frame.pack(side='left', fill='x', expand=True, padx=5, pady=2)

            ctk.CTkLabel(info_frame, text=nombre, anchor='w', font=ctk.CTkFont(size=13)).pack(side='left', padx=(0, 6))
            ctk.CTkLabel(info_frame, text=tamano_str, anchor='w',
                         font=ctk.CTkFont(size=11), text_color="gray60").pack(side='left')

            # Botón Eliminar
            btn_eliminar = ctk.CTkButton(
                item_frame, 
                text="🗑️", 
                width=35, 
                fg_color="red", 
                hover_color="darkred",
                command=lambda aid=adjunto_id, r=ruta: self.confirmar_eliminar_adjunto(aid, r)
            )
            btn_eliminar.pack(side='right', padx=2)
            Tooltip(btn_eliminar, "Eliminar archivo")

            # Botón Descargar
            btn_descargar = ctk.CTkButton(
                item_frame, 
                text="⬇️", 
                width=35,
                command=lambda r=ruta: self.descargar_adjunto_guardar(r)
            )
            btn_descargar.pack(side='right', padx=2)
            Tooltip(btn_descargar, "Descargar archivo")

            # Botón Renombrar
            btn_renombrar = ctk.CTkButton(
                item_frame,
                text="🏷️",
                width=35,
                command=lambda aid=adjunto_id, n=nombre, r=ruta: self.renombrar_adjunto(aid, n, r)
            )
            btn_renombrar.pack(side='right', padx=2)
            Tooltip(btn_renombrar, "Renombrar archivo")

            # Botón Editar (descarga, edita y resube)
            if usar_b2():  # Solo mostrar editar en modo Dropbox
                btn_editar = ctk.CTkButton(
                    item_frame, 
                    text="✏️", 
                    width=35,
                    command=lambda r=ruta, aid=adjunto_id: self.editar_adjunto(r, aid)
                )
                btn_editar.pack(side='right', padx=2)
                Tooltip(btn_editar, "Editar archivo")

            # Botón Visualizar (solo lectura)
            btn_ver = ctk.CTkButton(
                item_frame, 
                text="👁️", 
                width=35, 
                command=lambda r=ruta: self.abrir_adjunto(r)
            )
            btn_ver.pack(side='right', padx=2)
            Tooltip(btn_ver, "Visualizar archivo")

    def renombrar_adjunto(self, adjunto_id, nombre_actual, ruta_relativa):
        """Muestra un diálogo para renombrar un adjunto y aplica el cambio en B2/local y BD."""

        # --- Diálogo de entrada ---
        dlg = ctk.CTkToplevel(self)
        dlg.title("Renombrar archivo")
        dlg.geometry("420x160")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()
        dlg.update_idletasks()
        x = (dlg.winfo_screenwidth() // 2) - 210
        y = (dlg.winfo_screenheight() // 2) - 80
        dlg.geometry(f"420x160+{x}+{y}")

        ctk.CTkLabel(dlg, text="Nuevo nombre del archivo:", anchor='w').pack(padx=16, pady=(16, 4), fill='x')

        entry = ctk.CTkEntry(dlg, width=388)
        entry.pack(padx=16)
        entry.insert(0, nombre_actual)
        entry.select_range(0, 'end')
        entry.focus_set()

        lbl_error = ctk.CTkLabel(dlg, text="", text_color="red", font=ctk.CTkFont(size=11))
        lbl_error.pack(padx=16, pady=(2, 0), fill='x')

        # Extraer prefijo RMA de la ruta (ej: "RMA-000123" de "RMA-000123/foto.jpg")
        partes_ruta = ruta_relativa.replace("\\", "/").split("/")
        carpeta_rma = partes_ruta[0] if len(partes_ruta) > 1 else ""

        def _aplicar():
            nuevo_nombre = entry.get().strip()
            if not nuevo_nombre:
                lbl_error.configure(text="El nombre no puede estar vacío.")
                return

            # Validar caracteres no permitidos en nombres de archivo
            chars_invalidos = set('/\\:*?"<>|')
            if any(c in chars_invalidos for c in nuevo_nombre):
                lbl_error.configure(text='Nombre inválido. No usar: / \\ : * ? " < > |')
                return

            # Respetar prefijo RMA: si el usuario NO lo incluyó, añadirlo
            prefijo = carpeta_rma.upper() + "_"
            if carpeta_rma:
                if nuevo_nombre.upper().startswith(prefijo):
                    nuevo_nombre = prefijo + nuevo_nombre[len(prefijo):]
                else:
                    nuevo_nombre = prefijo + nuevo_nombre

            if nuevo_nombre == nombre_actual:
                dlg.destroy()
                return

            # Obtener extensión del original si el nuevo nombre no la tiene
            _, ext_original = os.path.splitext(nombre_actual)
            _, ext_nuevo = os.path.splitext(nuevo_nombre)
            if not ext_nuevo and ext_original:
                nuevo_nombre += ext_original

            # Construir nueva ruta relativa
            nueva_ruta_relativa = f"{carpeta_rma}/{nuevo_nombre}" if carpeta_rma else nuevo_nombre

            # --- Deshabilitar botones y mostrar estado ---
            btn_ok.configure(state="disabled", text="Renombrando...")
            btn_cancelar.configure(state="disabled")
            dlg.update()

            # --- Operación de renombrado ---
            try:
                if usar_b2():
                    exito = self._renombrar_archivo_b2(ruta_relativa, nueva_ruta_relativa)
                else:
                    exito = self._renombrar_archivo_local(ruta_relativa, nueva_ruta_relativa)
            except Exception as e:
                lbl_error.configure(text=f"Error: {e}")
                btn_ok.configure(state="normal", text="Renombrar")
                btn_cancelar.configure(state="normal")
                return

            if not exito:
                lbl_error.configure(text="No se pudo renombrar el archivo. Inténtelo de nuevo.")
                btn_ok.configure(state="normal", text="Renombrar")
                btn_cancelar.configure(state="normal")
                return

            # --- Actualizar BD ---
            try:
                conn, cursor = self.master.conectar_db()
                cursor.execute(
                    "UPDATE rma_adjuntos SET nombre_archivo = ?, ruta_relativa = ? WHERE id = ?",
                    (nuevo_nombre, nueva_ruta_relativa, adjunto_id)
                )
                cursor.execute(
                    """INSERT INTO rma_historial (rma_id, fecha_cambio, usuario, descripcion_cambio)
                       VALUES (?, ?, ?, ?)""",
                    (
                        self.current_rma_id,
                        datetime.datetime.now().isoformat(),
                        self.username,
                        f"Adjunto renombrado: '{nombre_actual}' → '{nuevo_nombre}'"
                    )
                )
                conn.commit()
                conn.close()
            except Exception as e:
                messagebox.showerror("Error BD", f"El archivo fue renombrado pero no se pudo actualizar la base de datos: {e}")

            dlg.destroy()
            self.cargar_lista_adjuntos(self.current_rma_id)

        def _cancelar():
            dlg.destroy()

        btn_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_frame.pack(pady=(6, 12))
        btn_ok = ctk.CTkButton(btn_frame, text="Renombrar", width=120, command=_aplicar)
        btn_ok.pack(side='left', padx=6)
        btn_cancelar = ctk.CTkButton(btn_frame, text="Cancelar", width=100,
                                      fg_color="gray40", hover_color="gray30", command=_cancelar)
        btn_cancelar.pack(side='left', padx=6)

        entry.bind("<Return>", lambda e: _aplicar())
        entry.bind("<Escape>", lambda e: _cancelar())

    def _renombrar_archivo_b2(self, ruta_relativa_origen, ruta_relativa_destino):
        """
        Renombra un archivo en B2 copiando (descarga+resubida) y borrando el original.
        Retorna True si tuvo éxito, False si falló.
        """
        import tempfile

        b2_api, bucket = get_b2_client()
        if not b2_api or not bucket:
            return False

        ruta_b2_origen = normalizar_ruta_b2(f"{B2_ROOT_FOLDER}/{ruta_relativa_origen}")
        ruta_b2_destino = normalizar_ruta_b2(f"{B2_ROOT_FOLDER}/{ruta_relativa_destino}")

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = tmp.name

            downloaded = bucket.download_file_by_name(ruta_b2_origen)
            downloaded.save_to(tmp_path)

            bucket.upload_local_file(local_file=tmp_path, file_name=ruta_b2_destino)

            file_versions = bucket.ls(ruta_b2_origen, latest_only=True, recursive=False)
            for file_version, _ in file_versions:
                if file_version.file_name == ruta_b2_origen:
                    b2_api.delete_file_version(file_version.id_, file_version.file_name)
                    break

            return True

        except Exception as e:
            print(f"Error renombrando archivo en B2: {e}")
            return False
        finally:
            try:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass

    def _renombrar_archivo_local(self, ruta_relativa_origen, ruta_relativa_destino):
        """
        Renombra un archivo en almacenamiento local.
        Retorna True si tuvo éxito, False si falló.
        """
        try:
            ruta_origen = os.path.join(ADJUNTOS_ROOT_DIR, ruta_relativa_origen)
            ruta_destino = os.path.join(ADJUNTOS_ROOT_DIR, ruta_relativa_destino)
            if not os.path.exists(ruta_origen):
                print(f"Archivo origen no encontrado: {ruta_origen}")
                return False
            os.rename(ruta_origen, ruta_destino)
            return True
        except Exception as e:
            print(f"Error renombrando archivo local: {e}")
            return False

    def abrir_adjunto(self, ruta_relativa):
        """Abre el archivo adjunto desde Backblaze B2 o almacenamiento local."""
        if usar_b2():
            self._abrir_adjunto_b2(ruta_relativa)
        else:
            self._abrir_adjunto_local(ruta_relativa)

    def _abrir_adjunto_b2(self, ruta_relativa):
        """Descarga temporalmente un archivo de Backblaze B2 y lo abre."""
        b2_api, bucket = get_b2_client()
        if not b2_api or not bucket:
            messagebox.showerror("Error", "No se puede conectar con Backblaze B2.")
            return
        
        # Construir ruta en B2
        ruta_b2 = normalizar_ruta_b2(f"{B2_ROOT_FOLDER}/{ruta_relativa}")
        
        try:
            # Crear archivo temporal
            nombre_archivo = os.path.basename(ruta_relativa)
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{nombre_archivo}") as temp_file:
                temp_path = temp_file.name
            
            # Descargar archivo de B2
            downloaded_file = bucket.download_file_by_name(ruta_b2)
            downloaded_file.save_to(temp_path)
            
            # Abrir archivo temporal
            self._abrir_archivo_sistema(temp_path)
            
            # Programar eliminación del archivo temporal después de un tiempo
            # (El usuario tendrá tiempo para abrirlo en su programa)
            def limpiar_temp():
                try:
                    os.unlink(temp_path)
                except:
                    pass
            
            # Limpiar después de 60 segundos (suficiente tiempo para que se abra)
            threading.Timer(60.0, limpiar_temp).start()
            
        except B2Error as e:
            if "file_not_found" in str(e).lower() or "not_found" in str(e).lower():
                messagebox.showerror("Error", f"Archivo no encontrado en Backblaze B2: {ruta_relativa}")
            else:
                messagebox.showerror("Error", f"Error descargando de Backblaze B2: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Error procesando archivo de Backblaze B2: {e}")

    def _abrir_adjunto_local(self, ruta_relativa):
        """Abre un archivo del almacenamiento local (implementación original)."""
        ruta_completa = os.path.join(ADJUNTOS_ROOT_DIR, ruta_relativa)
        
        if not os.path.exists(ruta_completa):
            messagebox.showerror("Error", f"Archivo no encontrado: {ruta_completa}")
            return
        
        self._abrir_archivo_sistema(ruta_completa)

    def _abrir_archivo_sistema(self, ruta_archivo):
        """Abre un archivo con el programa predeterminado del sistema."""
        try:
            if sys.platform == "win32":
                os.startfile(ruta_archivo)
            elif sys.platform == "darwin":
                subprocess.call(['open', ruta_archivo])
            else:
                subprocess.call(['xdg-open', ruta_archivo])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el archivo: {e}")

    def _abrir_archivo_sistema(self, ruta_archivo):
        """Abre un archivo con el programa predeterminado del sistema."""
        try:
            if sys.platform.startswith('win'):
                os.startfile(ruta_archivo)
            elif sys.platform.startswith('darwin'):  # macOS
                os.system(f'open "{ruta_archivo}"')
            else:  # Linux y otros
                os.system(f'xdg-open "{ruta_archivo}"')
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el archivo: {e}")

    def editar_adjunto(self, ruta_relativa, adjunto_id):
        """
        Descarga un archivo de Backblaze B2, permite editarlo y lo resube automáticamente.
        """
        if not usar_b2():
            messagebox.showinfo("Información", "La función de editar solo está disponible con archivos de Backblaze B2.")
            return
            
        b2_api, bucket = get_b2_client()
        if not b2_api or not bucket:
            messagebox.showerror("Error", "No se puede conectar con Backblaze B2.")
            return
            
        # Construir ruta en Backblaze B2
        ruta_b2 = normalizar_ruta_b2(f"{B2_ROOT_FOLDER}/{ruta_relativa}")
        nombre_archivo = os.path.basename(ruta_relativa)
        
        try:
            # 1. Crear archivo temporal para edición
            temp_dir = tempfile.mkdtemp(prefix="dropbox_edit_")
            temp_path = os.path.join(temp_dir, nombre_archivo)
            
            # 2. Descargar archivo de Backblaze B2
            print(f"Descargando {nombre_archivo} para edición...")
            downloaded_file = bucket.download_file_by_name(ruta_b2)
            downloaded_file.save_to(temp_path)
            
            # 3. Mostrar diálogo informativo
            respuesta = messagebox.askyesno(
                "Editar Archivo",
                f"Se va a abrir '{nombre_archivo}' para edición.\n\n"
                f"IMPORTANTE:\n"
                f"• El archivo se descargará temporalmente\n"
                f"• Podrás editarlo con el programa predeterminado\n"
                f"• Cuando GUARDES y CIERRES el programa, se resubirá automáticamente\n"
                f"• Los cambios se sincronizarán con Backblaze B2\n\n"
                f"¿Continuar?"
            )
            
            if not respuesta:
                # Limpiar archivo temporal si el usuario cancela
                try:
                    os.remove(temp_path)
                    os.rmdir(temp_dir)
                except:
                    pass
                return
            
            # 4. Obtener tiempo de modificación inicial
            tiempo_inicial = os.path.getmtime(temp_path)
            
            # 5. Abrir archivo para edición
            self._abrir_archivo_sistema(temp_path)
            
            # 6. Crear diálogo de seguimiento
            self._crear_dialogo_seguimiento_edicion(temp_path, ruta_b2, tiempo_inicial, temp_dir, nombre_archivo)
            
        except B2Error as e:
            error_details = str(e)
            if "not_found" in error_details.lower():
                messagebox.showerror("Error", f"Archivo no encontrado en Backblaze B2: {ruta_relativa}")
            else:
                messagebox.showerror("Error", f"Error descargando de Backblaze B2: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Error procesando archivo para edición: {e}")

    def _crear_dialogo_seguimiento_edicion(self, temp_path, ruta_b2, tiempo_inicial, temp_dir, nombre_archivo):
        """Crea un diálogo para hacer seguimiento del proceso de edición."""
        
        # Crear ventana de seguimiento
        dialogo = Toplevel(self)
        dialogo.title("Editando archivo...")
        dialogo.geometry("500x300")
        dialogo.resizable(False, False)
        dialogo.transient(self)
        dialogo.grab_set()
        
        # Centrar en pantalla
        dialogo.update_idletasks()
        x = (dialogo.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialogo.winfo_screenheight() // 2) - (300 // 2)
        dialogo.geometry(f"500x300+{x}+{y}")
        
        # Frame principal
        main_frame = ctk.CTkFrame(dialogo)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        titulo = ctk.CTkLabel(main_frame, text=f"📝 Editando: {nombre_archivo}", 
                             font=ctk.CTkFont(size=16, weight="bold"))
        titulo.pack(pady=(10, 20))
        
        # Estado
        self.estado_label = ctk.CTkLabel(main_frame, 
                                        text="🟡 Archivo abierto para edición...\nGuarda los cambios y cierra el programa cuando termines.",
                                        font=ctk.CTkFont(size=12))
        self.estado_label.pack(pady=10)
        
        # Botones
        botones_frame = ctk.CTkFrame(main_frame)
        botones_frame.pack(pady=20, fill="x")
        
        # Botón para verificar cambios manualmente
        btn_verificar = ctk.CTkButton(botones_frame, text="🔄 Verificar cambios",
                                     command=lambda: self._verificar_cambios_manual(temp_path, tiempo_inicial))
        btn_verificar.pack(side="left", padx=10, pady=10)
        
        # Botón para subir cambios
        self.btn_subir = ctk.CTkButton(botones_frame, text="⬆️ Subir cambios", 
                                      state="disabled",
                                      command=lambda: self._subir_cambios_editados(temp_path, ruta_b2, temp_dir, dialogo))
        self.btn_subir.pack(side="left", padx=10, pady=10)
        
        # Botón cancelar
        btn_cancelar = ctk.CTkButton(botones_frame, text="❌ Cancelar", 
                                    fg_color="#D32F2F", hover_color="#B71C1C",
                                    command=lambda: self._cancelar_edicion(temp_path, temp_dir, dialogo))
        btn_cancelar.pack(side="right", padx=10, pady=10)

        # Variables de estado
        dialogo.tiempo_inicial = tiempo_inicial
        dialogo.temp_path = temp_path
        dialogo.cambios_detectados = False
        
        # Iniciar verificación automática cada 3 segundos
        self._verificar_cambios_automatico(dialogo, temp_path, tiempo_inicial)

    def _verificar_cambios_automatico(self, dialogo, temp_path, tiempo_inicial):
        """Verifica automáticamente si el archivo ha sido modificado."""
        try:
            if not os.path.exists(temp_path) or not dialogo.winfo_exists():
                return
                
            tiempo_actual = os.path.getmtime(temp_path)
            
            if tiempo_actual > tiempo_inicial and not dialogo.cambios_detectados:
                # ¡Cambios detectados!
                dialogo.cambios_detectados = True
                self.estado_label.configure(
                    text="✅ ¡Cambios detectados!\nPuedes subir los cambios a Backblaze B2 ahora.",
                    text_color="green"
                )
                self.btn_subir.configure(state="normal")
                dialogo.tiempo_inicial = tiempo_actual  # Actualizar para futuras verificaciones
            
            # Programar próxima verificación
            dialogo.after(3000, lambda: self._verificar_cambios_automatico(dialogo, temp_path, tiempo_inicial))
            
        except Exception as e:
            print(f"Error verificando cambios: {e}")

    def _verificar_cambios_manual(self, temp_path, tiempo_inicial):
        """Verificación manual de cambios."""
        try:
            if not os.path.exists(temp_path):
                self.estado_label.configure(text="❌ Error: Archivo temporal no encontrado", text_color="red")
                return
                
            tiempo_actual = os.path.getmtime(temp_path)
            
            if tiempo_actual > tiempo_inicial:
                self.estado_label.configure(
                    text="✅ ¡Cambios detectados!\nPuedes subir los cambios a Backblaze B2.",
                    text_color="green"
                )
                self.btn_subir.configure(state="normal")
            else:
                self.estado_label.configure(
                    text="ℹ️ No se detectaron cambios aún.\nGuarda el archivo en tu programa de edición.",
                    text_color="blue"
                )
        except Exception as e:
            self.estado_label.configure(text=f"❌ Error verificando cambios: {e}", text_color="red")

    def _subir_cambios_editados(self, temp_path, ruta_b2, temp_dir, dialogo):
        """Sube los cambios editados de vuelta a Backblaze B2."""
        try:
            if not os.path.exists(temp_path):
                messagebox.showerror("Error", "Archivo temporal no encontrado.")
                return
                
            b2_api, bucket = get_b2_client()
            if not b2_api or not bucket:
                messagebox.showerror("Error", "No se puede conectar con Backblaze B2.")
                return
            
            # Subir a Backblaze B2 (sobrescribir automáticamente)
            bucket.upload_local_file(
                local_file=temp_path,
                file_name=ruta_b2
            )
            
            # Limpiar archivos temporales
            try:
                os.remove(temp_path)
                os.rmdir(temp_dir)
            except:
                pass
            
            # Cerrar diálogo y mostrar éxito
            dialogo.destroy()
            messagebox.showinfo("Éxito", "¡Archivo editado y sincronizado con Backblaze B2 correctamente!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error subiendo cambios a Backblaze B2: {e}")

    def _cancelar_edicion(self, temp_path, temp_dir, dialogo):
        """Cancela la edición y limpia archivos temporales."""
        respuesta = messagebox.askyesno(
            "Cancelar edición", 
            "¿Estás seguro de que quieres cancelar?\nSe perderán todos los cambios no subidos."
        )
        
        if respuesta:
            # Limpiar archivos temporales
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                os.rmdir(temp_dir)
            except Exception as e:
                print(f"Error limpiando archivos temporales: {e}")
            
            # Cerrar diálogo
            dialogo.destroy()

    def confirmar_eliminar_adjunto(self, adjunto_id, ruta_relativa):
        """Pide confirmación antes de eliminar el registro y el archivo."""
        try:
            # Verificar que la aplicación sigue activa
            if not hasattr(self, 'master') or not self.master.winfo_exists():
                return
            
            if messagebox.askyesno("Confirmar Eliminación", 
                                 "¿Está seguro de que desea eliminar este adjunto? Esta acción es irreversible y también eliminará el archivo del disco."):
                self.eliminar_adjunto(adjunto_id, ruta_relativa)
        except Exception as e:
            print(f"Error en confirmación de eliminación: {e}")

    def eliminar_adjunto(self, adjunto_id, ruta_relativa):
        """Elimina el registro de la base de datos y el archivo físico."""
        try:
            conn, cursor = self.master.conectar_db()
        except Exception as e:
            messagebox.showerror("Error", f"Error conectando a la base de datos: {e}")
            return
        
        try:
            # 1. Eliminar archivo físico primero
            if usar_b2():
                exito_archivo = self._eliminar_archivo_b2(ruta_relativa)
            else:
                exito_archivo = self._eliminar_archivo_local(ruta_relativa)
            
            # 2. Eliminar registro de la BD (incluso si el archivo falló)
            cursor.execute("DELETE FROM rma_adjuntos WHERE id = ?", (adjunto_id,))
            conn.commit()
            
            if exito_archivo:
                messagebox.showinfo("Éxito", "Adjunto eliminado correctamente.")
            else:
                messagebox.showwarning("Parcial", "Registro eliminado de la base de datos, pero hubo problemas eliminando el archivo.")
            
            # Recargar el listado solo si la aplicación sigue activa
            try:
                if hasattr(self, 'adjuntos_list_frame') and self.adjuntos_list_frame.winfo_exists():
                    self.cargar_lista_adjuntos(self.current_rma_id)
            except Exception as e:
                print(f"No se pudo recargar lista de adjuntos: {e}")
            
        except Exception as e:
            # Manejar rollback de forma compatible con diferentes tipos de BD
            try:
                if hasattr(conn, 'rollback'):
                    conn.rollback()
            except Exception:
                pass  # Ignorar errores de rollback en Turso
            messagebox.showerror("Error", f"Error al eliminar el adjunto: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _eliminar_archivo_b2(self, ruta_relativa):
        """
        Elimina un archivo de Backblaze B2.
        Retorna True si fue exitoso, False si hubo error.
        """
        b2_api, bucket = get_b2_client()
        if not b2_api or not bucket:
            print("No se puede conectar con Backblaze B2 para eliminar archivo")
            return False
        
        ruta_b2 = normalizar_ruta_b2(f"{B2_ROOT_FOLDER}/{ruta_relativa}")
        
        try:
            # Listar versiones del archivo para obtener file_id
            file_versions = bucket.ls(ruta_b2, latest_only=True, recursive=False)
            for file_version, _ in file_versions:
                if file_version.file_name == ruta_b2:
                    b2_api.delete_file_version(file_version.id_, file_version.file_name)
                    return True
            # Si no se encontró, considerarlo ya eliminado
            print(f"Archivo no encontrado en Backblaze B2 (ya eliminado?): {ruta_b2}")
            return True
        except B2Error as e:
            print(f"Error eliminando archivo de Backblaze B2: {e}")
            return False

    def descargar_adjunto_guardar(self, ruta_relativa):
        """
        Descarga un archivo adjunto y permite al usuario guardarlo donde quiera.
        Llama a la función de rma_utils.py para manejar la lógica.
        """
        from lib.rma_utils import descargar_adjunto
        
        descargar_adjunto(
            ruta_relativa=ruta_relativa,
            usar_b2_fn=usar_b2,
            get_b2_client_fn=get_b2_client,
            normalizar_ruta_b2_fn=normalizar_ruta_b2,
            b2_root_folder=B2_ROOT_FOLDER,
            adjuntos_root_dir=ADJUNTOS_ROOT_DIR
        )

    def _eliminar_archivo_local(self, ruta_relativa):
        """
        Elimina un archivo del almacenamiento local.
        Retorna True si fue exitoso, False si hubo error.
        """
        ruta_completa = os.path.join(ADJUNTOS_ROOT_DIR, ruta_relativa)
        
        try:
            if os.path.exists(ruta_completa):
                os.remove(ruta_completa)
                return True
            else:
                print(f"Archivo local no encontrado (ya eliminado?): {ruta_completa}")
                return True  # Considerarlo exitoso si ya no existe
        except Exception as e:
            print(f"Error eliminando archivo local: {e}")
            return False
