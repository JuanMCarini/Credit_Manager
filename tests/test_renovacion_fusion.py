import tempfile
from pathlib import Path
from datetime import date, timedelta
import pytest

from src.database.models.deuda.series import Serie, Comision, ComisionesSerie
from src.database.models.deuda.movimientos import MovimientoDeuda, TipoMovimiento
from src.database.models.deuda.inversores import Inversor, CuentaComitente, TitularidadCuentaComitente
from src.database.models import SocioComercial
from src.logic.deuda.vencimiento import preview_renovacion, renovación


class _NonClosingSessionProxy:
    def __init__(self, session):
        self._session = session

    def close(self):
        pass

    def __getattr__(self, name):
        return getattr(self._session, name)


@pytest.fixture(autouse=True)
def patch_session_local(db_session, monkeypatch):
    factory = lambda: _NonClosingSessionProxy(db_session)
    monkeypatch.setattr("src.database.SessionLocal", factory)
    monkeypatch.setattr("src.database.connection.SessionLocal", factory)
    monkeypatch.setattr("src.logic.deuda.vencimiento.SessionLocal", factory)
    monkeypatch.setattr("src.logic.deuda.ctas_ctes.SessionLocal", factory)
    return db_session


def test_fusion_series_distinto_vencimiento_falla(db_session):
    db = db_session
    s1_name = "Serie Fusion Diff 1"
    s2_name = "Serie Fusion Diff 2"
    s_new = "Serie Fusion Nueva Diff"

    # s1 vence en 2026-01-01
    s1 = Serie(name=s1_name, fecha_suscripcion=date(2025, 1, 1), tna=0.40, plazo=365)
    # s2 vence en 2025-07-01
    s2 = Serie(name=s2_name, fecha_suscripcion=date(2025, 1, 1), tna=0.40, plazo=181)
    db.add_all([s1, s2])
    db.commit()

    with pytest.raises(ValueError, match="Las series a fusionar deben tener la misma fecha de vencimiento"):
        preview_renovacion(
            serie_vieja=[s1_name, s2_name],
            serie_nueva=s_new,
            fecha=date(2026, 1, 1),
            tna=0.50,
            plazo=180,
            path=None
        )


