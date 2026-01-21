# Hoja de Ruta: Migración CustomTkinter → PyQt6

**Proyecto:** Gestor de Expedientes RMA v1.0.11  
**Fecha inicio:** Enero 2026  
**Duración estimada:** 3-6 meses (gradual)  
**Estrategia:** Migración en paralelo sin interrumpir producción

---

## 📊 Análisis del Proyecto Actual

### Archivos a Migrar
```
app.py                          (1,500+ líneas - UI principal)
lib/
├── rma_editor_window.py       (UI compleja - CRÍTICO)
├── ventana_proveedor.py       (UI compleja)
├── proveedor_adjuntos.py      (UI + manejo archivos)
├── proveedor_tareas.py        (UI)
├── changelog_window.py        (UI simple)
├── avisos_manager.py          (UI dialogs)
├── estados_manager.py         (UI dialogs)
├── personas_manager.py        (UI dialogs)
├── personas_recepcion_manager.py (UI dialogs)
├── resultado_expediente_manager.py (UI dialogs)
├── tipos_cliente_manager.py   (UI dialogs)
├── github_issue_manager.py    (UI + API)
├── cliente_condiciones.py     (UI tablas)
├── safe_toplevel.py           (Utilidad UI)
└── Módulos estadísticas       (UI gráficos - 7 archivos)
    ├── anuales_estadisticas.py
    ├── articulos_estadisticas.py
    ├── cliente_estadisticas.py
    ├── comparativa_ventas.py
    ├── expedientes_quincena.py
    ├── resolucion_estadisticas.py
    └── client_rentability.py

Módulos NO-UI (sin cambios):
├── articulo_utils.py          (Lógica negocio)
├── cliente_utils.py           (Lógica negocio)
├── rma_utils.py               (Lógica negocio)
├── articulo_depreciacion.py   (Cálculos)
├── backup_manager.py          (Backend)
├── logger_config.py           (Backend)
├── pdf_fill.py                (Backend)
├── video_utils.py             (Backend)
├── historial_filtros.py       (Backend)
└── rma_asociaciones.py        (Backend)
```

**Total UI:** ~18 archivos  
**Total Backend (sin cambios):** ~10 archivos

---

## 🎯 Estrategia de Migración

### Principios Clave
1. **Nunca romper producción** - Versión CustomTkinter sigue funcionando
2. **Migración módulo a módulo** - No todo a la vez
3. **Testing continuo** - Cada módulo migrado se prueba completamente
4. **Carpeta paralela** - Crear `app_pyqt/` junto a código actual
5. **Compartir lógica** - Backend sin cambios, solo UI

### Estructura del Proyecto Durante Migración
```
Gestor_Expedientes/
├── app.py                    # CustomTkinter (PRODUCCIÓN)
├── app_pyqt.py              # PyQt (EN DESARROLLO)
├── lib/                      # Módulos CustomTkinter
├── lib_pyqt/                # Módulos PyQt (nuevos)
├── shared/                   # Lógica compartida (backend)
├── themes/                   # Temas JSON (CustomTkinter)
├── themes_qt/               # Archivos QSS (PyQt)
└── requirements.txt         # Ambas librerías temporalmente
```

---

## 📅 Fases de Migración (6 Meses)

### **FASE 0: Preparación (Semanas 1-2)**

#### Objetivos
- [ ] Instalar PyQt6 y dependencias
- [ ] Configurar entorno de desarrollo PyQt
- [ ] Estudiar arquitectura Qt (tutorial básico)
- [ ] Crear estructura de carpetas paralela
- [ ] Extraer lógica de negocio a módulos compartidos

#### Entregables
```bash
pip install PyQt6 PyQt6-tools
```
- Estructura `shared/` con utils sin UI
- Carpeta `lib_pyqt/` vacía lista
- Repositorio Git con branch `feature/pyqt-migration`

#### Tiempo: **2 semanas**

---

### **FASE 1: Módulo Piloto (Semanas 3-5)**

