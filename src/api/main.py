"""
Module: main.py
Description: Main entry point for the Credit Manager API.
             Exposes core engine logic securely via RESTful endpoints.
"""

import os
import shutil
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Dict

from sqlalchemy import text

# Import routers
from src.api.routes.reportes import router as reportes_router
from src.api.routes.clientes import router as clientes_router
from src.api.routes.creditos import router as creditos_router
from src.api.routes.cobranzas import router as cobranzas_router
from src.api.routes.auxiliares import router as auxiliares_router
from src.api.routes.system import router as system_router
from src.api.routes.carteras import router as carteras_router
from src.api.routes.auth import router as auth_router
from src.api.routes.usuarios import router as usuarios_router
from src.api.routes.liquidaciones import router as liquidaciones_router
from src.api.routes.papeleria import router as papeleria_router
from src.api.routes.facturacion import router as facturacion_router
from src.api.routes.bcra import router as bcra_router
from src.api.routes.finanzas import router as finanzas_router
from src.api.routes.comprobantes import router as comprobantes_router
from src.api.routes.planes import router as planes_router
from src.api.routes.cheques import router as cheques_router
from src.api.routes.posicion_iva import router as posicion_iva_router
from src.api.routes.inversores import router as inversores_router
from src.api.routes.posicion_iibb import router as posicion_iibb_router
from src.config import API_SETTINGS, COMPANY_DATA
from src.database import Base, engine, SessionLocal
from src.database.models.socios import SocioComercial

# -------------------------------------------------------------------
# Registro de Modelos de la Base de Datos
# -------------------------------------------------------------------
import src.database.models.finance.planes  # noqa: F401
import src.database.models.finance.posicion_iva  # noqa: F401
import src.database.models.finance.posicion_iibb  # noqa: F401
import src.database.models.system  # noqa: F401

# -------------------------------------------------------------------
# Inicialización de la Aplicación
# -------------------------------------------------------------------
from src.api.dependencies.auth import enforce_rbac, get_current_user
from src.api.routes.system import download_uploaded_file, PUBLIC_ASSETS_DIR, UPLOADS_BASE_DIR
from src.database.models.auth import Usuario
from src.api.scheduler import advisory_file_lock, start_scheduler, stop_scheduler
from src.database.seed_admin import seed_admin
from src.database.seed_geography import seed_provincias
from src.database.seed_conceptos import seed_conceptos
from src.database.seed_bancos import seed_bancos
from src.database.seed_modulos import seed_modulos

_STARTUP_LOCK_ID = 74839201
_STARTUP_LOCK_FILE = Path("data/.startup.lock")


@contextmanager
def _startup_db_lock(bind_engine):
    """Serializa la creación de esquema y seeds iniciales entre workers concurrentes."""
    with advisory_file_lock(_STARTUP_LOCK_FILE, blocking=True):
        pg_conn = None
        pg_locked = False
        if bind_engine is not None and bind_engine.dialect.name == "postgresql":
            try:
                pg_conn = bind_engine.connect()
                pg_conn.execute(text(f"SELECT pg_advisory_lock({_STARTUP_LOCK_ID})"))
                pg_locked = True
            except Exception as exc:
                print(f"⚠️ No se pudo adquirir advisory lock de PostgreSQL al iniciar: {exc}")
                if pg_conn is not None:
                    pg_conn.close()
                    pg_conn = None
        try:
            yield
        finally:
            if pg_conn is not None:
                try:
                    if pg_locked:
                        pg_conn.execute(text(f"SELECT pg_advisory_unlock({_STARTUP_LOCK_ID})"))
                except Exception:
                    pass
                finally:
                    pg_conn.close()