def test_fusion_series_mismo_vencimiento_exito(db_session):
    db = db_session
    s1_name = "Serie Fusion Same 1"
    s2_name = "Serie Fusion Same 2"
    s_new = "Serie Fusion Same Nueva"

    fecha_vto = date(2026, 1, 1)
    fecha_s1 = fecha_vto - timedelta(days=365)  # 2025-01-01
    plazo_s1 = 365
    fecha_s2 = fecha_vto - timedelta(days=180)  # 2025-07-05
    plazo_s2 = 180

    # Crear socio y comision para s1
    sc = SocioComercial(cuit="30700000099", razon_social="Socio Fusion Test")
    db.add(sc)
    db.flush()

    comision_obj = Comision(fecha=fecha_s1, id_socio_comercial=sc.id, porcentaje=3.0)
    db.add(comision_obj)
    db.flush()

    s1 = Serie(name=s1_name, fecha_suscripcion=fecha_s1, tna=0.40, plazo=plazo_s1, comision=True)
    s2 = Serie(name=s2_name, fecha_suscripcion=fecha_s2, tna=0.30, plazo=plazo_s2, comision=False)
    db.add_all([s1, s2])
    db.flush()

    db.add(ComisionesSerie(id_serie=s1.id, id_comision=comision_obj.id))

    # Inversor y Cuenta Comitente
    inv = Inversor(cuit="20444444449", razon_social="Inversor Fusion Test")
    db.add(inv)
    db.flush()

    cta = CuentaComitente(id_externo="8881", conjunta=False)
    db.add(cta)
    db.flush()

    db.add(TitularidadCuentaComitente(id_cuenta_comitente=cta.id, id_inversor=inv.id, orden=1))

    # Suscripción en s1: 100,000 (interes al 40% = 40,000 => total 140,000)
    mov1 = MovimientoDeuda(
        id_cuenta_comitente=cta.id,
        id_serie=s1.id,
        fecha=fecha_s1,
        monto=100000,
        tipo_movimiento=TipoMovimiento.SUSCRIPCION
    )
    # Suscripción en s2: 50,000 (interes al 30% x 180 / 365 = 7397.26 => total 57,397.26)
    mov2 = MovimientoDeuda(
        id_cuenta_comitente=cta.id,
        id_serie=s2.id,
        fecha=fecha_s2,
        monto=50000,
        tipo_movimiento=TipoMovimiento.SUSCRIPCION
    )
    db.add_all([mov1, mov2])
    db.commit()

    # Ambas series vencen el mismo día
    assert s1.fecha_vencimiento == s2.fecha_vencimiento == fecha_vto

    csv_content = (
        "Cta;Titular;CUIT;Dir;Cap;Int;Tot;Res;Susc;Obs\n"
        "8881;Inversor Fusion Test;20444444449;Calle 123;150000;47397.26;170000;37397.26;10000;Fusion Test\n"
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", encoding="utf-8") as tmp:
        tmp.write(csv_content)
        tmp_path = Path(tmp.name)

    try:
        # 1. Preview con lista de nombres
        preview = preview_renovacion(
            serie_vieja=[s1_name, s2_name],
            serie_nueva=s_new,
            fecha=fecha_vto,
            tna=0.45,
            plazo=365,
            path=tmp_path
        )

        assert len(preview["series_viejas"]) == 2
        assert preview["series_viejas"][0]["name"] == s1_name
        assert preview["series_viejas"][1]["name"] == s2_name
        assert preview["serie_nueva"]["name"] == s_new
        assert preview["serie_nueva"]["comision"] is True
        assert preview["resumen"]["total_capital_anterior"] == 150000.00
        assert preview["resumen"]["total_interes_anterior"] == 47397.26
        assert preview["resumen"]["total_rescates"] == 37397.26
        assert preview["resumen"]["total_renovado"] == 160000.00
        assert preview["resumen"]["total_nuevas_suscripciones"] == 10000.00
        assert preview["resumen"]["total_nuevo_capital"] == 170000.00

        # 2. Preview pasando JSON string como llegaría desde FormData
        preview_json = preview_renovacion(
            serie_vieja=f'["{s1_name}", "{s2_name}"]',
            serie_nueva=s_new,
            fecha=fecha_vto,
            tna=0.45,
            plazo=365,
            path=tmp_path
        )
        assert len(preview_json["series_viejas"]) == 2

        # 3. Ejecutar renovación fusionada
        df_ei = renovación(
            serie_vieja=[s1_name, s2_name],
            serie_nueva=s_new,
            fecha=fecha_vto,
            tna=0.45,
            plazo=365,
            path=tmp_path
        )

        assert not df_ei.empty

        # Verificar en DB
        db_nueva = db.query(Serie).filter(Serie.name == s_new).first()
        assert db_nueva is not None
        assert db_nueva.comision is True

        # Verificar que heredó comisiones_asociadas
        assert len(db_nueva.comisiones_asociadas) == 1
        assert db_nueva.comisiones_asociadas[0].id_comision == comision_obj.id

        # Verificar movimientos de s1
        movs_s1 = db.query(MovimientoDeuda).filter(MovimientoDeuda.id_serie == s1.id).all()
        tipos_s1 = {m.tipo_movimiento for m in movs_s1}
        assert TipoMovimiento.RESCATE in tipos_s1
        assert TipoMovimiento.RENOVACION_RESCATE in tipos_s1

        # Verificar movimientos de s2
        movs_s2 = db.query(MovimientoDeuda).filter(MovimientoDeuda.id_serie == s2.id).all()
        tipos_s2 = {m.tipo_movimiento for m in movs_s2}
        assert TipoMovimiento.RESCATE in tipos_s2
        assert TipoMovimiento.RENOVACION_RESCATE in tipos_s2

        # Verificar movimientos de s_new
        movs_nueva = db.query(MovimientoDeuda).filter(MovimientoDeuda.id_serie == db_nueva.id).all()
        tipos_nueva = {m.tipo_movimiento for m in movs_nueva}
        assert TipoMovimiento.RENOVACION_SUSCRIPCION in tipos_nueva
        assert TipoMovimiento.SUSCRIPCION in tipos_nueva

        total_renov_nueva = sum(m.monto for m in movs_nueva if m.tipo_movimiento == TipoMovimiento.RENOVACION_SUSCRIPCION)
        total_extra_nueva = sum(m.monto for m in movs_nueva if m.tipo_movimiento == TipoMovimiento.SUSCRIPCION)
        assert total_renov_nueva == 160000.00
        assert total_extra_nueva == 10000.00
    finally:
        tmp_path.unlink(missing_ok=True)


def test_fusion_rescate_total_columna_total_bruto(db_session):
    """
    Verifica que si una fila tiene rescate total (Rescate == Capital + Interés)
    pero en el archivo la columna Total se dejó como Capital + Interés (total bruto vencido),
    el sistema lo reconozca automáticamente, normalice el total a 0.00 y asigne 'Rescate Total'.
    También verifica cuentas con múltiples filas (cotitulares).
    """
    db = db_session
    s1_name = "Serie Fusion Bruto 1"
    s2_name = "Serie Fusion Bruto 2"
    s_new = "Serie Fusion Bruto Nueva"
    fecha_vto = date(2026, 10, 19)

    s1 = Serie(name=s1_name, fecha_suscripcion=date(2026, 7, 20), tna=0.32, plazo=91)
    s2 = Serie(name=s2_name, fecha_suscripcion=date(2026, 7, 21), tna=0.32, plazo=90)
    db.add_all([s1, s2])
    db.flush()

    # Inversor A (rescate total) en s1: Cta 7771
    inv_a = Inversor(cuit="20777777771", razon_social="Inversor Rescate Total")
    db.add(inv_a)
    db.flush()

    cta_a = CuentaComitente(id_externo="7771")
    db.add(cta_a)
    db.flush()

    db.add(TitularidadCuentaComitente(id_cuenta_comitente=cta_a.id, id_inversor=inv_a.id, orden=1))

    # Cap: 10,000,000, Int al 32% x 91/365 = 797808.22
    mov_a = MovimientoDeuda(id_cuenta_comitente=cta_a.id, id_serie=s1.id, fecha=date(2026, 7, 20), monto=10000000, tipo_movimiento=TipoMovimiento.SUSCRIPCION)

    # Inversor B (cuenta compartida 7772 en s1 y s2): Cta 7772
    inv_b1 = Inversor(cuit="20777777772", razon_social="Titular B1")
    inv_b2 = Inversor(cuit="20777777773", razon_social="Titular B2")
    db.add_all([inv_b1, inv_b2])
    db.flush()

    cta_b = CuentaComitente(id_externo="7772")
    db.add(cta_b)
    db.flush()

    db.add(TitularidadCuentaComitente(id_cuenta_comitente=cta_b.id, id_inversor=inv_b1.id, orden=1))
    db.add(TitularidadCuentaComitente(id_cuenta_comitente=cta_b.id, id_inversor=inv_b2.id, orden=2))

    # Suscripción en s1: 5,000,000 (int: 398904.11)
    mov_b1 = MovimientoDeuda(id_cuenta_comitente=cta_b.id, id_serie=s1.id, fecha=date(2026, 7, 20), monto=5000000, tipo_movimiento=TipoMovimiento.SUSCRIPCION)
    # Suscripción en s2: 3,000,000 (int al 32% x 90/365 = 236712.33)
    mov_b2 = MovimientoDeuda(id_cuenta_comitente=cta_b.id, id_serie=s2.id, fecha=date(2026, 7, 21), monto=3000000, tipo_movimiento=TipoMovimiento.SUSCRIPCION)

    db.add_all([mov_a, mov_b1, mov_b2])
    db.commit()

    csv_content = (
        "Cta;Titular;CUIT;Dir;Cap;Int;Tot;Res;Susc;Obs\n"
        "7771;Inversor Rescate Total;20777777771;Calle 1;10000000;797808.22;10797808.22;10797808.22;0;Rescate Total\n"
        "7772;Titular B1;20777777772;Calle 2;5000000;398904.11;5398904.11;0;0;Porcion s1\n"
        "7772;Titular B2;20777777773;Calle 2;3000000;236712.33;3236712.33;0;0;Porcion s2\n"
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", encoding="utf-8") as tmp:
        tmp.write(csv_content)
        tmp_path = Path(tmp.name)

    try:
        preview = preview_renovacion(
            serie_vieja=[s1_name, s2_name],
            serie_nueva=s_new,
            fecha=fecha_vto,
            tna=0.32,
            plazo=90,
            path=tmp_path
        )

        assert len(preview["series_viejas"]) == 2
        fila_7771 = next(f for f in preview["filas"] if f["id_cuenta"] == "7771")
        assert fila_7771["accion"] == "Rescate Total"
        assert fila_7771["rescate"] == 10797808.22
        assert fila_7771["renovacion"] == 0.0
        assert fila_7771["total"] == 0.0

        filas_7772 = [f for f in preview["filas"] if f["id_cuenta"] == "7772"]
        assert len(filas_7772) == 2
        tot_7772 = round(sum(f["total"] for f in filas_7772), 2)
        assert tot_7772 == round(5398904.11 + 3236712.33, 2)
    finally:
        tmp_path.unlink(missing_ok=True)
