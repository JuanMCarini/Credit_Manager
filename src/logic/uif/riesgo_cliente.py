import re
import copy
import pandas as pd

from src.database import SocioComercial
from enum import Enum

from src.database import SessionLocal
from src.database.models import Cliente, Empleador, Nacionalidad
from src.services.bcra import consultar_cuit_api, procesar_respuesta_bcra

class Riesgo(Enum):
    BAJO = "Bajo"
    MEDIO = "Medio"
    ALTO = "Alto"

DEFAULT_CONFIG = {
    "pesos": {
        "base": 0.25,
        "tipo_cliente": 0.1,
        "act_eco": 0.15,
        "nacionalidad": 0.05,
        "residencia": 0.05,
        "edad": 0.20,
        "antiguedad": 0.20,
        "bcra": 0.1
    },
    "multiplicadores": {
        "tipo_cliente_pep": 5,
        "act_eco_pasivo_sin_desc": 5,
        "act_eco_pasivo_con_desc": 3,
        "gafi_gris": 3,
        "gafi_negra": 5,
        "edad_60_75": 3,
        "edad_mayor_75": 5,
        "antiguedad_menor_6_meses": 3,
        "bcra_sit_2": 3,
        "bcra_sit_3_mas": 5
    },
    "cortes": {
        "bajo_max": 2.5,
        "medio_max": 3.5
    }
}

def _merge_configs(base: dict, custom: dict) -> dict:
    if not custom:
        return base
    merged = copy.deepcopy(base)
    for k, v in custom.items():
        if isinstance(v, dict) and k in merged:
            merged[k].update(v)
        else:
            merged[k] = v
    return merged

