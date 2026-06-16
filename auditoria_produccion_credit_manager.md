# Auditoría de Producción: Credit Manager

## Auditoría de Arquitectura Actual
El estado actual del código evidencia un diseño funcional y focalizado en solucionar las necesidades de negocio (cálculos financieros robustos usando `numpy_financial` y abstracciones de dominio adecuadas). Sin embargo, la arquitectura técnica presenta un alto grado de acoplamiento, deuda técnica severa en el frontend y carencias críticas de escalabilidad y seguridad para un entorno productivo financiero. El sistema no se encuentra listo para un pase a producción sin intervenciones estructurales; persisten prácticas de prototipado (como el uso de SQLite y endpoints monolíticos) que comprometen el rendimiento bajo concurrencia y la seguridad de los datos.

---

## Mejoras Propuestas (Por Dominio)

### Backend (Python/FastAPI)
1. **Archivo:** `src/api/main.py`
   - **Problema:** Monolito de más de 1800 líneas. Mezcla definición de Pydantic models, rutas, lógica de negocio e integración con la base de datos.
   - **Solución:** Implementar `APIRouter` de FastAPI para modularizar los endpoints por dominio (`routers/clientes.py`, `routers/creditos.py`, `routers/reportes.py`). Mover los esquemas Pydantic a un paquete `schemas/`.
2. **Archivo:** `src/api/main.py`
   - **Problema:** Riesgo de bloqueo del Event Loop. Uso de métodos `def` síncronos y `async def` inyectando una sesión de SQLAlchemy síncrona, lo cual bloqueará la concurrencia asíncrona natural de FastAPI.
   - **Solución:** Migrar a `asyncio` nativo en la base de datos con controladores asincrónicos (ej. `asyncpg`) o aislar operaciones síncronas pesadas usando `run_in_threadpool`.
3. **Archivo:** `src/api/main.py` (y módulos de lógica)
   - **Problema:** Configuración de CORS estática orientada a desarrollo (`allow_origins=["http://localhost:5173", ...]`).
   - **Solución:** Leer dominios permitidos desde variables de entorno (`config.py`) para admitir dominios productivos garantizando seguridad.

### Base de Datos
1. **Archivo:** `src/database/connection.py`
   - **Problema:** Uso de SQLite (`sqlite:///.../credit_manager.db`) para almacenamiento de datos financieros. Inadecuado para concurrencia, sin control de roles/accesos nativo y complejo para backups transaccionales continuos.
   - **Solución:** Migrar el motor a PostgreSQL. Actualizar el `SQLALCHEMY_DATABASE_URL` para ingerir credenciales seguras mediante las variables de entorno ya predispuestas en Pydantic `BaseSettings`.
2. **Archivo:** `src/api/main.py` (Endpoints de consultas, ej. `get_cliente_cuenta_corriente`)
   - **Problema:** Problemas severos de Query N+1. Bucles anidados (`for c in cliente.creditos: for cuota in c.cuotas: ... cuota.cobranzas`) provocan múltiples round-trips a la BD por cada registro.
   - **Solución:** Usar `joinedload` o `selectinload` de SQLAlchemy para pre-cargar las relaciones en una única consulta SQL optimizada.

### Frontend (React/Vite)
1. **Archivo:** `frontend/main.js` vs `frontend/package.json`
   - **Problema:** Discrepancia estructural severa. El `package.json` instala React, React-DOM y Zustand, pero el archivo `main.js` (de más de 3600 líneas) utiliza Vanilla JS puro para manipular el DOM directamente (`document.querySelectorAll`, `innerHTML`).
   - **Solución:** Refactorizar el frontend transformando el código Vanilla JS en verdaderos componentes funcionales React (`.jsx`), utilizando `Zustand` real para el estado global y `react-router-dom` para la navegación.

---

## Estrategia de Despliegue

### Configuración Previa
1. **Gestión de Dependencias (`requirements.txt`)**: Depurar paquetes de desarrollo inyectados en la lista (como `jupyter_client`, `ipython`, `notebook`). Dividir en `requirements.txt` (solo dependencias runtime productivas) y `requirements-dev.txt`.
2. **Servidor ASGI**: No exponer `uvicorn` crudo. Usar **Gunicorn** con `uvicorn.workers.UvicornWorker` para orquestar múltiples procesos trabajadores, aprovechando todos los núcleos del servidor.

### Infraestructura, Contenerización y Hosting
Para gestionar datos financieros sensibles, se requiere aislamiento, escalabilidad y alta seguridad.

1. **Contenerización (Docker)**: Crear un `Dockerfile` multietapa para compilar el frontend, y un `Dockerfile` dedicado para el backend en Python. Orquestarlos en desarrollo con `docker-compose.yml`.
2. **Alojamiento Cloud Propuesto (AWS / GCP)**:
   - **Base de Datos**: Amazon RDS for PostgreSQL (o Cloud SQL). Asegura backups automatizados (Point-in-Time Recovery) y cifrado en reposo (KMS).
   - **Backend**: Amazon ECS (Elastic Container Service) sobre AWS Fargate o Google Cloud Run. Son plataformas Serverless para contenedores, lo que reduce la carga operativa y escala automáticamente el backend según el tráfico sin latencia de cold-starts si se configura un mínimo de instancias.
   - **Frontend**: Amazon S3 + CloudFront (o servicios como Vercel/Netlify), lo cual distribuye los archivos estáticos mediante una CDN global para latencia ultrabaja y los protege de inyecciones servidoras directas.

---

## Plan de Acción Priorizado

**Prioridad Alta (Crítica para viabilidad)**
1. **Migración a PostgreSQL**: Abandonar SQLite, implementar el motor robusto y resolver las ineficiencias de consultas (N+1) en SQLAlchemy mediante *Eager Loading*.
2. **Contenerización Básica**: Creación de `Dockerfile` para el backend y preparación del WSGI/ASGI con Gunicorn.

**Prioridad Media (Mantenibilidad y Estabilidad)**
3. **Refactorización de `main.py`**: Separar endpoints mediante `APIRouter` e implementar esquemas Pydantic modulares.
4. **Desacople Frontend/Vanilla JS a React**: Migrar progresivamente el gigantesco DOM script (`main.js`) a componentes de React formales y configurar Zustand para el manejo de estado.

**Prioridad Baja (Optimización Continua)**
5. **Configuración CI/CD & Cloud**: Preparar infraestructura como código (Terraform o configuraciones manuales iniciales en la nube elegida).
6. **Limpieza de Dependencias**: Pulir `requirements.txt`.

¿Qué punto del Plan de Acción priorizado deseas abordar primero?
