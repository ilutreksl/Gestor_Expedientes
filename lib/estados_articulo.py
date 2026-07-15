import customtkinter as ctk
import tkinter as tk
import tkinter.messagebox as messagebox


def mostrar_expedientes_por_articulo_y_estado(parent, referencia, estado):
    """Muestra una ventana con los expedientes que contienen la referencia y tienen el estado indicado.
    parent: instancia principal de la app (se usará para llamar a parent.conectar_db() y parent.mostrar_nuevo_rma)
    referencia: referencia del artículo
    estado: estado a filtrar (puede ser 'Sin estado' si el campo es NULL)
    """
    if not referencia:
        messagebox.showinfo("Info", "Referencia vacía.")
        return

    # Crear ventana
    vent = ctk.CTkToplevel(parent)
    vent.title(f"Expedientes ({estado}) - {referencia}")
    vent.geometry("900x500")
    vent.resizable(True, True)
    vent.attributes('-topmost', False)
    vent.minsize(700, 400)
    vent.focus_set()
    vent.attributes('-topmost', True)
    vent.lift()
    vent.focus_force()
    vent.after(500, lambda: vent.attributes('-topmost', False))

    main = ctk.CTkFrame(vent)
    main.pack(fill="both", expand=True, padx=12, pady=12)

    header = ctk.CTkFrame(main)
    header.pack(fill="x", pady=(0,8))
    ctk.CTkLabel(header, text=f"Expedientes con referencia '{referencia}' y estado '{estado}'", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w")

    # Lista con scrollbar
    list_frame = ctk.CTkFrame(main)
    list_frame.pack(fill="both", expand=True)

    try:
        from tkinter import Canvas as _Canvas
        canvas = _Canvas(list_frame, borderwidth=0, highlightthickness=0)
    except Exception:
        canvas = ctk.CTkCanvas(list_frame, borderwidth=0, highlightthickness=0)

    sb = ctk.CTkScrollbar(list_frame, orientation="vertical", command=lambda *args: canvas.yview(*args))
    canvas.configure(yscrollcommand=lambda *args: sb.set(*args))
    sb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    sf = ctk.CTkFrame(canvas)
    window_id = canvas.create_window((0,0), window=sf, anchor="nw")

    def on_sf_configure(event):
        try:
            canvas.configure(scrollregion=canvas.bbox("all"))
        except Exception:
            pass

    def on_canvas_config(event):
        try:
            canvas.itemconfig(window_id, width=event.width)
        except Exception:
            pass

    sf.bind("<Configure>", on_sf_configure)
    canvas.bind("<Configure>", on_canvas_config)

    # Obtener expedientes desde la BD usando la conexión de la app
    try:
        conn, cursor = parent.conectar_db()
        # Si la app devuelve solo conn (compatibilidad), intentar adaptarse
        if cursor is None:
            cursor = conn.cursor()
    except Exception:
        # Alternativa: intentar usar parent.connect_db() si existe
        try:
            conn = parent.connect_db()
            cursor = conn.cursor()
        except Exception as e:
            messagebox.showerror("Error BD", f"No se pudo conectar a la base de datos: {e}")
            return

    try:
        # Construir condición para estados NULL
        if estado == 'Sin estado':
            sql = """
                SELECT DISTINCT m.id, m.codigo_rma, m.cliente, m.numero_documento_cliente, m.fecha_emision, m.estado
                FROM rma_maestro m
                JOIN rma_detalles d ON d.rma_id = m.id
                WHERE d.referencia_articulo = ? AND (d.estado_producto IS NULL OR d.estado_producto = '')
                ORDER BY m.fecha_emision DESC
            """
            params = (referencia,)
        else:
            sql = """
                SELECT DISTINCT m.id, m.codigo_rma, m.cliente, m.numero_documento_cliente, m.fecha_emision, m.estado
                FROM rma_maestro m
                JOIN rma_detalles d ON d.rma_id = m.id
                WHERE d.referencia_articulo = ? AND d.estado_producto = ?
                ORDER BY m.fecha_emision DESC
            """
            params = (referencia, estado)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
    except Exception as e:
        messagebox.showerror("Error BD", f"Error consultando expedientes: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return

    # Encabezados
    head = ctk.CTkFrame(sf)
    head.pack(fill="x", padx=5, pady=(0,6))
    head.grid_columnconfigure(0, weight=1, minsize=120)
    head.grid_columnconfigure(1, weight=2, minsize=240)
    head.grid_columnconfigure(2, weight=1, minsize=120)
    head.grid_columnconfigure(3, weight=1, minsize=120)
    hf = ctk.CTkFont(weight="bold")
    ctk.CTkLabel(head, text="CÓDIGO", font=hf).grid(row=0, column=0, padx=5, sticky="w")
    ctk.CTkLabel(head, text="CLIENTE", font=hf).grid(row=0, column=1, padx=5, sticky="w")
    ctk.CTkLabel(head, text="FECHA", font=hf).grid(row=0, column=2, padx=5, sticky="w")
    ctk.CTkLabel(head, text="ACCIONES", font=hf).grid(row=0, column=3, padx=5, sticky="w")

    colors = ("#FFFFFF", "#F7F8FA")

    def abrir_editor(rma_id):
        # Usar RmaEditorWindow (no parent.mostrar_nuevo_rma directo): mostrar_nuevo_rma
        # dibuja la ficha sobre el content_frame que se le pase, y RmaEditorWindow es
        # quien se encarga de intercambiarlo temporalmente por el suyo propio para que
        # la ficha se abra en su propia ventana en vez de sobre la ventana principal.
        # Llamar a mostrar_nuevo_rma directamente aquí dibujaba la ficha sobre la
        # ventana principal pero con el botón "Cerrar" de una ventana emergente, que
        # terminaba destruyendo la ventana principal entera al pulsarlo.
        try:
            from lib.rma_editor_window import RmaEditorWindow
            RmaEditorWindow(parent, rma_id=rma_id)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el editor: {e}")
            return
        try:
            vent.destroy()
        except Exception:
            pass

    for idx, r in enumerate(rows):
        try:
            rma_id, codigo, cliente, doc_cliente, fecha, estado_r = r
        except Exception:
            vals = list(r)
            rma_id = vals[0] if len(vals) > 0 else None
            codigo = vals[1] if len(vals) > 1 else ''
            cliente = vals[2] if len(vals) > 2 else ''
            fecha = vals[4] if len(vals) > 4 else ''

        # Usar fondo por defecto del tema (sin cebra)
        bg = "transparent"
        rf = ctk.CTkFrame(sf, fg_color="transparent")
        rf.pack(fill="x", padx=5, pady=2)
        rf.grid_columnconfigure(0, weight=1, minsize=120)
        rf.grid_columnconfigure(1, weight=2, minsize=240)
        rf.grid_columnconfigure(2, weight=1, minsize=120)
        rf.grid_columnconfigure(3, weight=1, minsize=120)

        lbl_code = ctk.CTkLabel(rf, text=str(codigo), anchor="w")
        lbl_code.grid(row=0, column=0, padx=5, sticky="w")
        lbl_client = ctk.CTkLabel(rf, text=str(cliente or ''), anchor="w")
        lbl_client.grid(row=0, column=1, padx=5, sticky="w")
        lbl_date = ctk.CTkLabel(rf, text=str(fecha or ''), anchor="w")
        lbl_date.grid(row=0, column=2, padx=5, sticky="w")

        btn_edit = ctk.CTkButton(rf, text="Editar", width=80, command=lambda rid=rma_id: abrir_editor(rid))
        btn_edit.grid(row=0, column=3, padx=5, sticky="e")

        # Doble clic en la fila para editar
        rf.bind("<Double-Button-1>", lambda e, rid=rma_id: abrir_editor(rid))

    try:
        conn.close()
    except Exception:
        pass
