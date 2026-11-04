import pytest
import io
import pandas as pd
from datetime import date
from src.database.models import Cliente, SocioComercial, TasaYComision, Relacion, Credito, Transferencia, Nacionalidad, Provincia
from src.logic.creditos.import_data import quota

CLIENTES_CSV_SAMPLE = """ID,APELLIDO,NOMBRE,D.N.I.,C.U.I.L.,LEGAJO,ESTADO,FECHA ESTADO,CBU,FECHA NACIMIENTO,SEXO,ESTADO CIVIL,NACIONALIDAD,TELÉFONO,CELULAR,E-MAIL,CALLE,CALLE NÚMERO,PISO,DEPTO.,BARRIO,LOCALIDAD,CÓDIGO POSTAL,PROVINCIA
608,SOSA,SILVINA MIRIAM,22348360,27223483602,,ACTIVO,2026-10-30,1.1031733003171e+20,1972-03-11,F,SOLTERO/A,ARGENTINA,2635142785,2634561787,SOSASILVINA691@GMAIL.COM,ROBERTO ORTIZ,149,,,,SANTA ROSA,5592,MENDOZA
607,FERNANDEZ,JULIO OSCAR,28024150,20280241505,,ACTIVO,2026-10-29,1.10285930028521e+20,1980-01-30,M,SOLTERO/A,ARGENTINA,2618239128,2612728739,JF224352@GMAIL.COM,BARRIO PUESTA DEL SOL II M A L 27,0,,,,CHACRAS DE CORIA,5505,MENDOZA
606,GIMENEZ,CLARA AMELIA,27473144,27274731449,,ACTIVO,2026-10-28,1.10266830026614e+20,1979-06-28,F,SOLTERO/A,ARGENTINA,2625235871,2625632929,GIMENEZCLARAAMELIA@GMAIL.COM,CHAPEAUROUGE,0,,,,GENERAL ALVEAR,5620,MENDOZA
605,ROMERO,CLAUDIA MARIELA,22902920,27229029202,,ACTIVO,2026-10-28,1.10606630060605e+20,1972-11-22,F,SOLTERO/A,ARGENTINA,2616182839,2616148321,CLAUDIAAAMARIELAROMERO@GMAIL.COM,LUGONES,2880,,,EL MANGRULLO,GENERAL GUTIÉRREZ,5511,MENDOZA
604,AMORES,HILDA VERONICA,24398488,27243984888,,ACTIVO,2026-10-28,1.10438130043807e+20,1975-02-04,F,SOLTERO/A,ARGENTINA,2637428374,2634755098,VEROAMORES221@GMAIL.COM,D ANGELO,362,,,,RIVADAVIA,5577,MENDOZA"""

CREDITOS_CSV_SAMPLE = """Emisión,Cliente,Apellido,Nombre,DNI,CBU,Estado,Organismo,Fondeador,Línea,Crédito,Capital,Cbz. Cap.,Interés,Cbz. Int.,Neto,Plazo,Imp. Cuota,Cbz.(%),Tasa,ID Externo,Q.Tr.,Comer.
2026-10-28,604,AMORES,HILDA VERONICA,24398488,0110438130043807597301,LIQUIDADO,MENDOZA - DIRECCIÓN GENERAL DE ESCUELAS,NEOCREDIT - MENDOZA (PREMIUM),AMJAR,14798,4069767.44,0,4148561.44,0,3500000,18,504973.71,0,125,CH_142123,3,MENDOZA - GABRIELA LAGOS
2026-10-28,605,ROMERO,CLAUDIA MARIELA,22902920,0110606630060605783651,LIQUIDADO,MENDOZA - PODER JUDICIAL,NEOCREDIT - MENDOZA (PREMIUM),AMJAR,14799,1162790.7,0,616849.68,0,1000000,9,212130.98,0,137,CH_142127,3,MENDOZA - GRISELDA SILVA
2026-10-28,606,GIMENEZ,CLARA AMELIA,27473144,0110266830026614175883,LIQUIDADO,MENDOZA - DIRECCIÓN GENERAL DE ESCUELAS,NEOCREDIT - MENDOZA (PREMIUM),AMJAR,14800,482558.14,0,655510.02,0,415000,24,53155.22,0,120,CH_142180,5,MENDOZA - GABRIELA LAGOS
2026-10-29,607,FERNANDEZ,JULIO OSCAR,28024150,0110285930028521696929,LIQUIDADO,MENDOZA - DIRECCIÓN GENERAL DE ESCUELAS,NEOCREDIT - MENDOZA (PREMIUM),AMJAR,14801,2516279.07,0,3418129.77,0,2164000,24,277175.67,0,120,CH_142207,3,MENDOZA - GABRIELA LAGOS
2026-10-30,608,SOSA,SILVINA MIRIAM,22348360,0110317330031710063383,LIQUIDADO,MENDOZA - DIRECCIÓN GENERAL DE ESCUELAS,NEOCREDIT - MENDOZA (PREMIUM),AMJAR,14802,515116.28,0,699737.28,0,443000,24,56741.6,0,120,CH_141969,3,MENDOZA - PEDROSA NESTOR"""