#### Objetivos: Validar estrategia con módulo simple

**Módulo elegido:** `changelog_window.py` (ventana simple, bajo riesgo)

#### Tareas
- [ ] Crear `lib_pyqt/changelog_window_qt.py`
- [ ] Convertir CTkToplevel → QDialog
- [ ] Convertir CTkTextbox → QTextEdit
- [ ] Aplicar primer tema QSS básico
- [ ] Integrar con app.py (botón test)
- [ ] Comparar resultado visual

#### Aprendizajes
- Patrones de conversión
- Sistema de señales/slots
- Gestión de layouts
- Estilizado QSS

#### Tiempo: **3 semanas** (incluye curva aprendizaje)

---

### **FASE 2: Managers y Diálogos (Semanas 6-10)**

#### Objetivos: Migrar ventanas de gestión (todas similares)

**Módulos a migrar:**
1. `estados_manager.py` → `estados_manager_qt.py`
2. `personas_manager.py` → `personas_manager_qt.py`
3. `personas_recepcion_manager.py` → `personas_recepcion_manager_qt.py`
4. `resultado_expediente_manager.py` → `resultado_expediente_manager_qt.py`
5. `tipos_cliente_manager.py` → `tipos_cliente_manager_qt.py`
6. `avisos_manager.py` → `avisos_manager_qt.py`

#### Patrón de conversión
```python
# CustomTkinter
class EstadosManager(customtkinter.CTkToplevel):
    def __init__(self):
        super().__init__()
        self.title("Gestión de Estados")
        self.geometry("400x300")
        
        frame = customtkinter.CTkFrame(self)
        frame.pack()
        
        btn = customtkinter.CTkButton(frame, text="Guardar", command=self.guardar)
        btn.grid(row=0, column=0)

# PyQt6
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton

class EstadosManagerQt(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestión de Estados")
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        btn = QPushButton("Guardar")
        btn.clicked.connect(self.guardar)
        layout.addWidget(btn)
```

#### Tiempo: **5 semanas** (1 semana cada 2 managers aprox)

---

### **FASE 3: Ventanas Complejas (Semanas 11-16)**

#### Objetivos: Migrar módulos con lógica UI compleja

**Prioridad 1 (críticas):**
1. `rma_editor_window.py` → `rma_editor_window_qt.py` (LA MÁS COMPLEJA)
2. `ventana_proveedor.py` → `ventana_proveedor_qt.py`

**Prioridad 2:**
3. `proveedor_adjuntos.py` → `proveedor_adjuntos_qt.py`
4. `proveedor_tareas.py` → `proveedor_tareas_qt.py`
5. `cliente_condiciones.py` → `cliente_condiciones_qt.py`
6. `github_issue_manager.py` → `github_issue_manager_qt.py`

#### Conversiones clave

**Tablas:**
```python
# CustomTkinter - CTkScrollableFrame manual
# PyQt6 - QTableWidget nativo (MEJOR)
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem

table = QTableWidget()
table.setColumnCount(3)
table.setHorizontalHeaderLabels(["ID", "Cliente", "Estado"])
table.setItem(0, 0, QTableWidgetItem("001"))
```

**Pestañas:**
```python
# CustomTkinter - CTkTabview
# PyQt6 - QTabWidget
from PyQt6.QtWidgets import QTabWidget, QWidget

tabs = QTabWidget()
tab1 = QWidget()
tabs.addTab(tab1, "Datos Generales")
```

**Combos/Selects:**
```python
# CustomTkinter - CTkComboBox
# PyQt6 - QComboBox (con autocompletado nativo!)
from PyQt6.QtWidgets import QComboBox

combo = QComboBox()
combo.addItems(["Opción 1", "Opción 2"])
combo.currentTextChanged.connect(self.on_change)
```

#### Tiempo: **6 semanas** (2 semanas RMA editor, 1 semana resto)

---

### **FASE 4: Módulos Estadísticas (Semanas 17-21)**

