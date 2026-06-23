from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from src.database.connection import get_db
from src.database.models.auth import Usuario, Rol, TipoRolEnum
from src.api.dependencies.auth import get_current_user, require_role, audit_log, get_password_hash, verify_password
from src.api.schemas.usuarios import (
    UsuarioResponse, 
    UsuarioCreate, 
    UsuarioUpdate, 
    UsuarioPasswordUpdate, 
    UsuarioMyPasswordUpdate, 
    RolResponse
)

router = APIRouter(prefix="/api/usuarios", tags=["Usuarios"])

# Dependencia para requerir explícitamente el rol de Administrador
admin_only = Depends(require_role([]))

@router.get("/roles", response_model=List[RolResponse], dependencies=[admin_only])
def get_roles(db: Session = Depends(get_db)):
    """Listar todos los roles disponibles (Solo Administrador)"""
    roles = db.query(Rol).all()
    return roles

@router.get("", response_model=List[UsuarioResponse], dependencies=[admin_only])
def list_usuarios(db: Session = Depends(get_db)):
    """Listar todos los usuarios (Solo Administrador)"""
    usuarios = db.query(Usuario).all()
    return usuarios

@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED, dependencies=[admin_only, Depends(audit_log("Crear Usuario"))])
def create_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    """Crear un nuevo usuario (Solo Administrador)"""
    db_user = db.query(Usuario).filter(func.lower(Usuario.email) == func.lower(usuario.email)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    db_rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    if not db_rol:
        raise HTTPException(status_code=400, detail="El rol especificado no existe")

    new_user = Usuario(
        email=usuario.email,
        hashed_password=get_password_hash(usuario.password),
        nombre_completo=usuario.nombre_completo,
        is_active=usuario.is_active,
        rol_id=usuario.rol_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.put("/me/password", dependencies=[Depends(audit_log("Cambio Contraseña Personal"))])
def update_my_password(
    password_data: UsuarioMyPasswordUpdate, 
    current_user: Usuario = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Permite al usuario logueado cambiar su propia contraseña"""
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta")
        
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    return {"msg": "Tu contraseña ha sido actualizada exitosamente"}

@router.put("/{user_id}", response_model=UsuarioResponse, dependencies=[admin_only, Depends(audit_log("Actualizar Usuario"))])
def update_usuario(user_id: int, usuario_update: UsuarioUpdate, db: Session = Depends(get_db)):
    """Actualizar datos de un usuario (Solo Administrador)"""
    db_user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if usuario_update.email is not None and usuario_update.email.lower() != db_user.email.lower():
        existing_email = db.query(Usuario).filter(func.lower(Usuario.email) == usuario_update.email.lower()).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="El email ya está registrado por otro usuario")
        db_user.email = usuario_update.email
        
    if usuario_update.nombre_completo is not None:
        db_user.nombre_completo = usuario_update.nombre_completo
        
    if usuario_update.rol_id is not None and usuario_update.rol_id != db_user.rol_id:
        if db_user.rol.nombre == TipoRolEnum.ADMINISTRADOR:
            admin_count = db.query(Usuario).join(Rol).filter(Rol.nombre == TipoRolEnum.ADMINISTRADOR, Usuario.is_active == True, Usuario.id != user_id).count()
            if admin_count == 0:
                raise HTTPException(status_code=400, detail="No se puede cambiar el rol a este usuario porque es el único administrador activo del sistema.")
        db_rol = db.query(Rol).filter(Rol.id == usuario_update.rol_id).first()
        if not db_rol:
            raise HTTPException(status_code=400, detail="El rol especificado no existe")
        db_user.rol_id = usuario_update.rol_id
        
    if usuario_update.is_active is not None and usuario_update.is_active != db_user.is_active:
        if usuario_update.is_active is False and db_user.rol.nombre == TipoRolEnum.ADMINISTRADOR:
            admin_count = db.query(Usuario).join(Rol).filter(Rol.nombre == TipoRolEnum.ADMINISTRADOR, Usuario.is_active == True, Usuario.id != user_id).count()
            if admin_count == 0:
                raise HTTPException(status_code=400, detail="No se puede desactivar a este usuario porque es el único administrador activo del sistema.")
        db_user.is_active = usuario_update.is_active
        
    db.commit()
    db.refresh(db_user)
    return db_user

@router.put("/{user_id}/password", dependencies=[admin_only, Depends(audit_log("Cambio Contraseña Usuario (Admin)"))])
def update_user_password(user_id: int, password_update: UsuarioPasswordUpdate, db: Session = Depends(get_db)):
    """Actualizar la contraseña de un usuario por un Administrador (Solo Administrador)"""
    db_user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    db_user.hashed_password = get_password_hash(password_update.password)
    db.commit()
    return {"msg": "Contraseña actualizada exitosamente"}

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[admin_only, Depends(audit_log("Eliminar Usuario"))])
def delete_usuario(user_id: int, db: Session = Depends(get_db)):
    """Eliminar un usuario (Solo Administrador)"""
    db_user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    if db_user.rol.nombre == TipoRolEnum.ADMINISTRADOR:
        admin_count = db.query(Usuario).join(Rol).filter(Rol.nombre == TipoRolEnum.ADMINISTRADOR, Usuario.is_active == True, Usuario.id != user_id).count()
        if admin_count == 0:
            raise HTTPException(status_code=400, detail="No se puede eliminar a este usuario porque es el único administrador activo del sistema.")
    
    # Check if there are constraints or foreign keys. It's usually better to just deactivate.
    # We will do a real delete here, but if there's audit logs, it might fail.
    # Let's try to delete. If it fails, maybe we fallback to soft delete or let the generic error handler catch it.
    try:
        db.delete(db_user)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="No se puede eliminar el usuario porque tiene registros asociados. En su lugar, desactívelo.")
    return None
