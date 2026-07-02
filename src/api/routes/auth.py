from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.database.models.auth import Usuario
from src.api.dependencies.auth import verify_password, create_access_token, get_current_user
from src.api.schemas.auth import Token
from src.database.connection import get_db

router = APIRouter(prefix="/api/auth", tags=["Autenticacion"])

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(func.lower(Usuario.email) == func.lower(form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
        
    access_token = create_access_token(
        data={"sub": user.email, "rol": user.rol.nombre}
    )
    return {"access_token": access_token, "token_type": "bearer", "user": {"email": user.email, "nombre": user.nombre_completo, "rol": user.rol.nombre}}

@router.post("/logout")
def logout(current_user: Usuario = Depends(get_current_user)):
    """
    Endpoint to handle user logout. Since JWT is stateless, the client should discard the token.
    """
    return {"msg": "Logout successful"}

@router.post("/refresh", response_model=Token)
def refresh_token(current_user: Usuario = Depends(get_current_user)):
    """
    Endpoint to refresh the JWT access token. Requires a valid, non-expired token.
    """
    access_token = create_access_token(
        data={"sub": current_user.email, "rol": current_user.rol.nombre}
    )
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "user": {
            "email": current_user.email, 
            "nombre": current_user.nombre_completo, 
            "rol": current_user.rol.nombre
        }
    }
