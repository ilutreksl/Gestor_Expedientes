"""
lib/rich_text_editor.py
Editor de texto enriquecido para el campo Observaciones Técnicas.
Soporta: negrita, cursiva, subrayado, tamaño de fuente, color de fuente,
inserción de imágenes (desde archivo y desde adjuntos Backblaze B2).

Almacenamiento: JSON serializado en el campo obs_tecnica de rma_maestro.
Compatibilidad hacia atrás: texto plano existente se carga sin formato.
"""

import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox
import customtkinter as ctk
import json
import base64
import io
import os
import tempfile
import threading

try:
    from PIL import Image, ImageTk
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

# ── Constantes ────────────────────────────────────────────────────────────────
FONT_SIZES       = [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36]
DEFAULT_SIZE     = 12
DEFAULT_FAMILY   = "Verdana Pro"
FONT_FAMILIES    = [
    "Verdana Pro",
    "Aptos",
    "Segoe UI",
    "Arial",
    "Calibri",
    "Cambria",
    "Comic Sans MS",
    "Consolas",
    "Courier New",
    "Georgia",
    "Helvetica",
    "Impact",
    "Tahoma",
    "Times New Roman",
    "Trebuchet MS",
    "Verdana",
]
MAX_IMAGE_WIDTH  = 800
MAX_IMAGE_HEIGHT = 600
THUMBNAIL_SIZE   = (130, 100)
JSON_MARKER      = '"version"'


