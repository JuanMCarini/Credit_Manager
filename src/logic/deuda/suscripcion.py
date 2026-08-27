import pandas as pd

from datetime import date
from pathlib import Path

from src.utils import select_file
from src.database import SessionLocal
from src.database.models.deuda import Inversor, CuentaComitente, TitularidadCuentaComitente, Serie, MovimientoDeuda
from src.database.models.deuda.movimientos import TipoMovimiento, TitularidadMovimientoDeuda
    
from src.services.arca_consulta import validar_datos_arca
    
def nueva_serie(nombre: str, fecha: str | date, tna: float, plazo: int, path: Path | None = None):
    
    if path == None:
        path = select_file()

    if isinstance(fecha, str):
        fecha = pd.to_datetime(fecha).date()
    
    if path.suffix == ".xlsx":
        df = pd.read_excel(path)
    elif path.suffix == ".csv":
        df = pd.read_csv(path, sep=";")
    else:
        raise ValueError("El archivo debe ser Excel o CSV")

    df.columns = ["ID Cta. Cte.", "Razón Social", "CUIT/CUIL", "Dirección", "Capital", "Interés", "Total"]
    
    # Aseguramos que las columnas monetarias sean numéricas (limpiando formato string de CSV)
    for col in ["Capital", "Interés", "Total"]:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace(r"[\$\s\.]", "", regex=True).str.replace(",", ".").astype(float)

    # Limpiamos filas completamente vacías al final del archivo
    df = df.dropna(subset=["ID Cta. Cte.", "CUIT/CUIL", "Capital"])
    df["Conjunta"] = False
    df = df.reset_index(drop=True)
    df.index.name = "ID Movimiento"

    # Calculamos el capital total por cuenta ANTES de explotar titulares múltiples
    df_ctas_monto = df.groupby(["ID Movimiento", "ID Cta. Cte."])["Capital"].sum().reset_index()
    df_ctas_monto.index.name = "ID Movimiento"

    # Buscamos coincidencias con " Y " o " Y/O "
    filtro = df["Razón Social"].str.contains(r" Y/O | Y ", regex=True, na=False)
    if filtro.any():
        df_multiples = df.loc[filtro].copy()
        df = df.loc[~filtro].copy()
        
        # Detectamos si es conjunta (tiene "Y")
        df_multiples["Conjunta"] = df_multiples["Razón Social"].apply(lambda x: " Y " in str(x).upper())
        
        # Separamos los nombres en una lista
        df_multiples["Razón Social"] = df_multiples["Razón Social"].apply(
            lambda x: str(x).upper().split(" Y ") if " Y " in str(x).upper() else str(x).upper().split(" Y/O ")
        )
        
        df_multiples["CUIT/CUIL"] = df_multiples["CUIT/CUIL"].apply(lambda x: str(x).split(" - "))
        
        # Explotamos las listas para que cada titular tenga su propia fila
        df_multiples = df_multiples.explode(["Razón Social", "CUIT/CUIL"])
        
        # Limpiamos espacios en blanco extra que hayan quedado tras el split
        df_multiples["Razón Social"] = df_multiples["Razón Social"].str.strip()
        df_multiples["CUIT/CUIL"] = df_multiples["CUIT/CUIL"].str.strip()
        
        # Unimos nuevamente al dataframe original
        df = pd.concat([df, df_multiples], ignore_index=True)
    else:
        df["Conjunta"] = False

    # Estandarizamos el CUIT/CUIL a nivel de todo el DataFrame
    df["CUIT/CUIL"] = df["CUIT/CUIL"].astype(str).str.replace("-", "", regex=False).str.strip()
    df["CUIT/CUIL"] = df["CUIT/CUIL"].str.replace(r"\.0$", "", regex=True)

    # Control del cálculo de intereses
    # Calculamos la diferencia (error) sin modificar las columnas originales
    error_interes = df["Interés"] - (df["Capital"] * tna * (plazo / 365))
    error_total = df["Total"] - (df["Capital"] + df["Interés"])
    
    # Comprobamos que en NINGUNA fila el error sea mayor a 1 centavo usando .abs().max()
    if error_interes.abs().max() > 0.01 or error_total.abs().max() > 0.01:
        raise ValueError("Error en el cálculo de totales o intereses. Verifique las fórmulas del archivo.")

    df_invs = df[["CUIT/CUIL", "Razón Social", "Dirección"]].copy()
    df_invs = df_invs.drop_duplicates()
    validar_datos_arca(df_invs)

    # ---------------------------------------------------------
    # Preparación de DataFrames
    # ---------------------------------------------------------
    df_ctas = df[["ID Cta. Cte.", "CUIT/CUIL", "Conjunta"]].copy()
    df_ctas = df_ctas.drop_duplicates()

    # ---------------------------------------------------------
    # TRANSACCIÓN ÚNICA: Upsert a la Base de Datos
    # ---------------------------------------------------------
    with SessionLocal() as db:
        
        # 1. Upsert Inversores
        for _, row in df_invs.iterrows():
            cuit_val = row["CUIT/CUIL"]
            inversor = db.query(Inversor).filter(Inversor.cuit == cuit_val).first()
            direccion = row.get("Dirección")
            
            if inversor:
                if pd.notna(direccion) and str(direccion).strip() != "":
                    inversor.domicilio_legal = str(direccion).strip()
            else:
                nuevo_inversor = Inversor(
                    cuit=cuit_val,
                    razon_social=str(row["Razón Social"]).strip().upper(),
                    domicilio_legal=str(direccion).strip() if pd.notna(direccion) else None
                )
                db.add(nuevo_inversor)
        
        db.flush() # Aseguramos que los Inversores nuevos tengan ID

        # 2. Upsert Cuentas Comitentes y Titularidades
        ctas_grouped = df_ctas.groupby("ID Cta. Cte.")
        for id_cta, group in ctas_grouped:
            id_externo_val = int(id_cta)
            cuits = group["CUIT/CUIL"].tolist()
            es_conjunta = group["Conjunta"].iloc[0]

            # Upsert de la cuenta comitente
            cuenta = db.query(CuentaComitente).filter(CuentaComitente.id_externo == id_externo_val).first()
            if not cuenta:
                cuenta = CuentaComitente(id_externo=id_externo_val, conjunta=bool(es_conjunta))
                db.add(cuenta)
                db.flush() # Flush para obtener cuenta.id

            # Upsert de los titulares
            for idx, cuit_val in enumerate(cuits):
                inversor = db.query(Inversor).filter(Inversor.cuit == cuit_val).first()
                if not inversor:
                    continue # No debería pasar

                titularidad = db.query(TitularidadCuentaComitente).filter(
                    TitularidadCuentaComitente.id_cuenta_comitente == cuenta.id,
                    TitularidadCuentaComitente.id_inversor == inversor.id
                ).first()

                if not titularidad:
                    # Buscar el orden máximo actual para esta cuenta
                    from sqlalchemy import func
                    max_orden = db.query(func.max(TitularidadCuentaComitente.orden)).filter(
                        TitularidadCuentaComitente.id_cuenta_comitente == cuenta.id
                    ).scalar() or 0
                    
                    titularidad = TitularidadCuentaComitente(
                        id_cuenta_comitente=cuenta.id,
                        id_inversor=inversor.id,
                        orden=max_orden + 1
                    )
                    db.add(titularidad)
                    db.flush() # Importante para que el próximo iterador vea el orden actualizado

        db.flush()

        # 3. Upsert Serie
        serie_kwargs = {
            "name": nombre,
            "fecha_suscripcion": fecha,
            "tna": tna,
            "plazo": plazo
        }
        serie = db.query(Serie).filter(Serie.name == nombre).first()
        if not serie:
            serie = Serie(**serie_kwargs)
            db.add(serie)
            db.flush() # Flush para obtener serie.id
        else:
            serie.name = nombre
            serie.fecha_suscripcion = fecha
            serie.tna = tna
            serie.plazo = plazo
            
        db.flush()

        # 4. Insertar Movimientos de Suscripción y Titularidades
        # Primero borramos los movimientos de suscripción existentes para esta serie
        if serie:
            db.query(MovimientoDeuda).filter(
                MovimientoDeuda.id_serie == serie.id,
                MovimientoDeuda.tipo_movimiento == TipoMovimiento.SUSCRIPCION
            ).delete()
            db.flush()

        for _, row in df_ctas_monto.iterrows():
            id_externo_val = int(row["ID Cta. Cte."])
            monto = row["Capital"]
            
            cuenta = db.query(CuentaComitente).filter(CuentaComitente.id_externo == id_externo_val).first()
            if cuenta and serie:
                movimiento = MovimientoDeuda(
                    id_cuenta_comitente=cuenta.id,
                    id_serie=serie.id,
                    fecha=fecha,
                    monto=monto,
                    tipo_movimiento=TipoMovimiento.SUSCRIPCION
                )
                db.add(movimiento)
                db.flush() # Aseguramos que el movimiento tenga ID

                # 5. Llenamos la tabla titularidad_movimiento_deuda en base a la cuenta
                titulares_cuenta = db.query(TitularidadCuentaComitente).filter(
                    TitularidadCuentaComitente.id_cuenta_comitente == cuenta.id
                ).all()

                for tc in titulares_cuenta:
                    tit_mov = db.query(TitularidadMovimientoDeuda).filter(
                        TitularidadMovimientoDeuda.id_movimiento_deuda == movimiento.id,
                        TitularidadMovimientoDeuda.id_inversor == tc.id_inversor
                    ).first()
                    
                    if not tit_mov:
                        tit_mov = TitularidadMovimientoDeuda(
                            id_movimiento_deuda=movimiento.id,
                            id_inversor=tc.id_inversor
                        )
                        db.add(tit_mov)

        # Commiteamos TODOS los cambios en un solo paso
        db.commit()