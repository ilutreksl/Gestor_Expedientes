# 🚀 Guía de Migración a Turso

## ✅ Completado hasta ahora:

- ✅ Código adaptado para usar Turso o SQLite local
- ✅ Dependencias Python instaladas (`libsql-client`, `python-dotenv`)
- ✅ Base de datos exportada a `turso_dump.sql`

---

## 📋 Pasos siguientes (requieren conexión a internet):

### **1. Crear cuenta en Turso (desde el navegador)**

**NOTA:** El CLI de Turso no tiene versión nativa para Windows. Usaremos la interfaz web que es más sencilla.

1. Ve a: **https://turso.tech/**
2. Haz clic en **"Sign Up"** o **"Get Started"**
3. Regístrate con tu email o GitHub
4. Confirma tu email si es necesario

---

### **2. Crear la base de datos desde el Dashboard**

1. Una vez dentro del dashboard de Turso (https://app.turso.tech/)
2. Haz clic en **"Create Database"** o **"New Database"**
3. Nombre: **`gestor-rma`**
4. Región: Elige **"Europe"** (Frankfurt o similar, más cerca de España)
5. Haz clic en **"Create"**

---

### **3. Importar tus datos**

Desde el dashboard web de Turso:

1. Selecciona tu base de datos **`gestor-rma`**
2. Ve a la pestaña **"SQL Editor"** o **"Shell"**
3. Abre el archivo **`turso_dump.sql`** con un editor de texto (Notepad++)
4. Copia TODO el contenido del archivo
5. Pégalo en el editor SQL del dashboard
6. Haz clic en **"Execute"** o **"Run"**

**Alternativa - Importar por secciones:**
Si el archivo es muy grande, puedes:
- Copiar y ejecutar las primeras 100-200 líneas
- Luego las siguientes 100-200 líneas
- Y así sucesivamente hasta completar

---

### **4. Obtener credenciales**

Desde el dashboard de tu base de datos `gestor-rma`:

**a) URL de la base de datos:**
- En la página principal de tu BD, verás una sección **"Connection"** o **"Database URL"**
- Copia la URL completa (ejemplo: `libsql://gestor-rma-usuario.turso.io`)

**b) Token de autenticación:**
- En la misma página, busca **"Create Token"** o **"API Tokens"**
- Haz clic en **"Create Token"** o **"Generate Token"**
- Copia el token completo que aparece (ejemplo: `eyJhbGciOiJFZERTQSIs...`)
- ⚠️ **IMPORTANTE:** Guarda este token, solo se muestra una vez

---

### **6. Configurar variables de entorno**

Crea un archivo `.env` en la raíz del proyecto (al lado de `app.py`) con este contenido:

```env
TURSO_DATABASE_URL=libsql://gestor-rma-XXXX.turso.io
TURSO_AUTH_TOKEN=eyJhbGciOiJFZERTQSIs...
```

**Reemplaza** los valores `XXXX` con los que obtuviste en el paso 5.

---

### **7. Probar la aplicación**

Simplemente ejecuta tu aplicación como siempre:

```powershell
python app.py
```

La aplicación detectará automáticamente el archivo `.env` y se conectará a Turso.

---

## 🔧 Solución de problemas

### La app no se conecta a Turso:
- Verifica que el archivo `.env` existe en la raíz del proyecto
- Verifica que las credenciales en `.env` son correctas
- Revisa la consola por mensajes de advertencia `[WARN]`

### Quiero volver a SQLite local:
- Simplemente renombra o elimina el archivo `.env`
- La app volverá a usar `rma_app.db` automáticamente

### Error al importar datos:
- Asegúrate de que `turso_dump.sql` está en la raíz del proyecto
- Prueba importar desde el dashboard web de Turso (https://turso.tech)

---

## 📊 Verificar que todo funciona

Una vez conectado a Turso, puedes verificar que tus datos están ahí:

```powershell
turso db shell gestor-rma "SELECT COUNT(*) FROM rma_maestro;"
```

---

## 🎯 Ventajas de usar Turso

- ✅ **Múltiples usuarios simultáneos** sin bloqueos
- ✅ **5 GB gratuitos** (vs 500 MB de otras opciones)
- ✅ **Backups automáticos** (1 día de Point-in-Time Restore)
- ✅ **Acceso desde cualquier lugar**
- ✅ **Sin configuración de servidor**

---

## ⚠️ Importante

- Tu base de datos local `rma_app.db` **NO se modifica**
- Si algo falla, simplemente borra `.env` y seguirás usando SQLite local
- Turso es **gratuito** para tu caso de uso (plan FREE)

---

¿Dudas? Consulta la documentación oficial: https://docs.turso.tech/
