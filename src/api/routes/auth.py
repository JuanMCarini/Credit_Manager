from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.database.models.auth import Usuario, RegistroAuditoria
from src.api.dependencies.auth import (
    verify_password,
    create_access_token,
    get_current_user,
    login_rate_limiter,
    revoke_token,
    extract_token_from_request,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from src.api.schemas.auth import Token
from src.database.connection import get_db
from src.config import API_SETTINGS

router = APIRouter(prefix="/api/auth", tags=["Autenticacion"])


def _get_client_ip(request: Request | None) -> str:
    if request is None:
        return "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


@router.post("/login", response_model=Token)
def login(
    request: Request = None,
    response: Response = None,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    client_ip = _get_client_ip(request)
    username = (form_data.username or "").strip()

    login_rate_limiter.check_rate_limit(client_ip, username)

    user = db.query(Usuario).filter(func.lower(Usuario.email) == func.lower(username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        login_rate_limiter.record_failure(client_ip, username)
        db.add(
            RegistroAuditoria(
                usuario_id=user.id if user else None,
                accion="Inicio de Sesión Fallido",
                endpoint="/api/auth/login",
                metodo="POST",
                direccion_ip=client_ip,
                estado="Fallo",
                detalles={"email_intentado": username},
            )
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        login_rate_limiter.record_failure(client_ip, username)
        db.add(
            RegistroAuditoria(
                usuario_id=user.id,
                accion="Inicio de Sesión Bloqueado (Usuario Inactivo)",
                endpoint="/api/auth/login",
                metodo="POST",
                direccion_ip=client_ip,
                estado="Fallo",
                detalles={"email_intentado": username},
            )
        )
        db.commit()
        raise HTTPException(status_code=400, detail="Usuario inactivo")

    login_rate_limiter.reset(client_ip, username)
    db.add(
        RegistroAuditoria(
            usuario_id=user.id,
            accion="Inicio de Sesión",
            endpoint="/api/auth/login",
            metodo="POST",
            direccion_ip=client_ip,
            estado="Éxito",
        )
    )
    db.commit()

    access_token = create_access_token(
        data={"sub": user.email, "rol": user.rol.nombre}
    )
    if response is not None:
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            samesite="lax",
            secure=(API_SETTINGS.env.strip().lower() == "production"),
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
        )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": user.email,
            "nombre": user.nombre_completo,
            "rol": user.rol.nombre,
        },
    }


@router.post("/logout")
def logout(
    request: Request = None,
    response: Response = None,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Revoca el JWT activo por su 'jti' y limpia la cookie HttpOnly de sesión.
    """
    token = extract_token_from_request(request)
    if token:
        revoke_token(token)
    if response is not None:
        response.delete_cookie(key="access_token", path="/")
    return {"msg": "Logout successful"}


@router.post("/refresh", response_model=Token)
def refresh_token(
    request: Request = None,
    response: Response = None,
    current_user: Usuario = Depends(get_current_user),
):
    """
    Renueva el token JWT activo revocando el anterior si fue provisto.
    """
    old_token = extract_token_from_request(request)
    if old_token:
        revoke_token(old_token)
    access_token = create_access_token(
        data={"sub": current_user.email, "rol": current_user.rol.nombre}
    )
    if response is not None:
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            samesite="lax",
            secure=(API_SETTINGS.env.strip().lower() == "production"),
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
        )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": current_user.email,
            "nombre": current_user.nombre_completo,
            "rol": current_user.rol.nombre,
        },
    }
