# Guía de Despliegue en Producción - Credit Manager

Esta guía detalla el paso a paso para publicar el sistema **Credit Manager** en internet utilizando una arquitectura moderna, segura y de bajo costo (estimado ~$6 USD/mes), accesible desde un dominio personalizado.

## Arquitectura Propuesta

- **Base de Datos:** [Supabase](https://supabase.com/) (PostgreSQL) - *Costo: $0 (Capa Gratuita)*
- **Archivos (PDFs/Legajos):** [AWS S3](https://aws.amazon.com/s3/) (Amazon) - *Costo: ~$0.20 USD/mes*
- **Backend (Python/FastAPI):** [Railway](https://railway.app/) - *Costo: ~$5 USD/mes (Plan Hobby)*
- **Frontend (React):** [Vercel](https://vercel.com/) o [Netlify](https://www.netlify.com/) - *Costo: $0 (Capa Gratuita)*
- **Dominio:** Tu dominio propio (ej. `neocredit.com`) conectado al Frontend.

---

## Paso 0: Ajustes Críticos de Seguridad (Previo al Despliegue)

Antes de subir el código a los servicios externos, **es obligatorio** tener en cuenta estos ajustes para garantizar la seguridad en producción:

1. **Entorno y Cookies Seguras (Autenticación):**
   - El código ahora detecta automáticamente si está en producción. En Railway, debes crear la variable de entorno `API_ENVIRONMENT=production`. 
   - Al hacer esto, el sistema forzará que todas las cookies de sesión se envíen de forma segura (`secure=True` vía HTTPS) para que no fallen entre Vercel y Railway.

2. **Secretos Fuertes (JWT):**
   - Si `API_ENVIRONMENT=production` está activo, la API **se negará a arrancar** si detecta que usas la clave secreta por defecto.
   - Durante el despliegue en Railway, asegúrate de definir `API_SECRET_KEY` con un valor largo y aleatorio (ej. generado con `openssl rand -hex 32`).

3. **Orígenes CORS Estrictos:**
   - La API permite peticiones desde `localhost` por defecto. 
   - En Railway, crea la variable de entorno `API_ALLOWED_ORIGINS` y asígnale el dominio exacto de tu frontend en Vercel (ej. `https://sistema.neocredit.com`).

4. **Almacenamiento de Archivos (AWS S3 / R2):**
   - Actualmente el código guarda las imágenes y legajos localmente en `data/uploads/`. 
   - Como los servicios en la nube como Railway son efímeros (borran su disco al reiniciarse), **es obligatorio** implementar un servicio como AWS S3 en el código backend antes de salir a producción para no perder datos.

---

## Paso 1: Configurar la Base de Datos (Supabase)

1. Ingresa a [Supabase.com](https://supabase.com/) y crea una cuenta gratuita.
2. Crea un nuevo proyecto (ej. `credit-manager-db`). Al crearlo, te dará una contraseña para la base de datos (**¡guárdala bien y usa una contraseña muy fuerte generada aleatoriamente!**).
3. Una vez creado el proyecto, ve a **Project Settings -> Database**.
4. Copia el **Connection String (URI)**.
5. Modifica tu archivo `.env` local (o configúralo en tu entorno de producción) para reemplazar SQLite por la nueva base de datos de Supabase. Debería verse algo así:
   ```env
   DB_USER=postgres
   DB_PASSWORD=[TU_PASSWORD_SUPER_FUERTE]
   DB_HOST=[TU_HOST].supabase.co
   DB_PORT=5432
   DB_NAME=postgres
   ```
6. **Seguridad (Opcional pero recomendado):** En Supabase, ve a `Network Restrictions` y restringe el acceso a la base de datos únicamente a las IPs públicas de tu backend en Railway, para evitar ataques de fuerza bruta externos.
7. Ejecuta Alembic o el script de inicialización de SQLAlchemy de tu proyecto local para crear todas las tablas en la nube de Supabase automáticamente.

---

## Paso 2: Configurar Almacenamiento en la Nube (AWS S3)

Dado que el sistema de archivos de Railway es **efímero** (se borra en cada actualización o reinicio del servidor), **es obligatorio implementar un almacenamiento externo como Amazon S3 o Cloudflare R2 antes de salir a producción**, para evitar la pérdida de PDFs, legajos e imágenes subidas localmente (carpeta `data/uploads`).

1. Crea una cuenta en [AWS Console](https://aws.amazon.com/).
2. Ve al servicio **S3** y crea un nuevo **Bucket** (ej. `credit-manager-legajos`).
3. **¡IMPORTANTE - SEGURIDAD!:** Asegúrate de que la configuración **"Block all public access"** esté **activada**. Los archivos (DNI, Legajos) son sumamente sensibles y bajo ninguna circunstancia el bucket debe ser público.
4. Ve a **IAM (Identity and Access Management)** y crea un usuario de acceso programático. Otórgale permisos exclusivos para leer y escribir en el bucket que acabas de crear.
5. Anota el `AWS_ACCESS_KEY_ID` y el `AWS_SECRET_ACCESS_KEY`.
6. Implementa Boto3 (o una librería compatible con S3) en el backend y refactoriza la carga de archivos para subirlos al Bucket. Para visualizarlos, deberás usar "Pre-signed URLs" para que el frontend pueda descargar los archivos temporalmente de manera 100% segura.

---

## Paso 3: Desplegar el Backend (Railway)

1. Sube tu código (backend y frontend) a un repositorio privado en **GitHub**. **ATENCIÓN: Asegúrate de NUNCA subir el archivo `.env`. El archivo `.dockerignore` y `.gitignore` ya deberían estar configurados para excluirlo.**
2. Ingresa a [Railway.app](https://railway.app/) y vincula tu cuenta de GitHub.
3. Haz clic en **New Project -> Deploy from GitHub repo**. Selecciona el repositorio de Credit Manager.
4. Railway detectará automáticamente el archivo `requirements.txt` o `Dockerfile` e intentará construir el entorno de Python.
5. Ve a la pestaña **Variables** en Railway y pega manualmente cada una de las variables de entorno que necesites en producción (Base de datos, tokens, CORS, etc.).
6. Ve a la pestaña **Settings -> Networking** y haz clic en **Generate Domain**. Railway te dará una URL pública para tu API (ej. `credit-manager-production.up.railway.app`). ¡Anota esta URL!

---

## Paso 4: Desplegar el Frontend (Vercel)

1. Ingresa a [Vercel.com](https://vercel.com/) y vincula tu cuenta de GitHub.
2. Haz clic en **Add New -> Project** y selecciona tu repositorio.
3. Como el proyecto es un monorepo, asegúrate de configurar en Vercel que el "Root Directory" o directorio principal de ejecución es la carpeta `frontend`.
4. En **Environment Variables**, debes configurar la URL del backend que acabamos de crear en Railway:
   ```env
   VITE_API_URL="https://credit-manager-production.up.railway.app"
   ```
5. Haz clic en **Deploy**. Vercel compilará la aplicación de React y te dará una URL pública temporal (ej. `credit-manager.vercel.app`).

---

## Paso 5: Conectar el Dominio Personalizado

1. Ve a la configuración de tu proyecto Frontend en **Vercel**.
2. Dirígete a **Settings -> Domains**.
3. Añade el subdominio que quieras usar (ej. `sistema.neocredit.com`).
4. Vercel te dará unas instrucciones (Registros DNS tipo CNAME o A).
5. Ingresa a tu proveedor de dominios (donde compraste `@neocredit`) y ve a la sección de **Gestión DNS**.
6. Agrega el registro CNAME que Vercel te indicó apuntando a `cname.vercel-dns.com.`.
7. En unos minutos, el dominio propagará. Podrás escribir `https://sistema.neocredit.com` en cualquier navegador y verás tu aplicación cargando.

---

## Resumen Final

Si realizaste todos los pasos correctamente:
- Tu dominio `sistema.neocredit.com` carga los archivos alojados en la red global de **Vercel**.
- Vercel se comunica con el backend de Python alojado en **Railway**.
- El backend lee, guarda clientes y procesa cobranzas conectándose a **Supabase**.
- Todo funciona de manera integrada, segura, escalable y con respaldos automáticos.
