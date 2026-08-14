import pandas as pd
from datetime import date
from src.database import SessionLocal
from src.database.models import Cartera, OperacionCartera, Cuota, TipoOperacionCartera

db = SessionLocal()

# 1. Extraemos todas las cuotas asociadas a todas las carteras
query = db.query(
    Cartera.nombre.label('cartera'),
    Cartera.estado.label('estado_cartera'),
    Cartera.tna_descuento,
    Cartera.fecha_compra,
    (Cuota.capital + Cuota.interes).label('importe_nominal'),
    Cuota.fecha_vencimiento
).join(
    OperacionCartera, Cartera.id == OperacionCartera.cartera_id
).join(
    Cuota, OperacionCartera.cuota_id == Cuota.id
).filter(Cartera.tipo_operacion == TipoOperacionCartera.VENTA)

df = pd.read_sql(query.statement, db.bind)

# 2. Conversión de fechas y cálculos de días
hoy = pd.to_datetime(date.today())
df['fecha_vencimiento'] = pd.to_datetime(df['fecha_vencimiento'])
df['fecha_compra'] = pd.to_datetime(df['fecha_compra'])

# Días al vencimiento desde HOY (si ya venció, se asumen 0 días de descuento, es decir, VA = Nominal)
df['dias_al_vto'] = (df['fecha_vencimiento'] - df["fecha_compra"]).dt.days
df['dias_al_vto'] = df['dias_al_vto'].clip(lower=0) 

# 3. Ajuste de TNA (si la guardas como 50.0 en vez de 0.50)
df['tna_decimal'] = df['tna_descuento'].astype(float)
if df['tna_decimal'].mean() > 1.5:  # heurística por si están en formato porcentual > 1
    df['tna_decimal'] = df['tna_decimal'] / 100

# 4. Fórmula de Descuento (Valor Actual)
# VA = Nominal / (1 + TNA * (dias/365))
df['valor_actual'] = df['importe_nominal'] / ((1 + (df['tna_decimal']*30/365)) ** (df['dias_al_vto'] / 30))

# 5. Agrupamos por Cartera para ver el resumen total
resumen = df.groupby(['cartera', 'estado_cartera']).agg(
    fecha_compra=('fecha_compra', 'max'),
    tna_descuento=('tna_descuento', 'max'),
    cantidad_cuotas=('importe_nominal', 'count'),
    valor_nominal_total=('importe_nominal', 'sum'),
    valor_actual_total=('valor_actual', 'sum')
).reset_index()

# Calculamos la "Pérdida por Descuento" proyectada hoy
resumen['diferencia_descuento'] = resumen['valor_nominal_total'] - resumen['valor_actual_total']
resumen = resumen.set_index("cartera")