#### Objetivos: Migrar ventanas con gráficos

**Módulos:**
1. `anuales_estadisticas.py`
2. `articulos_estadisticas.py`
3. `cliente_estadisticas.py`
4. `comparativa_ventas.py`
5. `expedientes_quincena.py`
6. `resolucion_estadisticas.py`
7. `client_rentability.py`

#### Ventaja PyQt: QtCharts nativo

```python
# Actualmente (CustomTkinter + matplotlib embebido)
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# PyQt6 (QtCharts nativo - MÁS RÁPIDO)
from PyQt6.QtCharts import QChart, QChartView, QBarSeries, QPieSeries
from PyQt6.QtWidgets import QWidget, QVBoxLayout

class EstadisticasQt(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        # Crear gráfico
        series = QBarSeries()
        # ... datos
        
        chart = QChart()
        chart.addSeries(series)
        
        chartView = QChartView(chart)
        layout.addWidget(chartView)
```

#### Opciones
- **Opción A:** Usar QtCharts (nativo, más rápido)
- **Opción B:** Seguir con matplotlib (menos cambios)

**Recomendación:** Opción A - Aprovechar para mejorar rendimiento

#### Tiempo: **5 semanas**

---

### **FASE 5: Aplicación Principal (Semanas 22-24)**

#### Objetivos: Migrar `app.py` → `app_pyqt.py`

**Conversiones principales:**

**Ventana Principal:**
```python
# CustomTkinter
class VentanaPrincipal(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1400x800")
        set_appearance_mode("dark")

# PyQt6
from PyQt6.QtWidgets import QMainWindow, QApplication
from PyQt6.QtCore import Qt

class VentanaPrincipalQt(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1400, 800)
        # Tema se aplica con QSS
```

**Login:**
```python
# CustomTkinter
class LoginApp(customtkinter.CTk):
    # ...

# PyQt6
from PyQt6.QtWidgets import QDialog, QLineEdit

class LoginAppQt(QDialog):
    def __init__(self):
        super().__init__()
        self.username_entry = QLineEdit()
        self.username_entry.setPlaceholderText("Usuario")
        # ...
```

**Menú:**
```python
# CustomTkinter - Botones en Frame
# PyQt6 - QMenuBar nativo
from PyQt6.QtWidgets import QMenuBar
from PyQt6.QtGui import QAction

menubar = self.menuBar()
file_menu = menubar.addMenu("Archivo")

action_nuevo = QAction("Nuevo RMA", self)
action_nuevo.triggered.connect(self.nuevo_rma)
file_menu.addAction(action_nuevo)
```

#### Tiempo: **3 semanas**

---

### **FASE 6: Temas y Pulido (Semanas 25-26)**

#### Objetivos: Sistema completo de temas QSS

**Convertir temas existentes:**

```css
/* themes_qt/w11_modern.qss */
QMainWindow {
    background-color: #F3F3F3; /* Modo claro */
}

QPushButton {
    background-color: #5E5E5E;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-family: 'Segoe UI';
    font-size: 13px;
}

QPushButton:hover {
    background-color: #4A4A4A;
}

QPushButton:pressed {
    background-color: #3D3D3D;
}

QLineEdit {
    background-color: #FFFFFF;
    border: 2px solid #E5E5E5;
    border-radius: 6px;
    padding: 6px;
    color: #1F1F1F;
}

QLineEdit:focus {
    border-color: #5E5E5E;
}
```

**Aplicar tema:**
```python
def aplicar_tema(self, nombre_tema):
    qss_path = f"themes_qt/{nombre_tema}.qss"
    with open(qss_path, 'r', encoding='utf-8') as f:
        self.setStyleSheet(f.read())
```

#### Tareas
- [ ] Convertir w11_modern.json → w11_modern.qss
- [ ] Convertir w11_blue.json → w11_blue.qss
- [ ] Convertir teal_corporate.json → teal_corporate.qss
- [ ] Crear selector de tema en configuración
- [ ] Implementar modo claro/oscuro dinámico
- [ ] Pulir iconos y recursos

