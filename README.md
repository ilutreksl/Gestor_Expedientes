# 📋 Gestor de Expedientes - ILUTREK S.L.

## 🚀 Aplicación de Gestión de Expedientes RMA

Sistema completo para la gestión de expedientes de devolución de mercancías (RMA) con dashboard analítico, exportación a Excel, rellenado de PDFs y sistema de trazabilidad automática.

---

## 📦 INSTALACIÓN DE DEPENDENCIAS

### **⚡ INSTALACIÓN RÁPIDA (Recomendada)**

Copia y ejecuta este comando en tu terminal para instalar todas las librerías necesarias:

```bash
pip install customtkinter Pillow CTkDatePicker bcrypt python-dotenv python-docx requests pandas pypdf win10toast pdfrw reportlab docx2pdf extract-msg pyspellchecker qrcode
```

### **📋 LIBRERÍAS OBLIGATORIAS**

Si prefieres instalar una por una:

```bash
# Manejo Backblaze S2
pip install b2sdk

# Interfaz gráfica moderna
pip install customtkinter

# Manejo de imágenes 
pip install Pillow

# Selector de fechas personalizado
pip install CTkDatePicker

# Seguridad y encriptación
pip install bcrypt

# Variables de entorno
pip install python-dotenv

# Manipulación de documentos Word
pip install python-docx

# Solicitudes HTTP (para Turso Cloud DB)
pip install requests

# Exportación a Excel (IMPRESCINDIBLE)
pip install pandas

# Rellenado de formularios PDF
pip install pypdf

# Notificaciones de Windows
pip install win10toast

# Graficos en excel
pip install matplotlib

# Word a PDF
pip install docx2pdf

# Importar correos .msg (Outlook) como correos asociados al expediente
pip install extract-msg

# Corrector ortográfico del editor de Observaciones Técnicas
pip install pyspellchecker

# Generación de QR de recepción en el documento de Autorización
pip install qrcode[pil]
```

### **📋 LIBRERÍAS OPCIONALES (Mejoran funcionalidad)**

```bash
# Para rellenado PDF alternativo más robusto
pip install pdfrw

# Para generar PDFs con mejor formato
pip install reportlab
```

---

## 🏗️ LIBRERÍAS INCLUIDAS EN PYTHON

Estas librerías ya están incluidas en Python y NO necesitas instalarlas:

- ✅ `tkinter` - Interfaz gráfica base
- ✅ `sqlite3` - Base de datos local
- ✅ `os` - Operaciones del sistema
- ✅ `sys` - Sistema Python
- ✅ `datetime` - Manejo de fechas
- ✅ `webbrowser` - Abrir navegador
- ✅ `locale` - Configuración regional
- ✅ `shutil` - Operaciones de archivos
- ✅ `subprocess` - Ejecutar comandos
- ✅ `threading` - Hilos de ejecución
- ✅ `json` - Manejo de JSON

---

## 🔧 CONFIGURACIÓN DE BASE DE DATOS

La aplicación soporta dos modos de base de datos:

### **🌐 Turso Cloud Database (Recomendado para equipos)**

Crea un archivo `.env` en la carpeta del proyecto con:

```env
TURSO_DATABASE_URL=libsql://tu-database-url.turso.io
TURSO_AUTH_TOKEN=tu-token-de-autenticacion
```

### **💾 SQLite Local (Por defecto)**

Si no configuras Turso, la aplicación usará automáticamente una base de datos SQLite local.

### **📱 Recepción de paquetes por QR (requiere Turso)**

Además de Turso, añade en el `.env`:

```env
QR_RECEPCION_HMAC_SECRET=mismo-secreto-que-el-HMAC_SECRET-del-Worker
QR_RECEPCION_WORKER_URL=https://tu-worker.tu-subdominio.workers.dev
```

`QR_RECEPCION_HMAC_SECRET` debe coincidir exactamente con el secreto `HMAC_SECRET` configurado en el Worker de Cloudflare (ver `cloudflare-worker-recepcion/`) — es lo que permite firmar y verificar los QR en ambos lados.

Opcional, para ver en el panel de Storage cuántas peticiones diarias lleva consumidas el Worker:

