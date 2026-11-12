"""
Module: file_validation.py
Description: Centraliza la validación de archivos subidos (Magic Bytes, límites de tamaño,
             protección contra Zip Bombs / Zip Slip y extracción por streaming en disco).
"""

import os
import shutil
import zipfile
from pathlib import Path
from typing import BinaryIO, Iterator, Tuple
from fastapi import HTTPException, UploadFile

from src.config import API_SETTINGS

DOCUMENT_AND_IMAGE_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
TABULAR_EXTS = {".csv", ".txt", ".xlsx", ".xls"}


def validate_magic_bytes(header: bytes, ext: str, filename: str = "archivo") -> None:
    """
    Verifica que los primeros bytes del archivo coincidan con la firma binaria real
    esperada para su extensión, bloqueando ejecutables o archivos falsificados.
    """
    ext = ext.lower()
    if not header:
        raise HTTPException(
            status_code=400,
            detail=f"El archivo '{filename}' está vacío.",
        )

    if ext == ".pdf":
        if not header.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=400,
                detail=f"El archivo '{filename}' no posee una cabecera PDF válida.",
            )
    elif ext == ".png":
        if not header.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(
                status_code=400,
                detail=f"El archivo '{filename}' no posee una cabecera PNG válida.",
            )
    elif ext in {".jpg", ".jpeg"}:
        if not header.startswith(b"\xff\xd8\xff"):
            raise HTTPException(
                status_code=400,
                detail=f"El archivo '{filename}' no posee una cabecera JPEG válida.",
            )
    elif ext == ".webp":
        if len(header) < 12 or not header.startswith(b"RIFF") or header[8:12] != b"WEBP":
            raise HTTPException(
                status_code=400,
                detail=f"El archivo '{filename}' no posee una cabecera WEBP válida.",
            )
    elif ext == ".ico":
        if not header.startswith((b"\x00\x00\x01\x00", b"\x00\x00\x02\x00", b"\x89PNG\r\n\x1a\n")):
            raise HTTPException(
                status_code=400,
                detail=f"El archivo '{filename}' no posee una cabecera ICO/PNG válida.",
            )
    elif ext in {".zip", ".xlsx"}:
        if not header.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
            raise HTTPException(
                status_code=400,
                detail=f"El archivo '{filename}' no posee una firma ZIP/XLSX válida.",
            )
    elif ext == ".xls":
        if not header.startswith((b"\xd0\xcf\x11\xe0", b"PK\x03\x04")):
            raise HTTPException(
                status_code=400,
                detail=f"El archivo '{filename}' no posee una firma Excel (.xls) válida.",
            )
    elif ext in {".csv", ".txt"}:
        if header.startswith((b"MZ", b"\x7fELF", b"%PDF-", b"\x89PNG")):
            raise HTTPException(
                status_code=400,
                detail=f"El archivo '{filename}' contiene contenido binario no válido para texto/CSV.",
            )
        if b"\x00" in header and not header.startswith((b"\xff\xfe", b"\xfe\xff")):
            raise HTTPException(
                status_code=400,
                detail=f"El archivo '{filename}' contiene bytes nulos no válidos para un archivo de texto/CSV.",
            )


def sanitize_filename(raw_filename: str | None) -> Tuple[str, str]:
    """Limpia el nombre de archivo y retorna (clean_name, ext_lower)."""
    raw = (raw_filename or "").replace("\\", "/").strip()
    if ".." in raw.split("/"):
        raise HTTPException(
            status_code=400,
            detail="Nombre de archivo inválido (contiene secuencia de navegación '..').",
        )
    clean_name = os.path.basename(raw)
    if not clean_name or clean_name in {".", ".."}:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido.")
    ext = os.path.splitext(clean_name)[1].lower()
    return clean_name, ext


def validate_upload_file(
    upload_file: UploadFile,
    allowed_exts: set[str],
    max_size_mb: float | None = None,
) -> Tuple[str, str]:
    """
    Valida extensión, tamaño máximo (sin cargar el archivo entero en RAM) y Magic Bytes
    de un UploadFile. Deja el puntero del archivo al inicio (offset 0).
    """
    clean_name, ext = sanitize_filename(upload_file.filename)
    normalized_exts = {e.lower() for e in allowed_exts}
    if ext not in normalized_exts:
        allowed_str = ", ".join(sorted(normalized_exts))
        raise HTTPException(
            status_code=400,
            detail=f"Formato de archivo no permitido ('{ext}'). Formatos admitidos: {allowed_str}",
        )

    file_obj = upload_file.file
    file_obj.seek(0, os.SEEK_END)
    size_bytes = file_obj.tell()
    file_obj.seek(0)

    if size_bytes <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"El archivo '{clean_name}' está vacío.",
        )

    limit_mb = max_size_mb if max_size_mb is not None else float(API_SETTINGS.max_single_file_mb)
    max_bytes = int(limit_mb * 1024 * 1024)
    if size_bytes > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"El archivo '{clean_name}' ({size_bytes / (1024 * 1024):.1f} MB) supera el límite máximo de {limit_mb:g} MB.",
        )

    header = file_obj.read(64)
    file_obj.seek(0)
    validate_magic_bytes(header, ext, clean_name)
    return clean_name, ext


def stream_save_upload_file(
    upload_file: UploadFile,
    dest_path: str | Path,
    chunk_size: int = 1024 * 1024,
) -> int:
    """Guarda un UploadFile en disco por streaming en bloques de 1 MB sin saturar RAM."""
    upload_file.file.seek(0)
    total_written = 0
    with open(dest_path, "wb") as dst:
        while True:
            chunk = upload_file.file.read(chunk_size)
            if not chunk:
                break
            dst.write(chunk)
            total_written += len(chunk)
    upload_file.file.seek(0)
    return total_written


