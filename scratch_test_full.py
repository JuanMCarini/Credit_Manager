import pandas as pd
import numpy as np

# Simulate _get_pending_installments
df = pd.DataFrame(
    index=[7267],
    data={
        "capital": [45914.17],
        "interes": [324326.96],
        "iva": [68108.66],
        "total": [438349.79],
        "fecha_vencimiento": [pd.Timestamp("2026-06-05")]
    }
)

amount = 438349.78
tasa_iva = 0.21

df["total_acum"] = df["total"].cumsum().round(2)
df_cobr = df[df["total_acum"] <= amount].copy()

cobr = df_cobr["total"].sum()
unuse_amount = round(amount - cobr, 2)

if unuse_amount > 0:
    pending_rows = df[df["total_acum"] > amount]

    if not pending_rows.empty:
        partial_df = pending_rows.iloc[[0]].copy()
        row = partial_df.index.values[0]
        partial_df.loc[row, "total"] = unuse_amount

        if unuse_amount < partial_df.loc[row, "interes"]:
            partial_df.loc[row, "interes"] = round(
                unuse_amount / (1 + tasa_iva), 2
            )
            partial_df.loc[row, "iva"] = round(
                unuse_amount - partial_df.loc[row, "interes"], 2
            )
            partial_df.loc[row, "capital"] = 0.0
        else:
            partial_df.loc[row, "capital"] = unuse_amount - (
                partial_df.loc[row, ["interes", "iva"]].sum()
            )

        df_cobr = pd.concat([df_cobr, partial_df], axis=0)

if "total_acum" in df_cobr.columns:
    df_cobr.drop(columns=["total_acum"], inplace=True)

df_cobr["tipo_cobranza"] = np.where(
    df_cobr["fecha_vencimiento"] <= pd.Timestamp("2026-06-30"),
    "COMUN",
    "ANTICIPO",
)

def _process_rounding_adjustment(df_pending: pd.DataFrame, df_cobr: pd.DataFrame):
    if df_cobr.empty or df_pending.empty:
        return df_cobr

    collected_per_cuota = df_cobr.groupby(level=0)[["capital", "interes", "iva", "total"]].sum()
    expected_per_cuota = df_pending.loc[collected_per_cuota.index, ["capital", "interes", "iva", "total"]]

    diff_total = (expected_per_cuota["total"] - collected_per_cuota["total"]).round(2)

    adjust_mask = (diff_total > 0.0) & (diff_total <= 0.05)
    cuotas_to_adjust = diff_total[adjust_mask].index

    print("Diff total:", diff_total)

    if cuotas_to_adjust.empty:
        print("No cuotas to adjust")
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

res = _process_rounding_adjustment(df, df_cobr)
print(res)
