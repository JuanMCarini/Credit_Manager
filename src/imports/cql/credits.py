from IPython.display import display
from src.database import engine, SessionLocal, Credito
from src.database.models import EstadoCredito, TipoCredito
from . import read as read_files
import pandas as pd
import numpy_financial as npf

# 1. Copiar y cruzar datos
df_creditos = read_files.df_creditos.copy()
df_inventario = read_files.df_inventario.copy()
df_creditos = df_creditos.merge(
    df_inventario[["Clave Externa", "CUIL"]], 
    left_index=True, 
    right_index=True, 
    how="left"
)
df_socios = pd.read_sql("socios_comerciales", engine, index_col="id")

# Función para calcular TNA dinámicamente usando numpy_financial
def calcular_tna(plazo, capital, cuota):
    try:
        p = int(plazo)
        c = float(capital)
        q = float(cuota)
        if p > 0 and c > 0 and q > 0:
            tasa_mensual = npf.rate(nper=p, pmt=-q, pv=c, fv=0)
            if pd.notna(tasa_mensual) and tasa_mensual > 0:
                return float(tasa_mensual * 365 / 30)
    except Exception:
        pass
    return 0.0

db = SessionLocal()

# 4. Obtener créditos existentes para evitar duplicados en reloads
existing_credits = {
    (c.id_externo, c.socio_originador_id)
    for c in db.query(Credito.id_externo, Credito.socio_originador_id).all()
}

new_credits = []
for i, row in df_creditos.iterrows():
    # A. Buscar el ID del Socio Originador de forma segura (como entero)
    linea = str(row["Línea"]).strip() if pd.notna(row["Línea"]) else None
    socio_id = None
    if linea == "PENALTY":
        socio_id = None
        tipo_credito = TipoCredito.PENALTY
    elif linea:
        matching_socios = df_socios[df_socios["razon_social"].apply(
            lambda rs: str(rs).upper() in linea.upper() if pd.notna(rs) else False
        )]
        tipo_credito = TipoCredito.FRANCES
        if not matching_socios.empty:
            socio_id = int(matching_socios.index[0]) # Obtenemos el índice numérico
        else:
            raise ValueError(f'⚠️ {linea} not in "soscios_comerciales.')
            
    # B. CONTROL DE CLAVE ÚNICA: Omitir si la combinación ya existe en DB o en el lote actual
    ext_id = str(row["Clave Externa"]).strip() if pd.notna(row["Clave Externa"]) else None
    credito_key = (ext_id, socio_id)
    if credito_key in existing_credits:
        continue
    # B. Limpiar el CUIL
    cuil_clean = "".join(filter(str.isdigit, str(row["CUIL"]))) if pd.notna(row["CUIL"]) else None
    
    # C. Limpiar fechas e importes
    f_emision_ts = pd.to_datetime(row["Emisión"], errors='coerce') if pd.notna(row["Emisión"]) else None
    f_emision = f_emision_ts.date() if pd.notna(f_emision_ts) else None
    
    capital = float(row["Capital"]) if pd.notna(row["Capital"]) else 0.0
    plazo = int(row["Plazo"]) if pd.notna(row["Plazo"]) else 0
    importe_cuota = float(row["Imp. Cuota"]) if pd.notna(row["Imp. Cuota"]) else 0.0
    
    # D. Calcular TNA
    tna_calculada = calcular_tna(plazo, capital, importe_cuota)
    
    # E. Determinar Estado
    estado_raw = str(row["Estado"]).strip().upper() if pd.notna(row["Estado"]) else ""
    estado_enum = (
        EstadoCredito.ACTIVO if "ACTIVO" in estado_raw
        else EstadoCredito.MOROSO if "MOROSO" in estado_raw or "MORA" in estado_raw
        else EstadoCredito.CANCELADO if "CANCELADO" in estado_raw or "CANCEL" in estado_raw
        else EstadoCredito.APROBADO
    )

    new_credit = Credito(
        id_externo=ext_id,
        cliente_cuil=cuil_clean,
        socio_originador_id=socio_id,       # ID como entero simple o None
        capital=capital,                    # Obligatorio (Float)
        plazo=plazo,                        # Obligatorio (Int)
        tna_c_iva=tna_calculada,            # Obligatorio (Float)
        fecha_emision=f_emision,            # Obligatorio (Date)
        estado=estado_enum,
        tipo_credito=tipo_credito
    )
    new_credits.append(new_credit)
    existing_credits.add(credito_key)
    
db.add_all(new_credits)
db.commit()
db.close()