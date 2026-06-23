from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone

from src.database.connection import get_db
from src.database.models.auth import Usuario, Rol, TipoRolEnum, RegistroAuditoria
from src.config import DATABASE_SETTINGS

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Para este ejemplo se usan variables fijas. En producción idealmente vienen de config.py
SECRET_KEY = "super_secret_key_change_in_production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
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
