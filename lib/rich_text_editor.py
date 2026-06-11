"""
lib/rich_text_editor.py
Editor de texto enriquecido para Observaciones Técnicas.

Correcciones v3:
- Miniaturas: ImageTk.PhotoImage se crea en el hilo principal (fix blanco)
- Imágenes al guardar desde expandido: se transfieren por JSON (b64), no por referencia
- Selección múltiple de imágenes desde adjuntos
- Redimensión de imágenes con doble clic
"""

import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog
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
DEFAULT_SIZE     = 11
DEFAULT_FAMILY   = "Segoe UI"
FONT_FAMILIES    = [
    "Segoe UI", "Arial", "Calibri", "Cambria", "Comic Sans MS",
    "Consolas", "Courier New", "Georgia", "Helvetica", "Impact",
    "Tahoma", "Times New Roman", "Trebuchet MS", "Verdana",
]
MAX_IMAGE_WIDTH  = 800
MAX_IMAGE_HEIGHT = 600
THUMBNAIL_SIZE   = (130, 100)
JSON_MARKER      = '"version"'


class RichTextEditor(tk.Frame):
    """
    Widget editor de texto enriquecido embebible en CustomTkinter.

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

        # _image_data: {img_id -> {"b64": str, "width": int, "height": int, "photo": PhotoImage}}
        self._image_data  = {}
        self._temp_files  = []
        self._img_counter = 0          # contador global para img_id únicos

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
                    padx=6, pady=2, cursor="hand2", font=("Segoe UI", 9))

        def btn(parent, text, cmd, **extra):
            kw = {**base, **extra}
            b = tk.Button(parent, text=text, command=cmd, **kw)
            b.pack(side="left", padx=2)
            return b

        def sep():
            tk.Frame(toolbar, width=1, bg="#888").pack(
                side="left", fill="y", padx=4, pady=2)

        btn(toolbar, "N", self._toggle_bold,   font=("Segoe UI", 9, "bold"))
        btn(toolbar, "I", self._toggle_italic, font=("Segoe UI", 9, "italic"))
        btn(toolbar, "S̲", self._toggle_underline)
        sep()

        # Familia
        tk.Label(toolbar, text="Fuente:", bg=t["tb"], fg=t["fg"],
                 font=("Segoe UI", 8)).pack(side="left", padx=(4, 1))
        self._family_var = tk.StringVar(value=DEFAULT_FAMILY)
        om = tk.OptionMenu(toolbar, self._family_var, *FONT_FAMILIES,
                           command=self._change_family)
        om.config(bg=t["btn"], fg=t["fg"], activebackground=t["act"],
                  activeforeground=t["fg"], relief="flat", bd=0,
                  highlightthickness=0, font=("Segoe UI", 9), width=14)
        om["menu"].config(bg=t["btn"], fg=t["fg"])
        om.pack(side="left", padx=2)
        sep()

        # Tamaño
        tk.Label(toolbar, text="Tam:", bg=t["tb"], fg=t["fg"],
                 font=("Segoe UI", 8)).pack(side="left", padx=(4, 1))
        self._size_var = tk.StringVar(value=str(DEFAULT_SIZE))
        om2 = tk.OptionMenu(toolbar, self._size_var,
                            *[str(s) for s in FONT_SIZES],
                            command=self._change_size)
        om2.config(bg=t["btn"], fg=t["fg"], activebackground=t["act"],
                   activeforeground=t["fg"], relief="flat", bd=0,
                   highlightthickness=0, font=("Segoe UI", 9), width=3)
        om2["menu"].config(bg=t["btn"], fg=t["fg"])
        om2.pack(side="left", padx=2)
        sep()

        # Color fuente
        self._color_btn = tk.Button(
            toolbar, text="A", width=2, command=self._pick_color,
            bg=t["btn"], fg=self._current_color,
            activebackground=t["act"], relief="flat", bd=0,
            padx=6, pady=2, cursor="hand2", font=("Segoe UI", 9, "bold"))
        self._color_btn.pack(side="left", padx=2)
        tk.Label(toolbar, text="Color", bg=t["tb"], fg=t["fg"],
                 font=("Segoe UI", 8)).pack(side="left", padx=(0, 4))
        sep()

        # Imágenes
        if PILLOW_AVAILABLE:
            btn(toolbar, "🖼 Imagen", self._insert_image_from_file)
            if self._get_adjuntos_fn is not None:
                btn(toolbar, "📎 Desde adjuntos", self._insert_image_from_adjuntos)
        else:
            tk.Label(toolbar, text="(instala Pillow para imágenes)",
                     bg=t["tb"], fg="#ff8800",
                     font=("Segoe UI", 8)).pack(side="left", padx=4)
        sep()

        btn(toolbar, "✕ Limpiar formato", self._clear_format)

        # Expandir — a la derecha
        tk.Frame(toolbar, bg=t["tb"]).pack(side="left", fill="x", expand=True)
        sep()
        btn(toolbar, "⛶ Expandir", self._abrir_ventana_expandida)

    def _build_toolbar_avanzada(self):
        """Segunda barra — solo en modo expandido."""
        t = self._theme()
        toolbar2 = tk.Frame(self, bg=t["tb"], pady=3)
        toolbar2.pack(fill="x", side="top")

        base = dict(bg=t["btn"], fg=t["fg"], activebackground=t["act"],
                    activeforeground=t["fg"], relief="flat", bd=0,
                    padx=6, pady=2, cursor="hand2", font=("Segoe UI", 9))

        def btn(parent, text, cmd, **extra):
            kw = {**base, **extra}
            b = tk.Button(parent, text=text, command=cmd, **kw)
            b.pack(side="left", padx=2)
            return b

        def sep():
            tk.Frame(toolbar2, width=1, bg="#888").pack(
                side="left", fill="y", padx=4, pady=2)

        # Resaltado
        self._bgcolor_btn = tk.Button(
            toolbar2, text="▌A", width=3, command=self._pick_bgcolor,
            bg=t["btn"], fg=t["fg"], activebackground=t["act"],
            relief="flat", bd=0, padx=6, pady=2, cursor="hand2",
            font=("Segoe UI", 9, "bold"))
        self._bgcolor_btn.pack(side="left", padx=2)
        tk.Label(toolbar2, text="Resaltado", bg=t["tb"], fg=t["fg"],
                 font=("Segoe UI", 8)).pack(side="left", padx=(0, 2))
        btn(toolbar2, "✕ Sin resaltado", self._clear_bgcolor)
        sep()

        # Fluorescentes rápidos
        tk.Label(toolbar2, text="🖊", bg=t["tb"], fg=t["fg"],
                 font=("Segoe UI", 9)).pack(side="left", padx=(4, 1))
        for nombre, bg_col, fg_col in [
            ("Amar", "#FFFF00", "#000000"), ("Verde", "#00FF7F", "#000000"),
            ("Cian", "#00FFFF", "#000000"), ("Rosa", "#FF69B4", "#000000"),
            ("Nara", "#FFA500", "#000000"),
        ]:
            tk.Button(toolbar2, text=f" {nombre} ", bg=bg_col, fg=fg_col,
                      activebackground=bg_col, activeforeground=fg_col,
                      relief="flat", bd=1, padx=4, pady=1,
                      cursor="hand2", font=("Segoe UI", 8),
                      command=lambda c=bg_col: self._apply_bgcolor(c)
                      ).pack(side="left", padx=1)
        sep()

        # Alineación
        tk.Label(toolbar2, text="Alinear:", bg=t["tb"], fg=t["fg"],
                 font=("Segoe UI", 8)).pack(side="left", padx=(4, 1))
        btn(toolbar2, "⬅ Izq",    lambda: self._set_align("left"))
        btn(toolbar2, "≡ Centro", lambda: self._set_align("center"))
        btn(toolbar2, "➡ Der",    lambda: self._set_align("right"))
        sep()

        btn(toolbar2, "S̶ Tachado", self._toggle_strikethrough)
        sep()

        tk.Label(toolbar2, text="Sangría:", bg=t["tb"], fg=t["fg"],
                 font=("Segoe UI", 8)).pack(side="left", padx=(4, 1))
        btn(toolbar2, "→ Aumentar", self._indent_increase)
        btn(toolbar2, "← Reducir",  self._indent_decrease)

    def _build_text_area(self, height):
        t = self._theme()
        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True)

        self.text = tk.Text(
            frame, wrap="word", height=height,
            font=("Segoe UI", DEFAULT_SIZE),
            bg=t["txt_bg"], fg=t["txt_fg"],
            insertbackground=t["ins"], selectbackground=t["sel"],
            relief="flat", padx=8, pady=6, undo=True, spacing3=2,
        )
        sb = tk.Scrollbar(frame, command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)

        # Atajos
        self.text.bind("<Control-b>", lambda e: (self._toggle_bold(),    "break")[1])
        self.text.bind("<Control-B>", lambda e: (self._toggle_bold(),    "break")[1])
        self.text.bind("<Control-i>", lambda e: (self._toggle_italic(),  "break")[1])
        self.text.bind("<Control-I>", lambda e: (self._toggle_italic(),  "break")[1])
        self.text.bind("<Control-u>", lambda e: (self._toggle_underline(),"break")[1])
        self.text.bind("<Control-U>", lambda e: (self._toggle_underline(),"break")[1])
        self.text.bind("<Control-z>", lambda e: (self.text.edit_undo(),  "break")[1])
        self.text.bind("<Control-y>", lambda e: (self.text.edit_redo(),  "break")[1])
        self.text.bind("<Control-v>", self._on_paste)
        self.text.bind("<Control-V>", self._on_paste)
        self.text.bind("<Button-3>",  self._context_menu)
        # Doble clic sobre imagen → redimensionar
        self.text.bind("<Double-Button-1>", self._on_double_click_image)

    def _configure_tags(self):
        self.text.tag_configure("bold",          font=("Segoe UI", DEFAULT_SIZE, "bold"))
        self.text.tag_configure("italic",        font=("Segoe UI", DEFAULT_SIZE, "italic"))
        self.text.tag_configure("underline",     underline=True)
        self.text.tag_configure("strikethrough", overstrike=True)

    # ──────────────────────────────────────────────────────────────────────────
    # Copiar / Pegar / Menú contextual
    # ──────────────────────────────────────────────────────────────────────────
    def _on_paste(self, event=None):
        try:
            text = self.text.clipboard_get()
        except tk.TclError:
            return "break"
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        try:
            self.text.delete("sel.first", "sel.last")
        except tk.TclError:
            pass
        insert_idx = self.text.index(tk.INSERT)
        self.text.insert(tk.INSERT, text)
        end_idx = self.text.index(tk.INSERT)
        if self._current_color != "#000000":
            self.text.tag_add(self._ensure_color_tag(self._current_color), insert_idx, end_idx)
        if self._current_size != DEFAULT_SIZE:
            self.text.tag_add(self._ensure_size_tag(self._current_size), insert_idx, end_idx)
        if self._current_family != DEFAULT_FAMILY:
            self.text.tag_add(self._ensure_family_tag(self._current_family), insert_idx, end_idx)
        return "break"

    def _context_menu(self, event):
        t = self._theme()
        menu = tk.Menu(self.text, tearoff=0,
                       bg=t["btn"], fg=t["fg"],
                       activebackground=t["act"], activeforeground=t["fg"],
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
    # Redimensión de imagen con doble clic
    # ──────────────────────────────────────────────────────────────────────────
    def _on_double_click_image(self, event):
        """Si el doble clic cae sobre una imagen embebida, abre diálogo de redimensión."""
        idx = self.text.index(f"@{event.x},{event.y}")
        char = self.text.get(idx)
        if char != "\ufffc":
            return
        # Buscar el img_id de esta posición
        for img_id, data in self._image_data.items():
            ranges = self.text.tag_ranges(img_id)
            if ranges and self.text.compare(str(ranges[0]), "==", idx):
                self._abrir_dialogo_redimension(img_id, data)
                return "break"

    def _abrir_dialogo_redimension(self, img_id, data):
        """Ventana para redimensionar una imagen ya insertada."""
        if not PILLOW_AVAILABLE:
            return

        win = tk.Toplevel(self)
        win.title("Redimensionar imagen")
        win.resizable(False, False)
        win.grab_set()

        t = self._theme()
        win.configure(bg=t["tb"])

        orig_w = data["width"]
        orig_h = data["height"]

        tk.Label(win, text=f"Tamaño original: {orig_w} × {orig_h} px",
                 bg=t["tb"], fg=t["fg"], font=("Segoe UI", 9)).grid(
            row=0, column=0, columnspan=3, padx=16, pady=(12, 4))

        tk.Label(win, text="Ancho (px):", bg=t["tb"], fg=t["fg"],
                 font=("Segoe UI", 9)).grid(row=1, column=0, padx=12, pady=4, sticky="e")
        w_var = tk.StringVar(value=str(orig_w))
        e_w = tk.Entry(win, textvariable=w_var, width=8,
                       font=("Segoe UI", 9))
        e_w.grid(row=1, column=1, padx=4, pady=4)

        tk.Label(win, text="Alto (px):", bg=t["tb"], fg=t["fg"],
                 font=("Segoe UI", 9)).grid(row=2, column=0, padx=12, pady=4, sticky="e")
        h_var = tk.StringVar(value=str(orig_h))
        e_h = tk.Entry(win, textvariable=h_var, width=8,
                       font=("Segoe UI", 9))
        e_h.grid(row=2, column=1, padx=4, pady=4)

        # Mantener proporción
        prop_var = tk.BooleanVar(value=True)
        tk.Checkbutton(win, text="Mantener proporción",
                       variable=prop_var,
                       bg=t["tb"], fg=t["fg"],
                       selectcolor=t["btn"],
                       activebackground=t["tb"],
                       font=("Segoe UI", 9)).grid(
            row=3, column=0, columnspan=3, padx=12, pady=4)

        ratio = orig_w / orig_h if orig_h else 1

        def _on_w_change(*_):
            if prop_var.get():
                try:
                    new_w = int(w_var.get())
                    h_var.set(str(max(1, round(new_w / ratio))))
                except ValueError:
                    pass

        def _on_h_change(*_):
            if prop_var.get():
                try:
                    new_h = int(h_var.get())
                    w_var.set(str(max(1, round(new_h * ratio))))
                except ValueError:
                    pass

        e_w.bind("<FocusOut>", _on_w_change)
        e_w.bind("<Return>",   _on_w_change)
        e_h.bind("<FocusOut>", _on_h_change)
        e_h.bind("<Return>",   _on_h_change)

        # Porcentajes rápidos
        pct_frame = tk.Frame(win, bg=t["tb"])
        pct_frame.grid(row=4, column=0, columnspan=3, pady=4)
        tk.Label(pct_frame, text="Rápido:", bg=t["tb"], fg=t["fg"],
                 font=("Segoe UI", 8)).pack(side="left", padx=(0, 4))
        for pct in [25, 50, 75, 100, 150]:
            def _set_pct(p=pct):
                w_var.set(str(max(1, round(orig_w * p / 100))))
                h_var.set(str(max(1, round(orig_h * p / 100))))
            tk.Button(pct_frame, text=f"{pct}%",
                      bg=t["btn"], fg=t["fg"],
                      activebackground=t["act"],
                      relief="flat", bd=0, padx=6, pady=1,
                      cursor="hand2", font=("Segoe UI", 8),
                      command=_set_pct).pack(side="left", padx=2)

        def _aplicar():
            try:
                new_w = max(10, int(w_var.get()))
                new_h = max(10, int(h_var.get()))
            except ValueError:
                messagebox.showwarning("Valor inválido",
                                       "Introduce números enteros válidos.", parent=win)
                return

            try:
                img_bytes = base64.b64decode(data["b64"])
                pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)

                # Guardar nuevo b64
                buf = io.BytesIO()
                pil_img.save(buf, format="PNG")
                new_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

                # Crear nueva PhotoImage
                new_photo = ImageTk.PhotoImage(pil_img)

                # Localizar posición de la imagen en el texto
                ranges = self.text.tag_ranges(img_id)
                if not ranges:
                    win.destroy()
                    return
                pos = str(ranges[0])

                # Reemplazar imagen en el widget
                self.text.delete(pos)
                self.text.image_create(pos, image=new_photo, padx=4, pady=4)
                self.text.tag_add(img_id, pos)

                # Actualizar datos
                self._image_data[img_id] = {
                    "b64": new_b64, "width": new_w, "height": new_h,
                    "photo": new_photo
                }

                win.destroy()
            except Exception as ex:
                messagebox.showerror("Error", f"No se pudo redimensionar:\n{ex}", parent=win)

        btn_frame = tk.Frame(win, bg=t["tb"])
        btn_frame.grid(row=5, column=0, columnspan=3, pady=(8, 12))
        tk.Button(btn_frame, text="✓ Aplicar", command=_aplicar,
                  bg="#2a7a2a", fg="#ffffff",
                  activebackground="#1e5e1e", activeforeground="#ffffff",
                  relief="flat", bd=0, padx=16, pady=4,
                  cursor="hand2", font=("Segoe UI", 9, "bold")).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Cancelar", command=win.destroy,
                  bg=t["btn"], fg=t["fg"],
                  activebackground=t["act"],
                  relief="flat", bd=0, padx=16, pady=4,
                  cursor="hand2", font=("Segoe UI", 9)).pack(side="left", padx=6)

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

    def _ensure_bgcolor_tag(self, color):
        tag = f"bgcolor_{color.lstrip('#')}"
        try:
            self.text.tag_cget(tag, "background")
        except tk.TclError:
            self.text.tag_configure(tag, background=color)
        return tag

    # ──────────────────────────────────────────────────────────────────────────
    # Acciones barra principal
    # ──────────────────────────────────────────────────────────────────────────
    def _toggle_bold(self):
        self._apply_or_remove_tag("bold");       self.text.focus_set()

    def _toggle_italic(self):
        self._apply_or_remove_tag("italic");     self.text.focus_set()

    def _toggle_underline(self):
        self._apply_or_remove_tag("underline");  self.text.focus_set()

    def _change_family(self, value):
        self._current_family = value
        try:
            s = self.text.index("sel.first")
            e = self.text.index("sel.last")
            for fam in FONT_FAMILIES:
                self.text.tag_remove(f"family_{fam.replace(' ', '_')}", s, e)
            self.text.tag_add(self._ensure_family_tag(value), s, e)
        except tk.TclError:
            pass
        self.text.focus_set()

    def _change_size(self, value):
        try:
            size = int(value)
            self._current_size = size
            s = self.text.index("sel.first")
            e = self.text.index("sel.last")
            for sz in FONT_SIZES:
                self.text.tag_remove(f"size_{sz}", s, e)
            self.text.tag_add(self._ensure_size_tag(size), s, e)
        except (tk.TclError, ValueError):
            pass
        self.text.focus_set()

    def _pick_color(self):
        color = colorchooser.askcolor(color=self._current_color,
                                      title="Seleccionar color de fuente")
        if color and color[1]:
            self._current_color = color[1]
            self._color_btn.config(fg=self._current_color)
            try:
                s = self.text.index("sel.first")
                e = self.text.index("sel.last")
                self.text.tag_add(self._ensure_color_tag(self._current_color), s, e)
            except tk.TclError:
                pass
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
    # Acciones barra avanzada
    # ──────────────────────────────────────────────────────────────────────────
    def _pick_bgcolor(self):
        color = colorchooser.askcolor(color=self._current_bgcolor or "#FFFF00",
                                      title="Seleccionar color de resaltado")
        if color and color[1]:
            self._apply_bgcolor(color[1])
        self.text.focus_set()

    def _apply_bgcolor(self, color):
        self._current_bgcolor = color
        if hasattr(self, '_bgcolor_btn'):
            lum = self._luminancia(color)
            self._bgcolor_btn.config(bg=color,
                                     fg="#000000" if lum > 0.4 else "#ffffff")
        try:
            s = self.text.index("sel.first")
            e = self.text.index("sel.last")
            self.text.tag_add(self._ensure_bgcolor_tag(color), s, e)
        except tk.TclError:
            pass
        self.text.focus_set()

    def _clear_bgcolor(self):
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
        try:
            r = int(hex_color[1:3], 16) / 255
            g = int(hex_color[3:5], 16) / 255
            b = int(hex_color[5:7], 16) / 255
            return 0.299 * r + 0.587 * g + 0.114 * b
        except Exception:
            return 0.5

    def _set_align(self, justify):
        try:
            s = self.text.index("sel.first linestart")
            e = self.text.index("sel.last lineend")
        except tk.TclError:
            s = self.text.index("insert linestart")
            e = self.text.index("insert lineend")
        for j in ("left", "center", "right"):
            self.text.tag_remove(f"align_{j}", s, e)
        tag = f"align_{justify}"
        try:
            self.text.tag_cget(tag, "justify")
        except tk.TclError:
            self.text.tag_configure(tag, justify=justify)
        self.text.tag_add(tag, s, e)
        self.text.focus_set()

    def _toggle_strikethrough(self):
        self._apply_or_remove_tag("strikethrough")
        self.text.focus_set()

    _INDENT_STEP = 30

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
        current = 0
        for tag in self.text.tag_names(s):
            if tag.startswith("indent_"):
                try:
                    current = int(tag[7:])
                except ValueError:
                    pass
        new_indent = max(0, current + delta)
        for tag in self.text.tag_names():
            if tag.startswith("indent_"):
                self.text.tag_remove(tag, s, e)
        if new_indent > 0:
            tag = f"indent_{new_indent}"
            try:
                self.text.tag_cget(tag, "lmargin1")
            except tk.TclError:
                self.text.tag_configure(tag, lmargin1=new_indent, lmargin2=new_indent)
            self.text.tag_add(tag, s, e)
        self.text.focus_set()

    # ──────────────────────────────────────────────────────────────────────────
    # Inserción de imágenes
    # ──────────────────────────────────────────────────────────────────────────
    def _insert_pil_image(self, pil_img, img_id=None):
        """
        Inserta una imagen PIL en la posición del cursor.
        Si img_id se proporciona, reutiliza esa clave (para recarga desde JSON).
        IMPORTANTE: debe llamarse siempre desde el hilo principal de Tkinter.
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
                (max(1, int(w * ratio)), max(1, int(h * ratio))), Image.LANCZOS)

        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        # Crear PhotoImage en el hilo principal
        photo = ImageTk.PhotoImage(pil_img)

        if img_id is None:
            img_id = f"img_{self._img_counter}"
            self._img_counter += 1

        idx = self.text.index(tk.INSERT)
        self.text.image_create(idx, image=photo, padx=4, pady=4)
        self.text.tag_add(img_id, idx)

        self._image_data[img_id] = {
            "b64": b64, "width": pil_img.width, "height": pil_img.height,
            "photo": photo   # referencia viva, evita GC
        }

    def _insert_image_from_file(self):
        if not PILLOW_AVAILABLE:
            messagebox.showwarning("Pillow no disponible", "Instala Pillow:\npip install Pillow")
            return
        # Selección múltiple
        paths = filedialog.askopenfilenames(
            title="Seleccionar imágenes (puedes elegir varias)",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp"),
                       ("Todos", "*.*")])
        if not paths:
            return
        errores = []
        for path in paths:
            try:
                self._insert_pil_image(Image.open(path))
            except Exception as e:
                errores.append(f"{os.path.basename(path)}: {e}")
        if errores:
            messagebox.showwarning("Algunas imágenes no se pudieron cargar",
                                   "\n".join(errores))

    def _insert_image_from_adjuntos(self):
        if not PILLOW_AVAILABLE:
            messagebox.showwarning("Pillow no disponible", "Instala Pillow:\npip install Pillow")
            return
        if not self._get_adjuntos_fn:
            messagebox.showinfo("No disponible", "Esta función requiere el expediente abierto.")
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
        if not self._get_b2_client_fn:
            return None
        try:
            b2_api, bucket = self._get_b2_client_fn()
            if not b2_api or not bucket:
                return None
            if self._normalizar_ruta_b2 and self._b2_root_folder:
                ruta_b2 = self._normalizar_ruta_b2(
                    f"{self._b2_root_folder}/{ruta_relativa}")
            else:
                ruta_b2 = ruta_relativa
            ext = os.path.splitext(ruta_relativa)[1]
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=ext, prefix="rte_img_")
            os.close(tmp_fd)
            downloaded = bucket.download_file_by_name(ruta_b2)
            downloaded.save_to(tmp_path)
            self._temp_files.append(tmp_path)
            return tmp_path
        except Exception as e:
            print(f"[RichTextEditor] Error descargando B2: {e}")
            return None

    def _descargar_adjunto_local(self, ruta_relativa, adjuntos_root):
        ruta = os.path.join(adjuntos_root, ruta_relativa)
        return ruta if os.path.exists(ruta) else None

    # ── Selector de adjuntos con selección múltiple ──────────────────────────
    def _abrir_selector_adjuntos(self, imagenes):
        t = self._theme()
        win = tk.Toplevel(self)
        win.title("Seleccionar imágenes de adjuntos")
        win.geometry("720x520")
        win.grab_set()
        win.resizable(True, True)
        win.configure(bg=t["tb"])

        tk.Label(win,
                 text="Clic para seleccionar / Doble clic para insertar una  ·  "
                      "Usa 'Insertar seleccionadas' para añadir varias",
                 bg=t["tb"], fg=t["fg"], font=("Segoe UI", 9)).pack(pady=(10, 4))

        # Área scroll
        cf = tk.Frame(win, bg=t["tb"])
        cf.pack(fill="both", expand=True, padx=10, pady=4)
        canvas = tk.Canvas(cf, bg=t["tb"], highlightthickness=0)
        sb2    = tk.Scrollbar(cf, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb2.set)
        sb2.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg=t["tb"])
        canvas.create_window((0, 0), window=inner, anchor="nw")

        # Barra inferior
        bar = tk.Frame(win, bg=t["tb"], pady=6)
        bar.pack(side="bottom", fill="x", padx=10)

        sel_label = tk.Label(bar, text="0 seleccionadas",
                             bg=t["tb"], fg=t["fg"], font=("Segoe UI", 9))
        sel_label.pack(side="left", padx=4)

        btn_insertar = tk.Button(
            bar, text="✓ Insertar seleccionadas",
            bg="#2a7a2a", fg="#ffffff",
            activebackground="#1e5e1e", activeforeground="#ffffff",
            relief="flat", bd=0, padx=14, pady=4,
            cursor="hand2", font=("Segoe UI", 9, "bold"),
            state="disabled")
        btn_insertar.pack(side="right", padx=4)
        tk.Button(bar, text="Cancelar", command=win.destroy,
                  bg=t["tb"], fg=t["fg"],
                  activebackground=t["act"],
                  relief="flat", bd=0, padx=10, pady=4,
                  cursor="hand2", font=("Segoe UI", 9)).pack(side="right", padx=4)

        MAX_COLS = 4
        # seleccionados: {adj_dict: {'lbl': widget, 'adj': dict}}
        seleccionados = {}
        thumb_data    = {}   # {nombre: {'adj': dict, 'bytes': bytes}}  — se llena en background

        def _actualizar_boton():
            n = len(seleccionados)
            sel_label.config(text=f"{n} seleccionada{'s' if n != 1 else ''}")
            btn_insertar.config(state="normal" if n > 0 else "disabled")

        def _toggle_seleccion(adj, lbl):
            key = adj["nombre"]
            if key in seleccionados:
                del seleccionados[key]
                lbl.config(relief="solid", bd=1, bg=t["tb"])
            else:
                seleccionados[key] = {"adj": adj, "lbl": lbl}
                lbl.config(relief="solid", bd=3, bg="#4a8a4a")
            _actualizar_boton()

        def _insertar_adj(adj):
            """Descarga e inserta una imagen (llamado desde hilo secundario, inserta en principal)."""
            ruta_rel = adj.get("ruta_relativa", "")
            tipo_alm = adj.get("tipo_almacenamiento", "local")
            adj_root = adj.get("adjuntos_root", "")
            if tipo_alm in ("backblaze", "b2") or (self._usar_b2_fn and self._usar_b2_fn()):
                local = self._descargar_adjunto_b2_temp(ruta_rel)
            else:
                local = self._descargar_adjunto_local(ruta_rel, adj_root)
            if local and os.path.exists(local):
                try:
                    img = Image.open(local)
                    # _insert_pil_image debe ejecutarse en el hilo principal
                    if win.winfo_exists():
                        win.after(0, lambda i=img: self._insert_pil_image(i))
                except Exception as ex:
                    if win.winfo_exists():
                        win.after(0, lambda: messagebox.showerror(
                            "Error", f"No se pudo cargar:\n{ex}", parent=win))

        def _insertar_seleccionadas():
            adjs = [v["adj"] for v in seleccionados.values()]
            win.destroy()
            def _do():
                for adj in adjs:
                    _insertar_adj(adj)
            threading.Thread(target=_do, daemon=True).start()

        btn_insertar.config(command=_insertar_seleccionadas)

        # ── Carga de miniaturas en segundo plano ─────────────────────────────
        col_ref = [0]
        row_ref = [0]

        def _place_thumb(adj, img_bytes):
            """Crea la miniatura y la coloca — ejecutado en hilo PRINCIPAL."""
            try:
                pil_thumb = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                pil_thumb.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
                photo = ImageTk.PhotoImage(pil_thumb)   # ← hilo principal ✓
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
            lbl.image = photo   # referencia extra para evitar GC
            lbl.pack()
            tk.Label(cell,
                     text=(nombre[:18] + "…" if len(nombre) > 18 else nombre),
                     bg=t["tb"], fg=t["fg"], font=("Segoe UI", 7)).pack()

            lbl.bind("<Button-1>",       lambda e, a=adj, l=lbl: _toggle_seleccion(a, l))
            lbl.bind("<Double-Button-1>", lambda e, a=adj: (win.destroy(),
                                                             threading.Thread(
                                                                 target=lambda: _insertar_adj(a),
                                                                 daemon=True).start()))
            inner.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _cargar_miniatura(adj):
            """Descarga la imagen — ejecutado en hilo SECUNDARIO."""
            ruta_rel = adj.get("ruta_relativa", "")
            tipo_alm = adj.get("tipo_almacenamiento", "local")
            adj_root = adj.get("adjuntos_root", "")
            if tipo_alm in ("backblaze", "b2") or (self._usar_b2_fn and self._usar_b2_fn()):
                local = self._descargar_adjunto_b2_temp(ruta_rel)
            else:
                local = self._descargar_adjunto_local(ruta_rel, adj_root)
            if not local or not os.path.exists(local):
                return
            try:
                with open(local, "rb") as f:
                    img_bytes = f.read()
                # Enviar los bytes al hilo principal para crear ImageTk
                if win.winfo_exists():
                    win.after(0, lambda b=img_bytes, a=adj: _place_thumb(a, b))
            except Exception:
                pass

        def _cargar_todas():
            for adj in imagenes:
                _cargar_miniatura(adj)

        threading.Thread(target=_cargar_todas, daemon=True).start()

    # ──────────────────────────────────────────────────────────────────────────
    # Serialización / Deserialización
    # ──────────────────────────────────────────────────────────────────────────
    def get_content(self):
        """Serializa a JSON para guardar en BD."""
        segments = []
        if not self.text.get("1.0", "end-1c") and not self._image_data:
            return ""

        image_positions = {}
        for img_id in self._image_data:
            ranges = self.text.tag_ranges(img_id)
            if ranges:
                image_positions[str(ranges[0])] = img_id

        idx = "1.0"
        while True:
            if self.text.compare(idx, ">=", "end-1c"):
                break
            char = self.text.get(idx)

            if char == "\ufffc":
                img_id = image_positions.get(str(idx))
                if img_id and img_id in self._image_data:
                    d = self._image_data[img_id]
                    segments.append({"type": "image",
                                     "b64": d["b64"],
                                     "width": d["width"],
                                     "height": d["height"]})
                idx = self.text.index(f"{idx}+1c")
                continue

            tags_at   = set(self.text.tag_names(idx))
            run_chars = []
            while True:
                c = self.text.get(idx)
                if not c or self.text.compare(idx, ">=", "end-1c"):
                    break
                if c == "\ufffc":
                    break
                if set(self.text.tag_names(idx)) != tags_at:
                    break
                run_chars.append(c)
                idx = self.text.index(f"{idx}+1c")

            if run_chars:
                size   = DEFAULT_SIZE
                color  = None
                family = None
                bgcolor = None
                align   = None
                indent  = 0
                for tag in tags_at:
                    if tag.startswith("size_"):
                        try: size = int(tag[5:])
                        except ValueError: pass
                    elif tag.startswith("color_"):
                        color = "#" + tag[6:]
                    elif tag.startswith("family_"):
                        family = tag[7:].replace("_", " ")
                    elif tag.startswith("bgcolor_"):
                        bgcolor = "#" + tag[8:]
                    elif tag.startswith("align_"):
                        align = tag[6:]
                    elif tag.startswith("indent_"):
                        try: indent = int(tag[7:])
                        except ValueError: pass
                segments.append({
                    "type":          "text",
                    "content":       "".join(run_chars),
                    "bold":          "bold"          in tags_at,
                    "italic":        "italic"        in tags_at,
                    "underline":     "underline"     in tags_at,
                    "strikethrough": "strikethrough" in tags_at,
                    "size":          size,
                    "color":         color,
                    "family":        family,
                    "bgcolor":       bgcolor,
                    "align":         align,
                    "indent":        indent,
                })
            else:
                idx = self.text.index(f"{idx}+1c")

        return json.dumps({"version": 1, "segments": segments}, ensure_ascii=False)

    def get_plain_text(self):
        return self.text.get("1.0", "end-1c").replace("\ufffc", "[IMAGEN]").strip()

    def set_content(self, raw):
        """Carga contenido: JSON propio o texto plano."""
        self.text.delete("1.0", "end")
        self._image_data.clear()
        # No resetear _img_counter para que los ids sean siempre únicos

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
        self.text.insert("1.0", raw)

    def _load_from_json(self, data):
        for seg in data.get("segments", []):
            if seg.get("type") == "image":
                if not PILLOW_AVAILABLE:
                    self.text.insert("end", "[IMAGEN]\n")
                    continue
                try:
                    img = Image.open(
                        io.BytesIO(base64.b64decode(seg["b64"]))
                    ).convert("RGB")
                    # Respetar tamaño guardado si difiere del original
                    w_guardado = seg.get("width")
                    h_guardado = seg.get("height")
                    if w_guardado and h_guardado and (img.width != w_guardado or img.height != h_guardado):
                        img = img.resize((w_guardado, h_guardado), Image.LANCZOS)
                    self._insert_pil_image(img)
                except Exception as e:
                    self.text.insert("end", f"[Error imagen: {e}]\n")
            elif seg.get("type") == "text":
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

    # ──────────────────────────────────────────────────────────────────────────
    # Limpieza
    # ──────────────────────────────────────────────────────────────────────────
    def _cleanup_temps(self, event=None):
        for p in self._temp_files:
            try:
                if os.path.exists(p):
                    os.unlink(p)
            except Exception:
                pass

    # ──────────────────────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────────────────────
    def clear(self):
        self.text.delete("1.0", "end")
        self._image_data.clear()

    def focus_set(self):
        self.text.focus_set()

    def get(self, *args):
        return self.get_plain_text()

    # ──────────────────────────────────────────────────────────────────────────
    # Ventana expandida
    # ──────────────────────────────────────────────────────────────────────────
    def _abrir_ventana_expandida(self):
        _VentanaExpandida(self)


