import io
import zipfile
from types import SimpleNamespace
import pytest
from fastapi import HTTPException, UploadFile
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import Response

from src.api.dependencies.auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    login_rate_limiter,
    revoke_token,
)
from src.api.routes.auth import login, logout
from src.api.routes.auxiliares import create_aux_record, update_aux_record
from src.api.schemas.auxiliares import TabulatorRequest
from src.api.schemas.usuarios import (
    UsuarioCreate,
    UsuarioMyPasswordUpdate,
    UsuarioPasswordUpdate,
)
from src.database.models import Provincia
from src.database.models.auth import RegistroAuditoria, Rol, TipoRolEnum, Usuario
from src.utils.file_validation import (
    DOCUMENT_AND_IMAGE_EXTS,
    extract_zip_streaming,
    validate_upload_file,
)


def _make_request(
    method: str = "POST",
    path: str = "/api/auth/login",
    ip: str = "198.51.100.25",
    token: str | None = None,
    cookie_token: str | None = None,
) -> Request:
    headers = []
    if token:
        headers.append((b"authorization", f"Bearer {token}".encode("utf-8")))
    if cookie_token:
        headers.append((b"cookie", f"access_token={cookie_token}".encode("utf-8")))
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": headers,
        "query_string": b"",
        "client": (ip, 54321),
    }
    return Request(scope)


