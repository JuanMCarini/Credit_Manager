import importlib
import zipfile
import io
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from src.database.models import Cliente, Credito, Cuota, TipoCredito, EstadoCuota, Cobranza
from src.database.models.creditos.cobranzas import TipoCobranzaEnum
from src.database.models.socios import TasaYComision, EstadoComisionEnum
from src.database.models.creditos.perfil_trans import (
    PerfilTransaccional,
    ReglasPerfilTransaccional,
    TipoSueldo,
)
from src.database.models.creditos.repet import RepetPerson, RepetAuditLog


class _NonClosingSessionProxy:
    def __init__(self, session):
        self._session = session

    def close(self):
        pass

    def __getattr__(self, name):
        return getattr(self._session, name)


def test_bcra_service_lazy_session_initialization(monkeypatch):
    import src.services.bcra as bcra_mod

    monkeypatch.setattr("curl_cffi.requests.Session", MagicMock())
    reloaded = importlib.reload(bcra_mod)
    assert reloaded.session_bcra is None

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.text = '{"status": 404}'
    fake_resp.json.return_value = {"status": 404}

    fake_session = MagicMock()
    fake_session.get.return_value = fake_resp

    create_calls = []

    def _fake_create():
        create_calls.append(1)
        return fake_session

    monkeypatch.setattr(reloaded, "crear_sesion_bcra", _fake_create)
    res = reloaded.consultar_cuit_api("20999999999")
    assert res["Estado"] == "Sin Deudas"
    assert len(create_calls) == 1

    # Segunda llamada reutiliza la sesión ya inicializada
    res2 = reloaded.consultar_cuit_api("20999999999")
    assert res2["Estado"] == "Sin Deudas"
    assert len(create_calls) == 1


def _run_coro_sync(coro):
    """Ejecuta una corrutina sin event loop (evita socketpair en sandbox de Windows)."""
    try:
        while True:
            coro.send(None)
    except StopIteration as stop:
        return stop.value


def test_repet_sync_preserves_data_on_invalid_payload(db_session, monkeypatch):
    from src.services.repet import sync_repet_data

    db_session.add(
        RepetPerson(
            nombre_completo="PERSONA TEST",
            nombre_normalizado="persona test",
            documento="11223344",
        )
    )
    db_session.commit()

    class _FakeResp:
        def __init__(self, payload, status=200):
            self._payload = payload
            self._status = status

        def raise_for_status(self):
            if self._status >= 400:
                raise RuntimeError(f"HTTP {self._status}")

        def json(self):
            return self._payload

    class _FakeClient:
        def __init__(self, payload_per, payload_ent):
            self.payload_per = payload_per
            self.payload_ent = payload_ent

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return False

        async def get(self, url, timeout=60.0):
            if "personas" in url:
                return _FakeResp(self.payload_per)
            return _FakeResp(self.payload_ent)

    # Caso 1: dict de error en lugar de lista
    monkeypatch.setattr(
        "src.services.repet.httpx.AsyncClient",
        lambda: _FakeClient({"error": "maintenance"}, []),
    )
    _run_coro_sync(sync_repet_data(db_session))
    assert db_session.query(RepetPerson).count() == 1

    # Caso 2: lista vacía
    monkeypatch.setattr(
        "src.services.repet.httpx.AsyncClient",
        lambda: _FakeClient([], []),
    )
    _run_coro_sync(sync_repet_data(db_session))
    assert db_session.query(RepetPerson).count() == 1


def test_repet_screen_person_audit_per_cuil_and_dni_match(db_session):
    from src.services.repet import screen_person

    c1 = Cliente(cuil="20111111111", documento="11111111", apellido="Gomez", nombre="Carlos")
    c2 = Cliente(cuil="20222222222", documento="22222222", apellido="Gomez", nombre="Carlos")
    c3 = Cliente(cuil="20333333333", documento="33333333", apellido="Lopez", nombre="Ana")
    db_session.add_all([c1, c2, c3])

    repet_target = RepetPerson(
        nombre_completo="ALIAS DISTINTO",
        nombre_normalizado="alias distinto",
        documento="33333333",
    )
    db_session.add(repet_target)
    db_session.commit()

    # Homónimos con distinto CUIL deben registrar logs separados hoy
    r1 = screen_person(db_session, "Carlos Gomez", c1.cuil)
    r2 = screen_person(db_session, "Carlos Gomez", c2.cuil)
    assert r1["status"] == "CLEAN"
    assert r2["status"] == "CLEAN"

    logs_homonimos = (
        db_session.query(RepetAuditLog)
        .filter(RepetAuditLog.cuil_cliente.in_([c1.cuil, c2.cuil]))
        .all()
    )
    assert len(logs_homonimos) == 2

    # Coincidencia exacta por DNI aunque el nombre difiera
    r3 = screen_person(db_session, "Ana Lopez", c3.cuil)
    assert r3["status"] == "ALERT"
    assert r3["score"] == 100.0
    assert r3["matched_id"] == repet_target.id


