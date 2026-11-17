import threading
import time
import uuid
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

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = API_SETTINGS.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = API_SETTINGS.access_token_expire_minutes


class LoginRateLimiter:
    """
    Limitador de intentos de login en memoria (thread-safe) con ventana deslizante
    por IP y por par (IP, usuario) para prevenir ataques de fuerza bruta.
    """

    def __init__(self, max_attempts: int = 5, window_seconds: int = 900):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._attempts: dict[str, list[float]] = {}

    def _prune(self, key: str, now: float) -> list[float]:
        cutoff = now - self.window_seconds
        timestamps = [ts for ts in self._attempts.get(key, []) if ts > cutoff]
        if timestamps:
            self._attempts[key] = timestamps
        else:
            self._attempts.pop(key, None)
        return timestamps

    def check_rate_limit(self, client_ip: str, username: str = "") -> None:
        now = time.monotonic()
        ip_key = f"ip:{client_ip or 'unknown'}"
        user_key = f"user:{client_ip or 'unknown'}:{(username or '').strip().lower()}"
        with self._lock:
            ip_attempts = self._prune(ip_key, now)
            user_attempts = self._prune(user_key, now)
            if len(user_attempts) >= self.max_attempts or len(ip_attempts) >= (self.max_attempts * 2):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Demasiados intentos fallidos de inicio de sesión. Por favor, aguarde 15 minutos antes de volver a intentar.",
                    headers={"Retry-After": str(self.window_seconds)},
                )

    def record_failure(self, client_ip: str, username: str = "") -> None:
        now = time.monotonic()
        ip_key = f"ip:{client_ip or 'unknown'}"
        user_key = f"user:{client_ip or 'unknown'}:{(username or '').strip().lower()}"
        with self._lock:
            ip_list = self._prune(ip_key, now)
            ip_list.append(now)
            self._attempts[ip_key] = ip_list

            user_list = self._prune(user_key, now)
            user_list.append(now)
            self._attempts[user_key] = user_list

    def reset(self, client_ip: str, username: str = "") -> None:
        ip_key = f"ip:{client_ip or 'unknown'}"
        user_key = f"user:{client_ip or 'unknown'}:{(username or '').strip().lower()}"
        with self._lock:
            self._attempts.pop(user_key, None)
            self._attempts.pop(ip_key, None)

    def clear_all(self) -> None:
        with self._lock:
            self._attempts.clear()


login_rate_limiter = LoginRateLimiter(
    max_attempts=API_SETTINGS.login_max_attempts,
    window_seconds=API_SETTINGS.login_window_seconds,
)

_revoked_tokens_lock = threading.Lock()
_revoked_tokens: dict[str, float] = {}


