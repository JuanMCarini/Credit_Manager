import json

def update_notebook():
    with open("notebooks/db_sandbox.ipynb", "r", encoding="utf-8") as f:
        nb = json.load(f)

    for cell in nb.get("cells", []):
        if cell["cell_type"] == "code":
            source = "".join(cell.get("source", []))
            if "session.add_all(movimientos)" in source:
                new_source = """from src.database import SessionLocal, Cuenta, Movimiento
from src.database.models.finance.bancos import Concepto
import pandas as pd

movimientos = []
with SessionLocal() as session:
    cuenta = session.get(Cuenta, 1)
    
    # 1. Cargamos el mapa de conceptos desde la base de datos
    conceptos_db = session.query(Concepto).all()
    mapa_conceptos = {c.name: c.id for c in conceptos_db}
    
    id_ingreso_nc = mapa_conceptos.get("Ingreso NO CLASIFICADO")
    id_egreso_nc = mapa_conceptos.get("EGRESO NO CLASIFICADO")
    
    for _, row in df.iterrows():
        # Ajustamos el signo del monto 
        monto = abs(row["Importe"])
        
        transaccion = str(row["Transacción"])
        
        # 2. Intentamos matchear la transacción con un nombre de concepto exacto
        concepto_id = mapa_conceptos.get(transaccion)
        
        # 3. Si no existe (es genérica), lo mandamos a los no clasificados
        if not concepto_id:
            if row["Importe"] < 0:
                concepto_id = id_egreso_nc
            elif row["Importe"] > 0:
                concepto_id = id_ingreso_nc
            else:
                raise ValueError("Monto igual a 0.")

        # 4. Armamos la descripción
        desc = transaccion
        if pd.notna(row["Info Adicional"]):
            desc += f" - {row['Info Adicional']}"
            
        # 5. Instanciamos
        nuevo_movimiento = Movimiento(
            cuenta_id=cuenta.id,
            fecha=row["Fec.Operación"].date(),
            nro_comprobante=str(row["Comprobante"]),
            monto=monto,
            concepto_id=concepto_id,
            descripcion=desc[:255]
        )
        movimientos.append(nuevo_movimiento)
    
    session.add_all(movimientos)
    
    # ⚠️ Descomenta la siguiente línea para guardar en la base de datos
    # session.commit()
    
    print(f"Se prepararon {len(movimientos)} movimientos para la cuenta {cuenta.id}")
"""
                lines = new_source.split('\n')
                cell_source = [line + '\n' for line in lines[:-1]]
                if lines[-1]:
                    cell_source.append(lines[-1])
                cell["source"] = cell_source
                break

    with open("notebooks/db_sandbox.ipynb", "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)

if __name__ == "__main__":
    update_notebook()
