"""Mixin extraido siguiendo el mismo patron que el resto de lib/ui_mixins:
solo aporta metodos que se combinan con VentanaPrincipal via herencia
multiple. Depende de atributos de instancia (self.rol, self.username, etc.)
inicializados en VentanaPrincipal.__init__.

Pantalla de administración para el flujo de recepción de paquetes por QR:
generación/cancelación de PINs, listado y revocación de dispositivos, y
configuración (mensaje de Incidencias, límites del PIN).
"""
from lib.app_core import *  # noqa: F401,F403 - helpers/constantes/imports compartidos con app.py


class DispositivosQRMixin:
    def mostrar_gestor_dispositivos_qr(self):
        """Abre la ventana de administración de dispositivos y PINs de recepción por QR"""
        if str(self.rol).strip().lower() not in ("admin", "administrador"):
            messagebox.showerror("Acceso Denegado", "Solo los administradores pueden gestionar dispositivos QR.")
            return

        from lib.safe_toplevel import SafeCTkToplevel
        from lib.dispositivos_qr_manager import DispositivosQRManager

        try:
            mgr = DispositivosQRManager()

            ventana = SafeCTkToplevel(self)
            ventana.title("Recepción por QR — Dispositivos y Configuración")
            ventana.geometry("750x650")
            ventana.transient(self)
            ventana.grab_set()

            tabview = ctk.CTkTabview(ventana)
            tabview.pack(fill="both", expand=True, padx=15, pady=15)
            tab_dispositivos = tabview.add("Dispositivos y PINs")
            tab_config = tabview.add("Configuración")

            self._construir_tab_dispositivos_qr(tab_dispositivos, mgr, ventana)
            self._construir_tab_config_recepcion_qr(tab_config, mgr, ventana)

        except Exception as e:
            logger.error(f"Error al abrir gestor de dispositivos QR: {e}")
            messagebox.showerror("Error", f"No se pudo abrir el gestor de dispositivos QR:\n{e}")
            import traceback
            traceback.print_exc()

    def _construir_tab_dispositivos_qr(self, tab, mgr, ventana):
        """Construye la pestaña de PINs pendientes y dispositivos registrados"""

        # Botón para generar un PIN nuevo
        top_frame = ctk.CTkFrame(tab, fg_color="transparent")
        top_frame.pack(fill="x", pady=(5, 10))

        btn_generar_pin = ctk.CTkButton(top_frame, text="🔑 Generar PIN nuevo", width=200)
        btn_generar_pin.pack(side="left", padx=5)

        # Sección: PINs pendientes
        label_pins = ctk.CTkLabel(tab, text="PINs pendientes", font=("Arial", 14, "bold"))
        label_pins.pack(anchor="w", pady=(10, 5))

        frame_pins = ctk.CTkScrollableFrame(tab, height=150)
        frame_pins.pack(fill="both", expand=True, pady=(0, 10))

        # Sección: Dispositivos registrados
        label_dispositivos = ctk.CTkLabel(tab, text="Dispositivos registrados", font=("Arial", 14, "bold"))
        label_dispositivos.pack(anchor="w", pady=(10, 5))

        frame_dispositivos = ctk.CTkScrollableFrame(tab, height=250)
        frame_dispositivos.pack(fill="both", expand=True)

        def refrescar_pins():
            for widget in frame_pins.winfo_children():
                widget.destroy()

            pins = mgr.listar_pins_pendientes()
            if not pins:
                ctk.CTkLabel(frame_pins, text="No hay PINs pendientes", text_color="gray").pack(pady=10)
                return

            for p in pins:
                fila = ctk.CTkFrame(frame_pins)
                fila.pack(fill="x", pady=3, padx=3)

                texto = f"PIN {p['pin']}  ·  generado por {p['creado_por']}  ·  caduca {p['fecha_caducidad'][:16].replace('T', ' ')}"
                ctk.CTkLabel(fila, text=texto, anchor="w").pack(side="left", padx=10, fill="x", expand=True)

                btn_cancelar = ctk.CTkButton(
                    fila, text="Cancelar", width=90, fg_color="red", hover_color="darkred",
                    command=lambda pid=p["id"]: cancelar_pin(pid)
                )
                btn_cancelar.pack(side="right", padx=5)

        def refrescar_dispositivos():
            for widget in frame_dispositivos.winfo_children():
                widget.destroy()

            dispositivos = mgr.listar_dispositivos()
            if not dispositivos:
                ctk.CTkLabel(frame_dispositivos, text="No hay dispositivos registrados", text_color="gray").pack(pady=10)
                return

            for d in dispositivos:
                fila = ctk.CTkFrame(frame_dispositivos)
                fila.pack(fill="x", pady=3, padx=3)

                if d["tipo"] == "personal":
                    tipo_texto = f"Personal — {d['nombre_persona'] or '(sin nombre)'}"
                else:
                    tipo_texto = "Compartido de almacén"

                texto = f"{tipo_texto}  ·  registrado {d['fecha_registro'][:16].replace('T', ' ')}"
                ctk.CTkLabel(fila, text=texto, anchor="w").pack(side="left", padx=10, fill="x", expand=True)

                btn_revocar = ctk.CTkButton(
                    fila, text="Revocar", width=90, fg_color="red", hover_color="darkred",
                    command=lambda did=d["id"]: revocar_dispositivo(did)
                )
                btn_revocar.pack(side="right", padx=5)

        def generar_pin():
            pin, error = mgr.generar_pin(self.username)
            if error:
                messagebox.showerror("Error", f"No se pudo generar el PIN:\n{error}")
                return
            config = mgr.obtener_config()
            minutos = config.get("pin_caducidad_minutos", 15)
            messagebox.showinfo(
                "PIN generado",
                f"PIN: {pin}\n\nCaduca en {minutos} minutos y solo se puede usar una vez.\n"
                "Dáselo al trabajador para que registre su móvil.",
                parent=ventana
            )
            refrescar_pins()

        def cancelar_pin(pin_id):
            if messagebox.askyesno("Confirmar", "¿Cancelar este PIN pendiente?", parent=ventana):
                success, msg = mgr.cancelar_pin(pin_id)
                if success:
                    refrescar_pins()
                else:
                    messagebox.showerror("Error", msg)

        def revocar_dispositivo(dispositivo_id):
            if messagebox.askyesno(
                "Confirmar",
                "¿Revocar este dispositivo?\n\nDejará de poder registrar recepciones hasta que "
                "se registre de nuevo con un PIN nuevo.",
                parent=ventana
            ):
                success, msg = mgr.revocar_dispositivo(dispositivo_id)
                if success:
                    refrescar_dispositivos()
                else:
                    messagebox.showerror("Error", msg)

        btn_generar_pin.configure(command=generar_pin)

        refrescar_pins()
        refrescar_dispositivos()

    def _construir_tab_config_recepcion_qr(self, tab, mgr, ventana):
        """Construye la pestaña de configuración: mensaje de Incidencias y límites del PIN"""

        config = mgr.obtener_config()

        ctk.CTkLabel(tab, text="Mensaje mostrado cuando el nombre no coincide (Incidencias)",
                     font=("Arial", 12, "bold")).pack(anchor="w", pady=(10, 5))

        textbox_mensaje = ctk.CTkTextbox(tab, height=100)
        textbox_mensaje.pack(fill="x", pady=(0, 15))
        textbox_mensaje.insert("1.0", config.get("mensaje_incidencias", ""))

        frame_limites = ctk.CTkFrame(tab, fg_color="transparent")
        frame_limites.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(frame_limites, text="Intentos máximos de PIN:").grid(row=0, column=0, sticky="w", padx=5, pady=8)
        entry_intentos = ctk.CTkEntry(frame_limites, width=80)
        entry_intentos.grid(row=0, column=1, sticky="w", padx=5, pady=8)
        entry_intentos.insert(0, str(config.get("pin_max_intentos", 5)))

        ctk.CTkLabel(frame_limites, text="Caducidad del PIN (minutos):").grid(row=1, column=0, sticky="w", padx=5, pady=8)
        entry_caducidad = ctk.CTkEntry(frame_limites, width=80)
        entry_caducidad.grid(row=1, column=1, sticky="w", padx=5, pady=8)
        entry_caducidad.insert(0, str(config.get("pin_caducidad_minutos", 15)))

        def guardar_config():
            mensaje = textbox_mensaje.get("1.0", "end").strip()

            try:
                intentos = int(entry_intentos.get().strip())
                caducidad = int(entry_caducidad.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Los intentos y la caducidad deben ser números enteros.")
                return

            if intentos < 1 or caducidad < 1:
                messagebox.showerror("Error", "Los valores deben ser mayores que cero.")
                return

            success, msg = mgr.actualizar_config(
                mensaje_incidencias=mensaje,
                pin_max_intentos=intentos,
                pin_caducidad_minutos=caducidad
            )
            if success:
                messagebox.showinfo("Éxito", msg, parent=ventana)
            else:
                messagebox.showerror("Error", msg, parent=ventana)

        btn_guardar = ctk.CTkButton(tab, text="💾 Guardar configuración", command=guardar_config)
        btn_guardar.pack(pady=10)
