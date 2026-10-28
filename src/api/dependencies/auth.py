from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone

from src.database.connection import get_db
from src.database.models.auth import Usuario, Rol, TipoRolEnum, RegistroAuditoria
from src.database.models.system import ModuloSistema
from src.config import API_SETTINGS

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = API_SETTINGS.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = API_SETTINGS.access_token_expire_minutes

PUBLIC_PATHS = {
    "/",
    "/api/v1/health",
    "/favicon.ico",
    "/api/auth/login",
    "/docs",
    "/redoc",
    "/openapi.json",
}


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(Usuario).filter(Usuario.email == email).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)


def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme_optional), db: Session = Depends(get_db)
):
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        user = db.query(Usuario).filter(Usuario.email == email).first()
        if user is None or not user.is_active:
            return None
        return user
    except Exception:
        return None


def require_role(allowed_roles: list[TipoRolEnum]):
    def role_checker(current_user: Usuario = Depends(get_current_user)):
        if (
            current_user.rol.nombre not in allowed_roles
            and current_user.rol.nombre != TipoRolEnum.ADMINISTRADOR
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operación no permitida para este rol",
            )
        return current_user
    return role_checker


def audit_log(accion: str):
    def _audit_log(
        request: Request,
        current_user: Usuario = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        log = RegistroAuditoria(
            usuario_id=current_user.id,
            accion=accion,
            endpoint=request.url.path,
            metodo=request.method,
            direccion_ip=request.client.host if request.client else None,
            estado="Éxito",
        )
        db.add(log)
        db.commit()
        return current_user
    return _audit_log


def _resolve_module_code(path: str) -> str | None:
    if path.startswith((
        "/api/v1/clientes",
        "/api/v1/creditos",
        "/api/v1/cobranzas",
        "/api/v1/procesos",
        "/api/v1/carteras",
        "/api/v1/liquidaciones",
        "/api/v1/papeleria",
        "/api/v1/facturacion",
        "/api/v1/bcra",
    )):
        return "creditos"
    if path.startswith("/api/cheques"):
        return "cheques"
    if path.startswith((
        "/api/v1/inversores",
        "/api/v1/series",
        "/api/v1/movimientos-deuda",
        "/api/v1/cuentas-comitentes",
    )):
        return "inversores"
    if path.startswith("/api/finanzas"):
        return "finanzas"
    return None


async def enforce_rbac(request: Request, db: Session = Depends(get_db)):
    """
    Global dependency to enforce authentication, module activation, and Role-Based Access Control.
    """
    if request.method == "OPTIONS":
        return

    path = request.url.path
    if path in PUBLIC_PATHS or path.startswith("/static"):
        return

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = auth_header.split(" ", 1)[1]
    current_user = get_current_user(token=token, db=db)

    # Verificar si el módulo asociado a la ruta está activo
    mod_code = _resolve_module_code(path)
    if mod_code:
        mod = db.query(ModuloSistema).filter(ModuloSistema.codigo == mod_code).first()
        if mod is not None and not mod.activo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"El módulo '{mod.nombre}' se encuentra desactivado.",
            )

    # Consultas de lectura (GET o listado paginado POST de tablas auxiliares) y rutas de sesión propias
    is_aux_data_query = (
        request.method == "POST"
        and path.startswith("/api/v1/auxiliares/")
        and path.endswith("/data")
    )
    if (
        request.method not in ["POST", "PUT", "DELETE", "PATCH"]
        or is_aux_data_query
        or path in ["/api/usuarios/me/password", "/api/auth/logout", "/api/auth/refresh"]
    ):
        return

    rol = current_user.rol.nombre
    
    if rol in [TipoRolEnum.ADMINISTRADOR, TipoRolEnum.GERENTE]:
        pass
    elif rol == TipoRolEnum.AUDITOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Acción no permitida: Los auditores solo tienen acceso de lectura."
        )
    elif rol == TipoRolEnum.OPERADOR_INVERSIONES:
        if not (
            path.startswith("/api/v1/inversores")
            or path.startswith("/api/v1/series")
            or path.startswith("/api/v1/movimientos-deuda")
            or path.startswith("/api/v1/cuentas-comitentes")
            or path.startswith("/api/v1/reports")
            or path.startswith("/api/v1/reportes")
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acción no permitida: Solo puede modificar datos del área de Inversiones."
            )
    elif rol == TipoRolEnum.RESPONSABLE_FINANZAS:
        if not (
            path.startswith("/api/finanzas")
            or path.startswith("/api/cheques")
            or path.startswith("/api/v1/facturacion")
            or path.startswith("/api/v1/reports")
            or path.startswith("/api/v1/reportes")
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acción no permitida: Solo puede modificar datos del área de Finanzas."
            )
    elif rol == TipoRolEnum.OPERADOR_COBRANZAS:
        if not (path.startswith("/api/v1/cobranzas") or path.startswith("/api/v1/procesos")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Acción no permitida: Solo puede modificar cobranzas y procesos de ingesta."
            )
    elif rol == TipoRolEnum.OFICIAL_CREDITO:
        if not (path.startswith("/api/v1/clientes") or path.startswith("/api/v1/creditos")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Acción no permitida: Solo puede modificar clientes y créditos."
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Rol no reconocido."
        )

    # Registramos en auditoría solo si no es de /api/usuarios
    if not path.startswith("/api/usuarios"):
        metodo_str = "Acción"
        if request.method == "POST":
            metodo_str = "Crear"
        elif request.method in ["PUT", "PATCH"]:
            metodo_str = "Editar"
        elif request.method == "DELETE":
            metodo_str = "Borrar"

        entidad_str = "Registro"
        if "clientes" in path:
            entidad_str = "Cliente"
        elif "creditos" in path:
            entidad_str = "Crédito"
        elif "cobranzas" in path:
            entidad_str = "Cobranza"
        elif "procesos" in path:
            entidad_str = "Proceso"
        elif "auxiliares" in path:
            entidad_str = "Tabla Auxiliar"

        partes_ruta = path.rstrip("/").split("/")
        id_registro = ""
        ultima_parte = partes_ruta[-1]
        
        if ultima_parte not in [
            "clientes",
            "creditos",
            "cobranzas",
            "procesos",
            "auxiliares",
            "provincias",
            "empleadores",
            "socios",
            "tasas_y_comisiones",
            "relaciones",
        ]:
            id_registro = f" (ID: {ultima_parte})"
        
        if request.method == "POST" and not id_registro:
            if "application/json" in request.headers.get("content-type", ""):
                try:
                    body = await request.json()
                    if isinstance(body, dict):
                        if "cuil" in body:
                            id_registro = f" (ID: {body['cuil']})"
                        elif "id" in body:
                            id_registro = f" (ID: {body['id']})"
                except Exception:
                    pass

        if request.method == "POST" and path in ["/api/v1/cobranzas/masiva", "/api/v1/cobranzas/individual"]:
            return

        accion_legible = f"{metodo_str} {entidad_str}{id_registro}"

        log = RegistroAuditoria(
            usuario_id=current_user.id,
            accion=accion_legible,
            endpoint=path,
            metodo=request.method,
            direccion_ip=request.client.host if request.client else None,
            estado="Éxito"
        )
        db.add(log)
        db.commit()
