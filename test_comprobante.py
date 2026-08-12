from fastapi.testclient import TestClient
from src.api.main import app
from src.api.dependencies.auth import enforce_rbac

# Override auth dependency
app.dependency_overrides[enforce_rbac] = lambda: None

client = TestClient(app)

payload = {
    "proveedor_id": 1,
    "tipo_comprobante": "A",
    "punto_venta": 3,
    "numero_comprobante": 252,
    "fecha_contable": "2026-07-31",
    "fecha_emision": "2026-07-31",
    "fecha_vencimiento": "2026-08-30",
    "importe_no_gravado": 0,
    "importe_exento": 0,
    "neto_gravado_21": 23098137.15,
    "neto_gravado_105": 0,
    "neto_gravado_27": 0,
    "iva_21": 4850608.80,
    "iva_105": 0,
    "iva_27": 0,
    "percepcion_iva": 0,
    "percepcion_iibb": 0,
    "percepcion_ganancias": 0,
    "otros_impuestos": 0
}

res = client.post("/api/finanzas/comprobantes", json=payload)
print("STATUS:", res.status_code)
print("RESPONSE:", res.json())
