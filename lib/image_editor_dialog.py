"""
lib/image_editor_dialog.py
Ventana modal para recortar y marcar (flechas, rectángulos, texto, lápiz)
una imagen antes de insertarla en el RichTextEditor.

Uso:
    dlg = ImageEditorDialog(parent, pil_image)
    parent.wait_window(dlg)
    resultado = dlg.result   # PIL.Image editada, o None si se canceló
"""
import tkinter as tk
from tkinter import colorchooser, simpledialog

from PIL import Image, ImageTk, ImageDraw, ImageFont

from lib.logger_config import get_logger

logger = get_logger()

# Si la imagen de entrada es más grande, se reduce a este máximo antes de
# editar: da margen de sobra para recortar/marcar con buena calidad sin
# disparar el consumo de memoria del historial de deshacer.
MAX_LADO_EDICION = 1600
MAX_LADO_CANVAS = 900
MAX_UNDO = 8
COLOR_DEFECTO = "#e53935"
GROSORES = [2, 4, 6, 8]


class ImageEditorDialog(tk.Toplevel):
    def __init__(self, parent, pil_image: Image.Image):
        super().__init__(parent)
        self.title("Editar imagen — recortar y marcar")
        self.resizable(True, True)
        self.grab_set()

        self.result = None  # se rellena solo si el usuario pulsa "Insertar"

        if pil_image.mode not in ("RGB",):
            fondo = Image.new("RGB", pil_image.size, (255, 255, 255))
            try:
                fondo.paste(pil_image, mask=pil_image.split()[-1] if pil_image.mode in ("RGBA", "LA") else None)
            except Exception:
                fondo.paste(pil_image)
            pil_image = fondo

        w, h = pil_image.size
        if w > MAX_LADO_EDICION or h > MAX_LADO_EDICION:
            ratio = min(MAX_LADO_EDICION / w, MAX_LADO_EDICION / h)
            pil_image = pil_image.resize((max(1, int(w * ratio)), max(1, int(h * ratio))), Image.LANCZOS)

        self._original = pil_image
        self._imagen = pil_image.copy()
        self._historial = []  # pila de deshacer (copias de self._imagen)

        self._herramienta = tk.StringVar(value="recortar")
        self._color_actual = COLOR_DEFECTO
        self._grosor = tk.IntVar(value=4)

        self._sel_inicio = None      # (x, y) en coords de canvas, para recorte
        self._sel_rect_id = None
        self._dibujo_actual_id = None
        self._puntos_lapiz = []

        self._photo = None  # referencia viva al PhotoImage mostrado

        logger.info(f"Editor de imágenes abierto ({pil_image.width}x{pil_image.height}px)")

        self._build_ui()
        self._redibujar_canvas()

        self.protocol("WM_DELETE_WINDOW", self._on_cancelar)
        self.bind("<Escape>", lambda e: self._on_cancelar())

    # ──────────────────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        toolbar = tk.Frame(self, pady=4)
        toolbar.pack(fill="x", side="top")

        def radio(text, valor):
            tk.Radiobutton(
                toolbar, text=text, value=valor, variable=self._herramienta,
                indicatoron=False, padx=8, pady=3
            ).pack(side="left", padx=2)

        radio("✂ Recortar", "recortar")
        radio("▭ Rectángulo", "rectangulo")
        radio("➜ Flecha", "flecha")
        radio("✏ Lápiz", "lapiz")
        radio("🅰 Texto", "texto")

        tk.Frame(toolbar, width=1, bg="#888").pack(side="left", fill="y", padx=6, pady=2)

        self._color_btn = tk.Button(
            toolbar, text="  ", bg=self._color_actual, width=3,
            command=self._elegir_color, relief="flat", bd=1, cursor="hand2"
        )
        self._color_btn.pack(side="left", padx=4)
        tk.Label(toolbar, text="Color").pack(side="left", padx=(0, 8))

        tk.Label(toolbar, text="Grosor:").pack(side="left")
        tk.OptionMenu(toolbar, self._grosor, *GROSORES).pack(side="left", padx=(2, 8))

        tk.Button(toolbar, text="↶ Deshacer", command=self._deshacer, cursor="hand2").pack(side="left", padx=4)
        tk.Button(toolbar, text="⟲ Restablecer", command=self._restablecer, cursor="hand2").pack(side="left", padx=4)

        barra_inferior = tk.Frame(self, pady=8)
        barra_inferior.pack(fill="x", side="bottom", padx=10)

        tk.Button(
            barra_inferior, text="✕ Cancelar", command=self._on_cancelar,
            bg="#7a2a2a", fg="white", activebackground="#5e1e1e",
            relief="flat", padx=16, pady=6, cursor="hand2"
        ).pack(side="right")
        tk.Button(
            barra_inferior, text="✔ Insertar imagen", command=self._on_insertar,
            bg="#2a7a2a", fg="white", activebackground="#1e5e1e",
            relief="flat", padx=16, pady=6, cursor="hand2", font=("Segoe UI", 10, "bold")
        ).pack(side="right", padx=(0, 8))

        self._canvas = tk.Canvas(self, bg="#3a3a3a", highlightthickness=0)
        self._canvas.pack(fill="both", expand=True, padx=10, pady=(6, 0))

        self._canvas.bind("<ButtonPress-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)

    # ──────────────────────────────────────────────────────────────────────
    # Escala imagen <-> canvas
    # ──────────────────────────────────────────────────────────────────────
    def _calcular_escala(self):
        w, h = self._imagen.size
        escala = min(MAX_LADO_CANVAS / w, MAX_LADO_CANVAS / h, 1.0)
        return escala

    def _redibujar_canvas(self):
        escala = self._calcular_escala()
        self._escala = escala
        w, h = self._imagen.size
        disp_w, disp_h = max(1, int(w * escala)), max(1, int(h * escala))
        imagen_mostrada = self._imagen if escala == 1.0 else self._imagen.resize((disp_w, disp_h), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(imagen_mostrada)

        self._canvas.delete("all")
        self._canvas.config(width=disp_w, height=disp_h)
        self._canvas.create_image(0, 0, anchor="nw", image=self._photo)

    def _canvas_a_imagen(self, x, y):
        """Convierte coordenadas de canvas a coordenadas de la imagen real, con clamp a los límites."""
        ix = int(x / self._escala)
        iy = int(y / self._escala)
        ix = max(0, min(self._imagen.width, ix))
        iy = max(0, min(self._imagen.height, iy))
        return ix, iy

    # ──────────────────────────────────────────────────────────────────────
    # Historial de deshacer
    # ──────────────────────────────────────────────────────────────────────
    def _guardar_estado_previo(self):
        self._historial.append(self._imagen.copy())
        if len(self._historial) > MAX_UNDO:
            self._historial.pop(0)

    def _deshacer(self):
        if not self._historial:
            return
        self._imagen = self._historial.pop()
        self._redibujar_canvas()

    def _restablecer(self):
        if self._imagen.tobytes() == self._original.tobytes():
            return
        self._guardar_estado_previo()
        self._imagen = self._original.copy()
        self._redibujar_canvas()

    # ──────────────────────────────────────────────────────────────────────
    # Interacción ratón
    # ──────────────────────────────────────────────────────────────────────
    def _on_press(self, event):
        herramienta = self._herramienta.get()
        x, y = self._canvas.canvasx(event.x), self._canvas.canvasy(event.y)

        if herramienta == "texto":
            self._solicitar_texto(x, y)
            return

        self._sel_inicio = (x, y)

        if herramienta == "lapiz":
            self._puntos_lapiz = [(x, y)]
        elif herramienta in ("recortar", "rectangulo", "flecha"):
            self._sel_rect_id = None

    def _on_drag(self, event):
        herramienta = self._herramienta.get()
        if self._sel_inicio is None:
            return
        x, y = self._canvas.canvasx(event.x), self._canvas.canvasy(event.y)
        x0, y0 = self._sel_inicio

        if herramienta == "recortar":
            if self._sel_rect_id:
                self._canvas.delete(self._sel_rect_id)
            self._sel_rect_id = self._canvas.create_rectangle(
                x0, y0, x, y, outline="#00e5ff", width=2, dash=(4, 2))

        elif herramienta == "rectangulo":
            if self._dibujo_actual_id:
                self._canvas.delete(self._dibujo_actual_id)
            self._dibujo_actual_id = self._canvas.create_rectangle(
                x0, y0, x, y, outline=self._color_actual, width=self._grosor.get())

        elif herramienta == "flecha":
            if self._dibujo_actual_id:
                self._canvas.delete(self._dibujo_actual_id)
            self._dibujo_actual_id = self._canvas.create_line(
                x0, y0, x, y, fill=self._color_actual, width=self._grosor.get(), arrow="last", arrowshape=(14, 16, 6))

        elif herramienta == "lapiz":
            self._puntos_lapiz.append((x, y))
            if len(self._puntos_lapiz) >= 2:
                (px, py) = self._puntos_lapiz[-2]
                self._canvas.create_line(
                    px, py, x, y, fill=self._color_actual, width=self._grosor.get(),
                    capstyle=tk.ROUND, joinstyle=tk.ROUND, tags="trazo_lapiz")

    def _on_release(self, event):
        herramienta = self._herramienta.get()
        if self._sel_inicio is None:
            return
        x, y = self._canvas.canvasx(event.x), self._canvas.canvasy(event.y)
        x0, y0 = self._sel_inicio

        if herramienta == "recortar":
            if self._sel_rect_id:
                self._canvas.delete(self._sel_rect_id)
                self._sel_rect_id = None
            self._aplicar_recorte(x0, y0, x, y)

        elif herramienta == "rectangulo":
            if self._dibujo_actual_id:
                self._canvas.delete(self._dibujo_actual_id)
                self._dibujo_actual_id = None
            self._aplicar_rectangulo(x0, y0, x, y)

        elif herramienta == "flecha":
            if self._dibujo_actual_id:
                self._canvas.delete(self._dibujo_actual_id)
                self._dibujo_actual_id = None
            self._aplicar_flecha(x0, y0, x, y)

        elif herramienta == "lapiz":
            self._canvas.delete("trazo_lapiz")
            self._aplicar_lapiz(self._puntos_lapiz)
            self._puntos_lapiz = []

        self._sel_inicio = None

    # ──────────────────────────────────────────────────────────────────────
    # Operaciones sobre la imagen real (flatten a PIL)
    # ──────────────────────────────────────────────────────────────────────
    def _aplicar_recorte(self, x0, y0, x1, y1):
        ix0, iy0 = self._canvas_a_imagen(min(x0, x1), min(y0, y1))
        ix1, iy1 = self._canvas_a_imagen(max(x0, x1), max(y0, y1))
        if ix1 - ix0 < 5 or iy1 - iy0 < 5:
            return  # selección demasiado pequeña, se ignora
        self._guardar_estado_previo()
        self._imagen = self._imagen.crop((ix0, iy0, ix1, iy1))
        logger.debug(f"Editor de imágenes: recorte aplicado -> {self._imagen.width}x{self._imagen.height}px")
        self._redibujar_canvas()

    def _aplicar_rectangulo(self, x0, y0, x1, y1):
        ix0, iy0 = self._canvas_a_imagen(min(x0, x1), min(y0, y1))
        ix1, iy1 = self._canvas_a_imagen(max(x0, x1), max(y0, y1))
        if ix1 - ix0 < 2 or iy1 - iy0 < 2:
            return
        self._guardar_estado_previo()
        draw = ImageDraw.Draw(self._imagen)
        draw.rectangle((ix0, iy0, ix1, iy1), outline=self._color_actual, width=self._grosor.get())
        self._redibujar_canvas()

    def _aplicar_flecha(self, x0, y0, x1, y1):
        ix0, iy0 = self._canvas_a_imagen(x0, y0)
        ix1, iy1 = self._canvas_a_imagen(x1, y1)
        if (ix0, iy0) == (ix1, iy1):
            return
        self._guardar_estado_previo()
        draw = ImageDraw.Draw(self._imagen)
        grosor = self._grosor.get()
        draw.line((ix0, iy0, ix1, iy1), fill=self._color_actual, width=grosor)
        self._dibujar_punta_flecha(draw, ix0, iy0, ix1, iy1, grosor)
        self._redibujar_canvas()

    def _dibujar_punta_flecha(self, draw, x0, y0, x1, y1, grosor):
        import math
        angulo = math.atan2(y1 - y0, x1 - x0)
        longitud = 8 + grosor * 2
        ancho = math.radians(28)
        p1 = (x1 - longitud * math.cos(angulo - ancho), y1 - longitud * math.sin(angulo - ancho))
        p2 = (x1 - longitud * math.cos(angulo + ancho), y1 - longitud * math.sin(angulo + ancho))
        draw.polygon([(x1, y1), p1, p2], fill=self._color_actual)

    def _aplicar_lapiz(self, puntos_canvas):
        if len(puntos_canvas) < 2:
            return
        self._guardar_estado_previo()
        puntos_imagen = [self._canvas_a_imagen(x, y) for x, y in puntos_canvas]
        draw = ImageDraw.Draw(self._imagen)
        draw.line(puntos_imagen, fill=self._color_actual, width=self._grosor.get(), joint="curve")
        self._redibujar_canvas()

    def _solicitar_texto(self, x, y):
        texto = simpledialog.askstring("Añadir texto", "Texto a escribir sobre la imagen:", parent=self)
        if not texto:
            return
        self._guardar_estado_previo()
        ix, iy = self._canvas_a_imagen(x, y)
        draw = ImageDraw.Draw(self._imagen)
        tam_fuente = 14 + self._grosor.get() * 3
        try:
            fuente = ImageFont.truetype("arial.ttf", tam_fuente)
        except Exception:
            fuente = ImageFont.load_default()
        draw.text((ix, iy), texto, fill=self._color_actual, font=fuente)
        self._redibujar_canvas()

    # ──────────────────────────────────────────────────────────────────────
    def _elegir_color(self):
        color = colorchooser.askcolor(color=self._color_actual, title="Color de marcado", parent=self)
        if color and color[1]:
            self._color_actual = color[1]
            self._color_btn.config(bg=self._color_actual)

    # ──────────────────────────────────────────────────────────────────────
    # Cierre
    # ──────────────────────────────────────────────────────────────────────
    def _on_insertar(self):
        self.result = self._imagen
        logger.info(f"Editor de imágenes: imagen aceptada ({self._imagen.width}x{self._imagen.height}px)")
        self.grab_release()
        self.destroy()

    def _on_cancelar(self):
        self.result = None
        logger.debug("Editor de imágenes: edición cancelada por el usuario")
        self.grab_release()
        self.destroy()
