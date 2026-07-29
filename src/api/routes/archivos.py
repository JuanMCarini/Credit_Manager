from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from src.database.connection import get_db
from src.api.dependencies.auth import get_current_user
from src.database.models.auth import Usuario
import os
from pathlib import Path

router = APIRouter(prefix="/api/archivos", tags=["Archivos"])

UPLOAD_DIR = Path("data/uploads")

@router.get("/{filename:path}")
async def get_archivo(
    filename: str,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Endpoint para descargar archivos subidos localmente, de forma segura.
    Requiere que el usuario esté autenticado.
    """
    file_path = UPLOAD_DIR / filename
    
    # Prevenir Path Traversal
    try:
        file_path = file_path.resolve()
        upload_dir_resolved = UPLOAD_DIR.resolve()
        # Verificar que el path resuelto esté dentro del directorio de uploads
        if not str(file_path).startswith(str(upload_dir_resolved)):
            raise HTTPException(status_code=403, detail="Acceso denegado")
    except Exception:
        raise HTTPException(status_code=400, detail="Ruta de archivo inválida")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
    return FileResponse(path=file_path, filename=file_path.name)