def test_uif_capital_neto_maximo_decimal_and_empty_rates(db_session, dummy_cliente, dummy_socio, monkeypatch):
    from src.logic.uif.perfil_transaccional import capital_neto_maximo

    factory = lambda: _NonClosingSessionProxy(db_session)
    monkeypatch.setattr("src.logic.uif.perfil_transaccional.SessionLocal", factory)

    periodo = date(2026, 9, 1)
    regla = ReglasPerfilTransaccional(
        id_socio_comercial=dummy_socio.id,
        cupo=Decimal("0.3000"),
        sueldo_tipo=TipoSueldo.neto,
        asignacion_familiar=True,
        horas_extras=True,
        vacaciones=True,
        otros=True,
        descuentos_voluntarios=True,
        cap_min=Decimal("1000.00"),
        cap_max=Decimal("500000.00"),
    )
    perfil = PerfilTransaccional(
        cuil_cliente=dummy_cliente.cuil,
        periodo=periodo,
        ingreso_bruto=Decimal("1200000.00"),
        ingreso_neto=Decimal("1000000.00"),
        asignacion_familiar=Decimal("0.00"),
        horas_extras=Decimal("0.00"),
        vacaciones=Decimal("0.00"),
        descuentos_voluntarios=Decimal("0.00"),
        otros=Decimal("0.00"),
    )
    db_session.add_all([regla, perfil])
    db_session.commit()

    # 1. Sin tasas activas: retorna DataFrame vacío con esquema esperado
    df_empty = capital_neto_maximo(dummy_cliente.cuil, periodo, dummy_socio)
    assert df_empty.empty
    assert list(df_empty.columns) == ["id", "plazo", "gracia", "tna_c_iva", "cap_neto_max"]

    # 2. Con tasa Decimal activa: no debe fallar por float / Decimal
    tasa = TasaYComision(
        fecha=periodo,
        estado=EstadoComisionEnum.ACTIVA,
        socio_originador_id=dummy_socio.id,
        socio_intermediario_id=dummy_socio.id,
        plazo=12,
        tna_c_iva=Decimal("0.600000"),
        colocacion_originador=Decimal("0.000000"),
        colocacion_intermediario=Decimal("0.000000"),
        cobranza_originador=Decimal("0.000000"),
        cobranza_intermediario=Decimal("0.000000"),
        colocacion_propia=Decimal("0.000000"),
        porcentaje_sellado=Decimal("0.010000"),
        gasto_1_porcentaje=Decimal("0.020000"),
        gasto_2_porcentaje=Decimal("0.000000"),
    )
    db_session.add(tasa)
    db_session.commit()

    df_res = capital_neto_maximo(dummy_cliente.cuil, periodo, dummy_socio)
    assert len(df_res) == 1
    assert df_res.iloc[0]["gracia"] == 2
    assert float(df_res.iloc[0]["cap_neto_max"]) > 0.0


def test_balances_y_bcra_logic_decimal_y_sin_cobranzas(
    db_session, dummy_cliente, dummy_socio, dummy_cartera, monkeypatch
):
    from src.reports.balances import saldos, cobranzas_recibidas, cuotas_teoricas
    from src.reports.bcra_logic import format_bcra_amount, generate_bcra_files

    monkeypatch.setattr("src.reports.balances.engine", db_session.get_bind())
    monkeypatch.setattr("src.reports.bcra_logic.engine", db_session.get_bind())

    assert format_bcra_amount(Decimal("15499.99")) == "000000000015"

    cred = Credito(
        cliente_cuil=dummy_cliente.cuil,
        socio_originador_id=dummy_socio.id,
        cartera_id=dummy_cartera.id,
        capital=Decimal("20000.00"),
        tna_c_iva=Decimal("0.550000"),
        plazo=2,
        fecha_emision=date(2026, 8, 1),
        tipo_credito=TipoCredito.FRANCES,
    )
    db_session.add(cred)
    db_session.flush()

    q1 = Cuota(
        credito_id=cred.id,
        nro_cuota=1,
        fecha_vencimiento=date(2026, 8, 15),
        capital=Decimal("10000.00"),
        interes=Decimal("1000.00"),
        iva=Decimal("210.00"),
        estado=EstadoCuota.MOROSA,
    )
    q2 = Cuota(
        credito_id=cred.id,
        nro_cuota=2,
        fecha_vencimiento=date(2026, 10, 15),
        capital=Decimal("10000.00"),
        interes=Decimal("1000.00"),
        iva=Decimal("210.00"),
        estado=EstadoCuota.PENDIENTE,
    )
    db_session.add_all([q1, q2])
    db_session.commit()

    # 1. Sin cobranzas
    df_saldos_sin_cobr = saldos(fecha=datetime(2026, 9, 30), con_saldo=True)
    assert len(df_saldos_sin_cobr) == 2

    df_teo = cuotas_teoricas(meses=3, fecha=datetime(2026, 10, 31))
    assert not df_teo.empty
    assert float(df_teo["total"].sum()) == 22420.0

    # 2. Con cobranza parcial Decimal y generación BCRA NORMAL + RECTIFICATORIO
    db_session.add(
        Cobranza(
            cuota_id=q1.id,
            fecha=date(2026, 9, 1),
            capital=Decimal("2000.00"),
            interes=Decimal("500.00"),
            iva=Decimal("105.00"),
            tipo_cobranza=TipoCobranzaEnum.COMUN,
        )
    )
    db_session.commit()

    df_cobr = cobranzas_recibidas(meses=3, fecha=datetime(2026, 9, 30))
    assert not df_cobr.empty
    assert float(df_cobr["total"].sum()) == 2605.0

    zip_normal = generate_bcra_files(fecha_corte=date(2026, 9, 30), tipo_reporte="NORMAL")
    with zipfile.ZipFile(io.BytesIO(zip_normal), "r") as zf:
        assert set(zf.namelist()) == {"PROVEEDORES.TXT", "IMPORTES.TXT", "TASA.TXT"}
        tasa_txt = zf.read("TASA.TXT").decode("cp1252")
        assert "055,00" in tasa_txt

    zip_recti = generate_bcra_files(fecha_corte=date(2026, 9, 30), tipo_reporte="RECTIFICATORIO")
    with zipfile.ZipFile(io.BytesIO(zip_recti), "r") as zf:
        assert zf.namelist() == ["RECTIFICATIVA.TXT"]
        assert dummy_cliente.cuil in zf.read("RECTIFICATIVA.TXT").decode("cp1252")
