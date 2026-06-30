import pandas as pd
import numpy as np

def _process_rounding_adjustment(df_pending: pd.DataFrame, df_cobr: pd.DataFrame):
    if df_cobr.empty or df_pending.empty:
        return df_cobr

    collected_per_cuota = df_cobr.groupby(level=0)[["capital", "interes", "iva", "total"]].sum()
    expected_per_cuota = df_pending.loc[collected_per_cuota.index, ["capital", "interes", "iva", "total"]]

    diff_total = (expected_per_cuota["total"] - collected_per_cuota["total"]).round(2)
    print("diff_total:", diff_total.to_dict())

    adjust_mask = (diff_total > 0.0) & (diff_total <= 0.05)
    cuotas_to_adjust = diff_total[adjust_mask].index

    print("cuotas_to_adjust:", cuotas_to_adjust)

    if cuotas_to_adjust.empty:
        return df_cobr

    adjustment_rows = []
    for cuota_id in cuotas_to_adjust:
        adj_row = df_pending.loc[cuota_id].copy()
        
        rem_capital = round(expected_per_cuota.loc[cuota_id, "capital"] - collected_per_cuota.loc[cuota_id, "capital"], 2)
        rem_interes = round(expected_per_cuota.loc[cuota_id, "interes"] - collected_per_cuota.loc[cuota_id, "interes"], 2)
        rem_iva = round(expected_per_cuota.loc[cuota_id, "iva"] - collected_per_cuota.loc[cuota_id, "iva"], 2)
        
        adj_row["capital"] = max(0.0, rem_capital)
        adj_row["interes"] = max(0.0, rem_interes)
        adj_row["iva"] = max(0.0, rem_iva)
        adj_row["total"] = round(adj_row["capital"] + adj_row["interes"] + adj_row["iva"], 2)
        adj_row["tipo_cobranza"] = "AJUSTE"
        
        adjustment_rows.append(pd.DataFrame([adj_row.to_dict()], index=[cuota_id]))

    if adjustment_rows:
        attrs_backup = df_cobr.attrs.copy()
        df_adj = pd.concat(adjustment_rows)
        df_cobr = pd.concat([df_cobr, df_adj])
        df_cobr.attrs = attrs_backup

    return df_cobr

# Mock data
df_pending = pd.DataFrame(
    index=[7267],
    data={
        "capital": [45914.17],
        "interes": [324326.96],
        "iva": [68108.66],
        "total": [438349.79]
    }
)

df_cobr = pd.DataFrame(
    index=[7267],
    data={
        "capital": [45914.16],
        "interes": [324326.96],
        "iva": [68108.66],
        "total": [438349.78],
        "tipo_cobranza": ["COMUN"]
    }
)

res = _process_rounding_adjustment(df_pending, df_cobr)
print("Result:")
print(res.to_string())
