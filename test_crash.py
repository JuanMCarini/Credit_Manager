import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from src.database.connection import SessionLocal
from src.database.models import Cliente, Credito, Cuota, Cobranza
from sqlalchemy.orm import joinedload

def test():
    db = SessionLocal()
    cuil = "27128114195"
    cliente = db.query(Cliente).options(
        joinedload(Cliente.creditos).joinedload(Credito.cuotas).joinedload(Cuota.cobranzas)
    ).filter(Cliente.cuil == cuil).first()

    if not cliente:
        print("Cliente no encontrado")
        return
        
    result = []
    for c in cliente.creditos:
        for cuota in c.cuotas:
            total_esperado = round(cuota.capital + cuota.interes + cuota.iva, 2)
            total_cobrado = 0.0
            detalle_cobranzas = []
            
            sorted_cobranzas = sorted(cuota.cobranzas, key=lambda cob: cob.fecha)
            for cob in sorted_cobranzas:
                tot = round(cob.capital + cob.interes + cob.iva, 2)
                total_cobrado += tot
                detalle_cobranzas.append({
                    "id": cob.id,
                    "fecha": cob.fecha.strftime("%d/%m/%Y"),
                    "tipo": cob.tipo_cobranza.value if hasattr(cob.tipo_cobranza, "value") else str(cob.tipo_cobranza),
                    "capital": round(cob.capital, 2),
                    "interes": round(cob.interes, 2),
                    "iva": round(cob.iva, 2),
                    "total": tot
                })
                
            total_cobrado = round(total_cobrado, 2)
            saldo = round(total_esperado - total_cobrado, 2)
            
            result.append({
                "credito_id": c.id,
                "nro_cuota": cuota.nro_cuota,
                "vencimiento_raw": cuota.fecha_vencimiento,
                "estado": cuota.estado.value if hasattr(cuota.estado, "value") else cuota.estado,
            })
            
    result.sort(key=lambda x: (x["vencimiento_raw"], x["credito_id"], x["nro_cuota"]))
    print("FINISHED OLD CODE SUCCESSFULLY!")

if __name__ == "__main__":
    try:
        test()
    except Exception as e:
        import traceback
        traceback.print_exc()