def test_task_2_1_login_rate_limiting_and_audit_log(db_session):
    login_rate_limiter.clear_all()
    rol = Rol(nombre=TipoRolEnum.ADMINISTRADOR)
    db_session.add(rol)
    db_session.flush()

    user = Usuario(
        email="sec_login@test.com",
        hashed_password=get_password_hash("StrongPass#2026"),
        nombre_completo="Admin Sec",
        rol_id=rol.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    req = _make_request(ip="203.0.113.10")
    bad_form = SimpleNamespace(username="sec_login@test.com", password="WrongPassword1!")

    # 5 intentos fallidos -> 401
    for _ in range(5):
        with pytest.raises(HTTPException) as exc:
            login(request=req, response=Response(), form_data=bad_form, db=db_session)
        assert exc.value.status_code == 401

    # 6to intento -> bloqueado con 429 Too Many Requests
    with pytest.raises(HTTPException) as exc_429:
        login(request=req, response=Response(), form_data=bad_form, db=db_session)
    assert exc_429.value.status_code == 429

    # Verificar que los fallos quedaron registrados en RegistroAuditoria sin exponer password
    audit_fails = (
        db_session.query(RegistroAuditoria)
        .filter(
            RegistroAuditoria.endpoint == "/api/auth/login",
            RegistroAuditoria.estado == "Fallo",
        )
        .all()
    )
    assert len(audit_fails) == 5
    assert audit_fails[0].direccion_ip == "203.0.113.10"
    assert audit_fails[0].detalles == {"email_intentado": "sec_login@test.com"}

    # Desde otra IP no bloqueada, el login exitoso resetea el contador y emite cookie HttpOnly
    req_ok = _make_request(ip="203.0.113.99")
    good_form = SimpleNamespace(username="sec_login@test.com", password="StrongPass#2026")
    resp = Response()
    res = login(request=req_ok, response=resp, form_data=good_form, db=db_session)
    assert "access_token" in res
    set_cookie = resp.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie
    assert "HttpOnly" in set_cookie
    login_rate_limiter.clear_all()


def test_task_2_2_password_complexity_and_token_revocation(db_session):
    # Contraseña corta (<10 chars)
    with pytest.raises(ValidationError):
        UsuarioCreate(
            email="u@test.com",
            nombre_completo="User",
            password="Ab1!short",
            rol_id=1,
        )

    # Sin mayúsculas
    with pytest.raises(ValidationError):
        UsuarioPasswordUpdate(password="alllowercase123!")

    # Sin números ni símbolos
    with pytest.raises(ValidationError):
        UsuarioPasswordUpdate(password="OnlyLettersValidLen")

    # Reutilización de la misma contraseña en cambio personal
    with pytest.raises(ValidationError):
        UsuarioMyPasswordUpdate(
            current_password="ValidPassword#2026",
            new_password="ValidPassword#2026",
        )

    # Contraseña válida
    valid_upd = UsuarioMyPasswordUpdate(
        current_password="OldPassword#2025",
        new_password="NewPassword#2026",
    )
    assert valid_upd.new_password == "NewPassword#2026"

    # Creación y revocación de JWT (jti) + soporte por Cookie HttpOnly
    rol = Rol(nombre=TipoRolEnum.GERENTE)
    db_session.add(rol)
    db_session.flush()
    user = Usuario(
        email="jwt_revoke@test.com",
        hashed_password=get_password_hash("ValidPassword#2026"),
        nombre_completo="Gerente Test",
        rol_id=rol.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    token = create_access_token({"sub": user.email, "rol": rol.nombre})

    # Autenticación vía cookie HttpOnly (sin header Authorization)
    req_cookie = _make_request("GET", "/api/v1/clientes", cookie_token=token)
    resolved_user = get_current_user(request=req_cookie, token=None, db=db_session)
    assert resolved_user.email == user.email

    # Logout revoca el token
    req_logout = _make_request("POST", "/api/auth/logout", token=token)
    logout(request=req_logout, response=Response(), current_user=user)

    # Intentar usar el token revocado debe lanzar 401
    with pytest.raises(HTTPException) as exc_revoked:
        get_current_user(request=req_cookie, token=token, db=db_session)
    assert exc_revoked.value.status_code == 401


def test_task_2_3_file_magic_bytes_size_and_streaming_zip(tmp_path):
    # 1. Ejecutable disfrazado de PDF -> 400
    fake_pdf = UploadFile(
        filename="legajo.pdf",
        file=io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00fake_exe_payload"),
    )
    with pytest.raises(HTTPException) as exc_magic:
        validate_upload_file(fake_pdf, DOCUMENT_AND_IMAGE_EXTS)
    assert exc_magic.value.status_code == 400

    # 2. PDF válido pero que supera max_size_mb -> 413
    valid_pdf_bytes = b"%PDF-1.7\n" + (b"0" * 2048)
    oversized_pdf = UploadFile(
        filename="contrato.pdf",
        file=io.BytesIO(valid_pdf_bytes),
    )
    with pytest.raises(HTTPException) as exc_size:
        validate_upload_file(oversized_pdf, DOCUMENT_AND_IMAGE_EXTS, max_size_mb=0.0005)
    assert exc_size.value.status_code == 413

    # 3. Extracción ZIP en streaming válida + rechazo de archivo con ratio de Zip Bomb
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("legajo_101.pdf", b"%PDF-1.4\ncontenido_legajo_valido")
        zf.writestr("foto_101.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
    zip_buf.seek(0)

    extracted = list(
        extract_zip_streaming(
            zip_buf,
            tmp_path / "extracted_ok",
            allowed_inner_exts=DOCUMENT_AND_IMAGE_EXTS,
        )
    )
    assert len(extracted) == 2
    assert {name for name, _ in extracted} == {"legajo_101.pdf", "foto_101.png"}

    # 4. Simulación de Zip Bomb (> 10 MB de ceros con altísimo ratio de compresión)
    bomb_buf = io.BytesIO()
    with zipfile.ZipFile(bomb_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("bomb.pdf", b"%PDF-1.4\n" + (b"\x00" * (11 * 1024 * 1024)))
    bomb_buf.seek(0)

    with pytest.raises(HTTPException) as exc_bomb:
        list(
            extract_zip_streaming(
                bomb_buf,
                tmp_path / "extracted_bomb",
                allowed_inner_exts=DOCUMENT_AND_IMAGE_EXTS,
                max_ratio=50.0,
            )
        )
    assert exc_bomb.value.status_code == 400
    assert "ratio de compresión" in exc_bomb.value.detail


def test_task_2_4_mass_assignment_and_pagination_limits(db_session):
    # Intento de forzar 'id' y campos inexistentes/internos en creación de tabla auxiliar
    res = create_aux_record(
        tabla="provincias",
        payload={
            "id": 99999,
            "nombre": "Provincia Segura",
            "__tablename__": "hacked",
            "atributo_inexistente": "malicioso",
        },
        db=db_session,
    )
    assert res["status"] == "success"
    assert res["id"] != 99999

    prov = db_session.query(Provincia).filter(Provincia.id == res["id"]).first()
    assert prov is not None
    assert prov.nombre == "Provincia Segura"

    # Intento de modificar 'id' en update_aux_record
    update_aux_record(
        tabla="provincias",
        record_id=prov.id,
        payload={"id": 88888, "nombre": "Provincia Actualizada"},
        db=db_session,
    )
    db_session.refresh(prov)
    assert prov.id == res["id"]
    assert prov.nombre == "Provincia Actualizada"

    # Límites de paginación en TabulatorRequest
    with pytest.raises(ValidationError):
        TabulatorRequest(page=0, size=50)
    with pytest.raises(ValidationError):
        TabulatorRequest(page=1, size=50000)
    valid_tab = TabulatorRequest(page=1, size=500)
    assert valid_tab.size == 500

