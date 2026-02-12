"""
Panel de tareas y badge visual para Gestor de Expedientes.

Este módulo maneja:
- Badge visual con contador de tareas pendientes
- Panel desplegable con lista de tareas
- Acciones sobre tareas (completar, abrir expediente, etc.)
"""

import customtkinter as ctk
from tkinter import messagebox
import datetime
from lib.logger_config import get_logger
from lib import tareas_notificaciones

logger = get_logger()


class TareasBadge(ctk.CTkFrame):
    """Badge visual que muestra el contador de tareas pendientes."""
    
    def __init__(self, parent, connect_db_func, username, on_click_callback=None, **kwargs):
        """
        Inicializa el badge de tareas.
        
        Args:
            parent: Widget padre
            connect_db_func: Función para conectar a la base de datos
            username: Nombre del usuario
            on_click_callback: Función a llamar cuando se hace click
        """
        super().__init__(parent, **kwargs)
        
        self.connect_db_func = connect_db_func
        self.username = username
        self.on_click_callback = on_click_callback
        self.contador_actual = 0
        
        # Configurar el frame como un pequeño badge circular
        self.configure(fg_color="transparent", cursor="hand2")
        
        # Solo mostrar el contador (sin icono propio, para evitar duplicados)
        self.label_contador = ctk.CTkLabel(
            self,
            text="0",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("gray70", "gray30"),
            corner_radius=10,
            width=22,
            height=22,
            text_color="white"
        )
        self.label_contador.pack()
        
        # Bind click
        self.bind("<Button-1>", self._on_click)
        self.label_contador.bind("<Button-1>", self._on_click)
        
        # Actualizar contador inicial
        self.actualizar_contador()
        
        logger.debug(f"Badge de tareas creado para usuario {username}")
    
    def _on_click(self, event=None):
        """Maneja el click en el badge."""
        logger.debug(f"Click en badge de tareas (contador: {self.contador_actual})")
        if self.on_click_callback:
            self.on_click_callback()
    
    def actualizar_contador(self):
        """Actualiza el contador de tareas pendientes."""
        try:
            count = tareas_notificaciones.contar_tareas_pendientes(
                self.connect_db_func,
                self.username
            )
            
            # Asegurar que count es un entero
            count = int(count) if count is not None else 0
            
            self.contador_actual = count
            self.label_contador.configure(text=str(count))
            
            # Cambiar color según cantidad
            if count == 0:
                self.label_contador.configure(fg_color=("gray70", "gray30"))
            elif count < 5:
                self.label_contador.configure(fg_color=("#2ecc71", "#27ae60"))  # Verde
            elif count < 10:
                self.label_contador.configure(fg_color=("#f39c12", "#e67e22"))  # Naranja
            else:
                self.label_contador.configure(fg_color=("#e74c3c", "#c0392b"))  # Rojo
            
            logger.debug(f"Contador de tareas actualizado: {count}")
            
        except Exception as e:
            logger.error(f"Error al actualizar contador de tareas: {e}", exc_info=True)
    
    def programar_actualizacion(self, intervalo_ms=300_000):
        """
        Programa actualizaciones periódicas del contador (por defecto cada 5 minutos).
        
        Args:
            intervalo_ms: Intervalo en milisegundos
        """
        try:
            self.actualizar_contador()
            self.after(intervalo_ms, lambda: self.programar_actualizacion(intervalo_ms))
        except Exception as e:
            logger.error(f"Error en actualización programada de badge: {e}", exc_info=True)