def revoke_token(token_or_jti: str, exp_timestamp: float | None = None) -> None:
    """Revoca un JWT por su claim 'jti' o decodificando el token completo."""
    if not token_or_jti:
        return
    jti = token_or_jti
    exp_ts = exp_timestamp or (time.time() + ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    if "." in token_or_jti:
        try:
            payload = jwt.decode(token_or_jti, SECRET_KEY, algorithms=[ALGORITHM])
            jti = payload.get("jti") or token_or_jti
            if payload.get("exp"):
                exp_ts = float(payload["exp"])
        except JWTError:
            pass
    now = time.time()
    with _revoked_tokens_lock:
        expired_keys = [k for k, v in _revoked_tokens.items() if v <= now]
        for k in expired_keys:
            _revoked_tokens.pop(k, None)
        _revoked_tokens[jti] = exp_ts


def is_token_revoked(jti: str | None) -> bool:
    if not jti:
        return False
    now = time.time()
    with _revoked_tokens_lock:
        exp_ts = _revoked_tokens.get(jti)
        if exp_ts is None:
            return False
        if exp_ts <= now:
            _revoked_tokens.pop(jti, None)
            return False
        return True


def extract_token_from_request(request: Request | None) -> str | None:
    if request is None:
        return None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        if cookie_token.startswith("Bearer "):
            return cookie_token.split(" ", 1)[1].strip()
        return cookie_token.strip()
    return None


def extract_client_ip(request: Request | None) -> str | None:
    """
    Obtiene la IP real del cliente priorizando X-Forwarded-For (proxy reverso Nginx)
    y X-Real-IP, con fallback a request.client.host.
    """
    if request is None:
        return None
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        first_ip = forwarded.split(",")[0].strip()
        if first_ip:
            return first_ip
    real_ip = request.headers.get("X-Real-IP")
    if real_ip and real_ip.strip():
        return real_ip.strip()
    if request.client and request.client.host:
        return request.client.host
    return None


SENSITIVE_AUDIT_KEYS = {
    "password",
    "current_password",
    "new_password",
    "hashed_password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "secret_key",
    "api_secret_key",
    "clave",
    "contrasena",
    "contraseña",
}


def sanitize_audit_payload(payload: object) -> dict | None:
    """
    Enmascara credenciales, secretos y tokens antes de persistir detalles en RegistroAuditoria.
    """
    if not isinstance(payload, dict):
        return None
    sanitized: dict = {}
    for key, val in payload.items():
        key_lower = str(key).strip().lower()
        if key_lower in SENSITIVE_AUDIT_KEYS or any(
            s in key_lower for s in ("password", "secret", "token", "clave", "contraseña")
        ):
            sanitized[key] = "***REDACTED***"
        elif isinstance(val, dict):
            sanitized[key] = sanitize_audit_payload(val)
        elif isinstance(val, list):
            sanitized[key] = f"[list:{len(val)} items]" if len(val) > 10 else val
        elif isinstance(val, str) and len(val) > 250:
            sanitized[key] = val[:250] + "..."
        else:
            sanitized[key] = val
    return sanitized


def _resolve_audit_entity(path: str) -> str:
    if path.startswith("/api/v1/liquidaciones"):
        return "Liquidación"
    if path.startswith("/api/v1/carteras"):
        return "Cartera"
    if path.startswith("/api/v1/inversores"):
        return "Inversor / Deuda"
    if path.startswith("/api/cheques"):
        return "Cheque"
    if path.startswith(("/api/finanzas/bancos", "/api/finanzas/cuentas", "/api/finanzas/movimientos")):
        return "Finanzas / Bancos"
    if path.startswith(("/api/finanzas/comprobantes", "/api/finanzas/proveedores")):
        return "Comprobante / Proveedor"
    if path.startswith(("/api/finanzas/posicion-iva", "/api/finanzas/posicion-iibb")):
        return "Posición IVA / IIBB"
    if path.startswith("/api/finanzas"):
        return "Finanzas"
    if path.startswith("/api/v1/facturacion"):
        return "Facturación"
    if path.startswith("/api/v1/planes"):
        return "Plan Financiero"
    if path.startswith("/api/v1/papeleria"):
        return "Papelería"
    if path.startswith("/api/v1/bcra"):
        return "BCRA"
    if path.startswith(("/api/v1/uploads", "/api/v1/system/uploads")):
        return "Documento / Archivo"
    if path.startswith("/api/v1/system"):
        return "Configuración del Sistema"
    if path.startswith(("/api/v1/reports", "/api/v1/reportes")):
        return "Reporte Regulatorio / Financiero"
    if "clientes" in path:
        return "Cliente"
    if "creditos" in path:
        return "Crédito"
    if "cobranzas" in path:
        return "Cobranza"
    if "procesos" in path:
        return "Proceso"
    if "auxiliares" in path:
        return "Tabla Auxiliar"
    return "Registro"


def _resolve_sensitive_read_action(path: str, method: str) -> str | None:
    """
    Identifica lecturas (GET) críticas de exportación masiva de PII o descarga de legajos/contratos
    que deben dejar traza obligatoria en RegistroAuditoria (ISO 27701 / Control 8.11 y 8.15).
    """
    if method != "GET":
        return None
    if path in ("/api/v1/bcra/export", "/api/v1/bcra/export-excel"):
        return "Exportación Masiva BCRA"
    if path.startswith("/api/v1/reports/uif"):
        return "Exportación Regulatoria UIF"
    if path.startswith("/api/v1/reports/balances/export"):
        return "Exportación Masiva de Saldos"
    if path.startswith(("/api/v1/uploads/", "/api/v1/system/uploads/")):
        return f"Descarga de Documento ({path.split('/')[-1]})"
    if "/documentos/" in path and path.endswith("/download"):
        return f"Descarga de Documento ({path})"
    if path == "/api/v1/system/arca/descargar-key":
        return "Descarga de Clave Privada Fiscal ARCA (arca.key)"
    if path == "/api/v1/system/arca/descargar-csr":
        return "Descarga de Solicitud CSR ARCA (arca.csr)"
    return None


BASE_PUBLIC_PATHS = {
    "/",
    "/api/v1/health",
    "/favicon.ico",
    "/api/auth/login",
    "/api/v1/system/logo",
    "/api/v1/system/favicon",
}

DOCS_PATHS = {
    "/docs",
    "/redoc",
    "/openapi.json",
}


def get_public_paths() -> set[str]:
    if API_SETTINGS.env.strip().lower() == "production":
        return BASE_PUBLIC_PATHS
    return BASE_PUBLIC_PATHS | DOCS_PATHS


PUBLIC_PATHS = get_public_paths()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.setdefault("jti", uuid.uuid4().hex)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    request: Request = None,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    resolved_token = token or extract_token_from_request(request)
    if not resolved_token:
        raise credentials_exception
    try:
        payload = jwt.decode(resolved_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        jti: str | None = payload.get("jti")
        if email is None or is_token_revoked(jti) or is_token_revoked(resolved_token):
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(Usuario).filter(Usuario.email == email).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


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


admin_only = require_role([TipoRolEnum.ADMINISTRADOR])


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
            direccion_ip=extract_client_ip(request),
            estado="Éxito",
        )
        db.add(log)
        db.commit()
        return current_user
    return _audit_log


def _is_shared_facturacion_path(path: str) -> bool:
    if path.startswith((
        "/api/v1/facturacion/libro-iva",
        "/api/v1/facturacion/descargar-masivo",
        "/api/v1/facturacion/ultima-fecha",
    )):
        return True
    if path.startswith("/api/v1/facturacion/") and path.endswith("/pdf"):
        return True
    return False


def _resolve_module_code(path: str) -> str | None:
    if path.startswith((
        "/api/v1/facturacion/emitir-individual",
        "/api/v1/facturacion/emitidas",
        "/api/v1/facturacion/receptores",
        "/api/v1/facturacion/tipos-comprobante",
        "/api/v1/facturacion/condiciones-iva-receptor",
        "/api/v1/facturacion/tipos-tributo",
        "/api/v1/facturacion/consultar-cuit",
    )):
        return "finanzas"
    if _is_shared_facturacion_path(path):
        return "finanzas_or_creditos"
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
        "/api/v1/uploads/legajos",
        "/api/v1/uploads/contratos_carteras",
        "/api/v1/system/uploads/legajos",
        "/api/v1/system/uploads/contratos_carteras",
    )):
        return "creditos"
    if path.startswith((
        "/api/cheques",
        "/api/v1/uploads/cheques",
        "/api/v1/system/uploads/cheques",
    )):
        return "cheques"
    if path.startswith("/api/v1/inversores"):
        return "inversores"
    if path.startswith((
        "/api/finanzas",
        "/api/v1/planes",
        "/api/v1/uploads/comprobantes",
        "/api/v1/system/uploads/comprobantes",
    )):
        return "finanzas"
    return None


