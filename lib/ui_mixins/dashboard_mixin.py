"""Mixin extraido automaticamente de VentanaPrincipal (app.py).

Estas clases NO son instanciables por si solas: solo aportan metodos que se
combinan con VentanaPrincipal via herencia multiple. Dependen de atributos de
instancia (self.conn, self.username, self.tree_rmas, etc.) inicializados en
VentanaPrincipal.__init__.
"""
from lib.app_core import *  # noqa: F401,F403 - helpers/constantes/imports compartidos con app.py
from lib.app_core import _get_cached_query, invalidate_cache  # nombres "privados" que el wildcard import no trae

class DashboardMixin:
    def actualizar_dashboard(self, año=None):
        """Actualiza las estadísticas del dashboard para el año seleccionado."""
        if año is None:
            año = self.combo_año_dashboard.get()
        
        # Limpiar estadísticas actuales de forma más exhaustiva
        try:
            for widget in self.stats_frame.winfo_children():
                widget.destroy()
            # Forzar actualización del frame
            self.stats_frame.update_idletasks()
        except Exception as e:
            print(f"Error limpiando dashboard: {e}")
        
        # Obtener estadísticas de la base de datos
        stats = self.obtener_estadisticas_expedientes(año)
        
        # Obtener artículos problemáticos
        periodo = self.combo_periodo.get()
        articulos_problematicos = self.obtener_articulos_problematicos(año, periodo)
        
        # Crear interfaz de estadísticas
        self.crear_interfaz_estadisticas(stats, articulos_problematicos)

    def obtener_estadisticas_expedientes(self, año):
        """Obtiene las estadísticas de expedientes para el año especificado."""
        try:
            conn, cursor = self.conectar_db()
            if not conn:
                return {}
            
            # Definir los estados a consultar (incluyendo variaciones posibles)
            estados_mapeados = {
                'Completado': ['Completado', 'Finalizado', 'Cerrado'],
                'Pendiente de Autorización': ['Pendiente de Autorización', 'Pendiente de Autorizacion', 'Pendiente Autorización', 'Pendiente', 'Sin Autorizar'],
                'Recibido': ['Recibido', 'Recepcionado'],
                'En Trámite': ['En Trámite', 'En Tramite', 'En Proceso', 'Procesando'],
                'Autorizado': ['Autorizado', 'Aprobado']
            }
            
            estadisticas = {}
            
            for estado_display, variaciones in estados_mapeados.items():
                count = 0
                for variacion in variaciones:
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM rma_maestro 
                        WHERE estado = ? 
                        AND strftime('%Y', fecha_emision) = ?
                    """, (variacion, año))
                    
                    result = cursor.fetchone()[0]
                    count += int(result) if result is not None else 0
                
                estadisticas[estado_display] = count
            
            # Obtener total del año
            cursor.execute("""
                SELECT COUNT(*) 
                FROM rma_maestro 
                WHERE strftime('%Y', fecha_emision) = ?
            """, (año,))
            
            total_result = cursor.fetchone()[0]
            estadisticas['Total'] = int(total_result) if total_result is not None else 0
            
            conn.close()
            return estadisticas
            
        except Exception as e:
            print(f"Error obteniendo estadísticas: {e}")
            return {}

    def obtener_articulos_problematicos(self, año, periodo):
        """Obtiene los 10 artículos con más problemas según el período especificado."""
        try:
            conn, cursor = self.conectar_db()
            if not conn:
                return []
            
            # Estados problemáticos a considerar (los que realmente aparecerán)
            estados_problematicos = [
                "NO FUNCIONA, ABONAR",
                "NO FUNCIONA ; NO ABONAR",
                "REPOSICION FALLO PRODUCTO", 
                "REPOSICION ; ABONAR",
                "FALLO SOLDADURA ; ABONAR",
                "FALLO SOLDADURA ; NO ABONAR",
                "FALLO MODULO ; ABONAR"
            ]
            
            # Crear placeholders para la consulta SQL
            placeholders = ','.join(['?' for _ in estados_problematicos])
            
            # Determinar condición de fecha según el período
            fecha_condicion = ""
            if periodo == "Trimestral":
                # Trimestre actual basado en el mes actual
                mes_actual = datetime.datetime.now().month
                if mes_actual <= 3:
                    trimestre = 1
                elif mes_actual <= 6:
                    trimestre = 2
                elif mes_actual <= 9:
                    trimestre = 3
                else:
                    trimestre = 4
                
                mes_inicio = (trimestre - 1) * 3 + 1
                mes_fin = trimestre * 3
                fecha_condicion = f"AND strftime('%Y', rm.fecha_emision) = '{año}' AND CAST(strftime('%m', rm.fecha_emision) AS INTEGER) BETWEEN {mes_inicio} AND {mes_fin}"
                
            elif periodo == "Semestral":
                # Primer semestre (1-6) o segundo semestre (7-12) según el mes actual
                mes_actual = datetime.datetime.now().month
                if mes_actual <= 6:
                    semestre = 1
                    fecha_condicion = f"AND strftime('%Y', rm.fecha_emision) = '{año}' AND CAST(strftime('%m', rm.fecha_emision) AS INTEGER) BETWEEN 1 AND 6"
                else:
                    semestre = 2
                    fecha_condicion = f"AND strftime('%Y', rm.fecha_emision) = '{año}' AND CAST(strftime('%m', rm.fecha_emision) AS INTEGER) BETWEEN 7 AND 12"
                    
            else:  # Anual
                fecha_condicion = f"AND strftime('%Y', rm.fecha_emision) = '{año}'"
            
            # Consulta para obtener artículos problemáticos
            query = f"""
                SELECT rd.referencia_articulo, COUNT(*) as problemas
                FROM rma_detalles rd
                JOIN rma_maestro rm ON rd.rma_id = rm.id
                WHERE rd.estado_producto IN ({placeholders})
                {fecha_condicion}
                GROUP BY rd.referencia_articulo
                ORDER BY problemas DESC
                LIMIT 10
            """
            
            cursor.execute(query, estados_problematicos)
            resultados = cursor.fetchall()
            
            # Convertir a lista de diccionarios para facilitar el manejo
            articulos_problematicos = [
                {
                    'referencia_articulo': row[0],
                    'problemas': int(row[1])
                }
                for row in resultados
            ]
            
            conn.close()
            return articulos_problematicos
            
        except Exception as e:
            print(f"Error obteniendo artículos problemáticos: {e}")
            return []

    def actualizar_almacenamiento(self):
        """Actualiza la información de almacenamiento en un thread separado."""
        import threading
        
        # Verificar que el frame existe y es válido
        if not hasattr(self, 'storage_info_frame') or not self.storage_info_frame.winfo_exists():
            logger.warning("storage_info_frame no existe, creándolo...")
            self.storage_info_frame = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
            self.storage_info_frame.pack(fill="x", pady=(4, 0))
        
        # Limpiar frame de storage
        for widget in self.storage_info_frame.winfo_children():
            widget.destroy()
        
        # Mostrar mensaje de carga
        loading_label = ctk.CTkLabel(self.storage_info_frame, 
                                    text="⏳ Consultando almacenamiento...", 
                                    font=ctk.CTkFont(size=9),
                                    text_color="gray")
        loading_label.pack(pady=4)
        
        # Ejecutar en thread separado para no bloquear UI
        def cargar_storage():
            try:
                self.mostrar_uso_almacenamiento()
            except Exception as e:
                logger.error(f"Error actualizando almacenamiento: {e}")
                # Limpiar y mostrar error
                self.master.after(0, lambda: self._mostrar_error_storage())
        
        thread = threading.Thread(target=cargar_storage, daemon=True)
        thread.start()

    def _mostrar_error_storage(self):
        """Muestra mensaje de error en el panel de storage."""
        for widget in self.storage_info_frame.winfo_children():
            widget.destroy()
        error_label = ctk.CTkLabel(self.storage_info_frame, 
                                  text="⚠️ Error al cargar storage", 
                                  font=ctk.CTkFont(size=9),
                                  text_color="orange")
        error_label.pack(pady=2)

    def mostrar_uso_almacenamiento(self):
        """Muestra el uso de almacenamiento de Backblaze B2 y Turso."""
        try:
            from lib.uso_almacenamiento import obtener_todos_los_usos
            
            # Obtener información de almacenamiento (no necesita parámetros ahora)
            usos = obtener_todos_los_usos()
            
            # Actualizar UI desde el thread principal
            self.master.after(0, lambda: self._actualizar_ui_storage(usos))
            
        except Exception as e:
            logger.error(f"Error mostrando uso de almacenamiento: {e}")
            self.master.after(0, lambda: self._mostrar_error_storage())

    def _actualizar_ui_storage(self, usos):
        """Actualiza la UI con la información de storage (debe ejecutarse en thread principal)."""
        try:
            # Limpiar frame
            for widget in self.storage_info_frame.winfo_children():
                widget.destroy()
            
            # Separador
            separador = ctk.CTkLabel(self.storage_info_frame, text="─" * 25, 
                                   font=ctk.CTkFont(size=8),
                                   wraplength=180)
            separador.pack(pady=(4, 4))
            
            # Título
            titulo_storage = ctk.CTkLabel(self.storage_info_frame, 
                                         text="☁️ Almacenamiento", 
                                         font=ctk.CTkFont(size=10, weight="bold"),
                                         wraplength=180)
            titulo_storage.pack(pady=(0, 6))
            
            # Mostrar Backblaze B2
            b2_info = usos.get('backblaze', {})
            if b2_info.get('error'):
                b2_texto = f"Backblaze B2: {b2_info['error']}"
            else:
                usado_mb = b2_info.get('usado_mb', 0)
                total_mb = b2_info.get('total_mb')
                tipo = b2_info.get('tipo_cuenta', 'N/A')
                
                # Mostrar en MB si es < 1GB, en GB si es >= 1GB
                if usado_mb < 1024:
                    usado_texto = f"{usado_mb:.1f}MB"
                else:
                    usado_texto = f"{usado_mb / 1024:.2f}GB"
                
                if total_mb and total_mb > 0:
                    total_gb = total_mb / 1024
                    b2_texto = f"Backblaze B2: {usado_texto} / {total_gb:.0f}GB ({tipo})"
                else:
                    b2_texto = f"Backblaze B2: {usado_texto} / Ilimitado ({tipo})"
            
            lbl_b2 = ctk.CTkLabel(self.storage_info_frame, 
                                 text=b2_texto, 
                                 font=ctk.CTkFont(size=9),
                                 anchor="w",
                                 wraplength=180)
            lbl_b2.pack(fill="x", padx=10, pady=2)
            
            # Mostrar Turso
            turso_info = usos.get('turso', {})
            if turso_info.get('error'):
                # No mostrar Turso si hay error (evitar ruido)
                pass
            else:
                usado_mb = turso_info.get('usado_mb')
                total_mb = turso_info.get('total_mb', 0)
                tipo = turso_info.get('tipo_cuenta', 'N/A')
                
                total_gb = total_mb / 1024
                
                if usado_mb is not None:
                    # Mostrar en MB si es < 1GB, en GB si es >= 1GB
                    if usado_mb < 1024:
                        usado_texto = f"{usado_mb:.1f}MB"
                    else:
                        usado_texto = f"{usado_mb / 1024:.2f}GB"
                    turso_texto = f"Turso: {usado_texto} / {total_gb:.0f}GB ({tipo})"
                else:
                    turso_texto = f"Turso: N/A / {total_gb:.0f}GB ({tipo})"
                
                lbl_turso = ctk.CTkLabel(self.storage_info_frame,
                                        text=turso_texto,
                                        font=ctk.CTkFont(size=9),
                                        anchor="w",
                                        wraplength=180)
                lbl_turso.pack(fill="x", padx=10, pady=2)

            # Mostrar Cloudflare Worker (recepción por QR)
            cf_info = usos.get('cloudflare_worker', {})
            if not cf_info.get('error'):
                peticiones = cf_info.get('peticiones_hoy', 0)
                limite = cf_info.get('limite_diario', 100_000)
                cf_texto = f"CF Worker: {peticiones:,} / {limite:,} peticiones hoy".replace(",", ".")

                lbl_cf = ctk.CTkLabel(self.storage_info_frame,
                                     text=cf_texto,
                                     font=ctk.CTkFont(size=9),
                                     anchor="w",
                                     wraplength=180)
                lbl_cf.pack(fill="x", padx=10, pady=2)

        except Exception as e:
            logger.error(f"Error actualizando UI de storage: {e}")

    def crear_interfaz_estadisticas(self, stats, articulos_problematicos):
        """Crea la interfaz visual para mostrar las estadísticas de forma simple y rápida."""
        # Verificar que el frame exista y esté limpio
        if not hasattr(self, 'stats_frame') or not self.stats_frame.winfo_exists():
            return
            
        # Doble verificación: limpiar cualquier widget remanente
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        
        # Título del año
        año_label = ctk.CTkLabel(self.stats_frame, 
                                text=f"Expedientes {self.combo_año_dashboard.get()}", 
                                font=ctk.CTkFont(size=12, weight="bold"),
                                wraplength=180)
        año_label.pack(pady=(8, 12))
        
        # Lista simple de estadísticas sin colores complejos
        estadisticas_texto = [
            f"📋 Total: {stats.get('Total', 0)}",
            f"✅ Completado: {stats.get('Completado', 0)}",
            f"⏳ Pend. Autor.: {stats.get('Pendiente de Autorización', 0)}",
            f"📥 Recibido: {stats.get('Recibido', 0)}",
            f"🔄 En Trámite: {stats.get('En Trámite', 0)}",
            f"✔️ Autorizado: {stats.get('Autorizado', 0)}"
        ]
        
        # Mostrar cada estadística en una fila simple
        for texto in estadisticas_texto:
            fila_label = ctk.CTkLabel(self.stats_frame, 
                                    text=texto, 
                                    font=ctk.CTkFont(size=10),
                                    anchor="w",
                                    wraplength=180)
            fila_label.pack(fill="x", padx=10, pady=1)
        
        # Botones de actualización
        botones_frame = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        botones_frame.pack(pady=(10, 8))
        
        btn_actualizar = ctk.CTkButton(botones_frame, 
                                     text="🔄 Stats",
                                     command=self.actualizar_dashboard,
                                     width=70, height=25,
                                     font=ctk.CTkFont(size=9))
        btn_actualizar.pack(side="left", padx=2)
        
        btn_storage = ctk.CTkButton(botones_frame, 
                                   text="☁️ Storage",
                                   command=self.actualizar_almacenamiento,
                                   width=70, height=25,
                                   font=ctk.CTkFont(size=9))
        btn_storage.pack(side="left", padx=2)
        
        # Frame para información de almacenamiento (inicialmente vacío)
        if not hasattr(self, 'storage_info_frame'):
            self.storage_info_frame = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
            self.storage_info_frame.pack(fill="x", pady=(4, 0))
