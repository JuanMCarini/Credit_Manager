"""
Module: main.py
Description: Main entry point for the Credit Manager API.
             Exposes core engine logic securely via RESTful endpoints.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict

# Import routers
from src.api.routes.reportes import router as reportes_router
from src.api.routes.clientes import router as clientes_router
from src.api.routes.creditos import router as creditos_router
from src.api.routes.cobranzas import router as cobranzas_router
from src.api.routes.auxiliares import router as auxiliares_router
from src.api.routes.system import router as system_router
from src.api.routes.carteras import router as carteras_router

# -------------------------------------------------------------------
# Inicialización de la Aplicación
# -------------------------------------------------------------------
app = FastAPI(
    title="Credit Manager Core Engine API",
    description="API RESTful para interactuar con el motor financiero de gestión de cartera de créditos.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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

app.include_router(clientes_router)
app.include_router(creditos_router)
app.include_router(reportes_router)
app.include_router(cobranzas_router)
app.include_router(auxiliares_router)
app.include_router(system_router)
app.include_router(carteras_router)

# -------------------------------------------------------------------
# Frontend
# -------------------------------------------------------------------
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")
