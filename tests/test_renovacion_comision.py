import tempfile
from pathlib import Path
from datetime import date
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


def test_renovacion_preserva_comision(db_session):
    db = db_session
    serie_vieja_nombre = "Serie Vieja Comision Test"
    serie_nueva_nombre = "Serie Nueva Comision Test"
    fecha_vieja = date(2025, 1, 1)
    fecha_nueva = date(2026, 1, 1)

    # Crear socio comercial y comisión
    sc = SocioComercial(cuit="30700000001", razon_social="Socio Test Renovacion")
    db.add(sc)
    db.flush()

    comision_obj = Comision(fecha=fecha_vieja, id_socio_comercial=sc.id, porcentaje=2.5)
    db.add(comision_obj)
    db.flush()

    # Crear serie vieja con comision=True y asociación en ComisionesSerie
    old_serie = Serie(
        name=serie_vieja_nombre,
        fecha_suscripcion=fecha_vieja,
        tna=0.40,
        plazo=365,
        comision=True
    )
    db.add(old_serie)
    db.flush()

    cs_asoc = ComisionesSerie(id_serie=old_serie.id, id_comision=comision_obj.id)
    db.add(cs_asoc)

    # Inversor y Cuenta Comitente
    inv = Inversor(cuit="20333333339", razon_social="Inversor Comision Test")
    db.add(inv)
    db.flush()

    cta = CuentaComitente(id_externo="9991", conjunta=False)
    db.add(cta)
    db.flush()

    db.add(TitularidadCuentaComitente(id_cuenta_comitente=cta.id, id_inversor=inv.id, orden=1))

    # Movimiento de suscripción en serie vieja
    mov = MovimientoDeuda(
        id_cuenta_comitente=cta.id,
        id_serie=old_serie.id,
        fecha=fecha_vieja,
        monto=100000,
        tipo_movimiento=TipoMovimiento.SUSCRIPCION
    )
    db.add(mov)
    db.commit()

    # CSV de renovación: 100k capital, 40k interés, 0 rescate, 0 suscripción -> 140k total
    csv_content = (
        "Cta;Titular;CUIT;Dir;Cap;Int;Tot;Res;Susc;Obs\n"
        "9991;Inversor Comision Test;20333333339;Av Libertador 100;100000;40000;140000;0;0;Renovacion\n"
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", encoding="utf-8") as tmp:
        tmp.write(csv_content)
        tmp_path = Path(tmp.name)

    try:
        # 1. Probar preview_renovacion
        preview = preview_renovacion(
            serie_vieja=serie_vieja_nombre,
            serie_nueva=serie_nueva_nombre,
            fecha=fecha_nueva,
            tna=0.50,
            plazo=365,
            path=tmp_path
        )
        assert preview["serie_vieja"]["comision"] is True
        assert preview["serie_nueva"]["comision"] is True

        # 2. Ejecutar renovación
        renovación(
            serie_vieja=serie_vieja_nombre,
            serie_nueva=serie_nueva_nombre,
            fecha=fecha_nueva,
            tna=0.50,
            plazo=365,
            path=tmp_path
        )

        # 3. Verificar en base de datos
        new_s = db.query(Serie).filter(Serie.name == serie_nueva_nombre).first()
        assert new_s is not None, "La nueva serie debe existir en la base de datos"
        assert new_s.comision is True, "La nueva serie debe heredar comision=True de la serie vieja"

        # Verificar que se hayan copiado las comisiones asociadas
        asociaciones = db.query(ComisionesSerie).filter(ComisionesSerie.id_serie == new_s.id).all()
        assert len(asociaciones) == 1
        assert asociaciones[0].id_comision == comision_obj.id
    finally:
        tmp_path.unlink(missing_ok=True)
