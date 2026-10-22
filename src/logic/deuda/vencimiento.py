import pandas as pd
from datetime import date
from pathlib import Path
from typing import Dict, Any

from src.database import SessionLocal
from src.database.models.deuda.series import Serie
from src.database.models.deuda.inversores import CuentaComitente
from src.database.models.deuda.movimientos import TipoMovimiento

from .utils import read_file
from src.logic.deuda.commit import new_serie, new_cta_cte, new_inversor, new_titular, new_movimiento
from src.logic.deuda.series import resumen


def _normalizar_series_viejas(series_viejas: str | list[str]) -> list[str]:
    if isinstance(series_viejas, str):
        import json
        s_clean = series_viejas.strip()
        if s_clean.startswith("[") and s_clean.endswith("]"):
            try:
                parsed = json.loads(s_clean)
                if isinstance(parsed, list):
                    return [str(s).strip() for s in parsed if str(s).strip()]
            except json.JSONDecodeError:
                pass
        if "," in s_clean:
            return [s.strip() for s in s_clean.split(",") if s.strip()]
        return [s_clean]
    return [str(s).strip() for s in series_viejas if str(s).strip()]


def validar_y_preparar_renovacion(
    serie_vieja: str | list[str],
    serie_nueva: str,
    fecha: str | date,
    tna: float,
    plazo: int,
    path: Path | None,
    db
):
    if isinstance(fecha, str):
        fecha = pd.to_datetime(fecha).date()

    series_nombres = _normalizar_series_viejas(serie_vieja)
    if not series_nombres:
        raise ValueError("Debe especificar al menos una serie de origen para renovar.")

    old_series = db.query(Serie).filter(Serie.name.in_(series_nombres)).all()
    encontradas = {s.name for s in old_series}
    faltantes = set(series_nombres) - encontradas
    if faltantes:
        raise ValueError(f"No se encontraron las siguientes series: {', '.join(faltantes)}.")

    # Validar que todas las series a fusionar tengan la misma fecha de vencimiento
    vencimientos = {s.fecha_vencimiento for s in old_series}
    if len(vencimientos) > 1:
        detalles = [f"{s.name} (Vto: {s.fecha_vencimiento})" for s in old_series]
        raise ValueError(f"Las series a fusionar deben tener la misma fecha de vencimiento. Fechas detectadas: {', '.join(detalles)}.")

    # Validar que serie_nueva no exista ya
    serie_existente = db.query(Serie).filter(Serie.name == serie_nueva).first()
    if serie_existente:
        raise ValueError(f"Ya existe una serie registrada con el nombre '{serie_nueva}'.")

    df = read_file(path)

    # Validar que contenga columnas necesarias para renovación (10 columnas)
    for col_req in ["Capital", "Interés", "Total", "Rescate", "Suscripción"]:
        if col_req not in df.columns:
            raise ValueError(f"El archivo debe contener la columna '{col_req}' (se esperan 10 columnas para renovación).")

    # Mapeo de cuentas comitentes para normalizar id interno e id_externo
    all_ctas = db.query(CuentaComitente).all()
    cta_map = {}
    for c in all_ctas:
        canonical = str(c.id_externo).strip() if c.id_externo else str(c.id).strip()
        cta_map[str(c.id).strip()] = canonical
        if c.id_externo:
            cta_map[str(c.id_externo).strip()] = canonical

    # Extraer resúmenes de todas las series viejas
    df_viejas_list = []
    series_con_saldos = {}
    for s in old_series:
        df_s = resumen(s.name)
        if df_s.empty:
            raise ValueError(f"La serie '{s.name}' no posee movimientos o cuentas registradas para renovar.")
        df_viejas_list.append(df_s)

        s_saldos = {}
        for _, r in df_s.iterrows():
            raw_cta = str(r["Cta. Cte."]).strip()
            cta_id = cta_map.get(raw_cta, raw_cta)
            if cta_id not in s_saldos:
                s_saldos[cta_id] = {"capital": 0.0, "interes": 0.0, "total": 0.0}
            s_saldos[cta_id]["capital"] += float(r["Capital"])
            s_saldos[cta_id]["interes"] += float(r["Interés"])
            s_saldos[cta_id]["total"] += float(r["Total"])
        series_con_saldos[s.id] = s_saldos

    df_vieja_total = pd.concat(df_viejas_list, ignore_index=True)

    # Validar totales globales
    errores = df_vieja_total[["Capital", "Interés"]].sum() - df[["Capital", "Interés"]].sum()
    if errores.abs().max() > 0.05:
        diferencias = []
        for col, diff in errores.items():
            if abs(diff) > 0.05:
                val_base = df_vieja_total[col].sum()
                val_archivo = df[col].sum()
                diferencias.append(f"{col}: Base={val_base:.2f} vs Archivo={val_archivo:.2f} (Dif={diff:.2f})")
        raise ValueError(f"Error en el cálculo de totales del archivo con los de la base. Detalles: {', '.join(diferencias)}")

    # Validar Total por fila:
    # La columna 'Total' puede venir como:
    # 1) Total neto a renovar: Capital + Interés - Rescate + Suscripción
    # 2) Total bruto vencido: Capital + Interés (frecuente en liquidaciones cuando se informa el total de la posición o rescates totales)
    # Si viene como bruto vencido, normalizamos 'Total' en df al neto resultante para la nueva serie.
    bad_tot_rows = []
    for idx, r in df.iterrows():
        calc_neto = round(float(r["Capital"]) + float(r["Interés"]) - float(r.get("Rescate", 0.0)) + float(r.get("Suscripción", 0.0)), 2)
        calc_bruto = round(float(r["Capital"]) + float(r["Interés"]), 2)
        tot_archivo = round(float(r["Total"]), 2)

        if abs(tot_archivo - calc_neto) <= 0.05:
            pass
        elif abs(tot_archivo - calc_bruto) <= 0.05:
            df.at[idx, "Total"] = 0.0 if abs(calc_neto) < 0.005 else calc_neto
        else:
            bad_tot_rows.append((r["ID Cta. Cte."], calc_neto, tot_archivo))

    if bad_tot_rows:
        detalles = [
            f"Cta {cta}: esperado {exp:.2f} vs archivo {arch:.2f}"
            for cta, exp, arch in bad_tot_rows
        ]
        raise ValueError(f"Error en el cálculo de Total en el archivo. Dif. Total: {'; '.join(detalles[:5])}.")

    # Validar correspondencia de Capital e Interés por cuenta individual normalizada (agrupando por si la cuenta tiene varias filas)
    df_vieja_total["Cta_Key"] = df_vieja_total["Cta. Cte."].astype(str).str.strip().map(lambda x: cta_map.get(x, x))
    grouped_base = df_vieja_total.groupby("Cta_Key")[["Capital", "Interés"]].sum()

    df_copy_keys = df["ID Cta. Cte."].astype(str).str.strip().map(lambda x: cta_map.get(x, x))
    grouped_file = df.groupby(df_copy_keys)[["Capital", "Interés"]].sum()

    expected_int_by_cta = {str(k).strip(): float(v) for k, v in grouped_base["Interés"].items()}
    expected_cap_by_cta = {str(k).strip(): float(v) for k, v in grouped_base["Capital"].items()}

    int_diffs = []
    cap_diffs = []
    for cta_id, r in grouped_file.iterrows():
        exp_int = expected_int_by_cta.get(cta_id, 0.0)
        exp_cap = expected_cap_by_cta.get(cta_id, 0.0)
        file_int = float(r["Interés"])
        file_cap = float(r["Capital"])
        if abs(file_int - exp_int) > 0.05:
            int_diffs.append(f"Cta {cta_id}: esperado {exp_int:.2f} vs archivo {file_int:.2f}")
        if abs(file_cap - exp_cap) > 0.05:
            cap_diffs.append(f"Cta {cta_id}: esperado {exp_cap:.2f} vs archivo {file_cap:.2f}")

    if int_diffs or cap_diffs:
        msgs = []
        if cap_diffs:
            msgs.append(f"Dif. Capital: {'; '.join(cap_diffs[:5])}")
        if int_diffs:
            msgs.append(f"Dif. Interés: {'; '.join(int_diffs[:5])}")
        raise ValueError(f"Discrepancia por cuenta entre el archivo y la base de datos. {'. '.join(msgs)}")

    return old_series, df, fecha, series_con_saldos, cta_map