class _VentanaExpandida(tk.Toplevel):
    """
    Ventana modal grande con el editor en modo expandido.
    Al guardar, vuelca el contenido (JSON con b64) al editor origen.
    """

    def __init__(self, editor_origen: RichTextEditor):
        super().__init__(editor_origen)
        self._editor_origen = editor_origen
        self.title("Observaciones Técnicas — Editor expandido")
        self.geometry("1200x750")
        self.minsize(800, 500)
        self.resizable(True, True)
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"1200x750+{(sw-1200)//2}+{(sh-750)//2}")
        self.grab_set()
        self.focus_set()
        self._build_ui()
        self._editor.set_content(editor_origen.get_content())
        self.protocol("WM_DELETE_WINDOW", self._on_cancelar)

    def _build_ui(self):
        t = self._editor_origen._theme()
        self.configure(bg=t["tb"])

        bar = tk.Frame(self, bg=t["tb"], pady=6)
        bar.pack(side="bottom", fill="x", padx=12)

        tk.Button(bar, text="💾  Guardar y cerrar", command=self._on_guardar,
                  bg="#2a7a2a", fg="#ffffff",
                  activebackground="#1e5e1e", activeforeground="#ffffff",
                  relief="flat", bd=0, padx=20, pady=6,
                  cursor="hand2", font=("Segoe UI", 10, "bold")
                  ).pack(side="right", padx=(6, 0))

        tk.Button(bar, text="✕  Cancelar", command=self._on_cancelar,
                  bg="#7a2a2a", fg="#ffffff",
                  activebackground="#5e1e1e", activeforeground="#ffffff",
                  relief="flat", bd=0, padx=20, pady=6,
                  cursor="hand2", font=("Segoe UI", 10)
                  ).pack(side="right")

        tk.Label(bar,
                 text="Los cambios se aplicarán al expediente al pulsar 'Guardar y cerrar'",
                 bg=t["tb"], fg=t["fg"], font=("Segoe UI", 9)).pack(side="left", padx=4)

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
        """Transfiere JSON completo (con imágenes en b64) al editor origen."""
        contenido = self._editor.get_content()
        self._editor_origen.set_content(contenido)
        self.grab_release()
        self.destroy()

    def _on_cancelar(self):
        contenido_actual   = self._editor.get_content()
        contenido_original = self._editor_origen.get_content()
        if contenido_actual != contenido_original:
            from tkinter import messagebox as _mb
            respuesta = _mb.askyesnocancel(
                "¿Descartar cambios?",
                "Hay cambios sin guardar en el editor expandido.\n\n"
                "¿Guardar y cerrar?\n"
                "(No = cerrar sin guardar, Cancelar = volver al editor)",
                parent=self)
            if respuesta is True:
                self._on_guardar()
                return
            elif respuesta is None:
                return
        self.grab_release()
        self.destroy()
