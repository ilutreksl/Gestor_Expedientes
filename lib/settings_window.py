"""
Ventana de Ajustes del Usuario - Gestor de Expedientes
Sistema de configuración con interfaz por pestañas y gestión completa de preferencias.
"""

import os
import json
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
from PIL import Image
import bcrypt

from lib.logger_config import get_logger
from lib.firma_manager import subir_firma_usuario_b2, eliminar_firma_usuario_b2
from lib.changelog_window import mostrar_ventana_cambios

logger = get_logger()


class SettingsWindow(ctk.CTkToplevel):
    """Ventana de ajustes con pestañas para configuración del usuario."""
    
    def __init__(self, parent, app_instance):
        """
        Inicializa la ventana de ajustes.
        
        Args:
            parent: Ventana padre
            app_instance: Instancia de la aplicación principal para acceder a métodos y datos
        """
        super().__init__(parent)
        
        self.app = app_instance
        self.username = app_instance.username
        self.user_settings = app_instance.user_settings.copy()
        self.original_settings = app_instance.user_settings.copy()
        self.has_changes = False
        
        logger.info(f"Abriendo ventana de ajustes para usuario: {self.username}")
        
        # Configuración de la ventana
        self.title("⚙️ Ajustes del Usuario")
        self.geometry("900x700")
        self.transient(parent)
        self.grab_set()
        
        # Icono
        try:
            self.iconbitmap("Icono_Ilutrek.ico")
        except Exception:
            pass
        
        # Variables de control
        self._init_variables()
        
        # Crear interfaz
        self._create_ui()
        
        # Vincular eventos
        self._bind_events()
        
        # Centrar ventana
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
        
        logger.debug("Ventana de ajustes inicializada correctamente")
    
    def _init_variables(self):
        """Inicializa variables de control para los widgets."""
        logger.debug("Inicializando variables de control")
        
        # General
        self.var_tooltips = tk.BooleanVar(value=self.user_settings.get("show_tooltips", True))
        self.var_compact = tk.BooleanVar(value=self.user_settings.get("compact_mode", True))
        self.var_icon_size = tk.IntVar(value=self.user_settings.get("icon_size", 24))
        
        # Notificaciones
        self.var_sonido = tk.BooleanVar(value=self.user_settings.get("notificaciones_sonoras", True))
        self.var_notif_inicio = tk.BooleanVar(value=self.user_settings.get("notificar_al_iniciar", True))
        self.var_dias_vencimiento = tk.IntVar(value=self.user_settings.get("dias_anticipacion_vencimiento", 7))
        self.var_dias_sin_gestionar = tk.IntVar(value=self.user_settings.get("dias_notificar_sin_gestionar", 15))
        self.var_volumen = tk.IntVar(value=self.user_settings.get("volumen_notificaciones", 70))
        
        # Seguridad
        self.var_tiene_firma = tk.BooleanVar(value=self.user_settings.get("tiene_firma", False))
        
        # Avanzado
        self.var_modo_debug = tk.BooleanVar(value=self.user_settings.get("modo_debug", False))
        
        logger.debug(f"Variables inicializadas: tooltips={self.var_tooltips.get()}, "
                    f"compact={self.var_compact.get()}, sonido={self.var_sonido.get()}")
    
    def _create_ui(self):
        """Crea la interfaz de usuario completa."""
        logger.debug("Creando interfaz de usuario")
        
        # Frame principal
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=12, pady=12)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # TabView
        self.tabview = ctk.CTkTabview(main_frame, width=850, height=580)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Crear pestañas
        self.tab_general = self.tabview.add("📋 General")
        self.tab_apariencia = self.tabview.add("🎨 Apariencia")
        self.tab_notificaciones = self.tabview.add("🔔 Notificaciones")
        self.tab_seguridad = self.tabview.add("🔒 Seguridad")
        self.tab_avanzado = self.tabview.add("⚙️ Avanzado")
        
        # Llenar pestañas
        self._create_general_tab()
        self._create_appearance_tab()
        self._create_notifications_tab()
        self._create_security_tab()
        self._create_advanced_tab()
        
        # Frame de botones (fuera del tabview)
        self._create_buttons_frame(main_frame)
        
        logger.debug("Interfaz creada: 5 pestañas y botones de acción")
    
    def _create_general_tab(self):
        """Crea la pestaña General."""
        logger.debug("Creando pestaña General")
        
        frame = ctk.CTkScrollableFrame(self.tab_general, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        row = 0
        
        # Título
        ctk.CTkLabel(frame, text="Configuración General", 
                    font=("Arial", 16, "bold")).grid(row=row, column=0, columnspan=2, 
                                                     sticky="w", padx=10, pady=(5,15))
        row += 1
        
        # Formato de fecha
        ctk.CTkLabel(frame, text="Formato de fecha:", 
                    font=("Arial", 12)).grid(row=row, column=0, sticky="w", padx=10, pady=8)
        date_values = ["YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY"]
        self.date_menu = ctk.CTkOptionMenu(frame, values=date_values, width=200,
                                           command=self._on_setting_changed)
        self.date_menu.set(self.user_settings.get("date_format", "YYYY-MM-DD"))
        self.date_menu.grid(row=row, column=1, sticky="w", padx=10, pady=8)
        self._add_tooltip(self.date_menu, "Formato de visualización de fechas en toda la aplicación")
        row += 1
        
        # Mostrar tooltips
        ctk.CTkLabel(frame, text="Mostrar tooltips:", 
                    font=("Arial", 12)).grid(row=row, column=0, sticky="w", padx=10, pady=8)
        switch_tooltips = ctk.CTkSwitch(frame, text="Activado", variable=self.var_tooltips,
                                        command=self._on_setting_changed)
        switch_tooltips.grid(row=row, column=1, sticky="w", padx=10, pady=8)
        self._add_tooltip(switch_tooltips, "Muestra ayuda contextual al pasar el mouse sobre elementos")
        row += 1
        
        # Modo compacto
        ctk.CTkLabel(frame, text="Modo compacto:", 
                    font=("Arial", 12)).grid(row=row, column=0, sticky="w", padx=10, pady=8)
        switch_compact = ctk.CTkSwitch(frame, text="Activado", variable=self.var_compact,
                                       command=self._on_setting_changed)
        switch_compact.grid(row=row, column=1, sticky="w", padx=10, pady=8)
        self._add_tooltip(switch_compact, "Reduce el espaciado en listados para ver más información")
        row += 1
        
        # Tamaño de iconos
        ctk.CTkLabel(frame, text="Tamaño de iconos:", 
                    font=("Arial", 12)).grid(row=row, column=0, sticky="w", padx=10, pady=8)
        
        icon_frame = ctk.CTkFrame(frame, fg_color="transparent")
        icon_frame.grid(row=row, column=1, sticky="w", padx=10, pady=8)
        
        self.icon_slider = ctk.CTkSlider(icon_frame, from_=16, to=32, number_of_steps=16,
                                         variable=self.var_icon_size, width=200,
                                         command=lambda v: self._on_icon_size_changed())
        self.icon_slider.pack(side="left", padx=(0, 10))
        
        self.icon_label = ctk.CTkLabel(icon_frame, text=f"{self.var_icon_size.get()} px",
                                       font=("Arial", 11))
        self.icon_label.pack(side="left")
        self._add_tooltip(self.icon_slider, "Ajusta el tamaño de los iconos en la interfaz (16-32 px)")
        row += 1
        
        # Espaciador
        ctk.CTkLabel(frame, text="").grid(row=row, column=0, pady=10)
        row += 1
        
        logger.debug("Pestaña General creada con 4 ajustes")
    
    def _create_appearance_tab(self):
        """Crea la pestaña Apariencia."""
        logger.debug("Creando pestaña Apariencia")
        
        frame = ctk.CTkScrollableFrame(self.tab_apariencia, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        row = 0
        
        # Título
        ctk.CTkLabel(frame, text="Personalización Visual", 
                    font=("Arial", 16, "bold")).grid(row=row, column=0, columnspan=2,
                                                     sticky="w", padx=10, pady=(5,15))
        row += 1
        
        # Tema
        ctk.CTkLabel(frame, text="Tema de la aplicación:", 
                    font=("Arial", 12)).grid(row=row, column=0, sticky="w", padx=10, pady=8)
        
        temas_disponibles = self.app.obtener_temas_disponibles()
        self.tema_menu = ctk.CTkOptionMenu(frame, values=temas_disponibles, width=300,
                                           command=self._on_theme_changed)
        
        tema_actual = self.user_settings.get("theme", "themes/BH_rime.json")
        tema_display = self.app.archivo_a_tema_display(tema_actual.replace("themes/", ""))
        if tema_display in temas_disponibles:
            self.tema_menu.set(tema_display)
        else:
            self.tema_menu.set("BH Rime (Predeterminado)")
        
        self.tema_menu.grid(row=row, column=1, sticky="w", padx=10, pady=8)
        self._add_tooltip(self.tema_menu, "Selecciona el tema de colores de la aplicación")
        row += 1
        
        # Modo claro/oscuro
        ctk.CTkLabel(frame, text="Modo de apariencia:", 
                    font=("Arial", 12)).grid(row=row, column=0, sticky="w", padx=10, pady=8)
        
        modo_values = ["Claro", "Oscuro"]
        self.modo_menu = ctk.CTkOptionMenu(frame, values=modo_values, width=200,
                                           command=lambda v: self._on_setting_changed())
        modo_actual = self.user_settings.get("appearance_mode", "light")
        self.modo_menu.set("Claro" if modo_actual == "light" else "Oscuro")
        self.modo_menu.grid(row=row, column=1, sticky="w", padx=10, pady=8)
        self._add_tooltip(self.modo_menu, "Alterna entre modo claro y oscuro (algunos temas solo soportan un modo)")
        row += 1
        
        # Aplicar estado inicial del modo según el tema
        self._update_mode_availability()
        
        # Botón restaurar tema predeterminado
        btn_restore = ctk.CTkButton(frame, text="🔄 Restaurar Tema Predeterminado", 
                                    command=self._restore_default_theme, width=250)
        btn_restore.grid(row=row, column=0, columnspan=2, padx=10, pady=15)
        self._add_tooltip(btn_restore, "Restaura el tema BH Rime en modo claro")
        row += 1
        
        # Separador
        sep = ctk.CTkFrame(frame, height=2, fg_color="gray40")
        sep.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=15)
        row += 1
        
        # Nota informativa
        info_text = ("💡 Los cambios de tema y modo se aplicarán al reiniciar la aplicación.\n"
                    "Esto garantiza que todos los elementos visuales se actualicen correctamente.")
        info_label = ctk.CTkLabel(frame, text=info_text, font=("Arial", 10),
                                 text_color="gray60", wraplength=700, justify="left")
        info_label.grid(row=row, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        row += 1
        
        logger.debug("Pestaña Apariencia creada con selector de tema y modo")
    
    def _create_notifications_tab(self):
        """Crea la pestaña Notificaciones."""
        logger.debug("Creando pestaña Notificaciones")
        
        frame = ctk.CTkScrollableFrame(self.tab_notificaciones, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        row = 0
        
        # Título
        ctk.CTkLabel(frame, text="Sistema de Notificaciones", 
                    font=("Arial", 16, "bold")).grid(row=row, column=0, columnspan=2,
                                                     sticky="w", padx=10, pady=(5,15))
        row += 1
        
        # Sonido en notificaciones
        switch_sonido = ctk.CTkSwitch(frame, text="Habilitar sonido en notificaciones", 
                                      variable=self.var_sonido, font=("Arial", 12),
                                      command=self._on_setting_changed)
        switch_sonido.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=8)
        self._add_tooltip(switch_sonido, "Reproduce un sonido cuando aparezcan notificaciones de tareas")
        row += 1
        
        # Notificar al iniciar
        switch_inicio = ctk.CTkSwitch(frame, text="Notificar tareas pendientes al iniciar", 
                                      variable=self.var_notif_inicio, font=("Arial", 12),
                                      command=self._on_setting_changed)
        switch_inicio.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=8)
        self._add_tooltip(switch_inicio, "Muestra notificaciones de tareas pendientes al abrir la aplicación")
        row += 1
        
        # Separador
        sep1 = ctk.CTkFrame(frame, height=2, fg_color="gray40")
        sep1.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=15)
        row += 1
        
        # Días de anticipación para vencimientos
        ctk.CTkLabel(frame, text="Días de anticipación para vencimientos:", 
                    font=("Arial", 12)).grid(row=row, column=0, sticky="w", padx=10, pady=8)
        
        dias_venc_frame = ctk.CTkFrame(frame, fg_color="transparent")
        dias_venc_frame.grid(row=row, column=1, sticky="w", padx=10, pady=8)
        
        self.slider_dias_venc = ctk.CTkSlider(dias_venc_frame, from_=0, to=30, 
                                             number_of_steps=30, variable=self.var_dias_vencimiento,
                                             width=200, command=lambda v: self._on_slider_changed('venc'))
        self.slider_dias_venc.pack(side="left", padx=(0, 10))
        
        self.label_dias_venc = ctk.CTkLabel(dias_venc_frame, 
                                           text=f"{self.var_dias_vencimiento.get()} días",
                                           font=("Arial", 11), width=60)
        self.label_dias_venc.pack(side="left")
        self._add_tooltip(self.slider_dias_venc, "Con cuántos días de anticipación notificar tareas próximas a vencer (0-30 días)")
        row += 1
        
        # Días para notificar expedientes sin gestionar
        ctk.CTkLabel(frame, text="Notificar expedientes sin gestionar (días):", 
                    font=("Arial", 12)).grid(row=row, column=0, sticky="w", padx=10, pady=8)
        
        dias_sin_frame = ctk.CTkFrame(frame, fg_color="transparent")
        dias_sin_frame.grid(row=row, column=1, sticky="w", padx=10, pady=8)
        
        self.slider_dias_sin = ctk.CTkSlider(dias_sin_frame, from_=0, to=60, 
                                            number_of_steps=60, variable=self.var_dias_sin_gestionar,
                                            width=200, command=lambda v: self._on_slider_changed('sin'))
        self.slider_dias_sin.pack(side="left", padx=(0, 10))
        
        self.label_dias_sin = ctk.CTkLabel(dias_sin_frame, 
                                          text=f"{self.var_dias_sin_gestionar.get()} días",
                                          font=("Arial", 11), width=60)
        self.label_dias_sin.pack(side="left")
        self._add_tooltip(self.slider_dias_sin, "Notifica expedientes que llevan X días sin gestionar (0 = desactivado)")
        row += 1
        
        # Separador
        sep2 = ctk.CTkFrame(frame, height=2, fg_color="gray40")
        sep2.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=15)
        row += 1
        
        # Volumen de notificaciones
        ctk.CTkLabel(frame, text="Volumen de notificaciones:", 
                    font=("Arial", 12)).grid(row=row, column=0, sticky="w", padx=10, pady=8)
        
        vol_frame = ctk.CTkFrame(frame, fg_color="transparent")
        vol_frame.grid(row=row, column=1, sticky="w", padx=10, pady=8)
        
        self.slider_volumen = ctk.CTkSlider(vol_frame, from_=0, to=100, 
                                           number_of_steps=20, variable=self.var_volumen,
                                           width=200, command=lambda v: self._on_slider_changed('vol'))
        self.slider_volumen.pack(side="left", padx=(0, 10))
        
        self.label_volumen = ctk.CTkLabel(vol_frame, text=f"{self.var_volumen.get()}%",
                                         font=("Arial", 11), width=50)
        self.label_volumen.pack(side="left")
        self._add_tooltip(self.slider_volumen, "Ajusta el volumen del sonido de notificaciones (0-100%)")
        row += 1
        
        logger.debug("Pestaña Notificaciones creada con 5 ajustes")
    
    def _create_security_tab(self):
        """Crea la pestaña Seguridad."""
        logger.debug("Creando pestaña Seguridad")
        
        frame = ctk.CTkScrollableFrame(self.tab_seguridad, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        row = 0
        
        # Título
        ctk.CTkLabel(frame, text="Seguridad y Credenciales", 
                    font=("Arial", 16, "bold")).grid(row=row, column=0, columnspan=2,
                                                     sticky="w", padx=10, pady=(5,15))
        row += 1
        
        # Email
        ctk.CTkLabel(frame, text="Email:", 
                    font=("Arial", 12)).grid(row=row, column=0, sticky="w", padx=10, pady=8)
        
        self.entry_email = ctk.CTkEntry(frame, width=400, placeholder_text="correo@ejemplo.com")
        
        # Intentar prellenar desde BD
        try:
            conn, cursor = self.app.master.conectar_db()
            if conn and cursor:
                cursor.execute("PRAGMA table_info('usuarios')")
                cols = [r[1] for r in cursor.fetchall()]
                if 'email' in cols:
                    cursor.execute("SELECT email FROM usuarios WHERE nombre_usuario = ?", (self.username,))
                    row_data = cursor.fetchone()
                    if row_data and row_data[0]:
                        self.entry_email.insert(0, row_data[0])
                try:
                    conn.close()
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"No se pudo cargar email desde BD: {e}")
        
        self.entry_email.grid(row=row, column=1, sticky="w", padx=10, pady=8)
        self.entry_email.bind('<KeyRelease>', lambda e: self._validate_email())
        self._add_tooltip(self.entry_email, "Dirección de correo electrónico para recuperación de cuenta")
        row += 1
        
        # Label de validación email
        self.email_validation_label = ctk.CTkLabel(frame, text="", font=("Arial", 9),
                                                   text_color="gray60")
        self.email_validation_label.grid(row=row, column=1, sticky="w", padx=10, pady=0)
        row += 1
        
        # Separador
        sep1 = ctk.CTkFrame(frame, height=2, fg_color="gray40")
        sep1.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=15)
        row += 1
        
        # Cambiar contraseña
        ctk.CTkLabel(frame, text="Cambiar Contraseña", 
                    font=("Arial", 14, "bold")).grid(row=row, column=0, columnspan=2,
                                                     sticky="w", padx=10, pady=(5,10))
        row += 1
        
        ctk.CTkLabel(frame, text="Nueva contraseña:", 
                    font=("Arial", 12)).grid(row=row, column=0, sticky="w", padx=10, pady=8)
        
        self.entry_password = ctk.CTkEntry(frame, width=400, show="*", 
                                          placeholder_text="Mínimo 8 caracteres")
        self.entry_password.grid(row=row, column=1, sticky="w", padx=10, pady=8)
        self.entry_password.bind('<KeyRelease>', lambda e: self._validate_password())
        self._add_tooltip(self.entry_password, "Nueva contraseña (mínimo 8 caracteres, recomendado incluir mayúsculas, números y símbolos)")
        row += 1
        
        ctk.CTkLabel(frame, text="Confirmar contraseña:", 
                    font=("Arial", 12)).grid(row=row, column=0, sticky="w", padx=10, pady=8)
        
        self.entry_password2 = ctk.CTkEntry(frame, width=400, show="*",
                                           placeholder_text="Repite la contraseña")
        self.entry_password2.grid(row=row, column=1, sticky="w", padx=10, pady=8)
        self.entry_password2.bind('<KeyRelease>', lambda e: self._validate_password())
        self._add_tooltip(self.entry_password2, "Confirma tu nueva contraseña")
        row += 1
        
        # Label de validación contraseña
        self.password_validation_label = ctk.CTkLabel(frame, text="", font=("Arial", 9),
                                                      text_color="gray60")
        self.password_validation_label.grid(row=row, column=1, sticky="w", padx=10, pady=0)
        row += 1
        
        # Separador
        sep2 = ctk.CTkFrame(frame, height=2, fg_color="gray40")
        sep2.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=15)
        row += 1
        
        # Gestión de firma
        ctk.CTkLabel(frame, text="Gestión de Firma Digital", 
                    font=("Arial", 14, "bold")).grid(row=row, column=0, columnspan=2,
                                                     sticky="w", padx=10, pady=(5,10))
        row += 1
        
        # Estado de la firma
        switch_firma = ctk.CTkSwitch(frame, text="¿Tiene firma registrada?", 
                                     variable=self.var_tiene_firma, state="disabled",
                                     font=("Arial", 12))
        switch_firma.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=8)
        self._add_tooltip(switch_firma, "Indicador de estado: Muestra si tienes una firma digital configurada (solo lectura)")
        row += 1
        
        # Botones de firma
        firma_btns_frame = ctk.CTkFrame(frame, fg_color="transparent")
        firma_btns_frame.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=10)
        
        btn_adjuntar = ctk.CTkButton(firma_btns_frame, text="📎 Adjuntar Firma", 
                     command=self._adjuntar_firma, width=150, height=35)
        btn_adjuntar.pack(side="left", padx=5)
        self._add_tooltip(btn_adjuntar, "Sube tu firma digital en formato PNG (max 810x740px, 2MB)")
        
        btn_cambiar = ctk.CTkButton(firma_btns_frame, text="🔄 Cambiar Firma", 
                     command=self._cambiar_firma, width=150, height=35)
        btn_cambiar.pack(side="left", padx=5)
        self._add_tooltip(btn_cambiar, "Reemplaza tu firma digital actual por una nueva")
        
        btn_eliminar = ctk.CTkButton(firma_btns_frame, text="🗑️ Eliminar Firma", 
                     command=self._eliminar_firma, width=150, height=35,
                     fg_color="darkred", hover_color="red")
        btn_eliminar.pack(side="left", padx=5)
        self._add_tooltip(btn_eliminar, "Elimina permanentemente tu firma digital del sistema")
        row += 1
        
        # Info sobre requisitos de firma
        info_firma = ("Requisitos: Solo PNG, máx 810x740 px, máx 2 MB, fondo transparente recomendado")
        ctk.CTkLabel(frame, text=info_firma, font=("Arial", 9), 
                    text_color="gray60").grid(row=row, column=0, columnspan=2,
                                             sticky="w", padx=10, pady=5)
        row += 1
        
        logger.debug("Pestaña Seguridad creada con gestión de email, contraseña y firma")
    
    def _create_advanced_tab(self):
        """Crea la pestaña Avanzado."""
        logger.debug("Creando pestaña Avanzado")
        
        frame = ctk.CTkScrollableFrame(self.tab_avanzado, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        row = 0
        
        # Título
        ctk.CTkLabel(frame, text="Opciones Avanzadas", 
                    font=("Arial", 16, "bold")).grid(row=row, column=0, columnspan=2,
                                                     sticky="w", padx=10, pady=(5,15))
        row += 1
        
        # Modo debug
        switch_debug = ctk.CTkSwitch(frame, text="Modo de depuración (Logs extendidos)", 
                                     variable=self.var_modo_debug, font=("Arial", 12),
                                     command=self._on_setting_changed)
        switch_debug.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=8)
        self._add_tooltip(switch_debug, "Activa logs más detallados para diagnóstico de problemas")
        row += 1
        
        # Separador
        sep1 = ctk.CTkFrame(frame, height=2, fg_color="gray40")
        sep1.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=15)
        row += 1
        
        # Gestión de configuración
        ctk.CTkLabel(frame, text="Gestión de Configuración", 
                    font=("Arial", 14, "bold")).grid(row=row, column=0, columnspan=2,
                                                     sticky="w", padx=10, pady=(5,10))
        row += 1
        
        config_btns_frame = ctk.CTkFrame(frame, fg_color="transparent")
        config_btns_frame.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=10)
        
        btn_exportar = ctk.CTkButton(config_btns_frame, text="💾 Exportar Configuración", 
                     command=self._exportar_config, width=200, height=35)
        btn_exportar.pack(side="left", padx=5)
        self._add_tooltip(btn_exportar, "Guarda todos tus ajustes en un archivo JSON para backup o transferencia")
        
        btn_importar = ctk.CTkButton(config_btns_frame, text="📥 Importar Configuración", 
                     command=self._importar_config, width=200, height=35)
        btn_importar.pack(side="left", padx=5)
        self._add_tooltip(btn_importar, "Carga ajustes desde un archivo JSON exportado previamente")
        row += 1
        
        # Separador
        sep2 = ctk.CTkFrame(frame, height=2, fg_color="gray40")
        sep2.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=15)
        row += 1
        
        # Limpieza de datos
        ctk.CTkLabel(frame, text="Limpieza de Datos", 
                    font=("Arial", 14, "bold")).grid(row=row, column=0, columnspan=2,
                                                     sticky="w", padx=10, pady=(5,10))
        row += 1
        
        limpieza_btns_frame = ctk.CTkFrame(frame, fg_color="transparent")
        limpieza_btns_frame.grid(row=row, column=0, columnspan=2, sticky="w", padx=10, pady=10)
        
        btn_historial = ctk.CTkButton(limpieza_btns_frame, text="🗑️ Limpiar Historial de Búsquedas", 
                     command=self._limpiar_historial, width=240, height=35)
        btn_historial.pack(side="left", padx=5)
        self._add_tooltip(btn_historial, "Elimina todas las búsquedas guardadas del historial")
        
        btn_cache = ctk.CTkButton(limpieza_btns_frame, text="🧹 Limpiar Caché de Datos", 
                     command=self._limpiar_cache, width=200, height=35)
        btn_cache.pack(side="left", padx=5)
        self._add_tooltip(btn_cache, "Elimina la caché de consultas para forzar recarga de datos")
        row += 1
        
        # Separador
        sep3 = ctk.CTkFrame(frame, height=2, fg_color="gray40")
        sep3.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=15)
        row += 1
        
        # Restablecer configuración
        ctk.CTkLabel(frame, text="Acciones de Restablecimiento", 
                    font=("Arial", 14, "bold")).grid(row=row, column=0, columnspan=2,
                                                     sticky="w", padx=10, pady=(5,10))
        row += 1
        
        btn_reset = ctk.CTkButton(frame, text="⚠️ Restablecer Ajustes Predeterminados",
                                 command=self._restablecer_defaults, width=300, height=35,
                                 fg_color="darkorange", hover_color="orange")
        btn_reset.grid(row=row, column=0, columnspan=2, padx=10, pady=10)
        self._add_tooltip(btn_reset, "Restaura todos los ajustes a sus valores predeterminados (excepto email y contraseña)")
        row += 1
        
        # Advertencia
        warning_text = ("⚠️ ADVERTENCIA: Restablecer los ajustes eliminará todas tus preferencias personalizadas.")
        ctk.CTkLabel(frame, text=warning_text, font=("Arial", 9), 
                    text_color="orange").grid(row=row, column=0, columnspan=2,
                                             sticky="w", padx=10, pady=5)
        row += 1
        
        logger.debug("Pestaña Avanzado creada con opciones de gestión y limpieza")
    
    def _create_buttons_frame(self, parent):
        """Crea el frame de botones en la parte inferior."""
        logger.debug("Creando frame de botones")
        
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(10, 5))
        
        # Configurar grid
        for i in range(5):
            btn_frame.grid_columnconfigure(i, weight=1)
        
        # Botones
        btn_cancelar = ctk.CTkButton(btn_frame, text="❌ Cancelar", command=self._on_cancel,
                     width=120, height=35)
        btn_cancelar.grid(row=0, column=0, padx=5)
        self._add_tooltip(btn_cancelar, "Cierra sin guardar cambios (Esc)")
        
        btn_cambios = ctk.CTkButton(btn_frame, text="📋 Ver Cambios", command=self._ver_cambios,
                     width=120, height=35)
        btn_cambios.grid(row=0, column=1, padx=5)
        self._add_tooltip(btn_cambios, "Muestra qué ajustes han sido modificados")
        
        btn_ayuda = ctk.CTkButton(btn_frame, text="❓ Ayuda", command=self._abrir_ayuda,
                     width=120, height=35)
        btn_ayuda.grid(row=0, column=2, padx=5)
        self._add_tooltip(btn_ayuda, "Abre el manual de usuario en la sección de ajustes")
        
        self.btn_aplicar = ctk.CTkButton(btn_frame, text="✓ Aplicar", command=self._on_apply,
                                        width=120, height=35)
        self.btn_aplicar.grid(row=0, column=3, padx=5)
        self._add_tooltip(self.btn_aplicar, "Guarda cambios sin cerrar la ventana")
        
        self.btn_guardar = ctk.CTkButton(btn_frame, text="💾 Guardar y Cerrar", command=self._on_save,
                                        width=140, height=35, fg_color="green", hover_color="darkgreen")
        self.btn_guardar.grid(row=0, column=4, padx=5)
        self._add_tooltip(self.btn_guardar, "Guarda cambios y cierra la ventana (Ctrl+S)")
        
        logger.debug("Frame de botones creado con 5 acciones")
    
    def _bind_events(self):
        """Vincula eventos de teclado."""
        logger.debug("Vinculando eventos de teclado")
        
        self.bind("<Control-s>", lambda e: self._on_save())
        self.bind("<Escape>", lambda e: self._on_cancel())
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
    
    def _add_tooltip(self, widget, text):
        """Añade un tooltip a un widget si están habilitados."""
        if self.user_settings.get("show_tooltips", True):
            try:
                from lib.tooltip import ToolTip
                ToolTip(widget, text)
            except Exception:
                pass
    
    # ==================== CALLBACKS Y VALIDACIONES ====================
    
    def _on_setting_changed(self, *args):
        """Marca que hay cambios sin guardar."""
        if not self.has_changes:
            self.has_changes = True
            self.title("⚙️ Ajustes del Usuario *")
            logger.debug("Configuración modificada - cambios sin guardar")
    
    def _on_icon_size_changed(self):
        """Actualiza la etiqueta del tamaño de icono."""
        self.icon_label.configure(text=f"{self.var_icon_size.get()} px")
        self._on_setting_changed()
    
    def _on_slider_changed(self, slider_type):
        """Actualiza las etiquetas de los sliders."""
        if slider_type == 'venc':
            self.label_dias_venc.configure(text=f"{self.var_dias_vencimiento.get()} días")
        elif slider_type == 'sin':
            self.label_dias_sin.configure(text=f"{self.var_dias_sin_gestionar.get()} días")
        elif slider_type == 'vol':
            self.label_volumen.configure(text=f"{self.var_volumen.get()}%")
        self._on_setting_changed()
    
    def _on_theme_changed(self, *args):
        """Maneja el cambio de tema."""
        self._update_mode_availability()
        self._on_setting_changed()
    
    def _update_mode_availability(self):
        """Habilita/deshabilita el selector de modo según el tema."""
        tema_seleccionado = self.tema_menu.get()
        if tema_seleccionado == "BH Rime (Predeterminado)":
            self.modo_menu.set("Claro")
            self.modo_menu.configure(state="disabled")
        else:
            self.modo_menu.configure(state="normal")
    
    def _restore_default_theme(self):
        """Restaura el tema predeterminado."""
        logger.info(f"Usuario {self.username} restaurando tema predeterminado")
        self.tema_menu.set("BH Rime (Predeterminado)")
        self.modo_menu.set("Claro")
        self._update_mode_availability()
        self._on_setting_changed()
        messagebox.showinfo("Tema Restaurado", 
                          "El tema predeterminado se aplicará al reiniciar la aplicación.",
                          parent=self)
    
    def _validate_email(self):
        """Valida el formato del email en tiempo real."""
        email = self.entry_email.get().strip()
        if not email:
            self.email_validation_label.configure(text="", text_color="gray60")
            return True
        
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, email):
            self.email_validation_label.configure(text="✓ Email válido", text_color="green")
            self._on_setting_changed()
            return True
        else:
            self.email_validation_label.configure(text="✗ Email inválido", text_color="red")
            return False
    
    def _validate_password(self):
        """Valida las contraseñas en tiempo real."""
        pw1 = self.entry_password.get()
        pw2 = self.entry_password2.get()
        
        if not pw1 and not pw2:
            self.password_validation_label.configure(text="", text_color="gray60")
            return True
        
        if pw1 and len(pw1) < 8:
            self.password_validation_label.configure(text="✗ Mínimo 8 caracteres", text_color="red")
            return False
        
        if pw1 and pw2:
            if pw1 == pw2:
                self.password_validation_label.configure(text="✓ Las contraseñas coinciden", text_color="green")
                self._on_setting_changed()
                return True
            else:
                self.password_validation_label.configure(text="✗ Las contraseñas no coinciden", text_color="red")
                return False
        
        if pw1 and not pw2:
            self.password_validation_label.configure(text="Confirma tu contraseña", text_color="gray60")
            return False
        
        return True
    
    # ==================== GESTIÓN DE FIRMA ====================
    
    def _adjuntar_firma(self):
        """Permite al usuario adjuntar su firma."""
        logger.info(f"Usuario {self.username} iniciando proceso de adjuntar firma")
        
        # Mostrar requisitos
        messagebox.showinfo(
            "Requisitos de la Firma",
            "La firma debe cumplir los siguientes requisitos:\n\n"
            "• Formato: Solo archivos .PNG\n"
            "• Dimensiones máximas: 810x740 px\n"
            "• Tamaño máximo: 2 MB\n"
            "• Fondo transparente (recomendado)",
            parent=self
        )
        
        # Selector de archivo
        ruta = filedialog.askopenfilename(
            title="Seleccionar imagen de firma",
            filetypes=[("Imágenes PNG", "*.png")],
            parent=self
        )
        
        if not ruta:
            logger.debug("Usuario canceló selección de firma")
            return
        
        # Validar PNG
        if not ruta.lower().endswith('.png'):
            messagebox.showerror("Error", "Solo se aceptan archivos PNG.", parent=self)
            logger.warning(f"Usuario intentó subir archivo no PNG: {ruta}")
            return
        
        # Validar imagen
        try:
            with Image.open(ruta) as img:
                ancho, alto = img.size
                
                if ancho < 100 or alto < 50:
                    messagebox.showwarning(
                        "Dimensiones pequeñas",
                        f"La imagen es muy pequeña ({ancho}x{alto} px).\n"
                        "Se recomienda al menos 300x150 px para mejor calidad.",
                        parent=self
                    )
                
                if ancho > 810 or alto > 740:
                    messagebox.showerror(
                        "Dimensiones excedidas",
                        f"La imagen excede las dimensiones máximas ({ancho}x{alto} px).\n"
                        "Las dimensiones máximas permitidas son 810x740 px.",
                        parent=self
                    )
                    logger.warning(f"Firma con dimensiones excedidas: {ancho}x{alto}")
                    return
                
                tamanio_mb = os.path.getsize(ruta) / (1024 * 1024)
                if tamanio_mb > 2:
                    messagebox.showerror(
                        "Archivo muy grande",
                        f"El archivo pesa {tamanio_mb:.2f} MB.\n"
                        "El tamaño máximo es 2 MB.",
                        parent=self
                    )
                    logger.warning(f"Firma con tamaño excedido: {tamanio_mb:.2f} MB")
                    return
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer la imagen:\n{e}", parent=self)
            logger.error(f"Error al validar firma: {e}", exc_info=True)
            return
        
        # Subir a B2
        try:
            from app import get_b2_client  # Importar función de app.py
            exito, resultado = subir_firma_usuario_b2(self.username, ruta, get_b2_client)
            
            if exito:
                self.var_tiene_firma.set(True)
                messagebox.showinfo(
                    "Éxito",
                    "Su firma ha sido guardada correctamente.\n"
                    f"Archivo: {resultado}",
                    parent=self
                )
                logger.info(f"Firma adjuntada exitosamente para usuario {self.username}")
                self._on_setting_changed()
            else:
                messagebox.showerror("Error", f"No se pudo subir la firma:\n{resultado}", parent=self)
                logger.error(f"Error subiendo firma: {resultado}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al procesar la firma:\n{e}", parent=self)
            logger.error(f"Excepción al subir firma: {e}", exc_info=True)
    
    def _cambiar_firma(self):
        """Permite cambiar la firma existente."""
        if not self.var_tiene_firma.get():
            self._adjuntar_firma()
            return
        
        respuesta = messagebox.askyesno(
            "Cambiar Firma",
            "¿Desea reemplazar su firma actual por una nueva?\n\n"
            "La firma anterior será eliminada.",
            parent=self
        )
        
        if respuesta:
            logger.info(f"Usuario {self.username} cambiando firma existente")
            self._adjuntar_firma()
    
    def _eliminar_firma(self):
        """Elimina la firma del usuario."""
        if not self.var_tiene_firma.get():
            messagebox.showinfo("Información", "No tiene firma registrada.", parent=self)
            return
        
        respuesta = messagebox.askyesno(
            "Confirmar Eliminación",
            "¿Está seguro de que desea eliminar su firma?\n\n"
            "Esta acción no se puede deshacer.",
            parent=self
        )
        
        if not respuesta:
            return
        
        try:
            from app import get_b2_client
            exito = eliminar_firma_usuario_b2(self.username, get_b2_client)
            
            if exito:
                self.var_tiene_firma.set(False)
                messagebox.showinfo("Éxito", "Su firma ha sido eliminada correctamente.", parent=self)
                logger.info(f"Firma eliminada para usuario {self.username}")
                self._on_setting_changed()
            else:
                messagebox.showwarning(
                    "Advertencia",
                    "No se pudo eliminar la firma del almacenamiento.\n"
                    "Es posible que ya no exista.",
                    parent=self
                )
                self.var_tiene_firma.set(False)
                self._on_setting_changed()
                logger.warning(f"Firma no encontrada en B2 para usuario {self.username}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al eliminar la firma:\n{e}", parent=self)
            logger.error(f"Error eliminando firma: {e}", exc_info=True)
    
    # ==================== OPCIONES AVANZADAS ====================
    
    def _exportar_config(self):
        """Exporta la configuración actual a un archivo JSON."""
        logger.info(f"Usuario {self.username} exportando configuración")
        
        archivo = filedialog.asksaveasfilename(
            title="Exportar Configuración",
            defaultextension=".json",
            filetypes=[("Archivo JSON", "*.json"), ("Todos los archivos", "*.*")],
            initialfile=f"config_{self.username}.json",
            parent=self
        )
        
        if not archivo:
            return
        
        try:
            # Recolectar configuración actual
            config = self._collect_current_settings()
            
            with open(archivo, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Éxito", 
                              f"Configuración exportada correctamente a:\n{archivo}",
                              parent=self)
            logger.info(f"Configuración exportada a: {archivo}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar configuración:\n{e}", parent=self)
            logger.error(f"Error exportando configuración: {e}", exc_info=True)
    
    def _importar_config(self):
        """Importa configuración desde un archivo JSON."""
        logger.info(f"Usuario {self.username} importando configuración")
        
        archivo = filedialog.askopenfilename(
            title="Importar Configuración",
            filetypes=[("Archivo JSON", "*.json"), ("Todos los archivos", "*.*")],
            parent=self
        )
        
        if not archivo:
            return
        
        respuesta = messagebox.askyesno(
            "Confirmar Importación",
            "¿Desea importar esta configuración?\n\n"
            "Esto sobrescribirá sus ajustes actuales.",
            parent=self
        )
        
        if not respuesta:
            return
        
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Aplicar configuración importada
            self._apply_imported_settings(config)
            
            messagebox.showinfo("Éxito", "Configuración importada correctamente.", parent=self)
            logger.info(f"Configuración importada desde: {archivo}")
            self._on_setting_changed()
        except Exception as e:
            messagebox.showerror("Error", f"Error al importar configuración:\n{e}", parent=self)
            logger.error(f"Error importando configuración: {e}", exc_info=True)
    
    def _limpiar_historial(self):
        """Limpia el historial de búsquedas."""
        logger.info(f"Usuario {self.username} limpiando historial de búsquedas")
        
        respuesta = messagebox.askyesno(
            "Confirmar Limpieza",
            "¿Desea limpiar todo el historial de búsquedas?\n\n"
            "Esta acción no se puede deshacer.",
            parent=self
        )
        
        if respuesta:
            try:
                self.user_settings["historial_busquedas"] = []
                messagebox.showinfo("Éxito", "Historial de búsquedas limpiado.", parent=self)
                logger.info(f"Historial limpiado para usuario {self.username}")
                self._on_setting_changed()
            except Exception as e:
                messagebox.showerror("Error", f"Error al limpiar historial:\n{e}", parent=self)
                logger.error(f"Error limpiando historial: {e}", exc_info=True)
    
    def _limpiar_cache(self):
        """Limpia la caché de datos."""
        logger.info(f"Usuario {self.username} limpiando caché de datos")
        
        try:
            # Acceder al cache global de app.py
            import sys
            app_module = sys.modules.get('__main__')
            if app_module and hasattr(app_module, '_query_cache'):
                cache_size = len(app_module._query_cache)
                app_module._query_cache.clear()
                messagebox.showinfo(
                    "Caché Limpiada",
                    f"Se eliminaron {cache_size} consultas del caché.\n\n"
                    "La próxima carga puede ser más lenta.",
                    parent=self
                )
                logger.info(f"Caché limpiada: {cache_size} entradas eliminadas")
            else:
                messagebox.showwarning(
                    "Advertencia",
                    "No se pudo acceder al caché de la aplicación.",
                    parent=self
                )
                logger.warning("No se encontró _query_cache en el módulo principal")
        except Exception as e:
            logger.error(f"Error al limpiar caché: {e}", exc_info=True)
            messagebox.showerror(
                "Error",
                f"No se pudo limpiar el caché:\n{str(e)}",
                parent=self
            )
    
    def _restablecer_defaults(self):
        """Restablece todos los ajustes a sus valores predeterminados."""
        logger.warning(f"Usuario {self.username} intentando restablecer ajustes predeterminados")
        
        respuesta = messagebox.askyesno(
            "⚠️ Confirmar Restablecimiento",
            "¿Está seguro de que desea restablecer todos los ajustes?\n\n"
            "Se perderán todas sus preferencias personalizadas.\n"
            "(Email y contraseña NO se modificarán)",
            parent=self
        )
        
        if not respuesta:
            return
        
        try:
            # Valores predeterminados
            defaults = {
                "date_format": "YYYY-MM-DD",
                "show_tooltips": True,
                "compact_mode": True,
                "icon_size": 24,
                "theme": "themes/BH_rime.json",
                "appearance_mode": "light",
                "notificaciones_sonoras": True,
                "notificar_al_iniciar": True,
                "dias_anticipacion_vencimiento": 7,
                "dias_notificar_sin_gestionar": 15,
                "volumen_notificaciones": 70,
                "modo_debug": False,
                "historial_busquedas": []
            }
            
            # Aplicar defaults
            for key, value in defaults.items():
                self.user_settings[key] = value
            
            # Recargar UI con defaults
            self._apply_imported_settings(defaults)
            
            messagebox.showinfo("Éxito", "Ajustes restablecidos a valores predeterminados.", parent=self)
            logger.info(f"Ajustes restablecidos para usuario {self.username}")
            self._on_setting_changed()
        except Exception as e:
            messagebox.showerror("Error", f"Error al restablecer ajustes:\n{e}", parent=self)
            logger.error(f"Error restableciendo ajustes: {e}", exc_info=True)
    
    # ==================== ACCIONES DE BOTONES ====================
    
    def _on_cancel(self):
        """Maneja el botón Cancelar."""
        if self.has_changes:
            respuesta = messagebox.askyesnocancel(
                "Cambios sin guardar",
                "Hay cambios sin guardar. ¿Desea guardarlos antes de salir?",
                parent=self
            )
            
            if respuesta is None:  # Cancel
                return
            elif respuesta:  # Yes
                self._on_save()
                return
        
        logger.info(f"Usuario {self.username} cerró ajustes sin guardar cambios")
        self.destroy()
    
    def _ver_cambios(self):
        """Muestra la ventana de cambios."""
        logger.info("Abriendo ventana de cambios desde ajustes")
        try:
            mostrar_ventana_cambios(self)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el registro de cambios:\n{e}", parent=self)
            logger.error(f"Error abriendo changelog: {e}", exc_info=True)
    
    def _abrir_ayuda(self):
        """Abre el manual de usuario."""
        logger.info("Abriendo manual de usuario desde ajustes")
        try:
            self.app.mostrar_manual_usuario()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el manual:\n{e}", parent=self)
            logger.error(f"Error abriendo manual: {e}", exc_info=True)
    
    def _on_apply(self):
        """Aplica los cambios sin cerrar la ventana."""
        logger.info(f"Usuario {self.username} aplicando ajustes sin cerrar")
        
        if not self._save_settings():
            return
        
        self.has_changes = False
        self.title("⚙️ Ajustes del Usuario")
        messagebox.showinfo("Ajustes Aplicados", 
                          "Los cambios se han guardado correctamente.\n"
                          "Algunos cambios (tema/modo) se aplicarán al reiniciar.",
                          parent=self)
    
    def _on_save(self):
        """Guarda los cambios y cierra la ventana."""
        logger.info(f"Usuario {self.username} guardando ajustes y cerrando")
        
        if not self._save_settings():
            return
        
        # Mostrar mensaje si cambió tema/modo
        tema_cambio = self.user_settings.get("theme") != self.original_settings.get("theme")
        modo_cambio = self.user_settings.get("appearance_mode") != self.original_settings.get("appearance_mode")
        
        if tema_cambio or modo_cambio:
            messagebox.showinfo("Ajustes Guardados", 
                              "Los cambios de tema y modo se aplicarán al reiniciar la aplicación.",
                              parent=self)
        
        self.destroy()
    
    def _save_settings(self):
        """Guarda la configuración actual. Retorna True si tuvo éxito."""
        try:
            # Recolectar configuración
            config = self._collect_current_settings()
            
            # Actualizar user_settings
            self.user_settings.update(config)
            
            # Guardar a archivo
            from app import save_user_settings
            ok = save_user_settings(self.user_settings, self.username)
            
            if not ok:
                messagebox.showerror("Error", "No se pudieron guardar los ajustes.", parent=self)
                return False
            
            # Actualizar aplicación
            self.app.user_settings = self.user_settings.copy()
            
            # Exponer globalmente
            try:
                import app
                app.USER_SETTINGS = self.user_settings
            except Exception:
                pass
            
            # Redibujar listado si cambió compact mode
            try:
                self.app.mostrar_lista_rma()
            except Exception:
                pass
            
            # Actualizar credenciales en BD
            self._update_credentials_db()
            
            logger.info(f"Ajustes guardados correctamente para usuario {self.username}")
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar ajustes:\n{e}", parent=self)
            logger.error(f"Error guardando ajustes: {e}", exc_info=True)
            return False
    
    def _collect_current_settings(self):
        """Recolecta la configuración actual de todos los widgets."""
        # Obtener archivo del tema
        tema_seleccionado = self.tema_menu.get()
        archivo_tema = self.app.tema_display_a_archivo(tema_seleccionado)
        
        # Obtener modo
        modo_seleccionado = self.modo_menu.get()
        appearance_mode = "light" if modo_seleccionado == "Claro" else "dark"
        
        config = {
            "date_format": self.date_menu.get(),
            "show_tooltips": self.var_tooltips.get(),
            "compact_mode": self.var_compact.get(),
            "icon_size": self.var_icon_size.get(),
            "theme": f"themes/{archivo_tema}",
            "appearance_mode": appearance_mode,
            "notificaciones_sonoras": self.var_sonido.get(),
            "notificar_al_iniciar": self.var_notif_inicio.get(),
            "dias_anticipacion_vencimiento": self.var_dias_vencimiento.get(),
            "dias_notificar_sin_gestionar": self.var_dias_sin_gestionar.get(),
            "volumen_notificaciones": self.var_volumen.get(),
            "tiene_firma": self.var_tiene_firma.get(),
            "modo_debug": self.var_modo_debug.get()
        }
        
        return config
    
    def _apply_imported_settings(self, config):
        """Aplica configuración importada a los widgets."""
        try:
            # General
            if "date_format" in config:
                self.date_menu.set(config["date_format"])
            if "show_tooltips" in config:
                self.var_tooltips.set(config["show_tooltips"])
            if "compact_mode" in config:
                self.var_compact.set(config["compact_mode"])
            if "icon_size" in config:
                self.var_icon_size.set(config["icon_size"])
                self.icon_label.configure(text=f"{config['icon_size']} px")
            
            # Apariencia
            if "theme" in config:
                tema_archivo = config["theme"].replace("themes/", "")
                tema_display = self.app.archivo_a_tema_display(tema_archivo)
                self.tema_menu.set(tema_display)
            if "appearance_mode" in config:
                modo = "Claro" if config["appearance_mode"] == "light" else "Oscuro"
                self.modo_menu.set(modo)
            
            # Notificaciones
            if "notificaciones_sonoras" in config:
                self.var_sonido.set(config["notificaciones_sonoras"])
            if "notificar_al_iniciar" in config:
                self.var_notif_inicio.set(config["notificar_al_iniciar"])
            if "dias_anticipacion_vencimiento" in config:
                self.var_dias_vencimiento.set(config["dias_anticipacion_vencimiento"])
                self.label_dias_venc.configure(text=f"{config['dias_anticipacion_vencimiento']} días")
            if "dias_notificar_sin_gestionar" in config:
                self.var_dias_sin_gestionar.set(config["dias_notificar_sin_gestionar"])
                self.label_dias_sin.configure(text=f"{config['dias_notificar_sin_gestionar']} días")
            if "volumen_notificaciones" in config:
                self.var_volumen.set(config["volumen_notificaciones"])
                self.label_volumen.configure(text=f"{config['volumen_notificaciones']}%")
            
            # Avanzado
            if "modo_debug" in config:
                self.var_modo_debug.set(config["modo_debug"])
            
            logger.debug("Configuración importada aplicada a widgets")
        except Exception as e:
            logger.error(f"Error aplicando configuración importada: {e}", exc_info=True)
    
    def _update_credentials_db(self):
        """Actualiza email y contraseña en la base de datos."""
        try:
            email_val = self.entry_email.get().strip()
            pw = self.entry_password.get()
            pw2 = self.entry_password2.get()
            
            conn, cursor = self.app.master.conectar_db()
            if not conn:
                return
            
            try:
                # Asegurar que columna email existe
                cursor.execute("PRAGMA table_info('usuarios')")
                cols = [r[1] for r in cursor.fetchall()]
                if 'email' not in cols:
                    try:
                        cursor.execute("ALTER TABLE usuarios ADD COLUMN email TEXT")
                        logger.info("Columna 'email' añadida a tabla usuarios")
                    except Exception:
                        pass
                
                # Actualizar email
                if email_val and self._validate_email():
                    cursor.execute("UPDATE usuarios SET email = ? WHERE nombre_usuario = ?", 
                                 (email_val, self.username))
                    logger.info(f"Email actualizado para usuario {self.username}")
                
                # Actualizar contraseña
                if pw:
                    if pw != pw2:
                        messagebox.showerror("Error", "Las contraseñas no coinciden.", parent=self)
                        return
                    if len(pw) < 8:
                        messagebox.showerror("Error", "La contraseña debe tener al menos 8 caracteres.", parent=self)
                        return
                    
                    hashed = bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt())
                    cursor.execute("UPDATE usuarios SET password_hash = ? WHERE nombre_usuario = ?", 
                                 (hashed.decode('utf-8'), self.username))
                    logger.info(f"Contraseña actualizada para usuario {self.username}")
                
                conn.commit()
                
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
                    
        except Exception as e:
            logger.error(f"Error actualizando credenciales en BD: {e}", exc_info=True)