class RichTextEditor(tk.Frame):
    """
    Widget editor de texto enriquecido embebible en CustomTkinter.

    Uso:
        editor = RichTextEditor(
            parent,
            get_adjuntos_fn=self._get_adjuntos_imagenes,   # opcional
            get_b2_client_fn=get_b2_client,                 # opcional
            b2_root_folder=B2_ROOT_FOLDER,                  # opcional
            normalizar_ruta_b2_fn=normalizar_ruta_b2,       # opcional
        )
        editor.pack(fill="both", expand=True)

        json_str = editor.get_content()      # para guardar en BD
        plain    = editor.get_plain_text()   # para PDF/búsqueda
        editor.set_content(raw)              # cargar (JSON o texto plano)
    """

    def __init__(self, parent,
                 get_adjuntos_fn=None,
                 get_b2_client_fn=None,
                 b2_root_folder=None,
                 normalizar_ruta_b2_fn=None,
                 usar_b2_fn=None,
                 modo_expandido=False,
                 **kwargs):
        height = kwargs.pop("height", 16)
        super().__init__(parent, **kwargs)

        self._get_adjuntos_fn      = get_adjuntos_fn
        self._get_b2_client_fn     = get_b2_client_fn
        self._b2_root_folder       = b2_root_folder
        self._normalizar_ruta_b2   = normalizar_ruta_b2_fn
        self._usar_b2_fn           = usar_b2_fn
        self._modo_expandido       = modo_expandido

        self._image_refs  = []
        self._image_data  = {}
        self._temp_files  = []
        self._saved_sel   = None
        self._current_color   = "#000000"
        self._current_bgcolor = None
        self._current_size    = DEFAULT_SIZE
        self._current_family  = DEFAULT_FAMILY

        self._build_toolbar()
        if modo_expandido:
            self._build_toolbar_avanzada()
        self._build_text_area(height)
        self._configure_tags()
        self.bind("<Destroy>", self._cleanup_temps)

    # ──────────────────────────────────────────────────────────────────────────
    # Tema
    # ──────────────────────────────────────────────────────────────────────────
    def _theme(self):
        try:
            dark = ctk.get_appearance_mode() == "Dark"
        except Exception:
            dark = False
        if dark:
            return dict(tb="#2b2b2b", btn="#3d3d3d", fg="#ffffff",
                        act="#4d4d4d", txt_bg="#1a1a1a", txt_fg="#ffffff",
                        sel="#4a4a8a", ins="#ffffff")
        return dict(tb="#e0e0e0", btn="#d0d0d0", fg="#1a1a1a",
                    act="#c0c0c0", txt_bg="#ffffff", txt_fg="#1a1a1a",
                    sel="#aaccff", ins="#000000")

    # ──────────────────────────────────────────────────────────────────────────
    # Construcción UI
    # ──────────────────────────────────────────────────────────────────────────
    def _build_toolbar(self):
        t = self._theme()
        toolbar = tk.Frame(self, bg=t["tb"], pady=3)
        toolbar.pack(fill="x", side="top")

        base = dict(bg=t["btn"], fg=t["fg"], activebackground=t["act"],
                    activeforeground=t["fg"], relief="flat", bd=0,
                    padx=6, pady=2, cursor="hand2",
                    font=("Segoe UI", 9))

        def btn(parent, text, cmd, **extra):
            kw = {**base, **extra}
            b = tk.Button(parent, text=text, command=cmd, **kw)
            b.pack(side="left", padx=2)
            return b

        def sep():
            tk.Frame(toolbar, width=1, bg="#888").pack(
                side="left", fill="y", padx=4, pady=2)

        # Formato de texto
        btn(toolbar, "N", self._toggle_bold,
            font=("Segoe UI", 9, "bold"))
        btn(toolbar, "I", self._toggle_italic,
            font=("Segoe UI", 9, "italic"))
        btn(toolbar, "S̲", self._toggle_underline)
        sep()

        # Familia de fuente
        tk.Label(toolbar, text="Fuente:", bg=t["tb"], fg=t["fg"],
                 font=("Segoe UI", 8)).pack(side="left", padx=(4, 1))
        self._family_var = tk.StringVar(value=DEFAULT_FAMILY)
        family_cb = tk.OptionMenu(toolbar, self._family_var,
                                  *FONT_FAMILIES,
                                  command=self._change_family)
        family_cb.config(bg=t["btn"], fg=t["fg"], activebackground=t["act"],
                         activeforeground=t["fg"], relief="flat", bd=0,
                         highlightthickness=0, font=("Segoe UI", 9), width=14)
        family_cb["menu"].config(bg=t["btn"], fg=t["fg"])
        family_cb.pack(side="left", padx=2)
        family_cb.bind("<ButtonPress>", lambda e: self._save_selection())
        sep()

        # Tamaño
        tk.Label(toolbar, text="Tam:", bg=t["tb"], fg=t["fg"],
                 font=("Segoe UI", 8)).pack(side="left", padx=(4, 1))
        self._size_var = tk.StringVar(value=str(DEFAULT_SIZE))
        om = tk.OptionMenu(toolbar, self._size_var,
                           *[str(s) for s in FONT_SIZES],
                           command=self._change_size)
        om.config(bg=t["btn"], fg=t["fg"], activebackground=t["act"],
                  activeforeground=t["fg"], relief="flat", bd=0,
                  highlightthickness=0, font=("Segoe UI", 9), width=3)
        om["menu"].config(bg=t["btn"], fg=t["fg"])
        om.pack(side="left", padx=2)
        om.bind("<ButtonPress>", lambda e: self._save_selection())
        sep()
        self._color_btn = tk.Button(
            toolbar, text="A", width=2, command=self._pick_color,
            bg=t["btn"], fg=self._current_color,
            activebackground=t["act"], relief="flat", bd=0,
            padx=6, pady=2, cursor="hand2",
            font=("Segoe UI", 9, "bold"))
        self._color_btn.pack(side="left", padx=2)
        tk.Label(toolbar, text="Color", bg=t["tb"], fg=t["fg"],
                 font=("Segoe UI", 8)).pack(side="left", padx=(0, 4))
        sep()

        # Imágenes
        if PILLOW_AVAILABLE:
            btn(toolbar, "🖼 Imagen", self._insert_image_from_file)
            if self._get_adjuntos_fn is not None:
                btn(toolbar, "📎 Desde adjuntos",
                    self._insert_image_from_adjuntos)
        else:
            tk.Label(toolbar, text="(instala Pillow para imágenes)",
                     bg=t["tb"], fg="#ff8800",
                     font=("Segoe UI", 8)).pack(side="left", padx=4)
        sep()

        btn(toolbar, "✕ Limpiar formato", self._clear_format)

        # Expandir — alineado a la derecha
        tk.Frame(toolbar, bg=t["tb"]).pack(side="left", fill="x", expand=True)
        sep()
        btn(toolbar, "⛶ Expandir", self._abrir_ventana_expandida)

    def _build_toolbar_avanzada(self):
        """Segunda barra de herramientas — solo visible en modo expandido."""
        t = self._theme()
        toolbar2 = tk.Frame(self, bg=t["tb"], pady=3)
        toolbar2.pack(fill="x", side="top")

        base = dict(bg=t["btn"], fg=t["fg"], activebackground=t["act"],
                    activeforeground=t["fg"], relief="flat", bd=0,
                    padx=6, pady=2, cursor="hand2",
                    font=("Segoe UI", 9))

        def btn(parent, text, cmd, **extra):
            kw = {**base, **extra}
            b = tk.Button(parent, text=text, command=cmd, **kw)
            b.pack(side="left", padx=2)
            return b

        def sep():
            tk.Frame(toolbar2, width=1, bg="#888").pack(
                side="left", fill="y", padx=4, pady=2)

        # ── Color de fondo (resaltado) ────────────────────────────────────────
        self._bgcolor_btn = tk.Button(
            toolbar2, text="▌A", width=3, command=self._pick_bgcolor,
            bg=t["btn"], fg=t["fg"],
            activebackground=t["act"], relief="flat", bd=0,
            padx=6, pady=2, cursor="hand2",
            font=("Segoe UI", 9, "bold"))
        self._bgcolor_btn.pack(side="left", padx=2)
        tk.Label(toolbar2, text="Resaltado", bg=t["tb"], fg=t["fg"],
                 font=("Segoe UI", 8)).pack(side="left", padx=(0, 2))

        btn(toolbar2, "✕ Sin resaltado", self._clear_bgcolor)
        sep()

        # ── Fluorescentes rápidos ─────────────────────────────────────────────
        tk.Label(toolbar2, text="🖊", bg=t["tb"], fg=t["fg"],
                 font=("Segoe UI", 9)).pack(side="left", padx=(4, 1))
        FLUORES = [
            ("Amarillo",  "#FFFF00", "#000000"),
            ("Verde",     "#00FF7F", "#000000"),
            ("Cian",      "#00FFFF", "#000000"),
            ("Rosa",      "#FF69B4", "#000000"),
            ("Naranja",   "#FFA500", "#000000"),
        ]
        for nombre, bg_col, fg_col in FLUORES:
            tk.Button(
                toolbar2, text=f"  {nombre[:3]}  ",
                bg=bg_col, fg=fg_col,
                activebackground=bg_col, activeforeground=fg_col,
                relief="flat", bd=1, padx=4, pady=1,
                cursor="hand2", font=("Segoe UI", 8),
                command=lambda c=bg_col: self._apply_bgcolor(c)
            ).pack(side="left", padx=1)
        sep()

        # ── Alineación ────────────────────────────────────────────────────────
        tk.Label(toolbar2, text="Alinear:", bg=t["tb"], fg=t["fg"],
                 font=("Segoe UI", 8)).pack(side="left", padx=(4, 1))
        btn(toolbar2, "⬅ Izq",    lambda: self._set_align("left"))
        btn(toolbar2, "≡ Centro", lambda: self._set_align("center"))
        btn(toolbar2, "➡ Der",    lambda: self._set_align("right"))
        sep()

        # ── Tachado ───────────────────────────────────────────────────────────
        btn(toolbar2, "S̶ Tachado", self._toggle_strikethrough)
        sep()

        # ── Sangría ───────────────────────────────────────────────────────────
        tk.Label(toolbar2, text="Sangría:", bg=t["tb"], fg=t["fg"],
                 font=("Segoe UI", 8)).pack(side="left", padx=(4, 1))
        btn(toolbar2, "→ Aumentar", self._indent_increase)
        btn(toolbar2, "← Reducir",  self._indent_decrease)

    def _build_text_area(self, height):
        t = self._theme()
        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True)

        self.text = tk.Text(
            frame,
            wrap="word",
            height=height,
            font=(DEFAULT_FAMILY, DEFAULT_SIZE),
            bg=t["txt_bg"], fg=t["txt_fg"],
            insertbackground=t["ins"],
            selectbackground=t["sel"],
            relief="flat",
            padx=8, pady=6,
            undo=True,
            spacing3=2,
        )
        sb = tk.Scrollbar(frame, command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)

        # Atajos de teclado
        self.text.bind("<Control-b>", lambda e: (self._toggle_bold(),   "break")[1])
        self.text.bind("<Control-B>", lambda e: (self._toggle_bold(),   "break")[1])
        self.text.bind("<Control-i>", lambda e: (self._toggle_italic(),  "break")[1])
        self.text.bind("<Control-I>", lambda e: (self._toggle_italic(),  "break")[1])
        self.text.bind("<Control-u>", lambda e: (self._toggle_underline(),"break")[1])
        self.text.bind("<Control-U>", lambda e: (self._toggle_underline(),"break")[1])
        self.text.bind("<Control-z>", lambda e: (self.text.edit_undo(),  "break")[1])
        self.text.bind("<Control-y>", lambda e: (self.text.edit_redo(),  "break")[1])

        # ── Copiar/Pegar mejorado ──────────────────────────────────────────
        # Ctrl+C y Ctrl+X: comportamiento nativo de tk.Text (ya funciona)
        # Ctrl+V: interceptamos para limpiar texto del portapapeles antes de pegar
        self.text.bind("<Control-v>", self._on_paste)
        self.text.bind("<Control-V>", self._on_paste)
        # Clic derecho: menú contextual con copiar/pegar/cortar
        self.text.bind("<Button-3>", self._context_menu)

    def _configure_tags(self):
        self.text.tag_configure("bold",          font=(DEFAULT_FAMILY, DEFAULT_SIZE, "bold"))
        self.text.tag_configure("italic",        font=(DEFAULT_FAMILY, DEFAULT_SIZE, "italic"))
        self.text.tag_configure("underline",     underline=True)
        self.text.tag_configure("strikethrough", overstrike=True)

    # ──────────────────────────────────────────────────────────────────────────
    # Copiar / Pegar / Menú contextual
    # ──────────────────────────────────────────────────────────────────────────
    def _on_paste(self, event=None):
        """
        Pega texto plano desde el portapapeles aplicando el formato activo.
        Elimina caracteres de control extraños que algunos programas añaden.
        """
        try:
            text = self.text.clipboard_get()
        except tk.TclError:
            return "break"   # portapapeles vacío o no texto

        # Eliminar \r (retornos de carro de Windows/Outlook)
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Si hay selección, reemplazarla
        try:
            self.text.delete("sel.first", "sel.last")
        except tk.TclError:
            pass

        insert_idx = self.text.index(tk.INSERT)
        self.text.insert(tk.INSERT, text)
        end_idx = self.text.index(tk.INSERT)

        # Aplicar formato activo al texto pegado
        if self._current_color != "#000000":
            tag = self._ensure_color_tag(self._current_color)
            self.text.tag_add(tag, insert_idx, end_idx)
        if self._current_size != DEFAULT_SIZE:
            tag = self._ensure_size_tag(self._current_size)
            self.text.tag_add(tag, insert_idx, end_idx)
        if self._current_family != DEFAULT_FAMILY:
            tag = self._ensure_family_tag(self._current_family)
            self.text.tag_add(tag, insert_idx, end_idx)

        return "break"   # evitar el paste doble nativo de Tk

    def _context_menu(self, event):
        """Menú contextual con Cortar / Copiar / Pegar."""
        t = self._theme()
        menu = tk.Menu(self.text, tearoff=0,
                       bg=t["btn"], fg=t["fg"],
                       activebackground=t["act"],
                       activeforeground=t["fg"],
                       relief="flat", bd=0)

        menu.add_command(label="✂  Cortar",   command=lambda: self.text.event_generate("<<Cut>>"))
        menu.add_command(label="⎘  Copiar",   command=lambda: self.text.event_generate("<<Copy>>"))
        menu.add_command(label="⎗  Pegar",    command=self._on_paste)
        menu.add_separator()
        menu.add_command(label="Seleccionar todo",
                         command=lambda: self.text.tag_add("sel", "1.0", "end"))

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ──────────────────────────────────────────────────────────────────────────
    # Tags helpers
    # ──────────────────────────────────────────────────────────────────────────
    def _has_tag(self, tag):
        try:
            s = self.text.index("sel.first")
            e = self.text.index("sel.last")
        except tk.TclError:
            return False
        for i in range(0, len(self.text.tag_ranges(tag)), 2):
            r = self.text.tag_ranges(tag)
            if (self.text.compare(r[i], "<=", s) and
                    self.text.compare(r[i+1], ">=", e)):
                return True
        return False

    def _apply_or_remove_tag(self, tag):
        try:
            s = self.text.index("sel.first")
            e = self.text.index("sel.last")
        except tk.TclError:
            return
        if self._has_tag(tag):
            self.text.tag_remove(tag, s, e)
        else:
            self.text.tag_add(tag, s, e)

    def _ensure_size_tag(self, size):
        tag = f"size_{size}"
        try:
            self.text.tag_cget(tag, "font")
        except tk.TclError:
            self.text.tag_configure(tag, font=(DEFAULT_FAMILY, size))
        return tag

    def _ensure_family_tag(self, family):
        tag = f"family_{family.replace(' ', '_')}"
        try:
            self.text.tag_cget(tag, "font")
        except tk.TclError:
            self.text.tag_configure(tag, font=(family, DEFAULT_SIZE))
        return tag

    def _ensure_color_tag(self, color):
        tag = f"color_{color.lstrip('#')}"
        try:
            self.text.tag_cget(tag, "foreground")
        except tk.TclError:
            self.text.tag_configure(tag, foreground=color)
        return tag

    # ──────────────────────────────────────────────────────────────────────────
    # Acciones barra de herramientas
    # ──────────────────────────────────────────────────────────────────────────
    def _toggle_bold(self):
        self._apply_or_remove_tag("bold");      self.text.focus_set()

    def _toggle_italic(self):
        self._apply_or_remove_tag("italic");    self.text.focus_set()

    def _toggle_underline(self):
        self._apply_or_remove_tag("underline"); self.text.focus_set()

    def _save_selection(self):
        """Guarda la selección actual antes de que el foco pase a otro widget."""
        try:
            s = self.text.index("sel.first")
            e = self.text.index("sel.last")
            self._saved_sel = (s, e)
        except tk.TclError:
            self._saved_sel = None

    def _change_family(self, value):
        self._current_family = value
        # Restaurar selección guardada si el OptionMenu la quitó
        sel = getattr(self, '_saved_sel', None)
        try:
            s = self.text.index("sel.first")
            e = self.text.index("sel.last")
        except tk.TclError:
            if sel:
                s, e = sel
            else:
                self.text.focus_set()
                return
        for fam in FONT_FAMILIES:
            self.text.tag_remove(f"family_{fam.replace(' ', '_')}", s, e)
        self.text.tag_add(self._ensure_family_tag(value), s, e)
        self.text.focus_set()

    def _change_size(self, value):
        sel = getattr(self, '_saved_sel', None)
        try:
            size = int(value)
            self._current_size = size
            try:
                s = self.text.index("sel.first")
                e = self.text.index("sel.last")
            except tk.TclError:
                if sel:
                    s, e = sel
                else:
                    self.text.focus_set()
                    return
            for sz in FONT_SIZES:
                self.text.tag_remove(f"size_{sz}", s, e)
            self.text.tag_add(self._ensure_size_tag(size), s, e)
        except (ValueError,):
            pass
        self.text.focus_set()

    def _pick_color(self):
        color = colorchooser.askcolor(
            color=self._current_color,
            title="Seleccionar color de fuente")
        if color and color[1]:
            self._current_color = color[1]
            self._color_btn.config(fg=self._current_color)
            try:
                s = self.text.index("sel.first")
                e = self.text.index("sel.last")
                self.text.tag_add(self._ensure_color_tag(self._current_color), s, e)
            except tk.TclError:
                pass   # sin selección: solo cambia el color activo
        self.text.focus_set()

    # ── Color de fondo (resaltado) ────────────────────────────────────────────
    def _pick_bgcolor(self):
        color = colorchooser.askcolor(
            color=self._current_bgcolor or "#FFFF00",
            title="Seleccionar color de resaltado")
        if color and color[1]:
            self._apply_bgcolor(color[1])
        self.text.focus_set()

    def _apply_bgcolor(self, color):
        self._current_bgcolor = color
        # Actualizar indicador visual del botón
        if hasattr(self, '_bgcolor_btn'):
            self._bgcolor_btn.config(bg=color,
                                     fg="#000000" if self._luminancia(color) > 0.4 else "#ffffff")
        try:
            s = self.text.index("sel.first")
            e = self.text.index("sel.last")
            tag = self._ensure_bgcolor_tag(color)
            self.text.tag_add(tag, s, e)
        except tk.TclError:
            pass
        self.text.focus_set()

    def _clear_bgcolor(self):
        """Quita el resaltado de la selección actual."""
        try:
            s = self.text.index("sel.first")
            e = self.text.index("sel.last")
        except tk.TclError:
            s, e = "1.0", "end"
        for tag in self.text.tag_names():
            if tag.startswith("bgcolor_"):
                self.text.tag_remove(tag, s, e)
        if hasattr(self, '_bgcolor_btn'):
            t = self._theme()
            self._bgcolor_btn.config(bg=t["btn"], fg=t["fg"])
        self._current_bgcolor = None
        self.text.focus_set()

    def _luminancia(self, hex_color):
        """Devuelve luminancia aproximada (0-1) para elegir fg blanco o negro."""
        try:
            r = int(hex_color[1:3], 16) / 255
            g = int(hex_color[3:5], 16) / 255
            b = int(hex_color[5:7], 16) / 255
            return 0.299 * r + 0.587 * g + 0.114 * b
        except Exception:
            return 0.5

    def _ensure_bgcolor_tag(self, color):
        tag = f"bgcolor_{color.lstrip('#')}"
        try:
            self.text.tag_cget(tag, "background")
        except tk.TclError:
            self.text.tag_configure(tag, background=color)
        return tag

    # ── Alineación ────────────────────────────────────────────────────────────
    def _set_align(self, justify):
        """Aplica alineación al párrafo o párrafos seleccionados."""
        try:
            s = self.text.index("sel.first linestart")
            e = self.text.index("sel.last lineend")
        except tk.TclError:
            s = self.text.index("insert linestart")
            e = self.text.index("insert lineend")
        # Quitar alineaciones previas
        for j in ("left", "center", "right"):
            self.text.tag_remove(f"align_{j}", s, e)
        tag = f"align_{justify}"
        try:
            self.text.tag_cget(tag, "justify")
        except tk.TclError:
            self.text.tag_configure(tag, justify=justify)
        self.text.tag_add(tag, s, e)
        self.text.focus_set()

    # ── Tachado ───────────────────────────────────────────────────────────────
    def _toggle_strikethrough(self):
        self._apply_or_remove_tag("strikethrough")
        self.text.focus_set()

    # ── Sangría ───────────────────────────────────────────────────────────────
    _INDENT_STEP = 30   # píxeles por nivel de sangría

    def _indent_increase(self):
        self._change_indent(+self._INDENT_STEP)

    def _indent_decrease(self):
        self._change_indent(-self._INDENT_STEP)

    def _change_indent(self, delta):
        try:
            s = self.text.index("sel.first linestart")
            e = self.text.index("sel.last lineend")
        except tk.TclError:
            s = self.text.index("insert linestart")
            e = self.text.index("insert lineend")

        # Obtener sangría actual sumando todos los tags de sangría activos
        current = 0
        for tag in self.text.tag_names(s):
            if tag.startswith("indent_"):
                try:
                    current = int(tag[7:])
                except ValueError:
                    pass

        new_indent = max(0, current + delta)

        # Quitar tags de sangría anteriores en el rango
        for tag in self.text.tag_names():
            if tag.startswith("indent_"):
                self.text.tag_remove(tag, s, e)

        if new_indent > 0:
            tag = f"indent_{new_indent}"
            try:
                self.text.tag_cget(tag, "lmargin1")
            except tk.TclError:
                self.text.tag_configure(tag,
                                        lmargin1=new_indent,
                                        lmargin2=new_indent)
            self.text.tag_add(tag, s, e)
        self.text.focus_set()

    def _clear_format(self):
        try:
            s = self.text.index("sel.first")
            e = self.text.index("sel.last")
        except tk.TclError:
            s, e = "1.0", "end"
        for tag in self.text.tag_names():
            self.text.tag_remove(tag, s, e)
        self._family_var.set(DEFAULT_FAMILY)
        self._size_var.set(str(DEFAULT_SIZE))
        if hasattr(self, '_bgcolor_btn'):
            t = self._theme()
            self._bgcolor_btn.config(bg=t["btn"], fg=t["fg"])
        self._current_bgcolor = None
        self.text.focus_set()

    # ──────────────────────────────────────────────────────────────────────────
    # Inserción de imágenes
    # ──────────────────────────────────────────────────────────────────────────
    def _insert_pil_image(self, pil_img, nombre_adjunto=None):
        """
        Inserta una imagen PIL en el editor.
        Si nombre_adjunto se proporciona, guarda referencia al adjunto en lugar de base64.
        """
        if not PILLOW_AVAILABLE:
            return

        if pil_img.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", pil_img.size, (255, 255, 255))
            try:
                bg.paste(pil_img, mask=pil_img.split()[-1])
            except Exception:
                bg.paste(pil_img)
            pil_img = bg

        w, h = pil_img.size
        if w > MAX_IMAGE_WIDTH or h > MAX_IMAGE_HEIGHT:
            ratio = min(MAX_IMAGE_WIDTH / w, MAX_IMAGE_HEIGHT / h)
            pil_img = pil_img.resize(
                (max(1, int(w*ratio)), max(1, int(h*ratio))),
                Image.LANCZOS)

        photo = ImageTk.PhotoImage(pil_img)
        self._image_refs.append(photo)

        # Insertar en posición del cursor
        self.text.focus_force()
        self.text.update_idletasks()
        try:
            idx = self.text.index(tk.INSERT)
            if idx in ("0.0", ""):
                idx = "end-1c"
        except Exception:
            idx = "end-1c"

        self.text.image_create(idx, image=photo, padx=4, pady=4)
        # La imagen ocupa exactamente idx a idx+1c tras image_create
        pos_img = self.text.index(idx)
        self.text.mark_set(tk.INSERT, f"{pos_img}+1c")

        img_id = f"img_{len(self._image_data)}"
        if nombre_adjunto:
            self._image_data[img_id] = {
                "nombre": nombre_adjunto,
                "width": pil_img.width,
                "height": pil_img.height
            }
        else:
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            self._image_data[img_id] = {
                "b64": b64,
                "width": pil_img.width,
                "height": pil_img.height
            }
        # Aplicar tag con start Y end (sin end, tag_add no hace nada en tk.Text)
        self.text.tag_add(img_id, pos_img, f"{pos_img}+1c")

    def _insert_image_from_file(self):
        if not PILLOW_AVAILABLE:
            messagebox.showwarning("Pillow no disponible", "Instala Pillow:\npip install Pillow")
            return
        paths = filedialog.askopenfilenames(
            title="Seleccionar imágenes (puedes elegir varias)",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp"),
                       ("Todos", "*.*")])
        if not paths:
            return
        errores = []
        for path in paths:
            try:
                img = Image.open(path); img.load(); img = img.copy()
                self._insert_pil_image(img)  # sin nombre_adjunto → base64 temporal
            except Exception as e:
                errores.append(f"{os.path.basename(path)}: {e}")
        if errores:
            messagebox.showwarning("Error cargando imágenes", "\n".join(errores))

    def _insert_image_from_adjuntos(self):
        """Abre ventana con miniaturas descargando desde B2 si es necesario."""
        if not PILLOW_AVAILABLE:
            messagebox.showwarning("Pillow no disponible",
                                   "Instala Pillow:\npip install Pillow")
            return
        if not self._get_adjuntos_fn:
            messagebox.showinfo("No disponible",
                                "Esta función requiere el expediente abierto.")
            return

        adjuntos = self._get_adjuntos_fn()
        ext_img  = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"}
        imagenes = [a for a in adjuntos
                    if os.path.splitext(a.get("nombre", ""))[1].lower() in ext_img]

        if not imagenes:
            messagebox.showinfo("Sin adjuntos de imagen",
                                "No hay imágenes adjuntas en este expediente.")
            return

        self._abrir_selector_adjuntos(imagenes)

    # ── Descarga B2 ──────────────────────────────────────────────────────────
    def _descargar_adjunto_b2_temp(self, ruta_relativa):
        """
        Descarga un adjunto de Backblaze B2 a un fichero temporal.
        Devuelve la ruta local del temporal, o None si falla.
        """
        if not self._get_b2_client_fn:
            return None
        try:
            from b2sdk.v2.exception import B2Error
        except ImportError:
            B2Error = Exception

        try:
            b2_api, bucket = self._get_b2_client_fn()
            if not b2_api or not bucket:
                return None

            if self._normalizar_ruta_b2 and self._b2_root_folder:
                ruta_b2 = self._normalizar_ruta_b2(
                    f"{self._b2_root_folder}/{ruta_relativa}")
            else:
                ruta_b2 = ruta_relativa

            nombre   = os.path.basename(ruta_relativa)
            ext      = os.path.splitext(nombre)[1]
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=ext, prefix="rte_img_")
            os.close(tmp_fd)

            downloaded = bucket.download_file_by_name(ruta_b2)
            downloaded.save_to(tmp_path)

            self._temp_files.append(tmp_path)   # limpiar al destruir
            return tmp_path

        except Exception as e:
            print(f"[RichTextEditor] Error descargando B2: {e}")
            return None

    def _descargar_adjunto_local(self, ruta_relativa, adjuntos_root):
        """Devuelve ruta local si existe."""
        ruta = os.path.join(adjuntos_root, ruta_relativa)
        return ruta if os.path.exists(ruta) else None

    def _insertar_desde_adjunto(self, adj):
        """Descarga imagen e inserta en el editor con referencia al adjunto."""
        ruta_rel = adj.get("ruta_relativa", "")
        nombre   = adj.get("nombre", "")
        tipo_alm = adj.get("tipo_almacenamiento", "local")
        adj_root = adj.get("adjuntos_root", "")
        if tipo_alm in ("backblaze", "b2") or (self._usar_b2_fn and self._usar_b2_fn()):
            local = self._descargar_adjunto_b2_temp(ruta_rel)
        else:
            local = self._descargar_adjunto_local(ruta_rel, adj_root)
        if local and os.path.exists(local):
            try:
                img = Image.open(local); img.load(); img = img.copy()
                self.after(0, lambda i=img, n=nombre:
                           self._insert_pil_image(i, nombre_adjunto=n))
            except Exception as ex:
                self.after(0, lambda: messagebox.showerror(
                    "Error", f"No se pudo cargar la imagen:\n{ex}"))
        else:
            self.after(0, lambda: messagebox.showerror(
                "Error", f"No se pudo descargar: {nombre}"))

    # ── Selector de adjuntos ─────────────────────────────────────────────────
    def _abrir_selector_adjuntos(self, imagenes):
        t = self._theme()
        win = tk.Toplevel(self)
        win.title("Seleccionar imágenes de adjuntos")
        win.geometry("720x520")
        win.grab_set()
        win.resizable(True, True)
        win.configure(bg=t["tb"])

        tk.Label(win,
                 text="Clic para seleccionar · Doble clic para insertar una · "
                      "'Insertar seleccionadas' para varias",
                 bg=t["tb"], fg=t["fg"], font=("Segoe UI", 9)).pack(pady=(10, 4))

        # Área scroll
        cf = tk.Frame(win, bg=t["tb"])
        cf.pack(fill="both", expand=True, padx=10, pady=4)
        canvas = tk.Canvas(cf, bg=t["tb"], highlightthickness=0)
        sb2 = tk.Scrollbar(cf, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb2.set)
        sb2.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg=t["tb"])
        canvas.create_window((0, 0), window=inner, anchor="nw")

        # Barra inferior
        bar = tk.Frame(win, bg=t["tb"], pady=6)
        bar.pack(side="bottom", fill="x", padx=10)
        sel_lbl = tk.Label(bar, text="0 seleccionadas",
                           bg=t["tb"], fg=t["fg"], font=("Segoe UI", 9))
        sel_lbl.pack(side="left", padx=4)
        btn_ins = tk.Button(bar, text="✓ Insertar seleccionadas",
                            bg="#2a7a2a", fg="#ffffff", activebackground="#1e5e1e",
                            relief="flat", bd=0, padx=14, pady=4, cursor="hand2",
                            font=("Segoe UI", 9, "bold"), state="disabled")
        btn_ins.pack(side="right", padx=4)
        tk.Button(bar, text="Cancelar", command=win.destroy,
                  bg=t["tb"], fg=t["fg"], activebackground=t["act"],
                  relief="flat", bd=0, padx=10, pady=4,
                  cursor="hand2", font=("Segoe UI", 9)).pack(side="right", padx=4)

        MAX_COLS = 4
        seleccionados = {}

        def _update_btn():
            n = len(seleccionados)
            sel_lbl.config(text=f"{n} seleccionada{'s' if n != 1 else ''}")
            btn_ins.config(state="normal" if n > 0 else "disabled")

        def _toggle(adj, lbl):
            k = adj["nombre"]
            if k in seleccionados:
                del seleccionados[k]
                lbl.config(relief="solid", bd=1, bg=t["tb"])
            else:
                seleccionados[k] = adj
                lbl.config(relief="solid", bd=3, bg="#4a8a4a")
            _update_btn()

        def _place_thumb(adj, img_bytes):
            """Crea miniatura y la coloca — SIEMPRE en hilo principal."""
            try:
                pil_t = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                pil_t.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
                photo = ImageTk.PhotoImage(pil_t)  # hilo principal ✓
            except Exception:
                return

            c = col_ref[0]
            r = row_ref[0]
            col_ref[0] += 1
            if col_ref[0] >= MAX_COLS:
                col_ref[0] = 0
                row_ref[0] += 1

            nombre = adj.get("nombre", "")
            cell = tk.Frame(inner, bg=t["tb"], padx=4, pady=4)
            cell.grid(row=r, column=c, padx=6, pady=6)
            lbl = tk.Label(cell, image=photo, bg=t["tb"],
                           cursor="hand2", relief="solid", bd=1)
            lbl.image = photo  # referencia para evitar GC
            lbl.pack()
            tk.Label(cell,
                     text=(nombre[:18] + "…" if len(nombre) > 18 else nombre),
                     bg=t["tb"], fg=t["fg"], font=("Segoe UI", 7)).pack()
            lbl.bind("<Button-1>",        lambda e, a=adj, l=lbl: _toggle(a, l))
            lbl.bind("<Double-Button-1>",  lambda e, a=adj: _doble_clic(a))
            inner.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _doble_clic(adj):
            win.destroy()
            threading.Thread(target=lambda: self._insertar_desde_adjunto(adj),
                             daemon=True).start()

        def _insertar_seleccionadas():
            adjs = list(seleccionados.values())
            win.destroy()
            def _do():
                for adj in adjs:
                    self._insertar_desde_adjunto(adj)
            threading.Thread(target=_do, daemon=True).start()

        btn_ins.config(command=_insertar_seleccionadas)

        col_ref = [0]
        row_ref = [0]

        def _cargar_miniatura(adj):
            """Descarga imagen — hilo SECUNDARIO. Envía bytes al principal."""
            ruta_rel = adj.get("ruta_relativa", "")
            tipo_alm = adj.get("tipo_almacenamiento", "local")
            adj_root = adj.get("adjuntos_root", "")
            if tipo_alm in ("backblaze", "b2") or (
                    self._usar_b2_fn and self._usar_b2_fn()):
                local = self._descargar_adjunto_b2_temp(ruta_rel)
            else:
                local = self._descargar_adjunto_local(ruta_rel, adj_root)
            if not local or not os.path.exists(local):
                return
            try:
                with open(local, "rb") as f:
                    img_bytes = f.read()
                # Enviar bytes al hilo principal para crear ImageTk
                if win.winfo_exists():
                    win.after(0, lambda b=img_bytes, a=adj: _place_thumb(a, b))
            except Exception:
                pass

        threading.Thread(
            target=lambda: [_cargar_miniatura(a) for a in imagenes],
            daemon=True).start()

    # ──────────────────────────────────────────────────────────────────────────
    # Serialización / Deserialización
    # ──────────────────────────────────────────────────────────────────────────
    def get_content(self):
        """
        Serializa usando text.dump() — un solo recorrido que devuelve
        texto, imágenes y tags en orden, sin ningún tag_ranges ni
        comparación de posiciones.
        """
        try:
            items = self.text.dump("1.0", "end-1c",
                                   text=True, image=True, tag=True)
        except Exception:
            return ""

        # Construir mapa photo_name → datos de imagen
        # usando los nombres de PhotoImage guardados en _image_refs
        # Los PhotoImage en tk tienen nombre "pyimageN" — str(photo) devuelve ese nombre
        photo_to_data = {}
        for img_id, data in self._image_data.items():
            # Buscar la foto en _image_refs que corresponde a este img_id
            # La foto fue añadida a _image_refs en orden de inserción
            # El índice del img_id es el número al final: img_0, img_1...
            try:
                n = int(img_id.split("_")[1])
                if n < len(self._image_refs):
                    photo_name = str(self._image_refs[n])
                    photo_to_data[photo_name] = data
            except (ValueError, IndexError):
                pass

        segments = []
        active_tags = set()
        run_chars = []
        run_tags = frozenset()

        def _tags_to_attrs(tags):
            size = DEFAULT_SIZE; color = None; family = None
            bgcolor = None; align = None; indent = 0
            for tag in tags:
                if tag.startswith("size_"):
                    try: size = int(tag[5:])
                    except ValueError: pass
                elif tag.startswith("color_"):   color   = "#" + tag[6:]
                elif tag.startswith("family_"):  family  = tag[7:].replace("_", " ")
                elif tag.startswith("bgcolor_"): bgcolor = "#" + tag[8:]
                elif tag.startswith("align_"):   align   = tag[6:]
                elif tag.startswith("indent_"):
                    try: indent = int(tag[7:])
                    except ValueError: pass
            return dict(
                bold="bold" in tags, italic="italic" in tags,
                underline="underline" in tags, strikethrough="strikethrough" in tags,
                size=size, color=color, family=family,
                bgcolor=bgcolor, align=align, indent=indent)

        def _flush():
            nonlocal run_chars, run_tags
            if not run_chars:
                return
            attrs = _tags_to_attrs(run_tags)
            segments.append({"type": "text", "content": "".join(run_chars), **attrs})
            run_chars = []
            run_tags = frozenset()

        for item in items:
            kind = item[0]
            if kind == "tagon":
                tag = item[1]
                if not tag.startswith("img_") and tag != "sel":
                    new_tags = active_tags | {tag}
                    cur = frozenset(t for t in active_tags
                                    if not t.startswith("img_") and t != "sel")
                    nxt = frozenset(t for t in new_tags
                                    if not t.startswith("img_") and t != "sel")
                    if run_chars and nxt != run_tags:
                        _flush()
                        run_tags = nxt
                    elif not run_chars:
                        run_tags = nxt
                    active_tags.add(tag)

            elif kind == "tagoff":
                tag = item[1]
                active_tags.discard(tag)
                if not tag.startswith("img_") and tag != "sel":
                    nxt = frozenset(t for t in active_tags
                                    if not t.startswith("img_") and t != "sel")
                    if run_chars and nxt != run_tags:
                        _flush()
                        run_tags = nxt

            elif kind == "text":
                run_chars.extend(list(item[1]))

            elif kind == "image":
                _flush()
                photo_name = item[1]
                data = photo_to_data.get(photo_name)
                if data:
                    if "nombre" in data:
                        segments.append({"type": "image_ref",
                                         "nombre": data["nombre"],
                                         "width": data["width"],
                                         "height": data["height"]})
                    elif "b64" in data:
                        segments.append({"type": "image",
                                         "b64": data["b64"],
                                         "width": data["width"],
                                         "height": data["height"]})
                else:
                    print(f"[RTE] imagen no encontrada: {photo_name}, disponibles: {list(photo_to_data.keys())}")

        _flush()
        if not segments:
            return ""
        return json.dumps({"version": 1, "segments": segments}, ensure_ascii=False)

    def get_plain_text(self):
        """Texto plano para PDF/búsqueda (sin imágenes ni formato)."""
        return self.text.get("1.0", "end-1c").replace("\ufffc", "[IMAGEN]").strip()

    def set_content(self, raw):
        """Carga contenido: JSON propio o texto plano (retrocompatibilidad)."""
        self.text.delete("1.0", "end")
        self._image_refs.clear()
        self._image_data.clear()

        if not raw:
            return
        raw = str(raw).strip()

        if JSON_MARKER in raw:
            try:
                data = json.loads(raw)
                if data.get("version") == 1:
                    self._load_from_json(data)
                    return
            except (json.JSONDecodeError, KeyError):
                pass

        self.text.insert("1.0", raw)   # texto plano

    def _load_from_json(self, data):
        for seg in data.get("segments", []):
            tipo = seg.get("type")

            if tipo == "image_ref":
                # Imagen referenciada desde adjunto B2
                if not PILLOW_AVAILABLE:
                    self.text.insert("end", "[IMAGEN]\n")
                    continue
                nombre = seg.get("nombre", "")
                if not nombre:
                    continue
                try:
                    # Buscar la ruta relativa del adjunto por nombre
                    local = self._resolver_adjunto_por_nombre(nombre)
                    if local and os.path.exists(local):
                        img = Image.open(local)
                        img.load(); img = img.copy()
                        # Insertar directamente (estamos en hilo principal)
                        self._insert_pil_image_en_pos(img, nombre_adjunto=nombre)
                    else:
                        self.text.insert("end", f"[Imagen no disponible: {nombre}]\n")
                except Exception as e:
                    self.text.insert("end", f"[Error imagen {nombre}: {e}]\n")

            elif tipo == "image":
                # Imagen con base64 (desde archivo local, retrocompatibilidad)
                if not PILLOW_AVAILABLE:
                    self.text.insert("end", "[IMAGEN]\n")
                    continue
                try:
                    img = Image.open(
                        io.BytesIO(base64.b64decode(seg["b64"]))
                    ).convert("RGB")
                    wg, hg = seg.get("width"), seg.get("height")
                    if wg and hg and (img.width != wg or img.height != hg):
                        img = img.resize((wg, hg), Image.LANCZOS)
                    self._insert_pil_image_en_pos(img)
                except Exception as e:
                    self.text.insert("end", f"[Error imagen: {e}]\n")

            elif tipo == "text":
                content = seg.get("content", "")
                s = self.text.index("end-1c")
                self.text.insert("end", content)
                e = self.text.index("end-1c")
                if seg.get("bold"):          self.text.tag_add("bold",          s, e)
                if seg.get("italic"):        self.text.tag_add("italic",        s, e)
                if seg.get("underline"):     self.text.tag_add("underline",     s, e)
                if seg.get("strikethrough"): self.text.tag_add("strikethrough", s, e)
                sz = seg.get("size", DEFAULT_SIZE)
                if sz != DEFAULT_SIZE:
                    self.text.tag_add(self._ensure_size_tag(sz), s, e)
                col = seg.get("color")
                if col:
                    self.text.tag_add(self._ensure_color_tag(col), s, e)
                fam = seg.get("family")
                if fam:
                    self.text.tag_add(self._ensure_family_tag(fam), s, e)
                bgcol = seg.get("bgcolor")
                if bgcol:
                    self.text.tag_add(self._ensure_bgcolor_tag(bgcol), s, e)
                align = seg.get("align")
                if align:
                    tag_a = f"align_{align}"
                    try:
                        self.text.tag_cget(tag_a, "justify")
                    except tk.TclError:
                        self.text.tag_configure(tag_a, justify=align)
                    self.text.tag_add(tag_a, s, e)
                indent = seg.get("indent", 0)
                if indent:
                    tag_i = f"indent_{indent}"
                    try:
                        self.text.tag_cget(tag_i, "lmargin1")
                    except tk.TclError:
                        self.text.tag_configure(tag_i, lmargin1=indent, lmargin2=indent)
                    self.text.tag_add(tag_i, s, e)

    def _resolver_adjunto_por_nombre(self, nombre):
        """
        Resuelve la ruta local de un adjunto dado su nombre de archivo.
        Descarga desde B2 si es necesario.
        """
        if not self._get_adjuntos_fn:
            return None
        try:
            adjuntos = self._get_adjuntos_fn()
            for adj in adjuntos:
                if adj.get("nombre") == nombre:
                    ruta_rel = adj.get("ruta_relativa", "")
                    tipo_alm = adj.get("tipo_almacenamiento", "local")
                    adj_root = adj.get("adjuntos_root", "")
                    if tipo_alm in ("backblaze", "b2") or (
                            self._usar_b2_fn and self._usar_b2_fn()):
                        return self._descargar_adjunto_b2_temp(ruta_rel)
                    else:
                        return self._descargar_adjunto_local(ruta_rel, adj_root)
        except Exception as e:
            print(f"[RichTextEditor] error resolviendo adjunto {nombre}: {e}")
        return None

    def _insert_pil_image_en_pos(self, pil_img, nombre_adjunto=None):
        """
        Inserta imagen al final del contenido (para uso en _load_from_json).
        No depende del cursor INSERT.
        """
        if not PILLOW_AVAILABLE:
            return
        if pil_img.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", pil_img.size, (255, 255, 255))
            try:
                bg.paste(pil_img, mask=pil_img.split()[-1])
            except Exception:
                bg.paste(pil_img)
            pil_img = bg

        w, h = pil_img.size
        if w > MAX_IMAGE_WIDTH or h > MAX_IMAGE_HEIGHT:
            ratio = min(MAX_IMAGE_WIDTH / w, MAX_IMAGE_HEIGHT / h)
            pil_img = pil_img.resize(
                (max(1, int(w*ratio)), max(1, int(h*ratio))), Image.LANCZOS)

        photo = ImageTk.PhotoImage(pil_img)
        self._image_refs.append(photo)

        # Insertar al final usando posición explícita (no cursor)
        idx = self.text.index("end-1c")
        self.text.image_create(idx, image=photo, padx=4, pady=4)
        pos_img = self.text.index(idx)

        img_id = f"img_{len(self._image_data)}"
        if nombre_adjunto:
            self._image_data[img_id] = {
                "nombre": nombre_adjunto,
                "width": pil_img.width,
                "height": pil_img.height
            }
        else:
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            self._image_data[img_id] = {
                "b64": b64, "width": pil_img.width, "height": pil_img.height}

        self.text.tag_add(img_id, pos_img, f"{pos_img}+1c")

    # ──────────────────────────────────────────────────────────────────────────
    # Limpieza temporales
    # ──────────────────────────────────────────────────────────────────────────
    def _cleanup_temps(self, event=None):
        for p in self._temp_files:
            try:
                if os.path.exists(p):
                    os.unlink(p)
            except Exception:
                pass

    # ──────────────────────────────────────────────────────────────────────────
    # API pública de conveniencia
    # ──────────────────────────────────────────────────────────────────────────
    def clear(self):
        self.text.delete("1.0", "end")
        self._image_refs.clear()
        self._image_data.clear()

    def focus_set(self):
        self.text.focus_set()

    def get(self, *args):
        """Alias de get_plain_text() para compatibilidad con código existente."""
        return self.get_plain_text()

    # ──────────────────────────────────────────────────────────────────────────
    # Ventana expandida
    # ──────────────────────────────────────────────────────────────────────────
    def _abrir_ventana_expandida(self):
        """Abre el contenido del editor en una ventana grande independiente."""
        _VentanaExpandida(self)