def preview_renovacion(
    serie_vieja: str | list[str],
    serie_nueva: str,
    fecha: str | date,
    tna: float,
    plazo: int,
    path: Path | None = None
) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        old_series, df, fecha_dt, series_con_saldos, cta_map = validar_y_preparar_renovacion(
            serie_vieja, serie_nueva, fecha, tna, plazo, path, db
        )

        filas = []
        for _, row in df.iterrows():
            id_ext = str(row["ID Cta. Cte."]).strip()
            capital = round(float(row["Capital"]), 2)
            capital = 0.0 if abs(capital) < 0.005 else capital
            interes = round(float(row["Interés"]), 2)
            interes = 0.0 if abs(interes) < 0.005 else interes
            rescate = round(float(row.get("Rescate", 0.0)), 2)
            rescate = 0.0 if abs(rescate) < 0.005 else rescate
            suscripcion = round(float(row.get("Suscripción", 0.0)), 2)
            suscripcion = 0.0 if abs(suscripcion) < 0.005 else suscripcion
            total = round(float(row["Total"]), 2)
            total = 0.0 if abs(total) < 0.005 else total
            renovacion = round(capital + interes - rescate, 2)
            renovacion = 0.0 if abs(renovacion) < 0.005 else renovacion

            has_rescate = rescate >= 0.01
            has_renovacion = renovacion >= 0.01
            has_suscripcion = suscripcion >= 0.01

            if has_rescate and has_renovacion and has_suscripcion:
                accion = "Renovación con Rescate y Aporte"
                tipo_badge = "warning"
            elif has_rescate and has_renovacion:
                accion = "Renovación con Rescate Parcial"
                tipo_badge = "warning"
            elif has_rescate and not has_renovacion:
                accion = "Rescate Total"
                tipo_badge = "danger"
            elif has_suscripcion:
                accion = "Renovación con Aporte Extra"
                tipo_badge = "info"
            else:
                accion = "Renovación Total"
                tipo_badge = "success"

            filas.append({
                "id_cuenta": id_ext,
                "razon_social": " Y/O ".join(row["Razón Social"]) if isinstance(row["Razón Social"], list) else str(row["Razón Social"]),
                "cuit": " - ".join(row["CUIT/CUIL"]) if isinstance(row["CUIT/CUIL"], list) else str(row["CUIT/CUIL"]),
                "capital": capital,
                "interes": interes,
                "rescate": rescate,
                "renovacion": renovacion,
                "suscripcion": suscripcion,
                "total": total,
                "observacion": str(row.get("Observación", "")) if pd.notna(row.get("Observación", "")) else "",
                "accion": accion,
                "tipo_badge": tipo_badge
            })

        total_cap_viejo = round(float(df["Capital"].sum()), 2)
        total_int_viejo = round(float(df["Interés"].sum()), 2)
        total_rescate = round(float(df["Rescate"].sum()), 2)
        total_renovado = round(float((df["Capital"] + df["Interés"] - df["Rescate"]).sum()), 2)
        total_suscripciones = round(float(df["Suscripción"].sum()), 2)
        total_nuevo_cap = round(float(df["Total"].sum()), 2)

        cuentas_con_rescate = [f for f in filas if f["rescate"] >= 0.01]
        cuentas_con_suscripcion = [f for f in filas if f["suscripcion"] >= 0.01]

        tiene_comision = any(s.comision for s in old_series)

        # Información individual de cada serie vieja a fusionar
        series_viejas_info = []
        for s in old_series:
            s_saldos = series_con_saldos.get(s.id, {})
            cap_s = sum(c["capital"] for c in s_saldos.values())
            int_s = sum(c["interes"] for c in s_saldos.values())
            series_viejas_info.append({
                "id": s.id,
                "name": s.name,
                "tna": float(s.tna),
                "plazo": int(s.plazo),
                "fecha_suscripcion": str(s.fecha_suscripcion),
                "fecha_vencimiento": str(s.fecha_vencimiento),
                "comision": bool(s.comision),
                "capital": round(float(cap_s), 2),
                "interes": round(float(int_s), 2),
                "total": round(float(cap_s + int_s), 2)
            })

        return {
            "series_viejas": series_viejas_info,
            "serie_vieja": {
                "name": " + ".join(s.name for s in old_series),
                "tna": float(old_series[0].tna) if len(old_series) == 1 else None,
                "plazo": int(old_series[0].plazo) if len(old_series) == 1 else None,
                "fecha_suscripcion": str(old_series[0].fecha_suscripcion) if len(old_series) == 1 else None,
                "fecha_vencimiento": str(old_series[0].fecha_vencimiento),
                "comision": tiene_comision
            },
            "serie_nueva": {
                "name": serie_nueva,
                "fecha_suscripcion": str(fecha_dt),
                "tna": float(tna),
                "plazo": int(plazo),
                "comision": tiene_comision
            },
            "resumen": {
                "total_capital_anterior": 0.0 if abs(total_cap_viejo) < 0.005 else total_cap_viejo,
                "total_interes_anterior": 0.0 if abs(total_int_viejo) < 0.005 else total_int_viejo,
                "total_posicion_vencida": round((0.0 if abs(total_cap_viejo) < 0.005 else total_cap_viejo) + (0.0 if abs(total_int_viejo) < 0.005 else total_int_viejo), 2),
                "total_rescates": 0.0 if abs(total_rescate) < 0.005 else total_rescate,
                "total_renovado": 0.0 if abs(total_renovado) < 0.005 else total_renovado,
                "total_nuevas_suscripciones": 0.0 if abs(total_suscripciones) < 0.005 else total_suscripciones,
                "total_nuevo_capital": 0.0 if abs(total_nuevo_cap) < 0.005 else total_nuevo_cap,
                "cantidad_cuentas": len(filas),
                "cuentas_con_rescate": len(cuentas_con_rescate),
                "cuentas_con_suscripcion": len(cuentas_con_suscripcion),
                "cuentas_solo_renovacion": len(filas) - len(cuentas_con_rescate) - len(cuentas_con_suscripcion)
            },
            "filas": filas
        }
    finally:
        db.close()