#### Tiempo: **2 semanas**

---

## 🧪 Testing y Validación (Continuo)

### Por Cada Módulo Migrado

#### Checklist de Validación
- [ ] Funcionalidad idéntica a versión CustomTkinter
- [ ] Todos los botones funcionan
- [ ] Validaciones de formularios operativas
- [ ] Conexión con base de datos correcta
- [ ] Temas aplicados correctamente
- [ ] Sin errores en consola
- [ ] Rendimiento igual o mejor
- [ ] Teclado shortcuts funcionan

#### Testing de Integración
- [ ] Flujo completo: Login → Dashboard → Crear RMA → Guardar
- [ ] Navegación entre ventanas
- [ ] Carga de datos persistentes
- [ ] Exportación/Importación archivos
- [ ] Generación PDF
- [ ] Integración Dropbox
- [ ] Sistema de backups

---

## 🚀 Despliegue (Semana 27+)

### Estrategia de Lanzamiento

#### Opción 1: Lanzamiento Beta Paralelo
```
Mes 7: 
- Versión CustomTkinter sigue en producción
- Versión PyQt disponible como "Beta v2.0"
- Usuarios voluntarios prueban PyQt
- Feedback y correcciones

Mes 8:
- PyQt se convierte en versión principal
- CustomTkinter disponible como "Clásica" (deprecada)

Mes 9:
- Solo PyQt en producción
```

#### Opción 2: Switch Completo
```
Semana 27:
- Testing intensivo final
- Migración de datos/configuraciones

Semana 28:
- Lanzamiento PyQt v2.0 directo
- Comunicación a usuarios
- Soporte activo primeras semanas
```

**Recomendación:** Opción 1 (más seguro)

---

## ⚠️ Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| **Usuarios rechazan nueva UI** | Media | Alto | Testing beta con usuarios clave, mantener versión antigua disponible |
| **Bugs no detectados** | Alta | Medio | Testing exhaustivo, release beta primero |
| **Rendimiento peor** | Baja | Medio | Benchmarks en cada fase, optimizar antes de continuar |
| **Tiempo mayor estimado** | Alta | Medio | Buffers de 20% en cada fase, priorizar módulos críticos |
| **Pérdida de funcionalidad** | Media | Alto | Checklist por módulo, validación usuario final |
| **Dependencias PyQt rotas** | Baja | Alto | Versiones pinned en requirements.txt, testing CI |

---

## 📦 Dependencias y Configuración

### requirements_pyqt.txt
```txt
# Core PyQt
PyQt6==6.6.1
PyQt6-Charts==6.6.0
PyQt6-WebEngine==6.6.0  # Si necesitas navegador integrado

# Backend (sin cambios)
pillow==10.1.0
libsql-client==0.4.0
dropbox==11.36.2
python-dotenv==1.0.0
requests==2.31.0
PyPDF2==3.0.1

# Opcional: Desarrollo
pyqt6-tools==6.4.2  # Qt Designer
black==23.12.1
pytest==7.4.3
```

### Instalación
```bash
# Crear entorno virtual separado para testing
python -m venv venv_pyqt
venv_pyqt\Scripts\activate

# Instalar dependencias PyQt
pip install -r requirements_pyqt.txt
```

---

## 📚 Recursos de Aprendizaje PyQt

### Tutoriales Recomendados (1-2 semanas estudio)
1. **Qt for Python Official Docs**: https://doc.qt.io/qtforpython/
2. **Real Python PyQt Tutorial**: https://realpython.com/python-pyqt-gui-calculator/
3. **Qt Designer Tutorial**: Diseñar UI visualmente
4. **Signals & Slots Deep Dive**: Entender eventos Qt

### Libros
- "Create GUI Applications with Python & Qt6" - Martin Fitzpatrick
- "Rapid GUI Programming with Python and Qt" - Mark Summerfield

