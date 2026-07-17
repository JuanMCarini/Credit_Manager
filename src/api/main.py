"""
Module: main.py
Description: Main entry point for the Credit Manager API.
             Exposes core engine logic securely via RESTful endpoints.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Dict

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
from src.config import API_SETTINGS
from src.database import Base, engine

# -------------------------------------------------------------------
# Inicialización de la Base de Datos
# -------------------------------------------------------------------
Base.metadata.create_all(bind=engine)

# -------------------------------------------------------------------
# Inicialización de la Aplicación
# -------------------------------------------------------------------
from src.api.dependencies.auth import enforce_rbac
from src.api.scheduler import start_scheduler, stop_scheduler
from fastapi import Depends

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()

app = FastAPI(
    title="Credit Manager Core Engine API",
    description="API RESTful para interactuar con el motor financiero de gestión de cartera de créditos.",
    version="1.0.0",
    dependencies=[Depends(enforce_rbac)],
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=API_SETTINGS.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# Endpoints Root
# -------------------------------------------------------------------

@app.get("/", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """
    Endpoint de prueba de estado (health check).
    Retorna 200 OK y el estado general de la aplicación.
    """
    return {"status": "ok", "message": "Credit Manager API is running"}

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

# -------------------------------------------------------------------
# Frontend (Ahora servido por Nginx)
# -------------------------------------------------------------------