def init_main_company():
    try:
        with SessionLocal() as db:
            socio = db.query(SocioComercial).filter(SocioComercial.cuit == COMPANY_DATA.cuit).first()
            if not socio:
                SocioComercial.create_socio(
                    razon_social=COMPANY_DATA.razon_social,
                    cuit=COMPANY_DATA.cuit,
                    db=db,
                    domicilio_legal=COMPANY_DATA.domicilio,
                    mail=COMPANY_DATA.email_contacto,
                    telefono=COMPANY_DATA.telefono,
                    cbu=COMPANY_DATA.cbu,
                    nro_cuenta_bancaria=COMPANY_DATA.bank_account,
                    nombre_banco=COMPANY_DATA.bank_name,
                    dia_corte=COMPANY_DATA.dia_corte
                )
                print(f"✅ Empresa principal '{COMPANY_DATA.razon_social}' creada automáticamente en la base de datos.")
    except Exception as e:
        print(f"⚠️ Error al inicializar la empresa principal: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    with _startup_db_lock(engine):
        try:
            Base.metadata.create_all(bind=engine)
            from src.database.models.creditos.facturacion import ensure_facturas_schema
            ensure_facturas_schema(engine)
        except Exception as e:
            print(f"⚠️ Error creando esquema de base de datos: {e}")

        init_main_company()
        seed_admin()
        seed_bancos()

        try:
            with SessionLocal() as db:
                for seed_name, seed_fn in (
                    ("provincias", seed_provincias),
                    ("conceptos", seed_conceptos),
                    ("modulos", seed_modulos),
                ):
                    try:
                        seed_fn(db)
                    except Exception as e:
                        db.rollback()
                        print(f"⚠️ Error executing seed '{seed_name}': {e}")
        except Exception as e:
            print(f"⚠️ Error abriendo sesión para seeds iniciales: {e}")

    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()


_is_production = API_SETTINGS.env.strip().lower() == "production"

app = FastAPI(
    title="Credit Manager Core Engine API",
    description="API RESTful para interactuar con el motor financiero de gestión de cartera de créditos.",
    version="1.0.0",
    dependencies=[Depends(enforce_rbac)],
    lifespan=lifespan,
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=API_SETTINGS.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()"
    )
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response

os.makedirs("data/uploads", exist_ok=True)
os.makedirs("data/public", exist_ok=True)

# Migrar activos públicos institucionales (logo/favicon) a data/public si existían en data/uploads
for _public_asset in ("logo.png", "favicon.png", "favicon.ico"):
    _src_asset = UPLOADS_BASE_DIR / _public_asset
    _dst_asset = PUBLIC_ASSETS_DIR / _public_asset
    if _src_asset.is_file() and not _dst_asset.is_file():
        try:
            shutil.copy2(_src_asset, _dst_asset)
        except OSError:
            pass

# -------------------------------------------------------------------
# Endpoints Root, Health & Descarga Segura de Archivos
# -------------------------------------------------------------------

@app.get("/", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"])
def health_check() -> Dict[str, str]:
    """
    Endpoint de prueba de estado (health check).
    Retorna 200 OK y el estado general de la aplicación.
    """
    return {"status": "ok", "message": "Credit Manager API is running"}


@app.get("/favicon.ico", include_in_schema=False)
def get_favicon():
    for candidate in (
        PUBLIC_ASSETS_DIR / "favicon.ico",
        PUBLIC_ASSETS_DIR / "favicon.png",
        UPLOADS_BASE_DIR / "favicon.ico",
        UPLOADS_BASE_DIR / "favicon.png",
    ):
        if candidate.is_file():
            return FileResponse(str(candidate))
    return Response(status_code=204)


@app.get("/api/v1/uploads/{categoria}/{filename}", tags=["Uploads"])
def get_uploaded_file(
    categoria: str,
    filename: str,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Descarga autenticada de documentos en data/uploads/{categoria}/{filename}
    con validación estricta contra Path Traversal.
    """
    return download_uploaded_file(categoria=categoria, filename=filename, current_user=current_user)

# -------------------------------------------------------------------
# Registro de Routers
# -------------------------------------------------------------------

app.include_router(auth_router)
app.include_router(clientes_router)
app.include_router(creditos_router)
app.include_router(reportes_router)
app.include_router(cobranzas_router)
app.include_router(auxiliares_router)
app.include_router(system_router)
app.include_router(carteras_router)
app.include_router(usuarios_router)
app.include_router(liquidaciones_router)
app.include_router(papeleria_router)
app.include_router(facturacion_router)
app.include_router(bcra_router)
app.include_router(finanzas_router)
app.include_router(comprobantes_router)
app.include_router(planes_router)
app.include_router(cheques_router)
app.include_router(posicion_iva_router)
app.include_router(inversores_router)
app.include_router(posicion_iibb_router)