TRANSFERENCIAS_CSV_SAMPLE = """0720361788000001053090;30/10/2026;301953.49;23252218874;14801;CANCELACION DEUDA CON 3ROS
0720708420000000188836;30/10/2026;50325.58;30676983348;14801;ASOCIACION MUTUAL JULIO ARGENTINO ROCA
0110285930028521696929;30/10/2026;2164000.00;20280241505;14801;FERNANDEZ JULIO OSCAR
0000003100039569649410;30/10/2026;61813.95;20277657970;14802;CANCELACION DEUDA CON 3ROS
0720708420000000188836;30/10/2026;10302.33;30676983348;14802;ASOCIACION MUTUAL JULIO ARGENTINO ROCA
0110317330031710063383;30/10/2026;443000.00;27223483602;14802;SOSA SILVINA MIRIAM
0720708420000000188836;30/10/2026;23255.81;30676983348;14799;ASOCIACION MUTUAL JULIO ARGENTINO ROCA
0110606630060605783651;30/10/2026;1000000.00;27229029202;14799;ROMERO CLAUDIA MARIELA
0070246330004020357279;30/10/2026;139534.89;27232106811;14799;CANCELACION DEUDA CON 3ROS
0720361788000001053090;30/10/2026;488372.09;23252218874;14798;CANCELACION DEUDA CON 3ROS
0720708420000000188836;30/10/2026;81395.35;30676983348;14798;ASOCIACION MUTUAL JULIO ARGENTINO ROCA
0110438130043807597301;30/10/2026;3500000.00;27243984888;14798;AMORES HILDA VERONICA
0720361788000001053090;30/10/2026;57906.98;23252218874;14800;CANCELACION DEUDA CON 3ROS
0720708420000000188836;30/10/2026;9651.16;30676983348;14800;ASOCIACION MUTUAL JULIO ARGENTINO ROCA
0110599520000052429905;30/10/2026;102728.50;30675808992;14800;GC 366.561
0720708420000000188836;30/10/2026;116500.00;30676983348;14800;AMJAR C3
0000003100058351792903;30/10/2026;195771.50;27274731449;14800;GIMENEZ CLARA AMELIA"""


def test_import_clients_without_sa_instance_state_error(db_session):
    df_clts = pd.read_csv(io.StringIO(CLIENTES_CSV_SAMPLE))
    df_clts.columns = [str(c).strip() for c in df_clts.columns]

    res = quota.import_clients_from_dataframe(df_clts, db_session)

    assert len(res["errores"]) == 0, f"Se encontraron errores: {res['errores']}"
    assert res["nuevos"] == 5

    # Verificar que los clientes se hayan persistido
    sosa = db_session.query(Cliente).filter_by(cuil="27223483602").first()
    assert sosa is not None
    assert sosa.apellido == "SOSA"
    assert sosa.nombre == "SILVINA MIRIAM"
    assert sosa.id_nacionalidad is not None

    nac = db_session.query(Nacionalidad).filter_by(id=sosa.id_nacionalidad).first()
    assert nac is not None
    assert nac.nombre == "ARGENTINA"

    assert sosa.id_provincia is not None
    prov = db_session.query(Provincia).filter_by(id=sosa.id_provincia).first()
    assert prov is not None
    assert prov.nombre == "MENDOZA"


