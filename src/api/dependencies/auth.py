from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone

from src.database.connection import get_db
from src.database.models.auth import Usuario, Rol, TipoRolEnum, RegistroAuditoria
from src.config import DATABASE_SETTINGS, API_SETTINGS

class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> str | None:
        authorization: str = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            # Fallback to cookie
            param = request.cookies.get("access_token")

        if not param:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return param

oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="api/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=API_SETTINGS.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, API_SETTINGS.secret_key, algorithm=API_SETTINGS.algorithm)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, API_SETTINGS.secret_key, algorithms=[API_SETTINGS.algorithm])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(Usuario).filter(Usuario.email == email).first()
    if user is None:
        raise credentials_exception
    return user

def require_role(allowed_roles: list[TipoRolEnum]):
    def role_checker(current_user: Usuario = Depends(get_current_user)):
        if current_user.rol.nombre not in allowed_roles and current_user.rol.nombre != TipoRolEnum.ADMINISTRADOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operación no permitida para este rol"
            )
        return current_user
    return role_checker

def audit_log(accion: str):
    async def _audit_log(request: Request, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
        log = RegistroAuditoria(
            usuario_id=current_user.id,
            accion=accion,
            endpoint=request.url.path,
            metodo=request.method,
            direccion_ip=request.client.host if request.client else None,
            estado="Éxito"
        )
        db.add(log)
        db.commit()
        return current_user
    return _audit_log

async def enforce_rbac(request: Request, db: Session = Depends(get_db)):
    """
    Global dependency to enforce Role-Based Access Control on modifying actions.
    """
    if request.method not in ["POST", "PUT", "DELETE", "PATCH"]:
        return

    path = request.url.path
    if path == "/api/auth/login":
        return

    # Extraer el token del header o de la cookie
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    else:
        token = request.cookies.get("access_token")
        
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    # Reutilizar get_current_user para validar token y obtener usuario
    current_user = await get_current_user(token=token, db=db)
    
    if path == "/api/usuarios/me/password":
        return

    rol = current_user.rol.nombre
    
    if rol == TipoRolEnum.ADMINISTRADOR:
        pass
    elif rol == TipoRolEnum.AUDITOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Acción no permitida: Los auditores solo tienen acceso de lectura."
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

    # Si llegó hasta aquí, la acción de modificación fue aprobada por RBAC.
    # Registramos en auditoría solo si no es de /api/usuarios, ya que usuarios ya tiene sus propios logs específicos.
    if not path.startswith("/api/usuarios"):
        # Traducir a lenguaje humano
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

        # Intentar extraer el ID de la ruta (útil para Edición y Borrado)
        # Ejemplo: /api/v1/clientes/20363297588 -> El ID es 20363297588
        partes_ruta = path.rstrip("/").split("/")
        id_registro = ""
        ultima_parte = partes_ruta[-1]
        
        # Si la última parte de la URL no es el nombre del recurso, asumimos que es el ID en la URL
        if ultima_parte not in ["clientes", "creditos", "cobranzas", "procesos", "auxiliares", "provincias", "empleadores", "socios", "tasas_y_comisiones", "relaciones"]:
            id_registro = f" (ID: {ultima_parte})"
        
        # Si es POST, el ID no está en la URL, intentamos sacarlo del cuerpo de la petición (ej. CUIL al crear cliente)
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
                    pass # Si no hay body o no es JSON, lo ignoramos

        # Para cobranzas masivas o individuales, posponemos el log al endpoint para poder incluir el ID del proceso
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
