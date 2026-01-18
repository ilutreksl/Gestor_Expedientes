"""
Ventana de detalle de proveedores RMP con pestañas.
Organiza la información en: General, Contabilidad, Adjuntos, Historial y Tareas.
"""

import customtkinter as ctk
from tkinter import messagebox
import logging
import os
import pandas as pd
import sys

# Importar Tooltip desde app.py
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import Tooltip

logger = logging.getLogger("GestorExpedientes")


class VentanaDetalleProveedor(ctk.CTkToplevel):
    """Ventana detallada de proveedor con pestañas organizadas."""
    
    def __init__(self, parent, proveedor_nombre, estado_actual='', factura_actual='', 
                 connect_db_func=None, cargar_proveedores_func=None):
        super().__init__(parent)
        
        self.parent_app = parent
        self.proveedor_nombre = proveedor_nombre
        self.estado_actual = estado_actual
        self.factura_actual = factura_actual
        self.connect_db = connect_db_func
        self.cargar_proveedores = cargar_proveedores_func
        self.username = getattr(parent, 'username', 'unknown')
        
        # Configurar ventana
        self.title(f"Detalle RMP - {proveedor_nombre}")
        self.geometry("1200x900")
        self.resizable(True, True)
        self.attributes('-topmost', False)
        self.minsize(900, 600)
        self.focus_set()
        
        # Forzar aparición al frente
        self.attributes('-topmost', True)
        self.lift()
        try:
            self.focus_force()
        except:
            pass
        
        self.after(500, self._quitar_topmost)
        
        # Crear interfaz
        self._crear_interfaz()
        
        logger.info(f"Ventana de detalle abierta para proveedor: {proveedor_nombre}")
    
    def _quitar_topmost(self):
        """Quita el atributo topmost después de aparecer."""
        try:
            if self.winfo_exists():
                self.attributes('-topmost', False)
        except:
            pass
    
    def _crear_interfaz(self):
        """Crea la interfaz principal con encabezado y pestañas."""
        cont = ctk.CTkFrame(self)
        cont.pack(fill="both", expand=True, padx=12, pady=12)
        
        # ===== ENCABEZADO =====
        self._crear_encabezado(cont)
        
        # ===== PESTAÑAS =====
        self.tabview = ctk.CTkTabview(cont)
        self.tabview.pack(fill="both", expand=True, pady=(10,0))
        
        # Crear pestañas
        self.tabview.add("General")
        self.tabview.add("Contabilidad")
        self.tabview.add("Adjuntos")
        self.tabview.add("Historial")
        self.tabview.add("Tareas")
        
        # Llenar contenido de cada pestaña
        self._crear_pestaña_general()
        self._crear_pestaña_contabilidad()
        self._crear_pestaña_adjuntos()
        self._crear_pestaña_historial()
        self._crear_pestaña_tareas()
    
    def _crear_encabezado(self, parent):
        """Crea el encabezado con información del proveedor y estado."""
        header_frame = ctk.CTkFrame(parent, fg_color="#4A90E2", corner_radius=8)
        header_frame.pack(fill="x", pady=(0,10))
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(header_frame, text="RMP", 
                    font=ctk.CTkFont(size=11, weight="bold"), 
                    text_color="white").grid(row=0, column=0, padx=15, pady=(8,2), sticky="w")
        ctk.CTkLabel(header_frame, text=self.proveedor_nombre, 
                    font=ctk.CTkFont(size=14), 
                    text_color="white").grid(row=1, column=0, padx=15, pady=(0,8), sticky="w")
        
        ctk.CTkLabel(header_frame, text="ESTADO", 
                    font=ctk.CTkFont(size=11, weight="bold"), 
                    text_color="white").grid(row=0, column=1, padx=15, pady=(8,2), sticky="w")
        
        # Variable para rastrear el estado actual
        self.estado_var = {'actual': self.estado_actual or ''}
        
        # CTkOptionMenu para editar el estado
        opciones_estado = ["", "En Progreso", "Enviado", "Completado", "Exportado"]
        self.estado_menu = ctk.CTkOptionMenu(
            header_frame,
            values=opciones_estado,
            fg_color="white",
            button_color="#4A90E2",
            button_hover_color="#357ABD",
            text_color="#212529",
            dropdown_fg_color="white",
            dropdown_text_color="#212529",
            command=self._actualizar_estado
        )
        self.estado_menu.set(self.estado_actual if self.estado_actual in opciones_estado else "")
        self.estado_menu.grid(row=1, column=1, padx=15, pady=(0,8), sticky="ew")
    
    def _actualizar_estado(self, nuevo_estado):
        """Actualiza el estado del proveedor."""
        estado_anterior = self.estado_var['actual']
        if estado_anterior == nuevo_estado:
            return
        
        try:
            conn = self.connect_db()
            cur = conn.cursor()
            
            # Actualizar estado en la tabla
            try:
                cur.execute(
                    "INSERT INTO rma_proveedor (proveedor, estado, factura_abono) VALUES (?, ?, ?) ON CONFLICT(proveedor) DO UPDATE SET estado=excluded.estado",
                    (self.proveedor_nombre, nuevo_estado, self.factura_actual or '')
                )
            except Exception:
                cur.execute("UPDATE rma_proveedor SET estado = ? WHERE proveedor = ?", (nuevo_estado, self.proveedor_nombre))
                if getattr(cur, 'rowcount', 0) == 0:
                    cur.execute("INSERT INTO rma_proveedor (proveedor, estado, factura_abono) VALUES (?, ?, ?)", 
                               (self.proveedor_nombre, nuevo_estado, self.factura_actual or ''))
            
            # Añadir al historial
            if estado_anterior == '' or estado_anterior is None:
                comentario_text = f"Estado establecido a: {nuevo_estado}"
            else:
                comentario_text = f"Cambio de estado de '{estado_anterior}' a '{nuevo_estado}'"
            
            cur.execute(
                "INSERT INTO rma_proveedor_hist (proveedor, estado, comentario, usuario) VALUES (?, ?, ?, ?)",
                (self.proveedor_nombre, nuevo_estado, comentario_text, self.username)
            )
            
            conn.commit()
            conn.close()
            
            self.estado_var['actual'] = nuevo_estado
            
            # Refrescar historial
            self._cargar_historial()
            
            # Refrescar lista principal
            if self.cargar_proveedores:
                try:
                    self.cargar_proveedores()
                except Exception:
                    pass
            
            messagebox.showinfo("Actualizado", "Estado actualizado correctamente.")
            logger.info(f"Estado de proveedor {self.proveedor_nombre} actualizado a '{nuevo_estado}'")
            
        except Exception as e:
            logger.error(f"Error actualizando estado de proveedor {self.proveedor_nombre}: {e}", exc_info=True)
            messagebox.showerror("Error", f"No se pudo actualizar el estado: {e}")
    
    def _crear_pestaña_general(self):
        """Crea la pestaña General con el listado de expedientes."""
        tab = self.tabview.tab("General")
        
        # Botón exportar
        btn_frame = ctk.CTkFrame(tab)
        btn_frame.pack(fill="x", padx=5, pady=(5,10))
        btn_exportar = ctk.CTkButton(btn_frame, text="📊 Exportar a Excel", 
                     command=self._exportar_a_excel, width=150)
        btn_exportar.pack(side="right")
        Tooltip(btn_exportar, "Exporta todos los expedientes del proveedor a un archivo Excel")
        
        # Lista de expedientes
        sf_exp = ctk.CTkScrollableFrame(tab)
        sf_exp.pack(fill="both", expand=True, padx=5, pady=(0,5))
        
        # Encabezado
        head = ctk.CTkFrame(sf_exp)
        head.pack(fill="x", padx=5, pady=(0,5))
        head.grid_columnconfigure(0, weight=1, minsize=150)
        head.grid_columnconfigure(1, weight=2, minsize=250)
        head.grid_columnconfigure(2, weight=1, minsize=120)
        head.grid_columnconfigure(3, weight=1, minsize=120)
        head.grid_columnconfigure(4, weight=0, minsize=80)
        
        hf = ctk.CTkFont(weight="bold")
        ctk.CTkLabel(head, text="CÓDIGO", font=hf).grid(row=0, column=0, padx=5, sticky="w")
        ctk.CTkLabel(head, text="CLIENTE", font=hf).grid(row=0, column=1, padx=5, sticky="w")
        ctk.CTkLabel(head, text="FECHA", font=hf).grid(row=0, column=2, padx=5, sticky="w")
        ctk.CTkLabel(head, text="ESTADO", font=hf).grid(row=0, column=3, padx=5, sticky="w")
        ctk.CTkLabel(head, text="", font=hf).grid(row=0, column=4, padx=5)
        
        # Cargar expedientes
        self._cargar_expedientes(sf_exp)
    
    def _cargar_expedientes(self, parent_frame):
        """Carga y muestra los expedientes del proveedor."""
        try:
            conn = self.connect_db()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, codigo_rma, cliente, numero_documento_cliente, modelo, ref_proveedor, fecha_emision, estado "
                "FROM rma_maestro WHERE lower(Rma_Proveedor)=? OR Rma_Proveedor=? ORDER BY fecha_emision DESC",
                (self.proveedor_nombre.lower(), self.proveedor_nombre)
            )
            self.filas_expedientes = cur.fetchall()
            conn.close()
            
            logger.debug(f"Cargados {len(self.filas_expedientes)} expedientes para proveedor {self.proveedor_nombre}")
            
        except Exception as e:
            logger.error(f"Error cargando expedientes de proveedor {self.proveedor_nombre}: {e}", exc_info=True)
            messagebox.showerror("Error BD", f"No se pudieron cargar expedientes: {e}")
            self.filas_expedientes = []
        
        # Mostrar expedientes
        for idx, r in enumerate(self.filas_expedientes):
            try:
                rma_id, codigo, cliente, num_doc, modelo, ref_prov, fecha, estado = r
            except Exception:
                vals = list(r)
                rma_id = vals[0] if len(vals) > 0 else None
                codigo = vals[1] if len(vals) > 1 else ''
                cliente = vals[2] if len(vals) > 2 else ''
                fecha = vals[6] if len(vals) > 6 else ''
                estado = vals[7] if len(vals) > 7 else ''
            
            row = ctk.CTkFrame(parent_frame, fg_color="transparent")
            row.pack(fill="x", padx=5, pady=2)
            row.grid_columnconfigure(0, weight=1, minsize=150)
            row.grid_columnconfigure(1, weight=2, minsize=250)
            row.grid_columnconfigure(2, weight=1, minsize=120)
            row.grid_columnconfigure(3, weight=1, minsize=120)
            row.grid_columnconfigure(4, weight=0, minsize=80)
            
            lbl_codigo = ctk.CTkLabel(row, text=codigo, anchor="w", cursor="hand2")
            lbl_codigo.grid(row=0, column=0, padx=5, sticky="w")
            lbl_cliente = ctk.CTkLabel(row, text=cliente if cliente else "-", anchor="w")
            lbl_cliente.grid(row=0, column=1, padx=5, sticky="w")
            lbl_fecha = ctk.CTkLabel(row, text=fecha if fecha else "-", anchor="w")
            lbl_fecha.grid(row=0, column=2, padx=5, sticky="w")
            lbl_estado = ctk.CTkLabel(row, text=estado if estado else "-", anchor="w")
            lbl_estado.grid(row=0, column=3, padx=5, sticky="w")
            
            ctk.CTkButton(row, text="Editar", width=70, 
                         command=lambda rid=rma_id: self.parent_app._abrir_editor_rma(rma_id=rid)).grid(row=0, column=4, padx=5)
            
            # Doble clic abre editor
            row.bind("<Double-Button-1>", lambda e, rid=rma_id: self.parent_app._abrir_editor_rma(rma_id=rid))
            lbl_codigo.bind("<Double-Button-1>", lambda e, rid=rma_id: self.parent_app._abrir_editor_rma(rma_id=rid))
    
    def _exportar_a_excel(self):
        """Exporta los expedientes a Excel."""
        try:
            if not self.filas_expedientes:
                messagebox.showinfo('Exportar', 'No hay expedientes para exportar.')
                return
            
            data = []
            for r in self.filas_expedientes:
                (_id, codigo_rma, cliente, num_doc, modelo, ref_prov, fecha_emision, estado) = r
                data.append({
                    'Nº Expediente': codigo_rma,
                    'Proveedor': self.proveedor_nombre,
                    'Cliente': cliente or '',
                    'Numero Documento Cliente': num_doc or '',
                    'Descripcion Articulo': modelo or '',
                    'Referencia': ref_prov or ''
                })
            
            df = pd.DataFrame(data)
            base_dir = os.path.join(os.path.dirname(__file__), '..', 'Adjuntos_RMA')
            rmp_dir = os.path.join(base_dir, 'RMP')
            os.makedirs(rmp_dir, exist_ok=True)
            
            safe_name = ''.join(c for c in self.proveedor_nombre if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_name = safe_name.replace(' ', '_')
            file_path = os.path.join(rmp_dir, f"{safe_name}.xlsx")
            
            if os.path.exists(file_path):
                if not messagebox.askyesno('Exportar', f'El archivo {os.path.basename(file_path)} ya existe. ¿Desea sobreescribirlo?'):
                    return
            
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Expedientes')
                workbook = writer.book
                worksheet = writer.sheets['Expedientes']
                from openpyxl.utils import get_column_letter
                for i, col in enumerate(df.columns):
                    if df.empty:
                        max_len = len(str(col))
                    else:
                        col_max = df[col].astype(str).map(len).max()
                        max_len = max(int(col_max) if col_max is not None else 0, len(str(col)))
                    adjusted_width = min(max_len + 2, 60)
                    worksheet.column_dimensions[get_column_letter(i+1)].width = adjusted_width
            
            messagebox.showinfo('Exportar', f'Exportado correctamente: {file_path}')
            logger.info(f"Expedientes de proveedor {self.proveedor_nombre} exportados a {file_path}")
            
            # Subir a Dropbox si está habilitado
            self._subir_excel_dropbox(file_path, safe_name)
            
            # Añadir a historial
            self._registrar_exportacion(len(self.filas_expedientes), file_path)
            
        except Exception as e:
            logger.error(f"Error exportando expedientes de proveedor {self.proveedor_nombre}: {e}", exc_info=True)
            messagebox.showerror('Exportar', f'Error exportando a Excel: {e}')
    
    def _subir_excel_dropbox(self, file_path, safe_name):
        """Sube el archivo Excel a Dropbox si está configurado."""
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            from app import usar_dropbox, get_dropbox_client
            if usar_dropbox():
                import dropbox
                dropbox_path = f"/RMP/{safe_name}.xlsx"
                dbx = get_dropbox_client()
                with open(file_path, 'rb') as f:
                    dbx.files_upload(
                        f.read(),
                        dropbox_path,
                        mode=dropbox.files.WriteMode('overwrite')
                    )
                logger.info(f"Excel RMP subido a Dropbox: {dropbox_path}")
        except Exception as e:
            logger.warning(f"Error subiendo Excel RMP a Dropbox: {e}")
    
    def _registrar_exportacion(self, count, file_path):
        """Registra la exportación en el historial del proveedor."""
        try:
            conn = self.connect_db()
            cur = conn.cursor()
            
            rma_codes = [str(r[1]) for r in self.filas_expedientes if len(r) > 1 and r[1] is not None]
            codes_str = ', '.join(rma_codes)
            if len(codes_str) > 500:
                codes_str = codes_str[:500] + '...'
            
            comentario = f'Exportado {count} expedientes a Excel: {os.path.basename(file_path)}'
            if codes_str:
                comentario += f' (RMAs: {codes_str})'
            
            cur.execute(
                "INSERT INTO rma_proveedor_hist (proveedor, estado, comentario, usuario) VALUES (?, ?, ?, ?)",
                (self.proveedor_nombre, 'Exportado', comentario, self.username)
            )
            
            try:
                cur.execute(
                    "INSERT INTO rma_proveedor (proveedor, estado, factura_abono) VALUES (?, ?, ?) ON CONFLICT(proveedor) DO UPDATE SET estado=excluded.estado",
                    (self.proveedor_nombre, 'Exportado', self.factura_actual or '')
                )
            except Exception:
                cur.execute("UPDATE rma_proveedor SET estado = ? WHERE proveedor = ?", ('Exportado', self.proveedor_nombre))
                if getattr(cur, 'rowcount', 0) == 0:
                    cur.execute("INSERT INTO rma_proveedor (proveedor, estado, factura_abono) VALUES (?, ?, ?)", 
                               (self.proveedor_nombre, 'Exportado', self.factura_actual or ''))
            
            conn.commit()
            conn.close()
            
            self._cargar_historial()
            if self.cargar_proveedores:
                self.cargar_proveedores()
                
        except Exception as e:
            logger.warning(f'Error registrando exportación en historial: {e}')
    
    def _crear_pestaña_contabilidad(self):
        """Crea la pestaña de Contabilidad con el campo de factura."""
        tab = self.tabview.tab("Contabilidad")
        
        frame = ctk.CTkFrame(tab)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text="Factura de Abono", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(10,5))
        
        self.factura_entry = ctk.CTkEntry(frame, placeholder_text="Ej: FA2025001", width=300)
        self.factura_entry.insert(0, self.factura_actual or "")
        self.factura_entry.pack(anchor="w", pady=(0,10))
        
        btn_guardar_factura = ctk.CTkButton(frame, text="💾 Guardar Factura", 
                     command=self._guardar_factura, width=180)
        btn_guardar_factura.pack(anchor="w", pady=10)
        Tooltip(btn_guardar_factura, "Guarda el número de factura de abono del proveedor")
    
    def _guardar_factura(self):
        """Guarda la factura de abono del proveedor."""
        nueva_factura = self.factura_entry.get().strip()
        try:
            conn = self.connect_db()
            cur = conn.cursor()
            
            try:
                cur.execute(
                    "INSERT INTO rma_proveedor (proveedor, estado, factura_abono) VALUES (?, ?, ?) ON CONFLICT(proveedor) DO UPDATE SET factura_abono=excluded.factura_abono",
                    (self.proveedor_nombre, self.estado_var['actual'], nueva_factura)
                )
            except Exception:
                cur.execute("UPDATE rma_proveedor SET factura_abono = ? WHERE proveedor = ?", 
                           (nueva_factura, self.proveedor_nombre))
                if getattr(cur, 'rowcount', 0) == 0:
                    cur.execute("INSERT INTO rma_proveedor (proveedor, estado, factura_abono) VALUES (?, ?, ?)", 
                               (self.proveedor_nombre, self.estado_var['actual'], nueva_factura))
            
            conn.commit()
            conn.close()
            
            self.factura_actual = nueva_factura
            messagebox.showinfo("Guardado", "Factura de abono actualizada correctamente.")
            logger.info(f"Factura de proveedor {self.proveedor_nombre} actualizada: {nueva_factura}")
            
            if self.cargar_proveedores:
                try:
                    self.cargar_proveedores()
                except Exception:
                    pass
                    
        except Exception as e:
            logger.error(f"Error guardando factura de proveedor {self.proveedor_nombre}: {e}", exc_info=True)
            messagebox.showerror("Error", f"No se pudo guardar la factura: {e}")
    
    def _crear_pestaña_adjuntos(self):
        """Crea la pestaña de Adjuntos con gestión de archivos en Dropbox."""
        tab = self.tabview.tab("Adjuntos")
        
        # Importar funciones de adjuntos
        from lib.proveedor_adjuntos import (
            listar_adjuntos_proveedor, descargar_adjunto_proveedor,
            eliminar_adjunto_proveedor, visualizar_adjunto_proveedor,
            subir_adjunto_proveedor, formatear_tamaño
        )
        # Importar funciones de Dropbox desde el módulo principal
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from app import usar_dropbox, get_dropbox_client
        
        self.adjuntos_funcs = {
            'listar': listar_adjuntos_proveedor,
            'descargar': descargar_adjunto_proveedor,
            'eliminar': eliminar_adjunto_proveedor,
            'visualizar': visualizar_adjunto_proveedor,
            'subir': subir_adjunto_proveedor,
            'formatear': formatear_tamaño,
            'get_client': get_dropbox_client,
            'usar': usar_dropbox
        }
        
        # Botón subir
        btn_frame = ctk.CTkFrame(tab)
        btn_frame.pack(fill="x", padx=5, pady=(5,10))
        btn_subir = ctk.CTkButton(btn_frame, text="📤 Subir Archivo", 
                     command=self._subir_adjunto, width=150)
        btn_subir.pack(side="right")
        Tooltip(btn_subir, "Sube un nuevo archivo a Dropbox para este proveedor")
        
        btn_actualizar = ctk.CTkButton(btn_frame, text="🔄 Actualizar", 
                     command=self._cargar_adjuntos, width=120)
        btn_actualizar.pack(side="right", padx=(0,10))
        Tooltip(btn_actualizar, "Recarga la lista de archivos desde Dropbox")
        
        # Lista de adjuntos
        self.sf_adjuntos = ctk.CTkScrollableFrame(tab)
        self.sf_adjuntos.pack(fill="both", expand=True, padx=5, pady=(0,5))
        
        # Cargar adjuntos
        self._cargar_adjuntos()
    
    def _cargar_adjuntos(self):
        """Carga y muestra los adjuntos del proveedor."""
        # Limpiar lista actual
        for w in self.sf_adjuntos.winfo_children():
            w.destroy()
        
        try:
            # Listar adjuntos
            adjuntos = self.adjuntos_funcs['listar'](
                self.proveedor_nombre,
                self.adjuntos_funcs['get_client'],
                self.adjuntos_funcs['usar']
            )
            
            if not adjuntos:
                ctk.CTkLabel(self.sf_adjuntos, text="No hay adjuntos en Dropbox para este proveedor.", 
                           text_color="gray").pack(anchor="w", padx=10, pady=20)
                return
            
            # Encabezado
            head = ctk.CTkFrame(self.sf_adjuntos)
            head.pack(fill="x", padx=5, pady=(0,5))
            head.grid_columnconfigure(0, weight=3, minsize=300)
            head.grid_columnconfigure(1, weight=1, minsize=100)
            head.grid_columnconfigure(2, weight=1, minsize=150)
            head.grid_columnconfigure(3, weight=0, minsize=250)
            
            hf = ctk.CTkFont(weight="bold")
            ctk.CTkLabel(head, text="ARCHIVO", font=hf).grid(row=0, column=0, padx=5, sticky="w")
            ctk.CTkLabel(head, text="TAMAÑO", font=hf).grid(row=0, column=1, padx=5, sticky="w")
            ctk.CTkLabel(head, text="MODIFICADO", font=hf).grid(row=0, column=2, padx=5, sticky="w")
            ctk.CTkLabel(head, text="ACCIONES", font=hf).grid(row=0, column=3, padx=5)
            
            # Mostrar adjuntos
            for adj in adjuntos:
                row = ctk.CTkFrame(self.sf_adjuntos, fg_color="transparent")
                row.pack(fill="x", padx=5, pady=2)
                row.grid_columnconfigure(0, weight=3, minsize=300)
                row.grid_columnconfigure(1, weight=1, minsize=100)
                row.grid_columnconfigure(2, weight=1, minsize=150)
                row.grid_columnconfigure(3, weight=0, minsize=250)
                
                ctk.CTkLabel(row, text=adj['nombre'], anchor="w").grid(row=0, column=0, padx=5, sticky="w")
                ctk.CTkLabel(row, text=self.adjuntos_funcs['formatear'](adj['tamaño']), 
                           anchor="w").grid(row=0, column=1, padx=5, sticky="w")
                fecha_mod = str(adj['modificado'])[:10] if adj['modificado'] else "-"
                ctk.CTkLabel(row, text=fecha_mod, anchor="w").grid(row=0, column=2, padx=5, sticky="w")
                
                # Botones de acción
                btn_container = ctk.CTkFrame(row, fg_color="transparent")
                btn_container.grid(row=0, column=3, padx=5)
                
                btn_ver = ctk.CTkButton(btn_container, text="👁️", width=40, 
                             command=lambda p=adj['path']: self._visualizar_adjunto(p))
                btn_ver.pack(side="left", padx=2)
                Tooltip(btn_ver, "Visualizar archivo")
                
                btn_descargar = ctk.CTkButton(btn_container, text="⬇️", width=40, 
                             command=lambda p=adj['path']: self._descargar_adjunto(p))
                btn_descargar.pack(side="left", padx=2)
                Tooltip(btn_descargar, "Descargar archivo")
                
                btn_eliminar = ctk.CTkButton(btn_container, text="🗑️", width=40, fg_color="red",
                             command=lambda p=adj['path'], n=adj['nombre']: self._eliminar_adjunto(p, n))
                btn_eliminar.pack(side="left", padx=2)
                Tooltip(btn_eliminar, "Eliminar archivo")
            
            logger.debug(f"Cargados {len(adjuntos)} adjuntos para proveedor {self.proveedor_nombre}")
            
        except Exception as e:
            logger.error(f"Error cargando adjuntos de proveedor {self.proveedor_nombre}: {e}", exc_info=True)
            ctk.CTkLabel(self.sf_adjuntos, text=f"Error cargando adjuntos: {e}", 
                       text_color="red").pack(anchor="w", padx=10, pady=10)
    
    def _subir_adjunto(self):
        """Sube un nuevo adjunto."""
        exito, mensaje = self.adjuntos_funcs['subir'](
            self.proveedor_nombre,
            self.adjuntos_funcs['get_client'],
            self.adjuntos_funcs['usar']
        )
        
        if exito:
            messagebox.showinfo("Éxito", mensaje)
            self._cargar_adjuntos()
        elif "cancelada" not in mensaje.lower():
            messagebox.showerror("Error", mensaje)
    
    def _descargar_adjunto(self, dropbox_path):
        """Descarga un adjunto."""
        exito, mensaje = self.adjuntos_funcs['descargar'](
            dropbox_path,
            self.adjuntos_funcs['get_client'],
            self.adjuntos_funcs['usar']
        )
        
        if exito:
            messagebox.showinfo("Descargado", f"Archivo guardado en:\n{mensaje}")
        elif "cancelada" not in mensaje.lower():
            messagebox.showerror("Error", mensaje)
    
    def _visualizar_adjunto(self, dropbox_path):
        """Visualiza un adjunto."""
        exito, mensaje = self.adjuntos_funcs['visualizar'](
            dropbox_path,
            self.adjuntos_funcs['get_client'],
            self.adjuntos_funcs['usar']
        )
        
        if not exito:
            messagebox.showerror("Error", mensaje)
    
    def _eliminar_adjunto(self, dropbox_path, nombre):
        """Elimina un adjunto."""
        if not messagebox.askyesno("Confirmar", f"¿Eliminar el archivo '{nombre}'?\n\nEsta acción no se puede deshacer."):
            return
        
        exito, mensaje = self.adjuntos_funcs['eliminar'](
            dropbox_path,
            self.adjuntos_funcs['get_client'],
            self.adjuntos_funcs['usar']
        )
        
        if exito:
            messagebox.showinfo("Eliminado", mensaje)
            self._cargar_adjuntos()
        else:
            messagebox.showerror("Error", mensaje)
    
    def _crear_pestaña_historial(self):
        """Crea la pestaña de Historial."""
        tab = self.tabview.tab("Historial")
        
        # Lista de historial
        self.sf_hist = ctk.CTkScrollableFrame(tab, height=400)
        self.sf_hist.pack(fill="both", expand=True, padx=5, pady=(5,10))
        
        # Sección para añadir comentario
        comment_frame = ctk.CTkFrame(tab)
        comment_frame.pack(fill="x", padx=5, pady=(0,5))
        
        ctk.CTkLabel(comment_frame, text="Añadir comentario al historial:", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=5, pady=(5,3))
        self.comment_box = ctk.CTkTextbox(comment_frame, height=60)
        self.comment_box.pack(fill="x", padx=5, pady=(0,5))
        
        btn_comentario = ctk.CTkButton(comment_frame, text="💬 Añadir Comentario", 
                     command=self._añadir_comentario, width=180)
        btn_comentario.pack(anchor="e", padx=5, pady=(0,5))
        Tooltip(btn_comentario, "Añade un comentario o nota al historial del proveedor")
        
        # Cargar historial
        self._cargar_historial()
    
    def _cargar_historial(self):
        """Carga y muestra el historial del proveedor."""
        for w in self.sf_hist.winfo_children():
            w.destroy()
        
        try:
            conn = self.connect_db()
            cur = conn.cursor()
            cur.execute(
                "SELECT fecha, usuario, estado, comentario FROM rma_proveedor_hist WHERE lower(proveedor)=? OR proveedor=? ORDER BY fecha DESC",
                (self.proveedor_nombre.lower(), self.proveedor_nombre)
            )
            hist_rows = cur.fetchall()
            conn.close()
            
            if not hist_rows:
                ctk.CTkLabel(self.sf_hist, text="No hay historial registrado.", 
                           text_color="gray").pack(anchor="w", padx=5, pady=10)
            else:
                for idx, (fecha, usuario, estado_h, comentario) in enumerate(hist_rows):
                    rowf = ctk.CTkFrame(self.sf_hist, fg_color="transparent", corner_radius=6)
                    rowf.pack(fill="x", padx=3, pady=3)
                    txt = f"📅 {fecha} | 👤 {usuario}"
                    if estado_h:
                        txt += f" | 🏷️ {estado_h}"
                    ctk.CTkLabel(rowf, text=txt, font=ctk.CTkFont(weight="bold", size=11)).pack(anchor="w", padx=8, pady=(6,2))
                    if comentario:
                        ctk.CTkLabel(rowf, text=comentario, wraplength=1100, anchor="w").pack(anchor="w", padx=8, pady=(0,6))
            
            logger.debug(f"Cargado historial de proveedor {self.proveedor_nombre}: {len(hist_rows)} entradas")
            
        except Exception as e:
            logger.error(f"Error cargando historial de proveedor {self.proveedor_nombre}: {e}", exc_info=True)
            ctk.CTkLabel(self.sf_hist, text=f"Error cargando historial: {e}", 
                       text_color="red").pack(anchor="w", padx=5, pady=10)
    
    def _añadir_comentario(self):
        """Añade un comentario al historial."""
        text = self.comment_box.get("0.0", "end").strip()
        if not text:
            messagebox.showwarning("Vacío", "Escribe un comentario antes de añadirlo.")
            return
        
        try:
            conn = self.connect_db()
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS rma_proveedor_hist (id INTEGER PRIMARY KEY, proveedor TEXT, estado TEXT, comentario TEXT, usuario TEXT, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            cur.execute("INSERT INTO rma_proveedor_hist (proveedor, estado, comentario, usuario) VALUES (?, ?, ?, ?)", 
                       (self.proveedor_nombre, '', text, self.username))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Añadido", "Comentario añadido al historial.")
            self.comment_box.delete("0.0", "end")
            self._cargar_historial()
            
            logger.info(f"Comentario añadido al historial de proveedor {self.proveedor_nombre} por {self.username}")
            
            if self.cargar_proveedores:
                self.cargar_proveedores()
                
        except Exception as e:
            logger.error(f"Error añadiendo comentario a proveedor {self.proveedor_nombre}: {e}", exc_info=True)
            messagebox.showerror("Error BD", f"No se pudo añadir el comentario: {e}")
    
    def _crear_pestaña_tareas(self):
        """Crea la pestaña de Tareas similar a expedientes."""
        tab = self.tabview.tab("Tareas")
        
        # Importar funciones de tareas
        from lib.proveedor_tareas import (
            crear_tabla_tareas_proveedor, crear_tarea_proveedor,
            obtener_tareas_proveedor, actualizar_estado_tarea_proveedor,
            eliminar_tarea_proveedor
        )
        
        # Asegurar que existe la tabla
        crear_tabla_tareas_proveedor(self.connect_db)
        
        # Botones de control
        btn_frame = ctk.CTkFrame(tab)
        btn_frame.pack(fill="x", padx=5, pady=(5,10))
        
        btn_nueva_tarea = ctk.CTkButton(btn_frame, text="➕ Nueva Tarea", 
                     command=self._crear_tarea, width=150)
        btn_nueva_tarea.pack(side="left")
        Tooltip(btn_nueva_tarea, "Crea una nueva tarea o recordatorio para este proveedor")
        
        # Filtro de estado
        ctk.CTkLabel(btn_frame, text="Filtrar:").pack(side="left", padx=(20,5))
        self.filtro_tareas = ctk.CTkOptionMenu(btn_frame, values=["Todos", "Pendiente", "En Progreso", "Completado"],
                                                command=lambda x: self._cargar_tareas())
        self.filtro_tareas.set("Todos")
        self.filtro_tareas.pack(side="left")
        
        # Lista de tareas
        self.sf_tareas = ctk.CTkScrollableFrame(tab)
        self.sf_tareas.pack(fill="both", expand=True, padx=5, pady=(0,5))
        
        # Cargar tareas
        self._cargar_tareas()
    
    def _cargar_tareas(self):
        """Carga y muestra las tareas del proveedor."""
        from lib.proveedor_tareas import obtener_tareas_proveedor
        
        # Limpiar lista
        for w in self.sf_tareas.winfo_children():
            w.destroy()
        
        filtro = self.filtro_tareas.get()
        filtro_estado = filtro if filtro != "Todos" else None
        
        tareas = obtener_tareas_proveedor(self.proveedor_nombre, filtro_estado, self.connect_db)
        
        if not tareas:
            ctk.CTkLabel(self.sf_tareas, text="No hay tareas registradas.", 
                       text_color="gray").pack(anchor="w", padx=10, pady=20)
            return
        
        # Encabezado
        head = ctk.CTkFrame(self.sf_tareas)
        head.pack(fill="x", padx=5, pady=(0,5))
        head.grid_columnconfigure(0, weight=2, minsize=200)
        head.grid_columnconfigure(1, weight=3, minsize=300)
        head.grid_columnconfigure(2, weight=1, minsize=100)
        head.grid_columnconfigure(3, weight=1, minsize=120)
        head.grid_columnconfigure(4, weight=0, minsize=150)
        
        hf = ctk.CTkFont(weight="bold")
        ctk.CTkLabel(head, text="TÍTULO", font=hf).grid(row=0, column=0, padx=5, sticky="w")
        ctk.CTkLabel(head, text="DESCRIPCIÓN", font=hf).grid(row=0, column=1, padx=5, sticky="w")
        ctk.CTkLabel(head, text="VENCIMIENTO", font=hf).grid(row=0, column=2, padx=5, sticky="w")
        ctk.CTkLabel(head, text="ESTADO", font=hf).grid(row=0, column=3, padx=5, sticky="w")
        ctk.CTkLabel(head, text="ACCIONES", font=hf).grid(row=0, column=4, padx=5)
        
        # Mostrar tareas
        for tarea in tareas:
            tarea_id, titulo, descripcion, fecha_venc, estado, creado_por, fecha_creacion = tarea
            
            row = ctk.CTkFrame(self.sf_tareas, fg_color="transparent")
            row.pack(fill="x", padx=5, pady=2)
            row.grid_columnconfigure(0, weight=2, minsize=200)
            row.grid_columnconfigure(1, weight=3, minsize=300)
            row.grid_columnconfigure(2, weight=1, minsize=100)
            row.grid_columnconfigure(3, weight=1, minsize=120)
            row.grid_columnconfigure(4, weight=0, minsize=150)
            
            ctk.CTkLabel(row, text=titulo or "-", anchor="w").grid(row=0, column=0, padx=5, sticky="w")
            desc_truncada = (descripcion[:50] + "...") if descripcion and len(descripcion) > 50 else (descripcion or "-")
            ctk.CTkLabel(row, text=desc_truncada, anchor="w").grid(row=0, column=1, padx=5, sticky="w")
            ctk.CTkLabel(row, text=fecha_venc or "-", anchor="w").grid(row=0, column=2, padx=5, sticky="w")
            
            # Estado con color
            color_estado = {"Pendiente": "orange", "En Progreso": "blue", "Completado": "green"}.get(estado, "gray")
            ctk.CTkLabel(row, text=estado, anchor="w", text_color=color_estado).grid(row=0, column=3, padx=5, sticky="w")
            
            # Botones
            btn_container = ctk.CTkFrame(row, fg_color="transparent")
            btn_container.grid(row=0, column=4, padx=5)
            
            # Menú de estado
            estado_opts = ["Pendiente", "En Progreso", "Completado"]
            estado_menu = ctk.CTkOptionMenu(btn_container, values=estado_opts, width=90,
                                           command=lambda s, tid=tarea_id: self._cambiar_estado_tarea(tid, s))
            estado_menu.set(estado)
            estado_menu.pack(side="left", padx=2)
            
            ctk.CTkButton(btn_container, text="🗑️", width=30, fg_color="red",
                         command=lambda tid=tarea_id: self._eliminar_tarea(tid)).pack(side="left", padx=2)
        
        logger.debug(f"Cargadas {len(tareas)} tareas para proveedor {self.proveedor_nombre}")
    
    def _crear_tarea(self):
        """Abre diálogo para crear nueva tarea."""
        from lib.proveedor_tareas import crear_tarea_proveedor
        
        ventana = ctk.CTkToplevel(self)
        ventana.title("Nueva Tarea")
        ventana.geometry("500x400")
        ventana.transient(self)
        ventana.grab_set()
        
        frame = ctk.CTkFrame(ventana)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text="Título *", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10,2))
        entry_titulo = ctk.CTkEntry(frame, placeholder_text="Título de la tarea")
        entry_titulo.pack(fill="x", pady=(0,10))
        
        ctk.CTkLabel(frame, text="Descripción", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10,2))
        text_desc = ctk.CTkTextbox(frame, height=100)
        text_desc.pack(fill="x", pady=(0,10))
        
        ctk.CTkLabel(frame, text="Fecha de Vencimiento (DD/MM/AAAA)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10,2))
        entry_fecha = ctk.CTkEntry(frame, placeholder_text="DD/MM/AAAA")
        entry_fecha.pack(fill="x", pady=(0,10))
        
        def guardar():
            titulo = entry_titulo.get().strip()
            descripcion = text_desc.get("0.0", "end").strip()
            fecha = entry_fecha.get().strip()
            
            if not titulo:
                messagebox.showerror("Error", "El título es obligatorio")
                return
            
            exito, mensaje = crear_tarea_proveedor(
                self.proveedor_nombre, titulo, descripcion, fecha, 
                self.username, self.connect_db
            )
            
            if exito:
                messagebox.showinfo("Éxito", mensaje)
                ventana.destroy()
                self._cargar_tareas()
            else:
                messagebox.showerror("Error", mensaje)
        
        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(fill="x", pady=20)
        
        ctk.CTkButton(btn_frame, text="Cancelar", command=ventana.destroy, width=100).pack(side="right", padx=(10,0))
        ctk.CTkButton(btn_frame, text="Guardar", command=guardar, width=100).pack(side="right")
    
    def _cambiar_estado_tarea(self, tarea_id, nuevo_estado):
        """Cambia el estado de una tarea."""
        from lib.proveedor_tareas import actualizar_estado_tarea_proveedor
        
        exito, mensaje = actualizar_estado_tarea_proveedor(tarea_id, nuevo_estado, self.connect_db)
        
        if exito:
            self._cargar_tareas()
        else:
            messagebox.showerror("Error", mensaje)
    
    def _eliminar_tarea(self, tarea_id):
        """Elimina una tarea."""
        from lib.proveedor_tareas import eliminar_tarea_proveedor
        
        if not messagebox.askyesno("Confirmar", "¿Eliminar esta tarea?\n\nEsta acción no se puede deshacer."):
            return
        
        exito, mensaje = eliminar_tarea_proveedor(tarea_id, self.connect_db)
        
        if exito:
            messagebox.showinfo("Eliminado", mensaje)
            self._cargar_tareas()
        else:
            messagebox.showerror("Error", mensaje)
