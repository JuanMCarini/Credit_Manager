import os
import traceback
from datetime import datetime
import sys

# Ensure src is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.reports.finance.esp import reporte

try:
    df = reporte(fecha_corte=datetime.today(), n_periodos=2, salto_meses=1, tna_descuento=0.0)
    print(df.head())
    print("Success")
except Exception as e:
    traceback.print_exc()