def calculo(cuil: str, config_personalizada: dict = None) -> tuple[pd.DataFrame, Riesgo]:
    cfg = _merge_configs(DEFAULT_CONFIG, config_personalizada)
    pesos = cfg["pesos"]
    mults = cfg["multiplicadores"]
    cortes = cfg["cortes"]

    db = SessionLocal()
    row = (db
            .query(Cliente, Empleador.es_pasivo, SocioComercial.codigo_descuento, Nacionalidad.lista_gafi)
            .outerjoin(Empleador, Empleador.id == Cliente.empleador_id)
            .outerjoin(SocioComercial, SocioComercial.id == Empleador.socio_comercial_id)
            .outerjoin(Nacionalidad, Nacionalidad.id == Cliente.id_nacionalidad)
            .filter(Cliente.cuil == cuil).first())
    if row:
        cliente_obj, es_pasivo, codigo_descuento, lista_gafi = row
        datos = {c.name: getattr(cliente_obj, c.name) for c in Cliente.__table__.columns}
        datos["es_pasivo"] = es_pasivo
        datos["nacionalidad"] = cliente_obj.nacionalidad.nombre if cliente_obj.nacionalidad else None
        datos["codigo_descuento"] = codigo_descuento
        datos["lista_gafi"] = lista_gafi
    else:
        db.close()
        raise ValueError("Cliente no encontrado")

    detalles_riesgo = []

    # Bloqueos directos
    if datos["repet"]:
        db.close()
        df = pd.DataFrame([{"Factor": "Bloqueo por REPET", "Peso Base": 99.0, "Multiplicador": 1, "Puntaje": 99.0}])
        return df, Riesgo.ALTO

    if datos["pep"] and datos["nacionalidad"] != "ARGENTINA":
        db.close()
        df = pd.DataFrame([{"Factor": "Bloqueo por PEP Extranjero", "Peso Base": 99.0, "Multiplicador": 1, "Puntaje": 99.0}])
        return df, Riesgo.ALTO

    # Base
    peso_base = pesos["base"]
    detalles_riesgo.append({"Factor": "Riesgo Base", "Peso Base": peso_base, "Multiplicador": 1, "Puntaje": peso_base})

    # Tipo de Cliente
    peso_tipo = pesos["tipo_cliente"]
    mult_tipo = mults["tipo_cliente_pep"] if (datos["sujeto_obligado"] or datos["pep"]) else 1
    detalles_riesgo.append({"Factor": "Tipo de Cliente", "Peso Base": peso_tipo, "Multiplicador": mult_tipo, "Puntaje": peso_tipo * mult_tipo})

    # Actividad Economica
    peso_eco = pesos["act_eco"]
    if datos["es_pasivo"] and (not datos["codigo_descuento"]):
        mult_eco = mults["act_eco_pasivo_sin_desc"]
    elif datos["es_pasivo"]:
        mult_eco = mults["act_eco_pasivo_con_desc"]
    else:
        mult_eco = 1
    detalles_riesgo.append({"Factor": "Actividad Económica", "Peso Base": peso_eco, "Multiplicador": mult_eco, "Puntaje": peso_eco * mult_eco})

    # Nacionalidad (GAFI)
    peso_nac = pesos["nacionalidad"]
    if datos["lista_gafi"] == "Lista Blanca":
        mult_nac = 1
    elif datos["lista_gafi"] == "Lista Gris":
        mult_nac = mults["gafi_gris"]
    elif datos["lista_gafi"] == "Lista Negra":
        mult_nac = mults["gafi_negra"]
    else:
        mult_nac = 1
    detalles_riesgo.append({"Factor": "Nacionalidad", "Peso Base": peso_nac, "Multiplicador": mult_nac, "Puntaje": peso_nac * mult_nac})

    # Residencia
    peso_res = pesos["residencia"]
    detalles_riesgo.append({"Factor": "Residencia", "Peso Base": peso_res, "Multiplicador": 1, "Puntaje": peso_res})

    # Edad
    peso_edad = pesos["edad"]
    mult_edad = 1
    fn = datos.get("fecha_nacimiento")
    if fn:
        from datetime import date
        hoy = date.today()
        edad_anios = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
        if edad_anios <= 59:
            mult_edad = 1
        elif 60 <= edad_anios <= 75:
            mult_edad = mults["edad_60_75"]
        else:
            mult_edad = mults["edad_mayor_75"]
    detalles_riesgo.append({"Factor": "Edad", "Peso Base": peso_edad, "Multiplicador": mult_edad, "Puntaje": peso_edad * mult_edad})

    # Antiguedad
    peso_ant = pesos["antiguedad"]
    mult_ant = 1
    fn = datos.get("fecha_ingreso")
    if fn:
        from datetime import date
        hoy = date.today()
        antiguedad_meses = (hoy.year - fn.year) * 12 + (hoy.month - fn.month) - ((hoy.day) < (fn.day))
        if es_pasivo or antiguedad_meses > 6:
            mult_ant = 1
        elif antiguedad_meses <= 6:
            mult_ant = mults["antiguedad_menor_6_meses"]
    detalles_riesgo.append({"Factor": "Antigüedad", "Peso Base": peso_ant, "Multiplicador": mult_ant, "Puntaje": peso_ant * mult_ant})

    # BCRA
    peso_bcra = pesos["bcra"]
    mult_bcra = 1
    cuil_clean = re.sub(r"\D", "", cuil)
    resp_bcra = consultar_cuit_api(cuil_clean)
    filas = procesar_respuesta_bcra(resp_bcra)
    sits = [int(f["situacion"]) for f in filas if f.get("situacion") and str(f["situacion"]).isdigit()]
    max_sit = max(sits) if sits else 1

    if max_sit == 2:
        mult_bcra = mults["bcra_sit_2"]
    elif max_sit >= 3:
        mult_bcra = mults["bcra_sit_3_mas"]
    detalles_riesgo.append({"Factor": "Situación BCRA", "Peso Base": peso_bcra, "Multiplicador": mult_bcra, "Puntaje": peso_bcra * mult_bcra})

    db.close()

    # Consolidación final
    df = pd.DataFrame(detalles_riesgo)
    puntaje_total = df["Puntaje"].sum()

    if puntaje_total <= cortes["bajo_max"]:
        riesgo_final = Riesgo.BAJO
    elif puntaje_total <= cortes["medio_max"]:
        riesgo_final = Riesgo.MEDIO
    else:
        riesgo_final = Riesgo.ALTO

    df.loc[len(df)] = {"Factor": f"PUNTAJE TOTAL (Riesgo {riesgo_final.value})", "Peso Base": "", "Multiplicador": "", "Puntaje": puntaje_total}

    return df, riesgo_final