def extract_zip_streaming(
    zip_source: UploadFile | BinaryIO,
    dest_dir: str | Path,
    allowed_inner_exts: set[str] | None = None,
    max_files: int | None = None,
    max_single_file_mb: float | None = None,
    max_ratio: float | None = None,
    min_free_disk_mb: int | None = None,
) -> Iterator[Tuple[str, Path]]:
    """
    Inspecciona y extrae un archivo .zip directamente desde disco en streaming (bloques de 1 MB),
    protegiendo contra Zip Slip, Zip Bombs (por ratio de compresión y conteo real de bytes)
    y agotamiento de espacio en disco, soportando lotes de miles de legajos sin cargar en RAM.
    """
    file_obj: BinaryIO
    archive_name = "archivo.zip"
    if isinstance(zip_source, UploadFile):
        archive_name, _ = sanitize_filename(zip_source.filename or "lote.zip")
        file_obj = zip_source.file
    else:
        file_obj = zip_source

    file_obj.seek(0)
    header = file_obj.read(64)
    file_obj.seek(0)
    validate_magic_bytes(header, ".zip", archive_name)

    dest_base = Path(dest_dir).resolve()
    dest_base.mkdir(parents=True, exist_ok=True)

    limit_files = max_files if max_files is not None else int(API_SETTINGS.max_zip_files)
    limit_single_mb = (
        max_single_file_mb
        if max_single_file_mb is not None
        else float(API_SETTINGS.max_single_file_mb)
    )
    max_single_bytes = int(limit_single_mb * 1024 * 1024)
    limit_ratio = (
        max_ratio
        if max_ratio is not None
        else float(API_SETTINGS.max_zip_compression_ratio)
    )
    reserve_disk_mb = (
        min_free_disk_mb
        if min_free_disk_mb is not None
        else int(API_SETTINGS.min_free_disk_mb)
    )
    allowed_exts = (
        {e.lower() for e in allowed_inner_exts}
        if allowed_inner_exts is not None
        else DOCUMENT_AND_IMAGE_EXTS
    )

    try:
        zf = zipfile.ZipFile(file_obj)
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=400,
            detail=f"El archivo ZIP '{archive_name}' es inválido o está corrupto.",
        )

    with zf:
        valid_entries: list[zipfile.ZipInfo] = []
        total_declared_uncompressed = 0

        for info in zf.infolist():
            if info.is_dir():
                continue
            norm_entry = info.filename.replace("\\", "/")
            if norm_entry.startswith("__MACOSX/") or "/.__" in norm_entry:
                continue
            parts = [p for p in norm_entry.split("/") if p]
            if ".." in parts:
                raise HTTPException(
                    status_code=400,
                    detail=f"Archivo ZIP rechazado: ruta interna insegura ('{info.filename}').",
                )
            base_name = os.path.basename(norm_entry)
            if not base_name or base_name.startswith("."):
                continue

            if info.file_size > max_single_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"El archivo interno '{base_name}' ({info.file_size / (1024 * 1024):.1f} MB) supera el límite de {limit_single_mb:g} MB por documento.",
                )

            # Detección de Zip Bomb por ratio de compresión anómalo en entradas > 10 MB
            if info.file_size > 10 * 1024 * 1024:
                ratio = info.file_size / max(info.compress_size, 1)
                if ratio > limit_ratio:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Archivo ZIP rechazado por ratio de compresión sospechoso ({ratio:.1f}:1 en '{base_name}').",
                    )

            total_declared_uncompressed += info.file_size
            valid_entries.append(info)

        if len(valid_entries) > limit_files:
            raise HTTPException(
                status_code=400,
                detail=f"El archivo ZIP contiene {len(valid_entries)} archivos, superando el máximo permitido de {limit_files}.",
            )

        # Verificar espacio libre en disco antes de extraer
        try:
            free_disk_bytes = shutil.disk_usage(dest_base).free
            required_bytes = total_declared_uncompressed + (reserve_disk_mb * 1024 * 1024)
            if required_bytes > free_disk_bytes:
                raise HTTPException(
                    status_code=507,
                    detail="Espacio en disco insuficiente en el servidor para extraer el lote ZIP de forma segura.",
                )
        except OSError:
            pass

        for info in valid_entries:
            base_name, ext = sanitize_filename(info.filename)
            if allowed_exts and ext not in allowed_exts:
                continue

            target_path = (dest_base / base_name).resolve()
            if not target_path.is_relative_to(dest_base):
                raise HTTPException(
                    status_code=400,
                    detail=f"Ruta de extracción fuera del directorio permitido para '{base_name}'.",
                )

            with zf.open(info) as src:
                entry_header = src.read(64)
                if not entry_header:
                    continue
                validate_magic_bytes(entry_header, ext, base_name)

                written = 0
                with open(target_path, "wb") as dst:
                    dst.write(entry_header)
                    written += len(entry_header)
                    while True:
                        chunk = src.read(1024 * 1024)
                        if not chunk:
                            break
                        written += len(chunk)
                        if written > max_single_bytes:
                            dst.close()
                            target_path.unlink(missing_ok=True)
                            raise HTTPException(
                                status_code=413,
                                detail=f"El archivo interno '{base_name}' excede el tamaño máximo permitido de {limit_single_mb:g} MB al descomprimir.",
                            )
                        dst.write(chunk)

            yield base_name, target_path

