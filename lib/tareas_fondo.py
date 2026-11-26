"""Ejecutar operaciones lentas (red, Turso, B2, Word) sin congelar la interfaz.

Tkinter solo puede tocarse desde el hilo principal. Si una operación de red se
hace en ese hilo, la ventana deja de repintarse y Windows la marca como
"No responde". Aquí la operación se ejecuta en un hilo aparte mientras el hilo
principal sigue atendiendo la interfaz.

Uso típico (sustituye a una llamada directa y devuelve su resultado):

    datos = esperar_en_fondo(self, lambda: descargar(ruta), "Descargando adjunto...")

- Si la operación termina en menos de ~0,15 s no se muestra nada.
- Si tarda más, aparece una pequeña ventana "Procesando..." que además bloquea
  los clics en el resto de la aplicación (evita dobles guardados).
- Las excepciones de la operación se relanzan en el hilo principal, así que el
  manejo de errores existente (try/except) sigue funcionando igual.
- La operación NO debe tocar widgets: solo red, disco, cálculos.
"""

import threading
import time
import tkinter as tk

import customtkinter as ctk

_MARGEN_SIN_VENTANA = 0.15  # segundos antes de mostrar la ventana de espera


class OperacionDemasiadoLarga(TimeoutError):
    pass


def _en_hilo_principal():
    return threading.current_thread() is threading.main_thread()


def _ventana_raiz(widget):
    try:
        return widget.winfo_toplevel()
    except Exception:
        return widget


class _VentanaEspera:
    def __init__(self, parent, mensaje):
        self.ventana = None
        self.etiqueta = None
        try:
            raiz = _ventana_raiz(parent)
            v = ctk.CTkToplevel(raiz)
            v.title("Procesando")
            v.resizable(False, False)
            v.protocol("WM_DELETE_WINDOW", lambda: None)  # no se puede cerrar a medias
            try:
                v.transient(raiz)
            except Exception:
                pass
            marco = ctk.CTkFrame(v)
            marco.pack(fill="both", expand=True, padx=12, pady=12)
            self.etiqueta = ctk.CTkLabel(marco, text=mensaje, wraplength=320, justify="center")
            self.etiqueta.pack(padx=16, pady=(12, 8))
            barra = ctk.CTkProgressBar(marco, mode="indeterminate", width=260)
            barra.pack(padx=16, pady=(0, 14))
            barra.start()
            v.update_idletasks()
            try:
                ancho, alto = 360, v.winfo_reqheight()
                x = raiz.winfo_rootx() + (raiz.winfo_width() - ancho) // 2
                y = raiz.winfo_rooty() + (raiz.winfo_height() - alto) // 2
                v.geometry(f"{ancho}x{alto}+{max(x, 0)}+{max(y, 0)}")
            except Exception:
                pass
            v.lift()
            v.attributes("-topmost", True)
            try:
                v.grab_set()
            except Exception:
                pass
            self.ventana = v
        except Exception:
            self.ventana = None

    def mensaje(self, texto):
        try:
            if self.etiqueta is not None:
                self.etiqueta.configure(text=texto)
        except Exception:
            pass

    def cerrar(self):
        if self.ventana is None:
            return
        try:
            self.ventana.grab_release()
        except Exception:
            pass
        try:
            self.ventana.destroy()
        except Exception:
            pass
        self.ventana = None


def esperar_en_fondo(parent, funcion, mensaje="Procesando...", timeout=None):
    """Ejecuta `funcion()` en otro hilo sin congelar la interfaz y devuelve su resultado.

    `parent`: cualquier widget de la ventana desde la que se llama.
    `timeout`: segundos máximos de espera; si se superan se lanza
    OperacionDemasiadoLarga (la operación sigue en segundo plano y su resultado
    se descarta).
    Si se llama fuera del hilo principal o sin interfaz, ejecuta directamente.
    """
    if parent is None or not _en_hilo_principal():
        return funcion()
    try:
        if not parent.winfo_exists():
            return funcion()
    except Exception:
        return funcion()

    estado = {}

    def trabajo():
        try:
            estado["resultado"] = funcion()
        except BaseException as e:  # se relanza en el hilo principal
            estado["error"] = e

    hilo = threading.Thread(target=trabajo, daemon=True)
    inicio = time.monotonic()
    hilo.start()
    hilo.join(_MARGEN_SIN_VENTANA)

    if hilo.is_alive():
        ventana = _VentanaEspera(parent, mensaje)
        terminado = tk.BooleanVar(master=parent, value=False)
        esperador = ventana.ventana or parent

        def comprobar():
            if not hilo.is_alive() or (timeout and time.monotonic() - inicio > timeout):
                terminado.set(True)
            else:
                esperador.after(50, comprobar)

        try:
            esperador.after(50, comprobar)
            esperador.wait_variable(terminado)
        finally:
            ventana.cerrar()

    if hilo.is_alive():
        raise OperacionDemasiadoLarga(f"La operación ha superado {timeout} s y se ha cancelado la espera.")
    if "error" in estado:
        raise estado["error"]
    return estado.get("resultado")


def lanzar_en_fondo(parent, funcion, al_terminar=None, al_fallar=None):
    """Ejecuta `funcion()` en otro hilo sin bloquear y sin ventana de espera.

    `al_terminar(resultado)` y `al_fallar(excepcion)` se llaman en el hilo
    principal (pueden tocar widgets). Útil para trabajos que el usuario no
    necesita esperar (comprobaciones al arrancar, avisos periódicos...).
    """
    estado = {}

    def trabajo():
        try:
            estado["resultado"] = funcion()
        except BaseException as e:
            estado["error"] = e

    hilo = threading.Thread(target=trabajo, daemon=True)
    hilo.start()

    def comprobar():
        try:
            if not parent.winfo_exists():
                return
        except Exception:
            return
        if hilo.is_alive():
            parent.after(100, comprobar)
            return
        try:
            if "error" in estado:
                if al_fallar:
                    al_fallar(estado["error"])
            elif al_terminar:
                al_terminar(estado.get("resultado"))
        except Exception as e:
            print(f"Error en la respuesta de una tarea en segundo plano: {e}")

    try:
        parent.after(100, comprobar)
    except Exception:
        pass
    return hilo