class PanelTareas(ctk.CTkToplevel):
    """Panel desplegable que muestra la lista de tareas del usuario."""
    
    def __init__(self, parent, connect_db_func, username, abrir_expediente_callback=None, **kwargs):
        """
        Inicializa el panel de tareas.
        
        Args:
            parent: Ventana padre
            connect_db_func: Función para conectar a la base de datos
            username: Nombre del usuario
            abrir_expediente_callback: Función para abrir un expediente por código
        """
        super().__init__(parent, **kwargs)
        
        self.connect_db_func = connect_db_func
        self.username = username
        self.abrir_expediente_callback = abrir_expediente_callback
        
        # Configurar ventana
        self.title("📋 Mis Tareas")
        self.geometry("700x600")
        
        # Centrar en la pantalla
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 700) // 2
        y = (screen_height - 600) // 2
        self.geometry(f"700x600+{x}+{y}")
        
        # Forzar que aparezca al frente (incluso si la principal está maximizada)
        self.attributes('-topmost', True)
        self.lift()
        self.focus_force()
        # Quitar topmost después de 500ms para no ser molesto
        self.after(500, lambda: self.attributes('-topmost', False))
        
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            header_frame,
            text="📋 Mis Tareas Pendientes",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(side="left")
        
        # Botón refrescar
        ctk.CTkButton(
            header_frame,
            text="🔄 Actualizar",
            command=self.cargar_tareas,
            width=100
        ).pack(side="right")
        
        # Filtros
        filtros_frame = ctk.CTkFrame(self, fg_color="transparent")
        filtros_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(filtros_frame, text="Filtrar:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 10))
        
        self.filtro_var = ctk.StringVar(value="Todas")
        filtro_options = ["Todas", "Vencidas", "Hoy", "Próximas", "Alta Prioridad"]
        
        self.filtro_menu = ctk.CTkOptionMenu(
            filtros_frame,
            variable=self.filtro_var,
            values=filtro_options,
            command=lambda _: self.cargar_tareas(),
            width=150
        )
        self.filtro_menu.pack(side="left")
        
        # Scroll frame para tareas
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            label_text="",
            fg_color=("gray90", "gray20")
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Cargar tareas
        self.cargar_tareas()
        
        logger.info(f"Panel de tareas abierto para usuario {username}")
    
    def cargar_tareas(self):
        """Carga y muestra las tareas según el filtro activo."""
        try:
            # Limpiar scroll frame
            for widget in self.scroll_frame.winfo_children():
                widget.destroy()
            
            # Obtener tareas según filtro
            filtro = self.filtro_var.get()
            logger.debug(f"Cargando tareas con filtro: {filtro}")
            
            if filtro == "Vencidas":
                tareas_vencidas, _ = tareas_notificaciones.obtener_tareas_vencidas_hoy(
                    self.connect_db_func,
                    self.username
                )
                tareas = tareas_vencidas
            elif filtro == "Hoy":
                _, tareas_hoy = tareas_notificaciones.obtener_tareas_vencidas_hoy(
                    self.connect_db_func,
                    self.username
                )
                tareas = tareas_hoy
            elif filtro == "Próximas":
                todas = tareas_notificaciones.obtener_tareas_pendientes_usuario(
                    self.connect_db_func,
                    self.username
                )
                hoy = datetime.date.today().strftime("%Y-%m-%d")
                tareas = [t for t in todas if t['fecha_vencimiento'] and t['fecha_vencimiento'] > hoy]
            elif filtro == "Alta Prioridad":
                todas = tareas_notificaciones.obtener_tareas_pendientes_usuario(
                    self.connect_db_func,
                    self.username
                )
                tareas = [t for t in todas if t['prioridad'] == 'Alta']
            else:  # Todas
                tareas = tareas_notificaciones.obtener_tareas_pendientes_usuario(
                    self.connect_db_func,
                    self.username
                )
            
            # Mostrar tareas
            if not tareas:
                ctk.CTkLabel(
                    self.scroll_frame,
                    text="✨ No hay tareas pendientes",
                    font=ctk.CTkFont(size=14),
                    text_color="gray"
                ).pack(pady=50)
            else:
                for tarea in tareas:
                    self._crear_tarjeta_tarea(tarea)
            
            logger.info(f"Cargadas {len(tareas)} tareas con filtro '{filtro}'")
            
        except Exception as e:
            logger.error(f"Error al cargar tareas: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error al cargar tareas:\n{e}")
    
    def _crear_tarjeta_tarea(self, tarea):
        """Crea una tarjeta visual para una tarea."""
        # Frame principal de la tarea
        card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=("white", "gray25"),
            corner_radius=8
        )
        card.pack(fill="x", pady=5, padx=5)
        
        # Header de la tarea (título y prioridad)
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=5)
        
        # Icono de prioridad
        prioridad = tarea.get('prioridad', 'Normal')
        icono_prioridad = "🔴" if prioridad == 'Alta' else "🟡" if prioridad == 'Normal' else "🟢"
        
        ctk.CTkLabel(
            header,
            text=icono_prioridad,
            font=ctk.CTkFont(size=16)
        ).pack(side="left", padx=(0, 5))
        
        # Título
        ctk.CTkLabel(
            header,
            text=tarea['titulo'],
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).pack(side="left", fill="x", expand=True)
        
        # Info frame (código RMA y fecha)
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(fill="x", padx=10, pady=(0, 5))
        
        if tarea['codigo_rma']:
            ctk.CTkLabel(
                info,
                text=f"📋 {tarea['codigo_rma']}",
                font=ctk.CTkFont(size=11),
                text_color="gray"
            ).pack(side="left", padx=(0, 15))
        
        # Fecha con color según estado
        if tarea['fecha_vencimiento']:
            hoy = datetime.date.today().strftime("%Y-%m-%d")
            fecha = tarea['fecha_vencimiento']
            
            if fecha < hoy:
                color_fecha = "#e74c3c"  # Rojo (vencida)
                icono_fecha = "⚠️"
            elif fecha == hoy:
                color_fecha = "#f39c12"  # Naranja (hoy)
                icono_fecha = "📅"
            else:
                color_fecha = "gray"  # Gris (futura)
                icono_fecha = "🕐"
            
            ctk.CTkLabel(
                info,
                text=f"{icono_fecha} {fecha}",
                font=ctk.CTkFont(size=11),
                text_color=color_fecha
            ).pack(side="left")
        
        # Descripción (si existe)
        if tarea['descripcion'] and tarea['descripcion'].strip():
            ctk.CTkLabel(
                card,
                text=tarea['descripcion'][:100] + ("..." if len(tarea['descripcion']) > 100 else ""),
                font=ctk.CTkFont(size=11),
                text_color="gray",
                anchor="w",
                wraplength=600
            ).pack(fill="x", padx=10, pady=(0, 5))
        
        # Botones de acción
        botones = ctk.CTkFrame(card, fg_color="transparent")
        botones.pack(fill="x", padx=10, pady=5)
        
        # Botón completar
        ctk.CTkButton(
            botones,
            text="✓ Completar",
            command=lambda t=tarea: self._completar_tarea(t),
            width=100,
            height=28,
            fg_color=("#27ae60", "#2ecc71"),
            hover_color=("#229954", "#27ae60")
        ).pack(side="left", padx=(0, 5))
        
        # Botón abrir expediente (si tiene código RMA)
        if tarea['codigo_rma'] and self.abrir_expediente_callback:
            ctk.CTkButton(
                botones,
                text="Ver Expediente",
                command=lambda c=tarea['codigo_rma']: self._abrir_expediente(c),
                width=120,
                height=28
            ).pack(side="left")
    
    def _completar_tarea(self, tarea):
        """Marca una tarea como completada."""
        try:
            # Confirmar
            respuesta = messagebox.askyesno(
                "Completar Tarea",
                f"¿Marcar como completada la tarea:\n\n'{tarea['titulo']}'?"
            )
            
            if not respuesta:
                return
            
            # Marcar como completada
            exito = tareas_notificaciones.marcar_tarea_completada(
                self.connect_db_func,
                tarea['id'],
                self.username
            )
            
            if exito:
                logger.info(f"Tarea {tarea['id']} completada por {self.username}")
                messagebox.showinfo("Éxito", "✓ Tarea marcada como completada")
                self.cargar_tareas()  # Recargar lista
            else:
                messagebox.showerror("Error", "No se pudo completar la tarea")
                
        except Exception as e:
            logger.error(f"Error al completar tarea: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error al completar tarea:\n{e}")
    
    def _abrir_expediente(self, codigo_rma):
        """Abre un expediente por su código."""
        try:
            logger.info(f"Abriendo expediente {codigo_rma} desde panel de tareas")
            if self.abrir_expediente_callback:
                self.destroy()  # Cerrar panel antes de abrir expediente
                self.abrir_expediente_callback(codigo_rma)
        except Exception as e:
            logger.error(f"Error al abrir expediente: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error al abrir expediente:\n{e}")