```env
CLOUDFLARE_API_TOKEN=token-de-solo-lectura-de-analytics
CLOUDFLARE_ACCOUNT_ID=id-de-tu-cuenta-de-cloudflare
```

El token se crea en https://dash.cloudflare.com/profile/api-tokens con permiso **Account → Account Analytics → Read** (no necesita permisos de escritura).

---

## 🚀 EJECUCIÓN

### **Método 1: Archivo Python**
```bash
python app.py
```

### **Método 2: Archivo Ejecutable**
```bash
python Gestor_Expedientes.pyw
```

---

## ✨ CARACTERÍSTICAS PRINCIPALES

### **📊 Dashboard Analítico**
- 📈 Estadísticas en tiempo real por estado y año
- 🔍 Top 10 artículos problemáticos con análisis temporal
- 🎯 Visualización compacta (200px de ancho)

### **🔄 Sistema de Trazabilidad Automática**
- **Automático**: Al completar "Fecha Proceso" → Estado cambia a "En Trámite"
- **Jerarquía inteligente**: Completado → En Trámite → Recibido → Autorizado → Pendiente

### **📤 Exportación Avanzada a Excel**
- 📋 Dos hojas: Lista completa + Resumen estadístico
- 🎨 Formato profesional con colores y estilos
- 🔍 Filtros y totales automáticos

### **🤖 Confirmaciones Inteligentes**
- ⚠️ Validación automática de tareas pendientes
- 💡 Sugerencias contextuales antes de completar expedientes

### **📄 Rellenado de PDFs**
- 📝 Relleno automático de formularios PDF
- 🔧 Soporte para múltiples métodos de rellenado
- 📁 Gestión automática de archivos generados

### **🔔 Notificaciones**
- 🎯 Notificaciones nativas de Windows
- ⏰ Alertas contextuales del sistema

---

## 📁 ESTRUCTURA DEL PROYECTO

```
Gestor_Expedientes/
├── app.py                     # Aplicación principal
├── Gestor_Expedientes.pyw     # Ejecutable Windows
├── README.md                  # Este archivo
├── user_settings.json         # Configuración de usuario
├── .env                       # Variables de entorno (crear manualmente)
├── CTkDatePicker/             # Componente de fecha personalizado
├── icons/                     # Iconos de la aplicación
├── lib/
│   └── pdf_fill.py           # Funciones de rellenado PDF
├── plantillas/               # Plantillas PDF
├── themes/                   # Temas de la aplicación
├── Adjuntos_RMA/            # Archivos adjuntos de expedientes
└── scripts/                 # Scripts de utilidad
```

---

## 🛠️ RESOLUCIÓN DE PROBLEMAS

### **❌ Error: "customtkinter not found"**
```bash
pip install customtkinter
```

### **❌ Error: "pandas not found"**
```bash
pip install pandas
# Sin pandas, la exportación a Excel estará deshabilitada
```

### **❌ Error: "PIL/Pillow not found"**
```bash
pip install Pillow
```

### **❌ Error: Problemas con base de datos**
- Verifica las credenciales de Turso en el archivo `.env`
- La aplicación creará automáticamente la base de datos SQLite local si Turso no está disponible

---

## 👥 EQUIPO DE DESARROLLO

- **Empresa**: ILUTREK S.L.
- **Sistema**: Gestor de Expedientes RMA
- **Versión**: 2025.11
- **Tecnología**: Python + CustomTkinter + Turso/SQLite

---

## 📞 SOPORTE

Para cualquier problema o consulta:

1. 🔍 Verifica que todas las librerías estén instaladas
2. 📧 Contacta con el administrador del sistema
3. 🐛 Reporta errores con capturas de pantalla

---

## 🔄 CHANGELOG

### **✨ Últimas mejoras implementadas:**
- 🔄 Sistema de trazabilidad automática "En Trámite"
- 📊 Dashboard analítico con estadísticas en tiempo real
- 🤖 Confirmaciones inteligentes con validación de tareas
- 📊 Análisis de artículos problemáticos por períodos
- 💾 Soporte para decimales en cantidades de artículos
- 📤 Exportación Excel mejorada con formato profesional

---

¡Listo para usar! 🚀