def test_update_clients_from_crts(db_session):
    df_clts = pd.read_csv(io.StringIO(CLIENTES_CSV_SAMPLE))
    df_clts.columns = [str(c).strip() for c in df_clts.columns]
    quota.import_clients_from_dataframe(df_clts, db_session)

    df_crts = pd.read_csv(io.StringIO(CREDITOS_CSV_SAMPLE))
    df_crts.columns = [str(c).strip() for c in df_crts.columns]

    res_upd = quota.update_clients_from_crts_dataframe(df_crts, db_session)
    assert len(res_upd["errores"]) == 0
    assert res_upd["actualizados"] == 5

    # Verificar que el CBU se actualizó al formato de 22 dígitos del archivo de créditos
    sosa = db_session.query(Cliente).filter_by(cuil="27223483602").first()
    assert sosa.cbu == "0110317330031710063383"
    assert sosa.empleador is not None
    assert "DIRECCIÓN GENERAL DE ESCUELAS" in sosa.empleador.razon_social


def test_validation_fase_cero_missing_mapping(db_session):
    df_crts = pd.read_csv(io.StringIO(CREDITOS_CSV_SAMPLE))
    df_crts.columns = [str(c).strip() for c in df_crts.columns]

    # Sin relaciones cargadas
    map_socios = Relacion.get_external_mapping_cache(8, "socios_comerciales", db_session)

    lineas_faltantes = set()
    for _, row in df_crts.iterrows():
        linea_val = str(row.get('Línea', row.get('Linea', ''))).strip()
        if linea_val and linea_val != 'nan' and linea_val not in map_socios:
            lineas_faltantes.add(linea_val)

    assert "AMJAR" in lineas_faltantes


def test_import_credits_and_transfers_with_mapping(db_session):
    # 1. Clientes
    df_clts = pd.read_csv(io.StringIO(CLIENTES_CSV_SAMPLE))
    df_clts.columns = [str(c).strip() for c in df_clts.columns]
    quota.import_clients_from_dataframe(df_clts, db_session)

    # 2. Socio comercial SISTEMA QUOTA y socio comercial AMJAR
    socio_quota = SocioComercial(razon_social="SISTEMA QUOTA", cuit="30000000001", dia_corte=28)
    socio_amjar = SocioComercial(razon_social="ASOCIACION MUTUAL JULIO ARGENTINO ROCA", cuit="30676983348", dia_corte=28)
    db_session.add_all([socio_quota, socio_amjar])
    db_session.commit()

    # Mapeo en Relacion
    Relacion.add_single_mapping(
        socio_id=socio_quota.id,
        tabla="socios_comerciales",
        id_local=socio_amjar.id,
        id_foraneo="AMJAR",
        db=db_session
    )

    # Crear tasas y comisiones para AMJAR para los plazos (18, 9, 24) y tasas (1.25, 1.37, 1.20)
    rates_data = [
        (18, 1.25),
        (9, 1.37),
        (24, 1.20)
    ]
    for plazo, tasa in rates_data:
        tc = TasaYComision(
            fecha=date(2026, 1, 1),
            socio_originador_id=socio_amjar.id,
            socio_intermediario_id=socio_amjar.id,
            plazo=plazo,
            tna_c_iva=tasa,
            colocacion_originador=0.0
        )
        db_session.add(tc)
    db_session.commit()

    df_crts = pd.read_csv(io.StringIO(CREDITOS_CSV_SAMPLE))
    df_crts.columns = [str(c).strip() for c in df_crts.columns]
    quota.update_clients_from_crts_dataframe(df_crts, db_session)

    map_socios = Relacion.get_external_mapping_cache(socio_quota.id, "socios_comerciales", db_session)
    assert "AMJAR" in map_socios

    # Importar créditos
    res_crts = quota.import_credits_from_dataframe(df_crts, db_session, map_socios=map_socios)
    assert len(res_crts["errores"]) == 0, f"Errores créditos: {res_crts['errores']}"
    assert res_crts["nuevos_creditos"] == 5

    # 3. Transferencias
    df_transf = pd.read_csv(
        io.StringIO(TRANSFERENCIAS_CSV_SAMPLE),
        sep=";",
        header=None,
        names=["CBU/CVU", "Fecha", "Monto", "CUIT/CUIL", "ID Quota", "Razon Social"]
    )
    nuevos_ids = res_crts["nuevos_ids_externos"]
    res_transf = quota.import_transfers_from_dataframe(df_transf, df_crts, db_session, nuevos_ids_externos=nuevos_ids)
    assert len(res_transf["errores"]) == 0, f"Errores transf: {res_transf['errores']}"
    assert res_transf["importadas"] == 17

