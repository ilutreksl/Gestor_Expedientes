"""
Sistema de Avisos - Gestión de notificaciones para usuarios
Permite al administrador crear avisos que se muestran al iniciar la aplicación
"""

import os
import json
import customtkinter as ctk
from pathlib import Path
from tkinter import messagebox


class AvisosManager:
    """Gestor de avisos del sistema"""
    
    def __init__(self, root_path):
        """
        Inicializa el gestor de avisos
        
        Args:
            root_path: Ruta raíz de la aplicación
        """
        self.root_path = Path(root_path)
        self.avisos_file = self.root_path / "Avisos.md"
        self.settings_file = self.root_path / "user_settings.json"
        
        # Crear archivo de avisos si no existe
        if not self.avisos_file.exists():
            self.avisos_file.write_text(
                "# Bienvenido al Sistema de Gestión de Expedientes\n\n"
                "Este es un mensaje de ejemplo.\n\n"
                "El administrador puede modificar este texto para enviar avisos a todos los usuarios.",
                encoding='utf-8'
            )
    
    def is_aviso_activo(self):
        """
        Verifica si el aviso está activo
        
        Returns:
            bool: True si el aviso debe mostrarse
        """
        try:
            if not self.settings_file.exists():
                return False
            
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            return settings.get('global', {}).get('mostrar_aviso', False)
        except Exception as e:
            print(f"Error al leer estado del aviso: {e}")
            return False
    
    def set_aviso_activo(self, activo):
        """
        Activa o desactiva el aviso
        
        Args:
            activo: True para activar, False para desactivar
        """
        try:
            settings = {}
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            
            if 'global' not in settings:
                settings['global'] = {}
            
            settings['global']['mostrar_aviso'] = activo
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error al guardar estado del aviso: {e}")
            return False
    
    def get_contenido_aviso(self):
        """
        Obtiene el contenido del aviso
        
        Returns:
            str: Contenido del archivo Avisos.md
        """
        try:
            if not self.avisos_file.exists():
                return ""
            
            return self.avisos_file.read_text(encoding='utf-8')
        except Exception as e:
            print(f"Error al leer aviso: {e}")
            return ""
    
    def set_contenido_aviso(self, contenido):
        """
        Guarda el contenido del aviso
        
        Args:
            contenido: Texto a guardar en Avisos.md
        """
        try:
            self.avisos_file.write_text(contenido, encoding='utf-8')
            return True
        except Exception as e:
            print(f"Error al guardar aviso: {e}")
            return False
    
    def mostrar_aviso_popup(self, parent):
        """
        Muestra la ventana emergente con el aviso para usuarios
        
        Args:
            parent: Ventana padre
        """
        if not self.is_aviso_activo():
            return
        
        contenido = self.get_contenido_aviso()
        if not contenido.strip():
            return
        
        # Crear ventana emergente
        popup = ctk.CTkToplevel(parent)
        popup.title("📢 Información")
        popup.geometry("700x500")
        popup.resizable(True, True)
        
        # Centrar ventana
        popup.transient(parent)
        popup.grab_set()
        
        # Configurar para que aparezca al frente
        popup.attributes('-topmost', True)
        popup.lift()
        popup.focus_force()
        
        # Frame principal
        main_frame = ctk.CTkFrame(popup)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header con icono y título
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 15))
        
        icon_label = ctk.CTkLabel(
            header_frame,
            text="📢",
            font=ctk.CTkFont(size=32)
        )
        icon_label.pack(side="left", padx=(0, 10))
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="Aviso del sistema",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(side="left")
        
        # Separador
        separator = ctk.CTkFrame(main_frame, height=2, fg_color="gray")
        separator.pack(fill="x", pady=(0, 15))
        
        # Frame con scroll para el contenido
        content_frame = ctk.CTkScrollableFrame(
            main_frame,
            fg_color="transparent"
        )
        content_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # Procesar contenido Markdown simple
        self._renderizar_markdown(content_frame, contenido)
        
        # Botón de cerrar
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x")
        
        close_btn = ctk.CTkButton(
            btn_frame,
            text="✓ Aceptar",
            command=popup.destroy,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        close_btn.pack(side="right")
        
        # Centrar la ventana en la pantalla
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (popup.winfo_width() // 2)
        y = (popup.winfo_screenheight() // 2) - (popup.winfo_height() // 2)
        popup.geometry(f"+{x}+{y}")
    
    def _renderizar_markdown(self, parent, contenido):
        """
        Renderiza contenido Markdown de forma simple
        
        Args:
            parent: Frame contenedor
            contenido: Texto en formato Markdown
        """
        lineas = contenido.split('\n')
        
        for linea in lineas:
            linea = linea.rstrip()
            
            # Encabezados
            if linea.startswith('# '):
                label = ctk.CTkLabel(
                    parent,
                    text=linea[2:],
                    font=ctk.CTkFont(size=24, weight="bold"),
                    anchor="w"
                )
                label.pack(fill="x", pady=(10, 5))
            
            elif linea.startswith('## '):
                label = ctk.CTkLabel(
                    parent,
                    text=linea[3:],
                    font=ctk.CTkFont(size=20, weight="bold"),
                    anchor="w"
                )
                label.pack(fill="x", pady=(8, 4))
            
            elif linea.startswith('### '):
                label = ctk.CTkLabel(
                    parent,
                    text=linea[4:],
                    font=ctk.CTkFont(size=16, weight="bold"),
                    anchor="w"
                )
                label.pack(fill="x", pady=(6, 3))
            
            # Listas
            elif linea.startswith('- ') or linea.startswith('* '):
                label = ctk.CTkLabel(
                    parent,
                    text="  • " + linea[2:],
                    font=ctk.CTkFont(size=13),
                    anchor="w"
                )
                label.pack(fill="x", pady=2)
            
            # Líneas vacías
            elif not linea.strip():
                spacer = ctk.CTkFrame(parent, height=5, fg_color="transparent")
                spacer.pack(fill="x")
            
            # Texto normal
            else:
                label = ctk.CTkLabel(
                    parent,
                    text=linea,
                    font=ctk.CTkFont(size=13),
                    anchor="w",
                    wraplength=600,
                    justify="left"
                )
                label.pack(fill="x", pady=2)
    
    def mostrar_panel_admin(self, parent):
        """
        Muestra el panel de administración de avisos (solo para admin)
        
        Args:
            parent: Ventana padre
        """
        # Verificar si ya existe una ventana
        if hasattr(self, 'admin_window') and self.admin_window.winfo_exists():
            self.admin_window.focus()
            return
        
        self.admin_window = ctk.CTkToplevel(parent)
        self.admin_window.title("🔧 Administrar Avisos")
        self.admin_window.geometry("900x700")
        self.admin_window.resizable(True, True)
        
        # Configurar ventana
        self.admin_window.attributes('-topmost', True)
        self.admin_window.lift()
        self.admin_window.focus_force()
        self.admin_window.after(500, lambda: self.admin_window.attributes('-topmost', False))
        
        # Frame principal
        main_frame = ctk.CTkFrame(self.admin_window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 15))
        
        icon = ctk.CTkLabel(header_frame, text="🔧", font=ctk.CTkFont(size=28))
        icon.pack(side="left", padx=(0, 10))
        
        title = ctk.CTkLabel(
            header_frame,
            text="Administrar Avisos del Sistema",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(side="left")
        
        # Estado actual
        estado_actual = self.is_aviso_activo()
        estado_var = ctk.BooleanVar(value=estado_actual)
        
        estado_frame = ctk.CTkFrame(main_frame)
        estado_frame.pack(fill="x", pady=(0, 15))
        
        estado_check = ctk.CTkCheckBox(
            estado_frame,
            text="Mostrar aviso al iniciar la aplicación (todos los usuarios)",
            variable=estado_var,
            font=ctk.CTkFont(size=14, weight="bold"),
            checkbox_width=24,
            checkbox_height=24
        )
        estado_check.pack(padx=15, pady=15)
        
        # Instrucciones
        info_frame = ctk.CTkFrame(main_frame)
        info_frame.pack(fill="x", pady=(0, 10))
        
        info_label = ctk.CTkLabel(
            info_frame,
            text="ℹ️ El aviso se mostrará a todos los usuarios al iniciar la aplicación. "
                 "Puedes usar formato Markdown básico (títulos con #, listas con -, etc.)",
            font=ctk.CTkFont(size=12),
            wraplength=800,
            justify="left"
        )
        info_label.pack(padx=15, pady=10)
        
        # Separador
        sep = ctk.CTkFrame(main_frame, height=2, fg_color="gray")
        sep.pack(fill="x", pady=(0, 15))
        
        # Editor de texto
        editor_label = ctk.CTkLabel(
            main_frame,
            text="Contenido del Aviso:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        editor_label.pack(fill="x", pady=(0, 5))
        
        editor_frame = ctk.CTkFrame(main_frame)
        editor_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        editor = ctk.CTkTextbox(
            editor_frame,
            font=ctk.CTkFont(size=12),
            wrap="word"
        )
        editor.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Cargar contenido actual
        contenido_actual = self.get_contenido_aviso()
        editor.insert("1.0", contenido_actual)
        
        # Botones
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x")
        
        def vista_previa():
            """Muestra vista previa del aviso"""
            # Guardar temporalmente
            contenido_temp = editor.get("1.0", "end-1c")
            contenido_original = self.get_contenido_aviso()
            estado_original = self.is_aviso_activo()
            
            self.set_contenido_aviso(contenido_temp)
            self.set_aviso_activo(True)
            
            # Mostrar preview
            self.mostrar_aviso_popup(self.admin_window)
            
            # Restaurar
            self.set_contenido_aviso(contenido_original)
            self.set_aviso_activo(estado_original)
        
        def guardar():
            """Guarda los cambios"""
            contenido = editor.get("1.0", "end-1c")
            activo = estado_var.get()
            
            if self.set_contenido_aviso(contenido) and self.set_aviso_activo(activo):
                messagebox.showinfo(
                    "Éxito",
                    "Aviso guardado correctamente.\n\n" +
                    ("El aviso se mostrará a todos los usuarios al iniciar." if activo else "El aviso está desactivado."),
                    parent=self.admin_window
                )
            else:
                messagebox.showerror(
                    "Error",
                    "No se pudo guardar el aviso.",
                    parent=self.admin_window
                )
        
        btn_preview = ctk.CTkButton(
            btn_frame,
            text="👁️ Vista Previa",
            command=vista_previa,
            font=ctk.CTkFont(size=13),
            height=35
        )
        btn_preview.pack(side="left", padx=(0, 10))
        
        btn_cancel = ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            command=self.admin_window.destroy,
            font=ctk.CTkFont(size=13),
            height=35,
            fg_color="#dc2626",
            hover_color="#b91c1c"
        )
        btn_cancel.pack(side="right", padx=(10, 0))
        
        btn_save = ctk.CTkButton(
            btn_frame,
            text="💾 Guardar Cambios",
            command=guardar,
            font=ctk.CTkFont(size=13, weight="bold"),
            height=35
        )
        btn_save.pack(side="right")
        
        # Centrar ventana
        self.admin_window.update_idletasks()
        x = (self.admin_window.winfo_screenwidth() // 2) - (self.admin_window.winfo_width() // 2)
        y = (self.admin_window.winfo_screenheight() // 2) - (self.admin_window.winfo_height() // 2)
        self.admin_window.geometry(f"+{x}+{y}")