ROLE_READ_PREFIXES: dict[TipoRolEnum, tuple[str, ...]] = {
    TipoRolEnum.OPERADOR_INVERSIONES: (
        "/api/v1/inversores",
        "/api/v1/reports",
        "/api/v1/reportes",
        "/api/v1/auxiliares",
        "/api/finanzas/bancos",
        "/api/finanzas/cuentas",
    ),
    TipoRolEnum.RESPONSABLE_FINANZAS: (
        "/api/finanzas",
        "/api/v1/planes",
        "/api/cheques",
        "/api/v1/facturacion",
        "/api/v1/liquidaciones",
        "/api/v1/carteras",
        "/api/v1/inversores",
        "/api/v1/clientes",
        "/api/v1/creditos",
        "/api/v1/cobranzas",
        "/api/v1/papeleria",
        "/api/v1/reports",
        "/api/v1/reportes",
        "/api/v1/auxiliares",
        "/api/v1/uploads",
        "/api/v1/system/uploads",
    ),
    TipoRolEnum.OPERADOR_COBRANZAS: (
        "/api/v1/cobranzas",
        "/api/v1/procesos",
        "/api/v1/clientes",
        "/api/v1/creditos",
        "/api/v1/carteras",
        "/api/v1/liquidaciones",
        "/api/v1/reports/balances",
        "/api/v1/reports/cobranzas",
        "/api/v1/auxiliares",
        "/api/v1/uploads/legajos",
        "/api/v1/system/uploads/legajos",
    ),
    TipoRolEnum.OFICIAL_CREDITO: (
        "/api/v1/clientes",
        "/api/v1/creditos",
        "/api/v1/cobranzas",
        "/api/v1/carteras",
        "/api/v1/papeleria",
        "/api/v1/reports/balances",
        "/api/v1/reports/cobranzas",
        "/api/v1/auxiliares",
        "/api/v1/uploads/legajos",
        "/api/v1/system/uploads/legajos",
    ),
}