---

## 🎯 Priorización: Si Tiempo Limitado

### Escenario: Solo 3 Meses Disponibles

**Migración Mínima Viable:**

1. **Mes 1:** Preparación + `app.py` principal + Login
2. **Mes 2:** `rma_editor_window.py` (crítico) + managers básicos
3. **Mes 3:** Temas + Testing + Beta release

**Postergar:**
- Módulos estadísticas (migrar en v2.1)
- Ventanas secundarias (migrar en v2.2)

---

## ✅ Checklist de Progreso

### Preparación
- [ ] PyQt6 instalado y funcionando
- [ ] Entorno de desarrollo configurado
- [ ] Qt Designer instalado
- [ ] Tutorial básico PyQt completado
- [ ] Estructura carpetas creada
- [ ] Branch Git `feature/pyqt-migration` creado

### Fase 1: Piloto
- [ ] `changelog_window_qt.py` funcional
- [ ] Primer tema QSS básico aplicado
- [ ] Integración con app.py testeada

### Fase 2: Managers (6 módulos)
- [ ] `estados_manager_qt.py`
- [ ] `personas_manager_qt.py`
- [ ] `personas_recepcion_manager_qt.py`
- [ ] `resultado_expediente_manager_qt.py`
- [ ] `tipos_cliente_manager_qt.py`
- [ ] `avisos_manager_qt.py`

### Fase 3: Ventanas Complejas (6 módulos)
- [ ] `rma_editor_window_qt.py` ⭐ CRÍTICO
- [ ] `ventana_proveedor_qt.py`
- [ ] `proveedor_adjuntos_qt.py`
- [ ] `proveedor_tareas_qt.py`
- [ ] `cliente_condiciones_qt.py`
- [ ] `github_issue_manager_qt.py`

### Fase 4: Estadísticas (7 módulos)
- [ ] `anuales_estadisticas_qt.py`
- [ ] `articulos_estadisticas_qt.py`
- [ ] `cliente_estadisticas_qt.py`
- [ ] `comparativa_ventas_qt.py`
- [ ] `expedientes_quincena_qt.py`
- [ ] `resolucion_estadisticas_qt.py`
- [ ] `client_rentability_qt.py`

### Fase 5: App Principal
- [ ] `app_pyqt.py` - Login funcional
- [ ] `app_pyqt.py` - Dashboard funcional
- [ ] `app_pyqt.py` - Todas las ventanas integradas
- [ ] `app_pyqt.py` - Menús y navegación completa

### Fase 6: Temas y Pulido
- [ ] `w11_modern.qss` creado
- [ ] `w11_blue.qss` creado
- [ ] `teal_corporate.qss` creado
- [ ] Selector de temas funcional
- [ ] Modo claro/oscuro dinámico
- [ ] Iconos y recursos optimizados

### Testing Final
- [ ] Testing funcional completo
- [ ] Testing con usuarios beta
- [ ] Documentación actualizada
- [ ] Guía de migración para usuarios

### Despliegue
- [ ] Versión beta desplegada
- [ ] Feedback recogido y corregido
- [ ] Versión final desplegada
- [ ] Versión CustomTkinter deprecada oficialmente

---

## 📊 Métricas de Éxito

### KPIs para Evaluar Migración

| Métrica | Objetivo | Medición |
|---------|----------|----------|
| **Tiempo de carga** | ≤ versión actual | Cronómetro app startup |
| **Uso de RAM** | ≤ +20% vs actual | Task Manager |
| **Satisfacción usuario** | ≥ 80% positivo | Encuesta post-beta |
| **Bugs críticos** | 0 en producción | Bug tracker |
| **Tiempo renderizado** | ≤ versión actual | Profiler |
| **Curva aprendizaje** | ≤ 1 semana adaptación | Feedback usuarios |

---

## 🔄 Plan de Contingencia

### Si la Migración Falla o se Retrasa