class _VentanaExpandida(tk.Toplevel):
    """
    Ventana modal grande que contiene un RichTextEditor completo.
    Al pulsar 'Guardar y cerrar' vuelca el contenido al editor original.
    Al pulsar 'Cancelar' cierra sin modificar el original.
    """

    def __init__(self, editor_origen: RichTextEditor):
        super().__init__(editor_origen)
        self._editor_origen = editor_origen

        self.title("Observaciones Técnicas — Editor expandido")
        self.geometry("1200x750")
        self.minsize(800, 500)
        self.resizable(True, True)

        # Centrar en pantalla
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - 1200) // 2
        y = (sh - 750) // 2
        self.geometry(f"1200x750+{x}+{y}")

        # Modal: bloquea la ventana principal mientras está abierta
        self.grab_set()
        self.focus_set()

        self._build_ui()

        # Cargar contenido actual del editor original
        contenido_actual = editor_origen.get_content()
        self._editor.set_content(contenido_actual)

        # Interceptar cierre con la X para preguntar
        self.protocol("WM_DELETE_WINDOW", self._on_cancelar)

    def _build_ui(self):
        t = self._editor_origen._theme()

        self.configure(bg=t["tb"])

        # ── Barra inferior con botones ────────────────────────────────────────
        bar = tk.Frame(self, bg=t["tb"], pady=6)
        bar.pack(side="bottom", fill="x", padx=12)

        btn_cfg = dict(
            bg="#2a7a2a", fg="#ffffff",
            activebackground="#1e5e1e", activeforeground="#ffffff",
            relief="flat", bd=0, padx=20, pady=6,
            cursor="hand2", font=("Segoe UI", 10, "bold")
        )
        tk.Button(bar, text="💾  Guardar y cerrar",
                  command=self._on_guardar, **btn_cfg).pack(side="right", padx=(6, 0))

        btn_cfg_cancel = dict(
            bg="#7a2a2a", fg="#ffffff",
            activebackground="#5e1e1e", activeforeground="#ffffff",
            relief="flat", bd=0, padx=20, pady=6,
            cursor="hand2", font=("Segoe UI", 10)
        )
        tk.Button(bar, text="✕  Cancelar",
                  command=self._on_cancelar, **btn_cfg_cancel).pack(side="right")

        tk.Label(bar,
                 text="Los cambios se aplicarán al expediente al pulsar 'Guardar y cerrar'",
                 bg=t["tb"], fg=t["fg"],
                 font=("Segoe UI", 9)).pack(side="left", padx=4)

        # ── Editor expandido ──────────────────────────────────────────────────
        o = self._editor_origen
        self._editor = RichTextEditor(
            self,
            get_adjuntos_fn       = o._get_adjuntos_fn,
            get_b2_client_fn      = o._get_b2_client_fn,
            b2_root_folder        = o._b2_root_folder,
            normalizar_ruta_b2_fn = o._normalizar_ruta_b2,
            usar_b2_fn            = o._usar_b2_fn,
            modo_expandido        = True,
            height                = 30,
        )
        self._editor.pack(fill="both", expand=True, padx=8, pady=(8, 4))

    def _on_guardar(self):
        """Vuelca el contenido del editor expandido al editor original y cierra."""
        contenido = self._editor.get_content()
        self._editor_origen.set_content(contenido)
        self.grab_release()
        self.destroy()

    def _on_cancelar(self):
        """Cierra sin modificar el editor original, pidiendo confirmación si hay cambios."""
        contenido_actual  = self._editor.get_content()
        contenido_original = self._editor_origen.get_content()

        if contenido_actual != contenido_original:
            from tkinter import messagebox as _mb
            respuesta = _mb.askyesnocancel(
                "¿Descartar cambios?",
                "Hay cambios sin guardar en el editor expandido.\n\n"
                "¿Guardar y cerrar?\n"
                "(No = cerrar sin guardar, Cancelar = volver al editor)",
                parent=self
            )
            if respuesta is True:       # Sí → guardar y cerrar
                self._on_guardar()
                return
            elif respuesta is None:     # Cancelar → volver al editor
                return
            # respuesta is False → cerrar sin guardar

        self.grab_release()
        self.destroy()
