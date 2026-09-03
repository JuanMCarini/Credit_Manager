"""
Module: main.py
Description: Main entry point for the Credit Manager API.
             Exposes core engine logic securely via RESTful endpoints.
"""

import os
from fastapi import FastAPI, UploadFile, File
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
from src.api.routes.bcra import router as bcra_router
from src.api.routes.finanzas import router as finanzas_router
from src.api.routes.comprobantes import router as comprobantes_router
from src.api.routes.planes import router as planes_router
from src.api.routes.cheques import router as cheques_router
from src.api.routes.posicion_iva import router as posicion_iva_router
from src.api.routes.posicion_iibb import router as posicion_iibb_router
from src.config import API_SETTINGS
from src.database import Base, engine

# -------------------------------------------------------------------
# Inicialización de la Base de Datos
# -------------------------------------------------------------------
import src.database.models.finance.planes # Import to register the model
import src.database.models.finance.posicion_iva # Registrar PosicionIva
import src.database.models.finance.posicion_iibb # Registrar PosicionIibb
Base.metadata.create_all(bind=engine)

# -------------------------------------------------------------------
# Inicialización de la Aplicación
# -------------------------------------------------------------------
from src.api.dependencies.auth import enforce_rbac
from src.api.scheduler import start_scheduler, stop_scheduler
from fastapi import Depends
from src.database import SessionLocal
from src.database.models.socios import SocioComercial
from src.config import COMPANY_DATA

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

from src.database.seed_admin import seed_admin
from src.database.seed_geography import seed_provincias
from src.database.seed_conceptos import seed_conceptos
from src.database.seed_bancos import seed_bancos

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_main_company()
    seed_admin()
    seed_bancos()
    
    try:
        with SessionLocal() as db:
            seed_provincias(db)
            seed_conceptos(db)
    except Exception as e:
        print(f"⚠️ Error executing seeds: {e}")
        
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

os.makedirs("data/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="data/uploads"), name="static")

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
app.include_router(bcra_router)
app.include_router(finanzas_router)
app.include_router(comprobantes_router)
app.include_router(planes_router)
app.include_router(cheques_router)
app.include_router(posicion_iva_router)
app.include_router(posicion_iibb_router)

# -------------------------------------------------------------------
# Frontend (Ahora servido por Nginx)
# -------------------------------------------------------------------
