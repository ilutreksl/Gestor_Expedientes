import os
import sys
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox


def mostrar_ventana_cambios(parent, changelog_path: str = None):
    """Muestra una ventana con el listado de cambios/ajustes realizados en la aplicación.

    Si `changelog_path` es None, intenta localizar `CHANGELOG.md` (u otras variantes)
    en la raíz del proyecto. Si no existe, usa un texto por defecto.
    """
    try:
        # Determinar ruta por defecto si no se proporciona
        source_path = None
        if changelog_path and os.path.exists(changelog_path):
            source_path = changelog_path
        else:
            # Buscar archivos comunes en la raíz del proyecto
            root = os.path.dirname(os.path.dirname(__file__))
            candidates = [
                os.path.join(root, 'CHANGELOG.md'),
                os.path.join(root, 'CHANGELOG.txt'),
                os.path.join(root, 'CHANGELOG'),
                os.path.join(root, 'DROPBOX_MIGRATION_GUIDE.md'),
                os.path.join(root, 'README.md'),
            ]
            for c in candidates:
                if os.path.exists(c):
                    source_path = c
                    break

        # Leer contenido
        contenido = None
        if source_path:
            try:
                with open(source_path, 'r', encoding='utf-8') as fh:
                    contenido = fh.read()
            except Exception:
                contenido = None

        if not contenido:
            contenido = (
                "- Actualización RMA: Al actualizar ahora aparece un único mensaje y el formulario permanece abierto.\n"
                "- F5: Atajo global añadido para refrescar el listado de expedientes.\n"
                "- Listado de expedientes: Se eliminó la columna \"Acciones\" y ahora se abre el expediente con doble clic en cualquier punto de la fila.\n"
                "- Filas clicables: Se añadió cursor \"hand2\" y binding de doble clic a las filas y sus etiquetas.\n"
                "- Backups: Soporte \"Turso-first\" para volcados remotos; logs de backup guardados en `logs/backups/`.\n"
                "- Tareas: Añadido filtro \"Filtrar por Usuario\" en la ventana de gestión de tareas.\n"
            )

        dlg = ctk.CTkToplevel(parent)
        dlg.transient(parent)
        dlg.grab_set()
        dlg.title("Cambios realizados")
        try:
            dlg.iconbitmap("Icono_Ilutrek.ico")
        except Exception:
            pass

        frm = ctk.CTkFrame(dlg, fg_color="transparent")
        frm.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")
        dlg.grid_rowconfigure(0, weight=1)
        dlg.grid_columnconfigure(0, weight=1)

        txt = ctk.CTkTextbox(frm, width=760, height=360)
        txt.grid(row=0, column=0, sticky="nsew")
        txt.insert("0.0", contenido)
        try:
            txt.configure(state="disabled")
        except Exception:
            pass

        btn_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(6,12))
        btn_frame.grid_columnconfigure(0, weight=1)

        def cerrar():
            try:
                dlg.destroy()
            except Exception:
                pass

        # Botón para abrir el archivo de changelog si existe
        if source_path:
            def abrir_archivo():
                try:
                    if os.name == 'nt':
                        os.startfile(source_path)
                    else:
                        # macOS / linux
                        try:
                            opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
                            os.system(f"{opener} \"{source_path}\"")
                        except Exception:
                            messagebox.showinfo('Abrir archivo', f'Archivo ubicado en: {source_path}')
                except Exception as e:
                    messagebox.showerror('Error', f'No se pudo abrir el archivo: {e}')

            ctk.CTkButton(btn_frame, text="Abrir archivo", command=abrir_archivo).grid(row=0, column=0, padx=6)

        ctk.CTkButton(btn_frame, text="Cerrar", command=cerrar).grid(row=0, column=1, padx=6)

    except Exception as e:
        print(f"Error mostrando ventana de cambios: {e}")
