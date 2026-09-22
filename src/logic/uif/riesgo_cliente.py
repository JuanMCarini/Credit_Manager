import re
import copy
import pandas as pd

from src.database import SocioComercial
from enum import Enum

from src.database import SessionLocal
from src.database.models import Cliente, Empleador, Nacionalidad
from src.database.models.creditos.uif import FactoRiesgo, MultiplicadoresRiesgo
from src.services.bcra import consultar_cuit_api, procesar_respuesta_bcra

class Riesgo(Enum):
    BAJO = "Bajo"
    MEDIO = "Medio"
    ALTO = "Alto"


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

def _seed_db(db):

    DEFAULT_CONFIG = {
        "pesos": {
            "base": 0.25,
            "tipo_cliente": 0.1,
            "act_eco": 0.15,
            "nacionalidad": 0.05,
            "residencia": 0.05,
            "edad": 0.20,
            "antiguedad": 0.10,
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

    # Crear factor contenedor para los cortes
    cortes_factor = FactoRiesgo(codigo="cortes", detalle="Cortes de Riesgo", peso=0.0)
    db.add(cortes_factor)
    db.commit()
    db.refresh(cortes_factor)
    
    for k, v in DEFAULT_CONFIG["cortes"].items():
        db.add(MultiplicadoresRiesgo(
            codigo=k,
            id_riesgo=cortes_factor.id,
            detalle=f"Corte {k}",
            multiplicador=0.0,
            variable=v
        ))
        
    # Crear pesos y multiplicadores basados en DEFAULT_CONFIG
    mult_map = {
        "tipo_cliente": [("tipo_cliente_pep", None)],
        "act_eco": [("act_eco_pasivo_sin_desc", None), ("act_eco_pasivo_con_desc", None)],
        "nacionalidad": [("gafi_gris", None), ("gafi_negra", None)],
        "edad": [("edad_60_75", 60), ("edad_mayor_75", 75)],
        "antiguedad": [("antiguedad_menor_6_meses", 6)],
        "bcra": [("bcra_sit_2", 2), ("bcra_sit_3_mas", 3)]
    }
    
    for k, v in DEFAULT_CONFIG["pesos"].items():
        factor = FactoRiesgo(codigo=k, detalle=f"Factor {k}", peso=v)
        db.add(factor)
        db.commit()
        db.refresh(factor)
        
        if k in mult_map:
            for mult_key, var_val in mult_map[k]:
                if mult_key in DEFAULT_CONFIG["multiplicadores"]:
                    mult_val = DEFAULT_CONFIG["multiplicadores"][mult_key]
                    db.add(MultiplicadoresRiesgo(
                        codigo=mult_key,
                        id_riesgo=factor.id,
                        detalle=f"Multiplicador {mult_key}",
                        multiplicador=mult_val,
                        variable=var_val
                    ))
    
    db.commit()

def _get_config_from_db(db) -> dict:
    factores = db.query(FactoRiesgo).all()
    
    if not factores:
        _seed_db(db)
        factores = db.query(FactoRiesgo).all()
        
    cfg = {"pesos": {}, "multiplicadores": {}, "cortes": {}, "variables": {}, "detalles": {}}
    
    for factor in factores:
        if factor.codigo == "cortes":
            for mult in factor.multiplicadores:
                cfg["cortes"][mult.codigo] = float(mult.variable) if mult.variable is not None else 0.0
        else:
            cfg["pesos"][factor.codigo] = float(factor.peso)
            cfg["detalles"][factor.codigo] = factor.detalle
            for mult in factor.multiplicadores:
                cfg["multiplicadores"][mult.codigo] = float(mult.multiplicador)
                if mult.variable is not None:
                    cfg["variables"][mult.codigo] = float(mult.variable)
                
    return cfg

def _eval_tipo_cliente(datos, mults, vars):
    return mults.get("tipo_cliente_pep", 1) if (datos.get("sujeto_obligado") or datos.get("pep")) else 1

def _eval_act_eco(datos, mults, vars):
    if datos.get("es_pasivo") and (not datos.get("codigo_descuento")):
        return mults.get("act_eco_pasivo_sin_desc", 1)
    elif datos.get("es_pasivo"):
        return mults.get("act_eco_pasivo_con_desc", 1)
    return 1

def _eval_nacionalidad(datos, mults, vars):
    lista_gafi = datos.get("lista_gafi")
    if lista_gafi == "Lista Gris":
        return mults.get("gafi_gris", 1)
    elif lista_gafi == "Lista Negra":
        return mults.get("gafi_negra", 1)
    return 1

def _eval_edad(datos, mults, vars):
    fn = datos.get("fecha_nacimiento")
    if not fn: return 1
    
    from datetime import date
    hoy = date.today()
    edad_anios = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
    
    if edad_anios >= vars.get("edad_mayor_75", 75):
        return mults.get("edad_mayor_75", 1)
    elif edad_anios >= vars.get("edad_60_75", 60):
        return mults.get("edad_60_75", 1)
    return 1

def _eval_antiguedad(datos, mults, vars):
    fn = datos.get("fecha_ingreso")
    if not fn: return 1
    
    if datos.get("es_pasivo"): return 1
    
    from datetime import date
    hoy = date.today()
    antiguedad_meses = (hoy.year - fn.year) * 12 + (hoy.month - fn.month) - ((hoy.day) < (fn.day))
    
    if antiguedad_meses <= vars.get("antiguedad_menor_6_meses", 6):
        return mults.get("antiguedad_menor_6_meses", 1)
    return 1

def _eval_bcra(datos, mults, vars):
    cuil = datos.get("_cuil", "")
    cuil_clean = re.sub(r"\D", "", cuil)
    resp_bcra = consultar_cuit_api(cuil_clean)
    filas = procesar_respuesta_bcra(resp_bcra)
    sits = [int(f["situacion"]) for f in filas if f.get("situacion") and str(f["situacion"]).isdigit()]
    max_sit = max(sits) if sits else 1
    
    if max_sit >= vars.get("bcra_sit_3_mas", 3):
        return mults.get("bcra_sit_3_mas", 1)
    elif max_sit >= vars.get("bcra_sit_2", 2):
        return mults.get("bcra_sit_2", 1)
    return 1

EVALUADORES = {
    "tipo_cliente": _eval_tipo_cliente,
    "act_eco": _eval_act_eco,
    "nacionalidad": _eval_nacionalidad,
    "edad": _eval_edad,
    "antiguedad": _eval_antiguedad,
    "bcra": _eval_bcra,
}

def calculo(cuil: str, config_personalizada: dict = None) -> tuple[pd.DataFrame, Riesgo]:
    db = SessionLocal()
    
    base_config = _get_config_from_db(db)
    cfg = _merge_configs(base_config, config_personalizada)
    
    pesos = cfg["pesos"]
    mults = cfg["multiplicadores"]
    cortes = cfg["cortes"]

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
        datos["_cuil"] = cuil
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

    # Evaluacion dinámica
    for factor_code, peso in pesos.items():
        eval_func = EVALUADORES.get(factor_code)
        
        # Si existe evaluador, lo ejecutamos, sino multiplicador es 1
        mult = eval_func(datos, mults, cfg["variables"]) if eval_func else 1
        
        # Obtenemos nombre bonito si existe, sino caemos en el codigo formatteado
        factor_nombre = cfg["detalles"].get(factor_code, factor_code.replace("_", " ").title())
        
        detalles_riesgo.append({
            "Factor": factor_nombre,
            "Peso Base": peso,
            "Multiplicador": mult,
            "Puntaje": peso * mult
        })

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

    df.loc[len(df)] = {"Factor": f"PUNTAJE TOTAL (Riesgo {riesgo_final.value})", "Peso Base": df["Peso Base"].sum(), "Multiplicador": "", "Puntaje": puntaje_total}

    return df, riesgo_final