**Plan B: Mantener CustomTkinter a Largo Plazo**

1. **Fork de CustomTkinter:** Crear fork privado del proyecto
2. **Mantenimiento interno:** Correcciones de bugs propias
3. **Congelar versión Tkinter:** Pin de versiones Python compatibles
4. **Monitoreo activo:** Alertas si proyecto original se abandona

**Cuándo activar Plan B:**
- Si migración supera 9 meses
- Si bugs PyQt son críticos e insolubles
- Si usuarios rechazan masivamente nueva UI
- Si recursos de desarrollo se reducen

---

## 💡 Consejos Finales

### Do's ✅
- ✅ Empieza con módulo pequeño (aprendizaje)
- ✅ Testea cada módulo antes de siguiente
- ✅ Mantén versión CustomTkinter funcionando siempre
- ✅ Documenta decisiones de diseño
- ✅ Pide feedback temprano y frecuente
- ✅ Usa Qt Designer para ventanas complejas
- ✅ Aprovecha mejoras Qt (tablas, gráficos nativos)

### Don'ts ❌
- ❌ No migres todo a la vez
- ❌ No borres código CustomTkinter hasta final
- ❌ No ignores warnings/deprecations PyQt
- ❌ No asumas que todo será igual
- ❌ No subestimes curva de aprendizaje
- ❌ No lances a producción sin beta
- ❌ No te rindas en primeras semanas (es normal la frustración inicial)

---

## 📞 Soporte Durante Migración

### Cuando Necesites Ayuda

**Recursos:**
1. **Stack Overflow:** Tag `pyqt6` - comunidad muy activa
2. **Qt Forum:** https://forum.qt.io/category/15/qt-for-python
3. **GitHub PyQt6:** Issues del proyecto oficial
4. **Discord Python:** Canales Qt/GUI
5. **Copilot/IA:** Para conversiones específicas

**Red Flags (pedir ayuda experta):**
- Crashes frecuentes sin razón clara
- Memoria que crece sin control
- Rendimiento 50%+ peor que CustomTkinter
- Funcionalidad imposible de replicar

---

## 🎬 Próximos Pasos Inmediatos

### Esta Semana
1. **Decisión final:** ¿Proceder con migración? ✅/❌
2. **Si SÍ:** Instalar PyQt6 y hacer tutorial básico (2-3 horas)
3. **Si SÍ:** Crear branch Git y estructura carpetas
4. **Si NO:** Implementar Plan B (fork CustomTkinter)

### Próximas 2 Semanas (si procedes)
1. Completar tutorial PyQt oficial
2. Migrar `changelog_window.py` (módulo piloto)
3. Evaluar dificultad real vs estimada
4. Ajustar timeline si necesario

---

## 📈 Visualización del Progreso

```
SEMANAS: 1----5----10---15---20---25---27
         |    |     |    |    |    |    |
FASE 0:  [==]                             Preparación
FASE 1:  ....[====]                       Piloto
FASE 2:  .........[======]                Managers
FASE 3:  ................[=========]      Complejas
FASE 4:  .........................[======] Estadísticas
FASE 5:  ..............................[==] App Principal
FASE 6:  ................................[=] Temas
TESTING: ==================[============]   Continuo
DEPLOY:  .................................[==] Beta → Prod
```

---

## 📝 Conclusión

**Migración a PyQt6 es:**
- ✅ **Viable:** Técnicamente posible
- ✅ **Beneficiosa:** Mejor a largo plazo
- ⚠️ **Costosa:** 3-6 meses trabajo
- ✅ **Recomendada:** Si app tiene vida útil +3 años

**Decisión tuya:** ¿El beneficio a largo plazo justifica la inversión ahora?

**Mi recomendación:** **SÍ, proceder con migración gradual (Opción B de 6 meses)**

---

**Documento vivo:** Actualizar conforme avanza migración.  
**Última revisión:** Enero 2026  
**Próxima revisión:** Al completar Fase 1 (Piloto)