def renovación(
    serie_vieja: str | list[str],
    serie_nueva: str,
    fecha: str | date,
    tna: float,
    plazo: int,
    path: Path | None = None
):
    db = SessionLocal()
    try:
        old_series, df, fecha_dt, series_con_saldos, cta_map = validar_y_preparar_renovacion(
            serie_vieja, serie_nueva, fecha, tna, plazo, path, db
        )

        df_ei = df.loc[(df["Rescate"] >= 0.01) | (df["Suscripción"] >= 0.01)].copy()

        tiene_comision = any(s.comision for s in old_series)
        nueva_serie_obj = new_serie(db, serie_nueva, fecha_dt, tna, plazo, comision=tiene_comision)

        # Copiar comisiones asociadas únicas de todas las series viejas
        if tiene_comision:
            from src.database.models.deuda.series import ComisionesSerie
            comisiones_ids_agregadas = set()
            for s in old_series:
                for cs in s.comisiones_asociadas:
                    if cs.id_comision not in comisiones_ids_agregadas:
                        db.add(ComisionesSerie(id_serie=nueva_serie_obj.id, id_comision=cs.id_comision))
                        comisiones_ids_agregadas.add(cs.id_comision)

        for _, row in df.iterrows():
            id_externo_cta = str(row["ID Cta. Cte."]).strip()

            # Buscar o crear Cuenta Comitente
            cuenta = new_cta_cte(db, id_externo_cta, row)

            inversores_de_la_fila = []
            cuits = row["CUIT/CUIL"]
            razones_sociales = row["Razón Social"]
            direccion = row["Dirección"] if pd.notna(row["Dirección"]) else None

            for i in range(len(cuits)):
                cuit = cuits[i]
                rs = razones_sociales[i] if i < len(razones_sociales) else "Desconocido"
                inversor = new_inversor(db, cuit, rs, direccion)
                inversores_de_la_fila.append(inversor)
                new_titular(db, cuenta.id, inversor.id)

            total_rescate = round(float(row.get("Rescate", 0.0)), 2)
            total_rescate = 0.0 if abs(total_rescate) < 0.005 else total_rescate

            total_renovacion = round(float(row["Capital"]) + float(row["Interés"]) - total_rescate, 2)
            total_renovacion = 0.0 if abs(total_renovacion) < 0.005 else total_renovacion

            # Distribuir rescate y renovación a prorrata entre las series viejas donde la cuenta tenía saldo
            norm_cta = cta_map.get(id_externo_cta, id_externo_cta)
            saldos_por_serie = {}
            for s in old_series:
                s_dict = series_con_saldos.get(s.id, {})
                saldos_por_serie[s.id] = s_dict.get(norm_cta, {}).get("total", 0.0)

            total_vencido_cuenta = sum(saldos_por_serie.values())

            if total_vencido_cuenta > 0.005:
                # Si hay múltiples series, distribuimos a prorrata
                for s in old_series:
                    saldo_serie = saldos_por_serie[s.id]
                    if saldo_serie < 0.005:
                        continue
                    ratio = saldo_serie / total_vencido_cuenta
                    rescate_serie = round(total_rescate * ratio, 2)
                    renov_serie = round(total_renovacion * ratio, 2)

                    if rescate_serie >= 0.01:
                        new_movimiento(db, cuenta.id, s.id, fecha_dt, rescate_serie, TipoMovimiento.RESCATE, inversores_de_la_fila)
                    if renov_serie >= 0.01:
                        new_movimiento(db, cuenta.id, s.id, fecha_dt, renov_serie, TipoMovimiento.RENOVACION_RESCATE, inversores_de_la_fila)

            # En la nueva serie se registra la suscripción por renovación y el aporte extra
            if total_renovacion >= 0.01:
                new_movimiento(db, cuenta.id, nueva_serie_obj.id, fecha_dt, total_renovacion, TipoMovimiento.RENOVACION_SUSCRIPCION, inversores_de_la_fila)

            suscripcion = round(float(row.get("Suscripción", 0.0)), 2)
            if abs(suscripcion) < 0.005:
                suscripcion = 0.0
            if suscripcion >= 0.01:
                new_movimiento(db, cuenta.id, nueva_serie_obj.id, fecha_dt, suscripcion, TipoMovimiento.SUSCRIPCION, inversores_de_la_fila)

        # Guardar todos los cambios juntos
        db.commit()

        if not df_ei.empty:
            df_ei.sort_values(by=["Rescate", "Suscripción", "ID Cta. Cte."], inplace=True)
        return df_ei

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
