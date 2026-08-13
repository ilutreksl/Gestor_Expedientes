"""Mixin extraido automaticamente de VentanaPrincipal (app.py).

Estas clases NO son instanciables por si solas: solo aportan metodos que se
combinan con VentanaPrincipal via herencia multiple. Dependen de atributos de
instancia (self.conn, self.username, self.tree_rmas, etc.) inicializados en
VentanaPrincipal.__init__.
"""
from lib.app_core import *  # noqa: F401,F403 - helpers/constantes/imports compartidos con app.py
from lib.app_core import _get_cached_query, invalidate_cache  # nombres "privados" que el wildcard import no trae

class AdminMixin:
    def mostrar_menu_admin(self):
        """Muestra un menú desplegable con funciones de administración."""
        if str(self.rol).strip().lower() not in ("admin", "administrador"):
            messagebox.showerror("Acceso Denegado", "Solo los administradores tienen acceso a estas funciones.")
            return
            
        # Crear ventana de menú
        menu_window = ctk.CTkToplevel(self)
        menu_window.title("Menú de Administración")
        menu_window.geometry("650x550")
        menu_window.resizable(False, False)
        
        # Centrar la ventana
        menu_window.transient(self)
        menu_window.grab_set()
        
        # Título
        titulo = ctk.CTkLabel(menu_window, text="🔧 Funciones de Administración", 
                             font=ctk.CTkFont(size=16, weight="bold"))
        titulo.pack(pady=20)
        
        # Frame para botones con grid
        buttons_frame = ctk.CTkFrame(menu_window)
        buttons_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        # Configurar columnas del grid (2 columnas)
        buttons_frame.columnconfigure(0, weight=1)
        buttons_frame.columnconfigure(1, weight=1)
        
        # Lista de botones para distribuir en 2 columnas
        botones = [
            ("🗑️ Eliminar RMA", "#dc3545", "#c82333", lambda: [menu_window.destroy(), self.mostrar_eliminar_rma()]),
            ("🔢 Generar Número Manual", None, None, lambda: [menu_window.destroy(), self.mostrar_generar_numero_manual()]),
            ("📢 Administrar Avisos", None, None, lambda: [menu_window.destroy(), self.mostrar_admin_avisos()]),
            ("📋 Gestionar Estados Artículos", None, None, lambda: [menu_window.destroy(), self.mostrar_gestor_estados()]),
            ("👥 Gestionar Personas", None, None, lambda: [menu_window.destroy(), self.mostrar_gestor_personas()]),
            ("👤 Gestionar Personas Recepción", None, None, lambda: [menu_window.destroy(), self.mostrar_gestor_personas_recepcion()]),
            ("📎 Texto de Ayuda - Trazabilidad", None, None, lambda: [menu_window.destroy(), self.mostrar_editor_texto_trazabilidad()]),
            ("📱 Dispositivos QR Recepción", None, None, lambda: [menu_window.destroy(), self.mostrar_gestor_dispositivos_qr()]),
            ("📊 Gestionar Resultado Expediente", None, None, lambda: [menu_window.destroy(), self.mostrar_gestor_resultado_expediente()]),
            ("🏢 Gestionar Tipos de Cliente", None, None, lambda: [menu_window.destroy(), self.mostrar_gestor_tipos_cliente()]),
        ]
        
        # Crear botones en 2 columnas
        for idx, (texto, fg_color, hover_color, comando) in enumerate(botones):
            fila = idx // 2
            columna = idx % 2
            btn = ctk.CTkButton(buttons_frame,
                               text=texto,
                               width=280,
                               height=45,
                               fg_color=fg_color,
                               hover_color=hover_color,
                               command=comando)
            btn.grid(row=fila, column=columna, padx=10, pady=8, sticky="ew")
        
        # Botón Cerrar (ocupa ambas columnas)
        btn_cerrar = ctk.CTkButton(buttons_frame,
                                  text="❌ Cerrar",
                                  width=280,
                                  height=35,
                                  command=menu_window.destroy)
        btn_cerrar.grid(row=(len(botones) // 2) + 1, column=0, columnspan=2, padx=10, pady=(20, 10))

    def mostrar_admin_avisos(self):
        """Muestra el panel de administración de avisos (solo para admin)."""
        if str(self.rol).strip().lower() not in ("admin", "administrador"):
            messagebox.showerror("Acceso Denegado", "Solo los administradores pueden gestionar avisos.")
            return
        
        try:
            self.avisos_manager.mostrar_panel_admin(self)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el panel de avisos:\n{e}")

    def mostrar_gestor_estados(self):
        """Muestra la ventana de gestión de estados de artículos"""
        if str(self.rol).strip().lower() not in ("admin", "administrador"):
            messagebox.showerror("Acceso Denegado", "Solo los administradores pueden gestionar estados.")
            return
        
        try:
            # Crear ventana
            ventana = ctk.CTkToplevel(self)
            ventana.title("Gestionar Estados de Artículos")
            ventana.geometry("700x600")
            ventana.transient(self)
            ventana.grab_set()
            
            # Frame principal
            main_frame = ctk.CTkFrame(ventana)
            main_frame.pack(fill="both", expand=True, padx=15, pady=15)
            
            # Título
            titulo = ctk.CTkLabel(main_frame, text="📋 Gestión de Estados de Artículos",
                                 font=ctk.CTkFont(size=18, weight="bold"))
            titulo.pack(pady=(0, 15))
            
            # Frame de controles
            controles_frame = ctk.CTkFrame(main_frame)
            controles_frame.pack(fill="x", pady=(0, 10))
            
            # Entrada para nuevo estado
            entry_nuevo = ctk.CTkEntry(controles_frame, placeholder_text="Nuevo estado...", width=400)
            entry_nuevo.pack(side="left", padx=(10, 5), pady=10)
            
            # Botón añadir
            btn_anadir = ctk.CTkButton(controles_frame, text="➕ Añadir", width=100)
            btn_anadir.pack(side="left", padx=5, pady=10)
            
            # Lista de estados
            lista_frame = ctk.CTkFrame(main_frame)
            lista_frame.pack(fill="both", expand=True, pady=(0, 10))
            
            # Header
            header_frame = ctk.CTkFrame(lista_frame, fg_color=("gray80", "gray25"), height=35)
            header_frame.pack(fill="x", padx=2, pady=(2, 0))
            header_frame.pack_propagate(False)
            
            ctk.CTkLabel(header_frame, text="Estado", font=ctk.CTkFont(weight="bold"), width=450, anchor="w").pack(side="left", padx=10, pady=5)
            ctk.CTkLabel(header_frame, text="Acciones", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5, pady=5)
            
            # Scrollable frame
            scroll_frame = ctk.CTkScrollableFrame(lista_frame)
            scroll_frame.pack(fill="both", expand=True, padx=2, pady=2)
            
            # Frame de botones inferiores
            botones_frame = ctk.CTkFrame(main_frame)
            botones_frame.pack(fill="x")
            
            btn_recargar = ctk.CTkButton(botones_frame, text="↻ Recargar", width=120)
            btn_recargar.pack(side="left", padx=5, pady=5)
            
            btn_cerrar = ctk.CTkButton(botones_frame, text="Cerrar", width=100, 
                                       command=ventana.destroy)
            btn_cerrar.pack(side="right", padx=5, pady=5)
            
            # Manager
            estados_mgr = EstadosArticuloManager()
            
            # Funciones
            def cargar_estados():
                """Carga y muestra los estados"""
                # Limpiar lista
                for widget in scroll_frame.winfo_children():
                    widget.destroy()
                
                estados = estados_mgr.cargar_estados()
                
                for i, estado in enumerate(estados):
                    fila = ctk.CTkFrame(scroll_frame, fg_color=("gray90", "gray20"))
                    fila.pack(fill="x", padx=2, pady=2)
                    
                    # Estado (vacío se muestra como texto especial)
                    texto_estado = "(Vacío)" if estado == "" else estado
                    lbl_estado = ctk.CTkLabel(fila, text=texto_estado, width=450, anchor="w")
                    lbl_estado.pack(side="left", padx=10, pady=8)
                    
                    # Botones
                    acciones = ctk.CTkFrame(fila, fg_color="transparent")
                    acciones.pack(side="left", padx=5)
                    
                    # Editar
                    btn_editar = ctk.CTkButton(acciones, text="✏", width=30, height=25,
                                               command=lambda e=estado: editar_estado(e))
                    btn_editar.pack(side="left", padx=2)
                    Tooltip(btn_editar, "Editar este estado")
                    
                    # Mover arriba
                    if i > 0:
                        btn_arriba = ctk.CTkButton(acciones, text="▲", width=30, height=25,
                                                   command=lambda e=estado: mover_estado(e, 'arriba'))
                        btn_arriba.pack(side="left", padx=2)
                        Tooltip(btn_arriba, "Mover hacia arriba")
                    
                    # Mover abajo
                    if i < len(estados) - 1:
                        btn_abajo = ctk.CTkButton(acciones, text="▼", width=30, height=25,
                                                  command=lambda e=estado: mover_estado(e, 'abajo'))
                        btn_abajo.pack(side="left", padx=2)
                        Tooltip(btn_abajo, "Mover hacia abajo")
                    
                    # Eliminar
                    btn_eliminar = ctk.CTkButton(acciones, text="🗑", width=30, height=25,
                                                 fg_color="red", hover_color="darkred",
                                                 command=lambda e=estado: eliminar_estado(e))
                    btn_eliminar.pack(side="left", padx=2)
                    Tooltip(btn_eliminar, "Eliminar este estado")
            
            def anadir_estado():
                """Añade un nuevo estado"""
                nuevo = entry_nuevo.get().strip()
                if not nuevo:
                    messagebox.showwarning("Aviso", "Escribe un estado para añadir")
                    return
                
                success, msg = estados_mgr.añadir_estado(nuevo)
                if success:
                    entry_nuevo.delete(0, 'end')
                    cargar_estados()
                    recargar_estados_app()
                    messagebox.showinfo("Éxito", msg)
                else:
                    messagebox.showerror("Error", msg)
            
            def editar_estado(estado_antiguo):
                """Edita un estado existente"""
                # Ventana de edición
                ventana_edit = ctk.CTkToplevel(ventana)
                ventana_edit.title("Editar Estado")
                ventana_edit.geometry("500x150")
                ventana_edit.transient(ventana)
                ventana_edit.grab_set()
                
                ctk.CTkLabel(ventana_edit, text="Nuevo valor:", font=ctk.CTkFont(size=12)).pack(pady=(20, 5))
                
                entry_edit = ctk.CTkEntry(ventana_edit, width=400)
                entry_edit.insert(0, estado_antiguo)
                entry_edit.pack(pady=5)
                
                def guardar_edicion():
                    nuevo_valor = entry_edit.get().strip()
                    if not nuevo_valor:
                        messagebox.showwarning("Aviso", "El estado no puede estar vacío")
                        return
                    
                    success, msg = estados_mgr.editar_estado(estado_antiguo, nuevo_valor)
                    if success:
                        ventana_edit.destroy()
                        cargar_estados()
                        recargar_estados_app()
                        messagebox.showinfo("Éxito", msg)
                    else:
                        messagebox.showerror("Error", msg)
                
                ctk.CTkButton(ventana_edit, text="Guardar", command=guardar_edicion).pack(pady=10)
            
            def eliminar_estado(estado):
                """Elimina un estado"""
                texto_estado = "(Vacío)" if estado == "" else estado
                if not messagebox.askyesno("Confirmar", f"¿Eliminar el estado '{texto_estado}'?"):
                    return
                
                success, msg = estados_mgr.eliminar_estado(estado)
                if success:
                    cargar_estados()
                    recargar_estados_app()
                    messagebox.showinfo("Éxito", msg)
                else:
                    messagebox.showerror("Error", msg)
            
            def mover_estado(estado, direccion):
                """Mueve un estado arriba o abajo"""
                success, msg = estados_mgr.mover_estado(estado, direccion)
                if success:
                    cargar_estados()
                    recargar_estados_app()
                else:
                    messagebox.showinfo("Info", msg)
            
            def recargar_estados_app():
                """Recarga los estados en la aplicación principal"""
                self.OPCIONES["Estado_Producto"] = estados_mgr.cargar_estados()
            
            # Conectar botones
            btn_anadir.configure(command=anadir_estado)
            btn_recargar.configure(command=cargar_estados)
            entry_nuevo.bind("<Return>", lambda e: anadir_estado())
            
            # Cargar estados inicialmente
            cargar_estados()
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el gestor de estados:\n{e}")
            import traceback
            traceback.print_exc()

    def mostrar_gestor_personas(self):
        """
        Abre una ventana para gestionar la lista de personas
        """
        from lib.safe_toplevel import SafeCTkToplevel
        from lib.personas_manager import PersonasManager
        
        try:
            # Crear ventana de gestión
            gestor_window = SafeCTkToplevel(self)
            gestor_window.title("Gestión de Personas")
            gestor_window.geometry("600x500")
            gestor_window.transient(self)
            gestor_window.grab_set()
            
            # Frame principal con padding
            main_frame = ctk.CTkFrame(gestor_window)
            main_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Título
            title_label = ctk.CTkLabel(main_frame,
                                       text="👥 Gestión de Personas",
                                       font=("Arial", 18, "bold"))
            title_label.pack(pady=(0, 20))
            
            # Frame para agregar nueva persona
            add_frame = ctk.CTkFrame(main_frame)
            add_frame.pack(fill="x", pady=(0, 20))
            
            entry_label = ctk.CTkLabel(add_frame,
                                       text="Nueva Persona:",
                                       font=("Arial", 12))
            entry_label.pack(side="left", padx=(10, 5))
            
            entry_persona = ctk.CTkEntry(add_frame,
                                         width=300,
                                         placeholder_text="Ingrese el nombre de la persona")
            entry_persona.pack(side="left", padx=5)
            
            btn_agregar = ctk.CTkButton(add_frame,
                                        text="➕ Agregar",
                                        width=100)
            btn_agregar.pack(side="left", padx=5)
            
            # Frame scrollable para la lista de personas
            list_frame = ctk.CTkScrollableFrame(main_frame,
                                                label_text="Personas Registradas")
            list_frame.pack(fill="both", expand=True)
            
            # Instanciar el gestor
            personas_mgr = PersonasManager()
            
            def cargar_personas():
                """Carga y muestra la lista de personas"""
                # Limpiar lista actual
                for widget in list_frame.winfo_children():
                    widget.destroy()
                
                # Obtener personas
                personas = personas_mgr.cargar_personas()
                
                if not personas:
                    no_data_label = ctk.CTkLabel(list_frame,
                                                 text="No hay personas registradas",
                                                 text_color="gray")
                    no_data_label.pack(pady=20)
                    return
                
                # Mostrar cada persona
                for i, persona in enumerate(personas):
                    persona_frame = ctk.CTkFrame(list_frame)
                    persona_frame.pack(fill="x", pady=5, padx=5)
                    
                    # Nombre de la persona
                    nombre_label = ctk.CTkLabel(persona_frame,
                                               text=persona,
                                               font=("Arial", 12),
                                               anchor="w")
                    nombre_label.pack(side="left", padx=10, fill="x", expand=True)
                    
                    # Botones de acción
                    btn_frame = ctk.CTkFrame(persona_frame, fg_color="transparent")
                    btn_frame.pack(side="right", padx=5)
                    
                    # Botón Editar
                    btn_editar = ctk.CTkButton(btn_frame,
                                              text="✏️",
                                              width=40,
                                              command=lambda p=persona: editar_persona(p))
                    btn_editar.pack(side="left", padx=2)
                    Tooltip(btn_editar, "Editar persona")
                    
                    # Botón Subir
                    if i > 0:  # No mostrar para el primero
                        btn_subir = ctk.CTkButton(btn_frame,
                                                text="⬆️",
                                                width=40,
                                                command=lambda p=persona: mover_persona(p, "arriba"))
                        btn_subir.pack(side="left", padx=2)
                        Tooltip(btn_subir, "Mover arriba")
                    
                    # Botón Bajar
                    if i < len(personas) - 1:  # No mostrar para el último
                        btn_bajar = ctk.CTkButton(btn_frame,
                                                text="⬇️",
                                                width=40,
                                                command=lambda p=persona: mover_persona(p, "abajo"))
                        btn_bajar.pack(side="left", padx=2)
                        Tooltip(btn_bajar, "Mover abajo")
                    
                    # Botón Eliminar
                    btn_eliminar = ctk.CTkButton(btn_frame,
                                               text="🗑️",
                                               width=40,
                                               fg_color="red",
                                               hover_color="darkred",
                                               command=lambda p=persona: eliminar_persona(p))
                    btn_eliminar.pack(side="left", padx=2)
                    Tooltip(btn_eliminar, "Eliminar persona")
            
            def anadir_persona():
                """Agrega una nueva persona a la lista"""
                nueva_persona = entry_persona.get().strip()
                if nueva_persona:
                    success, msg = personas_mgr.añadir_persona(nueva_persona)
                    if success:
                        entry_persona.delete(0, "end")
                        cargar_personas()
                        recargar_personas_app()
                        messagebox.showinfo("Éxito", msg)
                    else:
                        messagebox.showerror("Error", msg)
                else:
                    messagebox.showwarning("Advertencia", "Por favor ingrese un nombre")
            
            def editar_persona(persona_actual):
                """Abre un diálogo para editar una persona"""
                from tkinter import simpledialog
                nueva_persona = simpledialog.askstring("Editar Persona",
                                                       f"Editar nombre de la persona:\n\n'{persona_actual}'",
                                                       initialvalue=persona_actual,
                                                       parent=gestor_window)
                if nueva_persona and nueva_persona.strip():
                    success, msg = personas_mgr.editar_persona(persona_actual, nueva_persona.strip())
                    if success:
                        cargar_personas()
                        recargar_personas_app()
                        messagebox.showinfo("Éxito", msg)
                    else:
                        messagebox.showerror("Error", msg)
            
            def eliminar_persona(persona):
                """Elimina una persona de la lista"""
                if messagebox.askyesno("Confirmar eliminación",
                                      f"¿Está seguro de eliminar la persona?\n\n'{persona}'",
                                      parent=gestor_window):
                    
                    success, msg = personas_mgr.eliminar_persona(persona)
                    if success:
                        cargar_personas()
                        recargar_personas_app()
                        messagebox.showinfo("Éxito", msg)
                    else:
                        messagebox.showerror("Error", msg)
            
            def mover_persona(persona, direccion):
                """Mueve una persona arriba o abajo"""
                success, msg = personas_mgr.mover_persona(persona, direccion)
                if success:
                    cargar_personas()
                    recargar_personas_app()
                else:
                    messagebox.showinfo("Info", msg)
            
            def recargar_personas_app():
                """Recarga las personas en la aplicación principal"""
                personas_actualizadas = personas_mgr.cargar_personas()
                self.OPCIONES["Autorizado_Por"] = personas_actualizadas
                self.OPCIONES["Gestionado_Por"] = personas_actualizadas
            
            # Conectar botones
            btn_agregar.configure(command=anadir_persona)
            entry_persona.bind("<Return>", lambda e: anadir_persona())
            
            # Cargar personas inicialmente
            cargar_personas()
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el gestor de personas:\n{e}")
            import traceback
            traceback.print_exc()

    def mostrar_gestor_personas_recepcion(self):
        """
        Abre una ventana para gestionar la lista de personas de recepción
        """
        from lib.safe_toplevel import SafeCTkToplevel
        from lib.personas_recepcion_manager import PersonasRecepcionManager
        
        try:
            # Crear ventana de gestión
            gestor_window = SafeCTkToplevel(self)
            gestor_window.title("Gestión de Personas de Recepción")
            gestor_window.geometry("600x500")
            gestor_window.transient(self)
            gestor_window.grab_set()
            
            # Frame principal con padding
            main_frame = ctk.CTkFrame(gestor_window)
            main_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Título
            title_label = ctk.CTkLabel(main_frame,
                                       text="👤 Gestión de Personas de Recepción",
                                       font=("Arial", 18, "bold"))
            title_label.pack(pady=(0, 20))
            
            # Frame para agregar nueva persona
            add_frame = ctk.CTkFrame(main_frame)
            add_frame.pack(fill="x", pady=(0, 20))
            
            entry_label = ctk.CTkLabel(add_frame,
                                       text="Nueva Persona:",
                                       font=("Arial", 12))
            entry_label.pack(side="left", padx=(10, 5))
            
            entry_persona = ctk.CTkEntry(add_frame,
                                         width=300,
                                         placeholder_text="Ingrese el nombre de la persona")
            entry_persona.pack(side="left", padx=5)
            
            btn_agregar = ctk.CTkButton(add_frame,
                                        text="➕ Agregar",
                                        width=100)
            btn_agregar.pack(side="left", padx=5)
            
            # Frame scrollable para la lista de personas
            list_frame = ctk.CTkScrollableFrame(main_frame,
                                                label_text="Personas de Recepción Registradas")
            list_frame.pack(fill="both", expand=True)
            
            # Instanciar el gestor
            personas_mgr = PersonasRecepcionManager()
            
            def cargar_personas():
                """Carga y muestra la lista de personas"""
                # Limpiar lista actual
                for widget in list_frame.winfo_children():
                    widget.destroy()
                
                # Obtener personas
                personas = personas_mgr.cargar_personas()
                
                if not personas:
                    no_data_label = ctk.CTkLabel(list_frame,
                                                 text="No hay personas de recepción registradas",
                                                 text_color="gray")
                    no_data_label.pack(pady=20)
                    return
                
                # Mostrar cada persona
                for i, persona in enumerate(personas):
                    persona_frame = ctk.CTkFrame(list_frame)
                    persona_frame.pack(fill="x", pady=5, padx=5)
                    
                    # Nombre de la persona
                    nombre_label = ctk.CTkLabel(persona_frame,
                                               text=persona,
                                               font=("Arial", 12),
                                               anchor="w")
                    nombre_label.pack(side="left", padx=10, fill="x", expand=True)
                    
                    # Botones de acción
                    btn_frame = ctk.CTkFrame(persona_frame, fg_color="transparent")
                    btn_frame.pack(side="right", padx=5)
                    
                    # Botón Editar
                    btn_editar = ctk.CTkButton(btn_frame,
                                              text="✏️",
                                              width=40,
                                              command=lambda p=persona: editar_persona(p))
                    btn_editar.pack(side="left", padx=2)
                    Tooltip(btn_editar, "Editar persona")
                    
                    # Botón Eliminar
                    btn_eliminar = ctk.CTkButton(btn_frame,
                                               text="🗑️",
                                               width=40,
                                               fg_color="red",
                                               hover_color="darkred",
                                               command=lambda p=persona: eliminar_persona(p))
                    btn_eliminar.pack(side="left", padx=2)
                    Tooltip(btn_eliminar, "Eliminar persona")
            
            def anadir_persona():
                """Agrega una nueva persona a la lista"""
                nueva_persona = entry_persona.get().strip()
                if nueva_persona:
                    success, msg = personas_mgr.añadir_persona(nueva_persona)
                    if success:
                        entry_persona.delete(0, "end")
                        cargar_personas()
                        recargar_personas_app()
                        messagebox.showinfo("Éxito", msg)
                    else:
                        messagebox.showerror("Error", msg)
                else:
                    messagebox.showwarning("Advertencia", "Por favor ingrese un nombre")
            
            def editar_persona(persona_actual):
                """Abre un diálogo para editar una persona"""
                from tkinter import simpledialog
                nueva_persona = simpledialog.askstring("Editar Persona de Recepción",
                                                       f"Editar nombre de la persona:\\n\\n'{persona_actual}'",
                                                       initialvalue=persona_actual,
                                                       parent=gestor_window)
                if nueva_persona and nueva_persona.strip():
                    success, msg = personas_mgr.editar_persona(persona_actual, nueva_persona.strip())
                    if success:
                        cargar_personas()
                        recargar_personas_app()
                        messagebox.showinfo("Éxito", msg)
                    else:
                        messagebox.showerror("Error", msg)
            
            def eliminar_persona(persona):
                """Elimina una persona de la lista"""
                if messagebox.askyesno("Confirmar eliminación",
                                      f"¿Está seguro de eliminar la persona de recepción?\\n\\n'{persona}'",
                                      parent=gestor_window):
                    
                    success, msg = personas_mgr.eliminar_persona(persona)
                    if success:
                        cargar_personas()
                        recargar_personas_app()
                        messagebox.showinfo("Éxito", msg)
                    else:
                        messagebox.showerror("Error", msg)
            
            def recargar_personas_app():
                """Recarga las personas de recepción en la aplicación principal"""
                personas_actualizadas = personas_mgr.cargar_personas()
                self.OPCIONES["Recepcionado_Por"] = personas_actualizadas
                logger.info("Opciones de Recepcionado_Por actualizadas en la aplicación")
            
            # Conectar botones
            btn_agregar.configure(command=anadir_persona)
            entry_persona.bind("<Return>", lambda e: anadir_persona())
            
            # Cargar personas inicialmente
            cargar_personas()
            
        except Exception as e:
            logger.error(f"Error al abrir gestor de personas de recepción: {e}")
            messagebox.showerror("Error", f"No se pudo abrir el gestor de personas de recepción:\\n{e}")
            import traceback
            traceback.print_exc()

    def mostrar_editor_texto_trazabilidad(self):
        """
        Abre una ventana para editar el texto de ayuda que se muestra en la
        ventana "Añadir Trazabilidad" de la ficha de expediente.
        """
        from lib.safe_toplevel import SafeCTkToplevel
        from lib.trazabilidad_manager import TrazabilidadManager

        if str(self.rol).strip().lower() not in ("admin", "administrador"):
            messagebox.showerror("Acceso Denegado", "Solo los administradores pueden editar este texto.")
            return

        try:
            manager = TrazabilidadManager()

            ventana = SafeCTkToplevel(self)
            ventana.title("Texto de Ayuda - Trazabilidad")
            ventana.geometry("560x420")
            ventana.transient(self)
            ventana.grab_set()

            main_frame = ctk.CTkFrame(ventana)
            main_frame.pack(fill="both", expand=True, padx=20, pady=20)

            ctk.CTkLabel(main_frame, text="📎 Texto de Ayuda - Añadir Trazabilidad",
                        font=("Arial", 16, "bold")).pack(pady=(0, 5))
            ctk.CTkLabel(main_frame,
                        text="Este texto se muestra a todos los usuarios en la parte superior de la\n"
                             "ventana \"Añadir Trazabilidad\" de la ficha de cada expediente.",
                        text_color="gray", justify="left").pack(pady=(0, 15))

            textbox_texto = ctk.CTkTextbox(main_frame, height=200, wrap="word")
            textbox_texto.pack(fill="both", expand=True, pady=(0, 15))
            textbox_texto.insert("1.0", manager.cargar_texto_ayuda())

            def guardar_texto():
                texto = textbox_texto.get("1.0", "end-1c").strip()
                if not texto:
                    messagebox.showwarning("Texto vacío", "El texto de ayuda no puede quedar vacío.")
                    return
                exito, mensaje = manager.guardar_texto_ayuda(texto)
                if exito:
                    messagebox.showinfo("Guardado", mensaje)
                    ventana.destroy()
                else:
                    messagebox.showerror("Error", mensaje)

            botones_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            botones_frame.pack(fill="x")

            ctk.CTkButton(botones_frame, text="✅ Guardar", command=guardar_texto,
                         height=38, font=ctk.CTkFont(weight="bold")).pack(side="left", fill="x", expand=True, padx=(0, 5))
            ctk.CTkButton(botones_frame, text="❌ Cancelar", width=100, fg_color="gray40",
                         hover_color="gray30", command=ventana.destroy).pack(side="right")

        except Exception as e:
            logger.error(f"Error al abrir el editor de texto de trazabilidad: {e}")
            messagebox.showerror("Error", f"No se pudo abrir el editor de texto:\n{e}")

    def mostrar_gestor_resultado_expediente(self):
        """
        Abre una ventana para gestionar la lista de resultados de expedientes
        """
        from lib.safe_toplevel import SafeCTkToplevel
        from lib.resultado_expediente_manager import ResultadoExpedienteManager
        
        try:
            # Crear ventana de gestión
            gestor_window = SafeCTkToplevel(self)
            gestor_window.title("Gestión de Resultado Expediente")
            gestor_window.geometry("600x500")
            gestor_window.transient(self)
            gestor_window.grab_set()
            
            # Frame principal con padding
            main_frame = ctk.CTkFrame(gestor_window)
            main_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Título
            title_label = ctk.CTkLabel(main_frame,
                                       text="📊 Gestión de Resultado Expediente",
                                       font=("Arial", 18, "bold"))
            title_label.pack(pady=(0, 20))
            
            # Frame para agregar nuevo resultado
            add_frame = ctk.CTkFrame(main_frame)
            add_frame.pack(fill="x", pady=(0, 20))
            
            entry_label = ctk.CTkLabel(add_frame,
                                       text="Nuevo Resultado:",
                                       font=("Arial", 12))
            entry_label.pack(side="left", padx=(10, 5))
            
            entry_resultado = ctk.CTkEntry(add_frame,
                                           width=300,
                                           placeholder_text="Ingrese el resultado del expediente")
            entry_resultado.pack(side="left", padx=5)
            
            btn_agregar = ctk.CTkButton(add_frame,
                                        text="➕ Agregar",
                                        width=100)
            btn_agregar.pack(side="left", padx=5)
            
            # Frame scrollable para la lista de resultados
            list_frame = ctk.CTkScrollableFrame(main_frame,
                                                label_text="Resultados Registrados")
            list_frame.pack(fill="both", expand=True)
            
            # Instanciar el gestor
            resultados_mgr = ResultadoExpedienteManager()
            
            def cargar_resultados():
                """Carga y muestra la lista de resultados"""
                # Limpiar lista actual
                for widget in list_frame.winfo_children():
                    widget.destroy()
                
                # Obtener resultados
                resultados = resultados_mgr.cargar_resultados()
                
                if not resultados:
                    no_data_label = ctk.CTkLabel(list_frame,
                                                 text="No hay resultados registrados",
                                                 text_color="gray")
                    no_data_label.pack(pady=20)
                    return
                
                # Mostrar cada resultado
                for i, resultado in enumerate(resultados):
                    resultado_frame = ctk.CTkFrame(list_frame)
                    resultado_frame.pack(fill="x", pady=5, padx=5)
                    
                    # Texto del resultado (mostrar etiqueta si está vacío)
                    texto_mostrar = resultado if resultado else "(vacío)"
                    color_texto = "gray" if not resultado else None
                    
                    nombre_label = ctk.CTkLabel(resultado_frame,
                                               text=texto_mostrar,
                                               font=("Arial", 12),
                                               anchor="w",
                                               text_color=color_texto)
                    nombre_label.pack(side="left", padx=10, fill="x", expand=True)
                    
                    # Botones de acción
                    btn_frame = ctk.CTkFrame(resultado_frame, fg_color="transparent")
                    btn_frame.pack(side="right", padx=5)
                    
                    # Botón Editar
                    btn_editar = ctk.CTkButton(btn_frame,
                                              text="✏️",
                                              width=40,
                                              command=lambda r=resultado: editar_resultado(r))
                    btn_editar.pack(side="left", padx=2)
                    Tooltip(btn_editar, "Editar resultado")
                    
                    # Botón Subir
                    if i > 0:  # No mostrar para el primero
                        btn_subir = ctk.CTkButton(btn_frame,
                                                text="⬆️",
                                                width=40,
                                                command=lambda r=resultado: mover_resultado(r, "arriba"))
                        btn_subir.pack(side="left", padx=2)
                        Tooltip(btn_subir, "Mover arriba")
                    
                    # Botón Bajar
                    if i < len(resultados) - 1:  # No mostrar para el último
                        btn_bajar = ctk.CTkButton(btn_frame,
                                                text="⬇️",
                                                width=40,
                                                command=lambda r=resultado: mover_resultado(r, "abajo"))
                        btn_bajar.pack(side="left", padx=2)
                        Tooltip(btn_bajar, "Mover abajo")
                    
                    # Botón Eliminar
                    btn_eliminar = ctk.CTkButton(btn_frame,
                                               text="🗑️",
                                               width=40,
                                               fg_color="red",
                                               hover_color="darkred",
                                               command=lambda r=resultado: eliminar_resultado(r))
                    btn_eliminar.pack(side="left", padx=2)
                    Tooltip(btn_eliminar, "Eliminar resultado")
            
            def anadir_resultado():
                """Agrega un nuevo resultado a la lista"""
                nuevo_resultado = entry_resultado.get().strip()
                if nuevo_resultado:
                    success, msg = resultados_mgr.añadir_resultado(nuevo_resultado)
                    if success:
                        entry_resultado.delete(0, "end")
                        cargar_resultados()
                        recargar_resultados_app()
                        messagebox.showinfo("Éxito", msg)
                    else:
                        messagebox.showerror("Error", msg)
                else:
                    messagebox.showwarning("Advertencia", "Por favor ingrese un resultado")
            
            def editar_resultado(resultado_actual):
                """Abre un diálogo para editar un resultado"""
                from tkinter import simpledialog
                
                texto_mostrar = resultado_actual if resultado_actual else "(vacío)"
                nuevo_resultado = simpledialog.askstring("Editar Resultado",
                                                         f"Editar resultado del expediente:\n\n'{texto_mostrar}'",
                                                         initialvalue=resultado_actual,
                                                         parent=gestor_window)
                if nuevo_resultado is not None and nuevo_resultado.strip():
                    success, msg = resultados_mgr.editar_resultado(resultado_actual, nuevo_resultado.strip())
                    if success:
                        cargar_resultados()
                        recargar_resultados_app()
                        messagebox.showinfo("Éxito", msg)
                    else:
                        messagebox.showerror("Error", msg)
            
            def eliminar_resultado(resultado):
                """Elimina un resultado de la lista"""
                texto_mostrar = resultado if resultado else "(vacío)"
                if messagebox.askyesno("Confirmar eliminación",
                                      f"¿Está seguro de eliminar el resultado?\n\n'{texto_mostrar}'",
                                      parent=gestor_window):
                    
                    success, msg = resultados_mgr.eliminar_resultado(resultado)
                    if success:
                        cargar_resultados()
                        recargar_resultados_app()
                        messagebox.showinfo("Éxito", msg)
                    else:
                        messagebox.showerror("Error", msg)
            
            def mover_resultado(resultado, direccion):
                """Mueve un resultado arriba o abajo"""
                success, msg = resultados_mgr.mover_resultado(resultado, direccion)
                if success:
                    cargar_resultados()
                    recargar_resultados_app()
                else:
                    messagebox.showinfo("Info", msg)
            
            def recargar_resultados_app():
                """Recarga los resultados en la aplicación principal"""
                self.OPCIONES["Resultado_Expediente"] = resultados_mgr.cargar_resultados()
            
            # Conectar botones
            btn_agregar.configure(command=anadir_resultado)
            entry_resultado.bind("<Return>", lambda e: anadir_resultado())
            
            # Cargar resultados inicialmente
            cargar_resultados()
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el gestor de resultado expediente:\n{e}")
            import traceback
            traceback.print_exc()

    def mostrar_gestor_tipos_cliente(self):
        """
        Abre una ventana para gestionar los tipos de cliente
        """
        from lib.safe_toplevel import SafeCTkToplevel
        from lib.tipos_cliente_manager import (cargar_tipos_cliente, guardar_tipos_cliente,
                                                anadir_tipo_cliente, eliminar_tipo_cliente,
                                                editar_tipo_cliente)
        
        try:
            # Crear ventana de gestión
            gestor_window = SafeCTkToplevel(self)
            gestor_window.title("Gestión de Tipos de Cliente")
            gestor_window.geometry("600x500")
            gestor_window.transient(self)
            gestor_window.grab_set()
            
            # Frame principal con padding
            main_frame = ctk.CTkFrame(gestor_window)
            main_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Título
            title_label = ctk.CTkLabel(main_frame,
                                       text="🏢 Gestión de Tipos de Cliente",
                                       font=("Arial", 18, "bold"))
            title_label.pack(pady=(0, 20))
            
            # Frame para agregar nuevo tipo
            add_frame = ctk.CTkFrame(main_frame)
            add_frame.pack(fill="x", pady=(0, 20))
            
            entry_label = ctk.CTkLabel(add_frame,
                                       text="Nuevo Tipo:",
                                       font=("Arial", 12))
            entry_label.pack(side="left", padx=(10, 5))
            
            entry_tipo = ctk.CTkEntry(add_frame,
                                      width=300,
                                      placeholder_text="Ingrese el nombre del tipo de cliente")
            entry_tipo.pack(side="left", padx=5)
            
            btn_agregar = ctk.CTkButton(add_frame,
                                        text="➕ Agregar",
                                        width=100)
            btn_agregar.pack(side="left", padx=5)
            
            # Frame scrollable para la lista de tipos
            list_frame = ctk.CTkScrollableFrame(main_frame,
                                                label_text="Tipos Registrados")
            list_frame.pack(fill="both", expand=True)
            
            def cargar_tipos():
                """Carga y muestra la lista de tipos de cliente"""
                # Limpiar el frame
                for widget in list_frame.winfo_children():
                    widget.destroy()
                
                # Cargar tipos
                tipos = cargar_tipos_cliente()
                
                if not tipos:
                    no_data_label = ctk.CTkLabel(list_frame,
                                                 text="No hay tipos de cliente registrados",
                                                 text_color="gray")
                    no_data_label.pack(pady=20)
                    return
                
                # Crear una fila para cada tipo
                for tipo in tipos:
                    row_frame = ctk.CTkFrame(list_frame)
                    row_frame.pack(fill="x", pady=5, padx=5)
                    
                    # Nombre del tipo
                    tipo_label = ctk.CTkLabel(row_frame,
                                              text=tipo,
                                              font=("Arial", 12),
                                              anchor="w")
                    tipo_label.pack(side="left", padx=10, fill="x", expand=True)
                    
                    # Botón Editar
                    btn_edit = ctk.CTkButton(row_frame,
                                             text="✏️",
                                             width=40,
                                             command=lambda t=tipo: editar_tipo(t))
                    btn_edit.pack(side="right", padx=2)
                    
                    # Botón Eliminar
                    btn_delete = ctk.CTkButton(row_frame,
                                               text="🗑️",
                                               width=40,
                                               fg_color="#ef4444",
                                               hover_color="#dc2626",
                                               command=lambda t=tipo: eliminar_tipo(t))
                    btn_delete.pack(side="right", padx=2)
            
            def agregar_tipo():
                """Agrega un nuevo tipo de cliente"""
                tipo = entry_tipo.get().strip()
                if tipo:
                    success, mensaje = anadir_tipo_cliente(tipo)
                    if success:
                        messagebox.showinfo("Éxito", mensaje)
                        entry_tipo.delete(0, 'end')
                        cargar_tipos()
                        # Recargar opciones en la aplicación principal
                        self.OPCIONES["Tipo_Cliente"] = cargar_tipos_cliente()
                    else:
                        messagebox.showerror("Error", mensaje)
                else:
                    messagebox.showwarning("Advertencia", "Debe ingresar un nombre para el tipo de cliente")
            
            def eliminar_tipo(tipo):
                """Elimina un tipo de cliente"""
                if messagebox.askyesno("Confirmar Eliminación",
                                      f"¿Está seguro de eliminar el tipo '{tipo}'?"):
                    success, mensaje = eliminar_tipo_cliente(tipo)
                    if success:
                        messagebox.showinfo("Éxito", mensaje)
                        cargar_tipos()
                        # Recargar opciones en la aplicación principal
                        self.OPCIONES["Tipo_Cliente"] = cargar_tipos_cliente()
                    else:
                        messagebox.showerror("Error", mensaje)
            
            def editar_tipo(tipo_antiguo):
                """Edita un tipo de cliente existente"""
                # Crear ventana de edición
                edit_window = ctk.CTkToplevel(gestor_window)
                edit_window.title("Editar Tipo de Cliente")
                edit_window.geometry("400x150")
                edit_window.transient(gestor_window)
                edit_window.grab_set()
                
                # Centrar ventana
                edit_window.update_idletasks()
                x = gestor_window.winfo_x() + (gestor_window.winfo_width() // 2) - (edit_window.winfo_width() // 2)
                y = gestor_window.winfo_y() + (gestor_window.winfo_height() // 2) - (edit_window.winfo_height() // 2)
                edit_window.geometry(f"+{x}+{y}")
                
                # Frame de contenido
                content_frame = ctk.CTkFrame(edit_window)
                content_frame.pack(fill="both", expand=True, padx=20, pady=20)
                
                # Label
                label = ctk.CTkLabel(content_frame,
                                    text="Nuevo nombre:",
                                    font=("Arial", 12))
                label.pack(pady=(0, 10))
                
                # Entry con valor actual
                entry_nuevo = ctk.CTkEntry(content_frame, width=300)
                entry_nuevo.insert(0, tipo_antiguo)
                entry_nuevo.pack(pady=(0, 20))
                entry_nuevo.focus_set()
                
                # Frame de botones
                buttons_frame = ctk.CTkFrame(content_frame)
                buttons_frame.pack()
                
                def guardar_edicion():
                    tipo_nuevo = entry_nuevo.get().strip()
                    if tipo_nuevo:
                        success, mensaje = editar_tipo_cliente(tipo_antiguo, tipo_nuevo)
                        if success:
                            messagebox.showinfo("Éxito", mensaje)
                            edit_window.destroy()
                            cargar_tipos()
                            # Recargar opciones en la aplicación principal
                            self.OPCIONES["Tipo_Cliente"] = cargar_tipos_cliente()
                        else:
                            messagebox.showerror("Error", mensaje)
                    else:
                        messagebox.showwarning("Advertencia", "El nombre no puede estar vacío")
                
                btn_guardar = ctk.CTkButton(buttons_frame,
                                            text="💾 Guardar",
                                            width=120,
                                            command=guardar_edicion)
                btn_guardar.pack(side="left", padx=5)
                
                btn_cancelar = ctk.CTkButton(buttons_frame,
                                             text="❌ Cancelar",
                                             width=120,
                                             fg_color="gray",
                                             command=edit_window.destroy)
                btn_cancelar.pack(side="left", padx=5)
                
                # Permitir Enter para guardar
                entry_nuevo.bind('<Return>', lambda e: guardar_edicion())
            
            # Configurar comando del botón agregar
            btn_agregar.configure(command=agregar_tipo)
            
            # Permitir Enter en el entry para agregar
            entry_tipo.bind('<Return>', lambda e: agregar_tipo())
            
            # Cargar tipos inicialmente
            cargar_tipos()
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el gestor de tipos de cliente:\n{e}")
            import traceback
            traceback.print_exc()

    def mostrar_gestion_usuarios(self):
        """Muestra la ventana de gestión de usuarios con opciones para añadir/editar usuarios."""
        # Solo admin tiene permisos para gestionar usuarios
        if str(self.rol).strip().lower() not in ("admin", "administrador"):
            messagebox.showerror("Error", "Solo el administrador puede gestionar usuarios.")
            return

        # Crear ventana modal
        ventana = ctk.CTkToplevel(self)
        ventana.title("Gestión de Usuarios")
        ventana.geometry("600x500")
        
        # Configurar para permitir minimización
        ventana.resizable(True, True)
        ventana.attributes('-topmost', False)
        ventana.minsize(500, 400)
        # No usar grab_set para permitir minimización completa
        try:
            ventana.focus_set()  # Solo dar foco sin modalidad
        except:
            pass
        
        # Forzar aparición al frente (incluso si la principal está maximizada)
        ventana.attributes('-topmost', True)   # Temporalmente al frente
        ventana.lift()
        ventana.focus_force()
        ventana.after(500, lambda: ventana.attributes('-topmost', False))  # Quitar topmost después de 500ms
        
        # Agregar icono personalizado
        try:
            ventana.iconbitmap("Icono_Ilutrek.ico")
        except Exception:
            pass

        # Frame principal
        frame = ctk.CTkFrame(ventana)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Título
        ctk.CTkLabel(frame, text="Gestión de Usuarios", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(0, 20))

        # Frame para el formulario de nuevo usuario
        form_frame = ctk.CTkFrame(frame)
        form_frame.pack(fill="x", padx=10, pady=10)

        # Campos del formulario
        ctk.CTkLabel(form_frame, text="Nombre de Usuario:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        entry_usuario = ctk.CTkEntry(form_frame)
        entry_usuario.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(form_frame, text="Contraseña:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        entry_password = ctk.CTkEntry(form_frame, show="*")
        entry_password.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(form_frame, text="Rol:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        # Lista de roles disponibles
        roles_disponibles = [
            "usuario",        # Usuario básico
            "admin",         # Administrador total
            "Dpto. Tecnico", # Departamento técnico
            "Administracion",# Administración
            "Contabilidad",  # Contabilidad
            "Almacen"        # Almacén
        ]
        combo_rol = ctk.CTkOptionMenu(form_frame, values=roles_disponibles)
        combo_rol.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        combo_rol.set("usuario")  # Valor por defecto

        form_frame.grid_columnconfigure(1, weight=1)

        def agregar_usuario():
            username = entry_usuario.get().strip()
            password = entry_password.get().strip()
            rol = combo_rol.get()

            if not username or not password:
                messagebox.showerror("Error", "Por favor, complete todos los campos.")
                return

            try:
                # Generar hash de la contraseña y guardarlo como str UTF-8
                password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode('utf-8')

                conn = connect_db()
                cursor = conn.cursor()

                # Verificar si el usuario ya existe
                cursor.execute("SELECT nombre_usuario FROM usuarios WHERE nombre_usuario = ?", (username,))
                if cursor.fetchone():
                    messagebox.showerror("Error", "El nombre de usuario ya existe.")
                    return

                # Insertar nuevo usuario
                cursor.execute(
                    "INSERT INTO usuarios (nombre_usuario, password_hash, rol) VALUES (?, ?, ?)",
                    (username, password_hash, rol)
                )
                conn.commit()
                messagebox.showinfo("Éxito", "Usuario creado correctamente.")
                
                # Limpiar campos
                entry_usuario.delete(0, 'end')
                entry_password.delete(0, 'end')
                combo_rol.set("usuario")
                
                # Actualizar lista de usuarios
                actualizar_lista_usuarios()

            except sqlite3.Error as e:
                messagebox.showerror("Error", f"Error al crear usuario: {e}")
            finally:
                conn.close()

        # Botón para agregar usuario
        ctk.CTkButton(form_frame, text="Agregar Usuario", command=agregar_usuario).grid(row=3, column=0, columnspan=2, pady=20)

        # Frame para la lista de usuarios
        list_frame = ctk.CTkFrame(frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(20,10))

        # Título de la lista
        ctk.CTkLabel(list_frame, text="Usuarios Existentes", font=ctk.CTkFont(weight="bold")).pack(pady=10)

        # Crear un frame scrollable para la lista de usuarios
        scroll_frame = ctk.CTkScrollableFrame(list_frame)
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        def actualizar_lista_usuarios():
            # Limpiar lista actual
            for widget in scroll_frame.winfo_children():
                widget.destroy()

            try:
                conn = connect_db()
                cursor = conn.cursor()
                # Asegurarnos de que la columna email exista (añadir si no)
                try:
                    cursor.execute("PRAGMA table_info('usuarios')")
                    cols = [r[1] for r in cursor.fetchall()]
                    if 'email' not in cols:
                        cursor.execute("ALTER TABLE usuarios ADD COLUMN email TEXT")
                        conn.commit()
                except Exception:
                    # Ignorar si ya existe o si el backend no permite ALTER (p.ej. versiones restringidas)
                    pass
                # Seleccionamos también el email si existe
                try:
                    cursor.execute("SELECT nombre_usuario, rol, COALESCE(email, '') FROM usuarios")
                except Exception:
                    # Fallback si la columna no existe por alguna razón
                    cursor.execute("SELECT nombre_usuario, rol FROM usuarios")
                usuarios = cursor.fetchall()

                for i, row in enumerate(usuarios):
                    # row can be (usuario, rol) or (usuario, rol, email)
                    usuario = row[0] if len(row) > 0 else ''
                    rol = row[1] if len(row) > 1 else ''
                    display_email = row[2] if len(row) > 2 else ''

                    row_frame = ctk.CTkFrame(scroll_frame)
                    row_frame.pack(fill="x", padx=5, pady=2)

                    label_text = f"{usuario} ({rol})"
                    if display_email:
                        label_text += f" — {display_email}"
                    lbl = ctk.CTkLabel(row_frame, text=label_text)
                    lbl.pack(side="left", padx=5)

                    # Hacer clic en el label abre editor de usuario, excepto para admin
                    if usuario != "admin":
                        def make_editor(u=usuario):
                            return lambda e=None: editar_usuario(u)
                        try:
                            lbl.bind("<Button-1>", make_editor(usuario))
                            lbl.configure(cursor="hand2")
                        except Exception:
                            pass
                    else:
                        # Mostrar cursor normal y no permitir edición
                        try:
                            lbl.configure(cursor="")
                        except Exception:
                            pass
                    
                    if usuario != "admin":  # No permitir eliminar al usuario admin
                        def make_delete(u=usuario):
                            return lambda: eliminar_usuario(u)
                        
                        ctk.CTkButton(row_frame, text="❌", width=30, command=make_delete(usuario)).pack(side="right", padx=5)

            except sqlite3.Error as e:
                messagebox.showerror("Error", f"Error al cargar usuarios: {e}")
            finally:
                conn.close()

        def editar_usuario(username):
            """Abrir dialogo para editar rol, password y email del usuario seleccionado."""
            # Proteger al usuario admin: no se puede editar
            if username == "admin":
                messagebox.showerror("Acceso denegado", "El usuario 'admin' no se puede editar ni eliminar.")
                return
            try:
                conn = connect_db()
                cur = conn.cursor()
                # Intentar obtener email si existe
                try:
                    cur.execute("SELECT nombre_usuario, rol, COALESCE(email, '') FROM usuarios WHERE nombre_usuario = ?", (username,))
                    row = cur.fetchone()
                    if row and len(row) >= 3:
                        _, rol_actual, email_actual = row
                    else:
                        cur.execute("SELECT nombre_usuario, rol FROM usuarios WHERE nombre_usuario = ?", (username,))
                        row2 = cur.fetchone()
                        rol_actual = row2[1] if row2 else ''
                        email_actual = ''
                except Exception:
                    # fallback
                    cur.execute("SELECT nombre_usuario, rol FROM usuarios WHERE nombre_usuario = ?", (username,))
                    row2 = cur.fetchone()
                    rol_actual = row2[1] if row2 else ''
                    email_actual = ''
                conn.close()
            except Exception:
                rol_actual = ''
                email_actual = ''

            # Editor modal
            ed = ctk.CTkToplevel(ventana)
            ed.title(f"Editar usuario: {username}")
            ed.geometry("420x260")
            ed.grab_set()

            f = ctk.CTkFrame(ed)
            f.pack(fill="both", expand=True, padx=12, pady=12)

            ctk.CTkLabel(f, text=f"Usuario: {username}", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,8))

            ctk.CTkLabel(f, text="Rol:").grid(row=1, column=0, sticky="e", padx=5, pady=6)
            rol_menu = ctk.CTkOptionMenu(f, values=roles_disponibles)
            rol_menu.grid(row=1, column=1, sticky="ew", padx=5, pady=6)
            try:
                rol_menu.set(rol_actual or "usuario")
            except Exception:
                rol_menu.set("usuario")

            ctk.CTkLabel(f, text="Nueva contraseña:").grid(row=2, column=0, sticky="e", padx=5, pady=6)
            new_pass = ctk.CTkEntry(f, show="*")
            new_pass.grid(row=2, column=1, sticky="ew", padx=5, pady=6)

            ctk.CTkLabel(f, text="Email:").grid(row=3, column=0, sticky="e", padx=5, pady=6)
            email_entry = ctk.CTkEntry(f)
            email_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=6)
            try:
                email_entry.insert(0, email_actual)
            except Exception:
                pass

            f.grid_columnconfigure(1, weight=1)

            def guardar_cambios():
                nuevo_rol = rol_menu.get()
                nueva_pass = new_pass.get().strip()
                nuevo_email = email_entry.get().strip()
                try:
                    conn2 = connect_db()
                    cur2 = conn2.cursor()
                    # Si se proporcionó nueva contraseña, hashearla
                    if nueva_pass:
                        # Guardar el hash como string UTF-8 para mantener compatibilidad
                        hashed = bcrypt.hashpw(nueva_pass.encode(), bcrypt.gensalt()).decode('utf-8')
                        try:
                            cur2.execute("UPDATE usuarios SET password_hash = ? WHERE nombre_usuario = ?", (hashed, username))
                        except Exception:
                            pass
                    # Actualizar rol y email
                    try:
                        cur2.execute("UPDATE usuarios SET rol = ?, email = ? WHERE nombre_usuario = ?", (nuevo_rol, nuevo_email, username))
                    except Exception:
                        # Si UPDATE falla porque la columna email no existe, intentar crearla y reintentar
                        try:
                            cur2.execute("PRAGMA table_info('usuarios')")
                            cols = [r[1] for r in cur2.fetchall()]
                            if 'email' not in cols:
                                cur2.execute("ALTER TABLE usuarios ADD COLUMN email TEXT")
                            cur2.execute("UPDATE usuarios SET rol = ?, email = ? WHERE nombre_usuario = ?", (nuevo_rol, nuevo_email, username))
                        except Exception:
                            pass
                    conn2.commit()
                    conn2.close()
                    messagebox.showinfo("Éxito", "Usuario actualizado correctamente.")
                    ed.destroy()
                    actualizar_lista_usuarios()
                except sqlite3.Error as e:
                    messagebox.showerror("Error", f"No se pudo actualizar usuario: {e}")

            btn_frame = ctk.CTkFrame(f)
            btn_frame.grid(row=6, column=0, columnspan=2, pady=(12,0))
            ctk.CTkButton(btn_frame, text="Guardar", command=guardar_cambios).pack(side="left", padx=6)
            ctk.CTkButton(btn_frame, text="Cancelar", command=ed.destroy).pack(side="left", padx=6)

        def eliminar_usuario(username):
            if messagebox.askyesno("Confirmar", f"¿Está seguro de eliminar al usuario {username}?"):
                try:
                    conn = connect_db()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM usuarios WHERE nombre_usuario = ?", (username,))
                    conn.commit()
                    messagebox.showinfo("Éxito", "Usuario eliminado correctamente.")
                    actualizar_lista_usuarios()
                except sqlite3.Error as e:
                    messagebox.showerror("Error", f"Error al eliminar usuario: {e}")
                finally:
                    conn.close()

        # Cargar lista inicial de usuarios
        actualizar_lista_usuarios()
        # Cargar lista inicial de usuarios
        actualizar_lista_usuarios()

    def mostrar_gestion_tareas(self):
        """Ventana para crear y listar tareas relacionadas con expedientes."""
        # Si NO es administrador, mostrar el panel de tareas personalizado (mismo que el badge)
        if self.rol != 'administrador':
            self.abrir_panel_tareas()
            return
        
        # Solo admin ve la ventana antigua con TODAS las tareas
        # Actualizar badge antes de mostrar la ventana
        if hasattr(self, 'badge_tareas'):
            self.badge_tareas.actualizar_contador()
        
        # Mostrar solo el listado de tareas y filtros (la creación se hace desde la ficha del expediente)
        ventana = ctk.CTkToplevel(self)
        ventana.title("Listado de Tareas")
        ventana.geometry("700x550")
        
        # Configurar para permitir minimización
        ventana.resizable(True, True)
        ventana.minsize(600, 400)
        
        # Forzar aparición al frente (incluso si la principal está maximizada)
        ventana.attributes('-topmost', True)
        ventana.lift()
        ventana.focus_force()
        # Quitar topmost después de 500ms para no ser molesto
        ventana.after(500, lambda: ventana.attributes('-topmost', False))

        frame = ctk.CTkFrame(ventana)
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(frame, text="Listado de Tareas", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(0,10))

        # Filtros y lista
        controls = ctk.CTkFrame(frame)
        controls.pack(fill="x", padx=5, pady=(0,10))

        ctk.CTkLabel(controls, text="Filtrar por estado:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        filtro_estado = ctk.CTkOptionMenu(controls, values=["Todos", "Pendiente", "En Progreso", "Completado"]) 
        filtro_estado.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        filtro_estado.set("Todos")

        # Filtro por creador de la tarea
        try:
            conn_tmp = connect_db()
            cur_tmp = conn_tmp.cursor()
            cur_tmp.execute("SELECT DISTINCT creado_por FROM tareas")
            creadores_rows = cur_tmp.fetchall()
            try:
                conn_tmp.close()
            except Exception:
                pass
            creadores = [r[0] for r in creadores_rows if r and r[0]]
        except Exception:
            creadores = []

        valores_creador = ["Todos"] + creadores
        ctk.CTkLabel(controls, text="Filtrar por Usuario:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        filtro_creador = ctk.CTkOptionMenu(controls, values=valores_creador)
        filtro_creador.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        filtro_creador.set("Todos")

        list_frame = ctk.CTkFrame(frame)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        scroll = ctk.CTkScrollableFrame(list_frame)
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        def abrir_expediente_por_codigo(codigo):
            try:
                conn = connect_db()
                cur = conn.cursor()
                cur.execute("SELECT id FROM rma_maestro WHERE codigo_rma = ?", (codigo,))
                row = cur.fetchone()
                conn.close()
                if row:
                    rma_id = row[0]
                    # Abrir en ventana independiente
                    self._abrir_editor_rma(rma_id=rma_id)
                    # No cerrar la ventana de tareas para poder seguir trabajando
                else:
                    messagebox.showwarning("No encontrado", f"No se encontró expediente con código {codigo}")
            except sqlite3.Error as e:
                messagebox.showerror("Error BD", f"Error buscando expediente: {e}")

        def actualizar_lista_tareas():
            for w in scroll.winfo_children():
                w.destroy()
            try:
                conn = connect_db()
                cur = conn.cursor()
                estado = filtro_estado.get()
                creador = filtro_creador.get()
                
                logger.debug(f"Filtrando tareas - Estado: {estado}, Creador: {creador}")

                base_sql = "SELECT id, codigo_rma, titulo, descripcion, fecha_vencimiento, estado, creado_por FROM tareas"
                where_clauses = []
                params = []
                if estado and estado != "Todos":
                    where_clauses.append("estado = ?")
                    params.append(estado)
                if creador and creador != "Todos":
                    where_clauses.append("creado_por = ?")
                    params.append(creador)

                order_clause = " ORDER BY fecha_vencimiento IS NULL, fecha_vencimiento ASC"

                if where_clauses:
                    sql = base_sql + " WHERE " + " AND ".join(where_clauses) + order_clause
                    cur.execute(sql, tuple(params))
                else:
                    cur.execute(base_sql + order_clause)
                    
                filas = cur.fetchall()
                logger.info(f"Admin viendo {len(filas)} tareas en total (filtro: {creador})")
                conn.close()

                # Encabezados de tabla con estructura en columnas
                header = ctk.CTkFrame(scroll)
                header.pack(fill="x", padx=5, pady=(0, 5))
                header.grid_columnconfigure(0, weight=2, minsize=200)  # Título
                header.grid_columnconfigure(1, weight=1, minsize=100)  # Código
                header.grid_columnconfigure(2, weight=1, minsize=120)  # Estado
                header.grid_columnconfigure(3, weight=1, minsize=120)  # Vencimiento
                header.grid_columnconfigure(4, weight=0, minsize=80)   # Acciones
                
                header_font = ctk.CTkFont(weight="bold")
                ctk.CTkLabel(header, text="TÍTULO", font=header_font, anchor="w").grid(row=0, column=0, padx=5, sticky="w")
                ctk.CTkLabel(header, text="CÓDIGO", font=header_font, anchor="w").grid(row=0, column=1, padx=5, sticky="w")
                ctk.CTkLabel(header, text="ESTADO", font=header_font, anchor="w").grid(row=0, column=2, padx=5, sticky="w")
                ctk.CTkLabel(header, text="VENCIMIENTO", font=header_font, anchor="w").grid(row=0, column=3, padx=5, sticky="w")
                ctk.CTkLabel(header, text="ACCIONES", font=header_font, anchor="center").grid(row=0, column=4, padx=5)

                # Filas de datos
                for tid, codigo, titulo, desc, fecha_v, estado_tarea, creador in filas:
                    row = ctk.CTkFrame(scroll, fg_color="transparent")
                    row.pack(fill="x", padx=5, pady=2)
                    
                    # Configurar columnas igual que header
                    row.grid_columnconfigure(0, weight=2, minsize=200)
                    row.grid_columnconfigure(1, weight=1, minsize=100)
                    row.grid_columnconfigure(2, weight=1, minsize=120)
                    row.grid_columnconfigure(3, weight=1, minsize=120)
                    row.grid_columnconfigure(4, weight=0, minsize=80)
                    
                    # Título - clickeable
                    titulo_lbl = ctk.CTkLabel(row, text=titulo, anchor="w", cursor="hand2")
                    titulo_lbl.grid(row=0, column=0, padx=5, sticky="w")
                    
                    # Código RMA - clickeable
                    codigo_lbl = ctk.CTkLabel(row, text=codigo, anchor="w", cursor="hand2")
                    codigo_lbl.grid(row=0, column=1, padx=5, sticky="w")
                    
                    # Estado
                    estado_lbl = ctk.CTkLabel(row, text=estado_tarea, anchor="w")
                    estado_lbl.grid(row=0, column=2, padx=5, sticky="w")
                    
                    # Fecha vencimiento
                    fecha_lbl = ctk.CTkLabel(row, text=fecha_v if fecha_v else "Sin fecha", anchor="w")
                    fecha_lbl.grid(row=0, column=3, padx=5, sticky="w")
                    
                    # Efectos hover para toda la fila
                    def on_enter(e, r=row):
                        try:
                            r.configure(fg_color="transparent")
                        except Exception:
                            pass
                    def on_leave(e, r=row):
                        try:
                            r.configure(fg_color="transparent")
                        except Exception:
                            pass
                    
                    row.bind("<Enter>", on_enter)
                    row.bind("<Leave>", on_leave)
                    titulo_lbl.bind("<Enter>", on_enter)
                    titulo_lbl.bind("<Leave>", on_leave)
                    codigo_lbl.bind("<Enter>", on_enter)
                    codigo_lbl.bind("<Leave>", on_leave)
                    
                    # Click para abrir expediente
                    titulo_lbl.bind("<Button-1>", lambda e, c=codigo: abrir_expediente_por_codigo(c))
                    codigo_lbl.bind("<Button-1>", lambda e, c=codigo: abrir_expediente_por_codigo(c))
                    
                    # Botones de acción
                    acciones_frame = ctk.CTkFrame(row, fg_color="transparent")
                    acciones_frame.grid(row=0, column=4, padx=5)
                    
                    def make_done(tid=tid):
                        return lambda: marcar_completada(tid)
                    def make_delete(tid=tid):
                        return lambda: eliminar_tarea(tid)
                    
                    if estado_tarea != "Completado":
                        ctk.CTkButton(acciones_frame, text="✅", width=30, command=make_done(tid)).pack(side="left", padx=2)
                    ctk.CTkButton(acciones_frame, text="❌", width=30, command=make_delete(tid)).pack(side="left", padx=2)

            except sqlite3.Error as e:
                messagebox.showerror("Error", f"Error cargando tareas: {e}")

        def marcar_completada(task_id):
            try:
                conn = connect_db()
                cur = conn.cursor()
                cur.execute("UPDATE tareas SET estado = 'Completado', notificado = 1 WHERE id = ?", (task_id,))
                conn.commit()
                conn.close()
                actualizar_lista_tareas()
                # Actualizar badge de tareas inmediatamente
                if hasattr(self, 'badge_tareas'):
                    self.badge_tareas.actualizar_contador()
            except sqlite3.Error as e:
                messagebox.showerror("Error", f"No se pudo actualizar la tarea: {e}")

        def eliminar_tarea(task_id):
            if not messagebox.askyesno("Confirmar", "¿Eliminar esta tarea?"):
                return
            try:
                conn = connect_db()
                cur = conn.cursor()
                cur.execute("DELETE FROM tareas WHERE id = ?", (task_id,))
                conn.commit()
                conn.close()
                actualizar_lista_tareas()
            except sqlite3.Error as e:
                messagebox.showerror("Error", f"No se pudo eliminar la tarea: {e}")

        filtro_estado.configure(command=lambda v=None: actualizar_lista_tareas())
        filtro_creador.configure(command=lambda v=None: actualizar_lista_tareas())
        actualizar_lista_tareas()

    def abrir_panel_tareas(self):
        """Abre el panel moderno de tareas con filtros y visualización mejorada."""
        logger = get_logger()
        logger.debug(f"Abriendo panel de tareas para usuario: {self.username}")
        
        try:
            # Crear el panel de tareas
            panel = PanelTareas(
                parent=self,
                connect_db_func=self.conectar_db,
                username=self.username,
                abrir_expediente_callback=self.abrir_expediente_desde_panel
            )
            
            # El panel se posiciona automáticamente y maneja su propia visibilidad
            logger.info(f"Panel de tareas abierto exitosamente para {self.username}")
            
        except Exception as e:
            logger.error(f"Error al abrir panel de tareas: {e}", exc_info=True)
            messagebox.showerror("Error", f"No se pudo abrir el panel de tareas:\n{e}")

    def abrir_expediente_desde_panel(self, codigo_rma):
        logger = get_logger()
        logger.debug(f"Abriendo expediente {codigo_rma} desde panel de tareas")
        try:
            conn, cursor = self.conectar_db()
            if not conn:
                logger.error("No se pudo conectar a la base de datos")
                return
            cursor.execute("SELECT id FROM rma_maestro WHERE Codigo_RMA = ?", (codigo_rma,))
            resultado = cursor.fetchone()
            conn.close()
            if resultado:
                rma_id = resultado[0]
                logger.info(f"Abriendo expediente en ventana flotante: {codigo_rma}")
                self._abrir_editor_rma(rma_id=rma_id)
            else:
                logger.warning(f"No se encontro expediente: {codigo_rma}")
                messagebox.showwarning("No encontrado", f"No se encontro el expediente {codigo_rma}")
        except Exception as e:
            logger.error(f"Error al abrir expediente desde panel: {e}", exc_info=True)
            messagebox.showerror("Error", f"No se pudo abrir el expediente:\n{e}")