ROLE_WRITE_PREFIXES: dict[TipoRolEnum, tuple[str, ...]] = {
    TipoRolEnum.OPERADOR_INVERSIONES: (
        "/api/v1/inversores",
        "/api/v1/reports",
        "/api/v1/reportes",
        "/api/v1/auxiliares/comisiones_deuda",
    ),
    TipoRolEnum.RESPONSABLE_FINANZAS: (
        "/api/finanzas",
        "/api/v1/planes",
        "/api/cheques",
        "/api/v1/facturacion",
        "/api/v1/liquidaciones",
        "/api/v1/carteras",
        "/api/v1/reports",
        "/api/v1/reportes",
    ),
    TipoRolEnum.OPERADOR_COBRANZAS: (
        "/api/v1/cobranzas",
        "/api/v1/procesos",
        "/api/v1/creditos/procesos",
    ),
    TipoRolEnum.OFICIAL_CREDITO: (
        "/api/v1/clientes",
        "/api/v1/creditos",
        "/api/v1/papeleria",
    ),
}


async def enforce_rbac(request: Request, db: Session = Depends(get_db)):
    """
    Global dependency to enforce authentication, module activation, and Role-Based Access Control.
    """
    if request.method == "OPTIONS":
        return

    path = request.url.path
    if path in get_public_paths():
        return

    token = extract_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    current_user = get_current_user(request=request, token=token, db=db)

    # Verificar si el módulo asociado a la ruta está activo
    mod_code = _resolve_module_code(path)
    if mod_code == "finanzas_or_creditos":
        mods_fc = (
            db.query(ModuloSistema)
            .filter(ModuloSistema.codigo.in_(["finanzas", "creditos"]))
            .all()
        )
        if mods_fc and all(not m.activo for m in mods_fc):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Los módulos 'Finanzas' y 'Créditos' se encuentran desactivados.",
            )
    elif mod_code:
        mod = db.query(ModuloSistema).filter(ModuloSistema.codigo == mod_code).first()
        if mod is not None and not mod.activo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"El módulo '{mod.nombre}' se encuentra desactivado.",
            )

    # Rutas propias de sesión habilitadas para cualquier usuario autenticado
    if path in {
        "/api/usuarios/me/password",
        "/api/auth/logout",
        "/api/auth/refresh",
        "/api/v1/system/arca/status",
    }:
        return current_user

    rol = current_user.rol.nombre

    # Gestión de usuarios exclusiva de ADMINISTRADOR
    if path.startswith("/api/usuarios") and rol != TipoRolEnum.ADMINISTRADOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operación no permitida: Solo los administradores pueden gestionar usuarios.",
        )

    is_aux_data_query = (
        request.method == "POST"
        and path.startswith("/api/v1/auxiliares/")
        and path.endswith("/data")
    )
    is_read_operation = (
        request.method not in ["POST", "PUT", "DELETE", "PATCH"]
        or is_aux_data_query
    )

    if is_read_operation:
        if rol not in [TipoRolEnum.ADMINISTRADOR, TipoRolEnum.GERENTE, TipoRolEnum.AUDITOR]:
            allowed_read = ROLE_READ_PREFIXES.get(rol)
            if not allowed_read or not path.startswith(allowed_read):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acceso de lectura no permitido para este rol en el módulo solicitado.",
                )

        sensitive_action = _resolve_sensitive_read_action(path, request.method)
        if sensitive_action:
            query_params = dict(request.query_params) if getattr(request, "query_params", None) else None
            log = RegistroAuditoria(
                usuario_id=current_user.id,
                accion=sensitive_action,
                endpoint=path,
                metodo=request.method,
                direccion_ip=extract_client_ip(request),
                estado="Éxito",
                detalles=sanitize_audit_payload(query_params) if query_params else None,
            )
            db.add(log)
            db.commit()

        return current_user

    # Operaciones de escritura (POST, PUT, PATCH, DELETE)
    if path.startswith("/api/v1/system") and rol != TipoRolEnum.ADMINISTRADOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operación no permitida: Solo los administradores pueden modificar la configuración del sistema.",
        )

    if rol in [TipoRolEnum.ADMINISTRADOR, TipoRolEnum.GERENTE]:
        pass
    elif rol == TipoRolEnum.AUDITOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Acción no permitida: Los auditores solo tienen acceso de lectura."
        )
    elif rol in ROLE_WRITE_PREFIXES:
        allowed_write = ROLE_WRITE_PREFIXES[rol]
        if not path.startswith(allowed_write):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acción no permitida para el rol '{rol.value if hasattr(rol, 'value') else rol}'.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Rol no reconocido."
        )

    # Registramos en auditoría solo si no es de /api/usuarios
    if not path.startswith("/api/usuarios"):
        if request.method == "POST" and path in ["/api/v1/cobranzas/masiva", "/api/v1/cobranzas/individual"]:
            return current_user

        metodo_str = "Acción"
        if request.method == "POST":
            metodo_str = "Crear"
        elif request.method in ["PUT", "PATCH"]:
            metodo_str = "Editar"
        elif request.method == "DELETE":
            metodo_str = "Borrar"

        entidad_str = _resolve_audit_entity(path)

        partes_ruta = path.rstrip("/").split("/")
        id_registro = ""
        ultima_parte = partes_ruta[-1]
        
        if ultima_parte not in {
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
            "liquidaciones",
            "carteras",
            "inversores",
            "cheques",
            "bancos",
            "cuentas",
            "movimientos",
            "comprobantes",
            "proveedores",
            "posicion-iva",
            "posicion-iibb",
            "facturacion",
            "planes",
            "papeleria",
            "bcra",
            "system",
            "uploads",
        }:
            id_registro = f" (ID: {ultima_parte})"
        
        detalles_sanitizados = None
        if "application/json" in request.headers.get("content-type", ""):
            try:
                body = await request.json()
                if isinstance(body, dict):
                    detalles_sanitizados = sanitize_audit_payload(body)
                    if request.method == "POST" and not id_registro:
                        if "cuil" in body:
                            id_registro = f" (ID: {body['cuil']})"
                        elif "id" in body:
                            id_registro = f" (ID: {body['id']})"
            except Exception:
                pass

        accion_legible = f"{metodo_str} {entidad_str}{id_registro}"

        log = RegistroAuditoria(
            usuario_id=current_user.id,
            accion=accion_legible,
            endpoint=path,
            metodo=request.method,
            direccion_ip=extract_client_ip(request),
            estado="Éxito",
            detalles=detalles_sanitizados,
        )
        db.add(log)
        db.commit()

    return current_user
