import pandas as pd

from src.logic.deuda.series import resumen_general

def simulacion_comisiones(tna: float, plazo: int, fecha_lim: str | None | pd.Period = pd.Period.now("D"), iva: float = 0.21):

    df_sim = resumen_general(True)

    if fecha_lim is None:
        fecha_lim = pd.Period(fecha_lim, freq="D")
    s_vencida = []
    while not df_sim.loc[(~df_sim.index.isin(s_vencida)) & (df_sim["Fecha Vencimiento"] <= fecha_lim)].empty:
        for s, row  in df_sim.loc[~df_sim.index.isin(s_vencida) & (df_sim["Fecha Vencimiento"] <= fecha_lim)].iterrows():
            new_serie = max(df_sim.index.astype(int)) + 1
            df_sim.loc[new_serie] = {
                "Fecha Suscripción": row["Fecha Vencimiento"],
                "TNA": tna,
                "Plazo": plazo,
                "% Comisión": row["% Comisión"],
                "Fecha Vencimiento": row["Fecha Vencimiento"] + plazo,
                "Capital": row["Total"],
                "Interés": row["Total"] * tna/365 * plazo,
                "Total": row["Total"] * (1 + tna/365 * plazo),
                "Comisión": row["Total"] * row["% Comisión"]/365 * plazo
            }
            s_vencida.append(s)

    df_com = df_sim.reset_index().copy()
    df_com["Mes Suscripción"] = df_com["Fecha Suscripción"].dt.to_timestamp()
    df_com["Mes Suscripción"] = df_com["Mes Suscripción"].dt.to_period("M")

    df_com = df_com.groupby("Mes Suscripción")[["Capital", "Interés", "Total", "Comisión"]].sum()
    
    if not df_com.empty:
        mes_inicio = df_com.index.min()
        # Transformamos la fecha límite diaria (freq="D") a su versión mensual (freq="M")
        mes_fin = pd.Period(fecha_lim, freq="M")
        
        # Generamos el calendario de meses completo
        rango_completo = pd.period_range(start=mes_inicio, end=mes_fin, freq="M")
        
        # Reindexamos la tabla usando este calendario, rellenando con $0 los meses sin datos
        df_com = df_com.reindex(rango_completo, fill_value=0)
        
        # (Opcional) Podemos nombrar el índice para que quede prolijo
        df_com.index.name = "Mes Suscripción"

    df_com["Comisión c/IVA"] = df_com["Comisión"] * (1 + iva)

    return df_com