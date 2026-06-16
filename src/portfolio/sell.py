import os
import tempfile
import zipfile
from datetime import date
from typing import Optional, Union

import pandas as pd
from IPython.display import display
from sqlalchemy import func
from sqlalchemy.orm import session

from src.database.connection import SessionLocal
from src.database.models import (
    Cartera,
    Cliente,
    Cobranza,
    Credito,
    Cuota,
    Empleador,
    EstadoCredito,
    EstadoCuota,
    EstadoCuotaCedida,
    OperacionCartera,
    SocioComercial,
    TipoCredito,
    TipoOperacionCartera,
)
from src.logic.status_updater import actualizar_estados
from src.utils.dates import normalize_date


class PortfolioSell:
    """
    Manages the selection and sale of active portfolio installments to third parties.
    """

    def __init__(self, db_session: session | None = None):
        """
        Initializes the portfolio sales manager with an active database session
        and empty state containers for tracking transactional elements.
        """
        self.db = db_session or SessionLocal()
        self._own_session = db_session is None

        # State containers
        self.cartera = None
        self.df_cuotas_venta = None

    def fetch_available_installments_for_sale(
        self,
        mora: bool = True,
        fecha_emision_desde: Optional[Union[str, date]] = None,
        fecha_emision_hasta: Optional[Union[str, date]] = None,
        fecha_vencimiento_desde: Optional[Union[str, date]] = None,
        fecha_vencimiento_hasta: Optional[Union[str, date]] = None,
        socio_originador_id: Optional[Union[int, list, tuple, set]] = None,
        cuotas_completas: bool = False,
        cartera_id: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        =============================================================================
        Method: fetch_available_installments_for_sale
        Description: Queries the database for all active installments that belong
                     to the institution and are eligible for portfolio sale. Filters
                     out already assigned, pending, or fully cancelled records,
                     cross-referencing current credit and installment status.
        =============================================================================
        """
        try:
            # 1. Admit states
            cuotas_admitidas = [EstadoCuota.PENDIENTE]
            creditos_admitidos = [EstadoCredito.ACTIVO, EstadoCredito.APROBADO]

            if mora:
                actualizar_estados()
                cuotas_admitidas.append(EstadoCuota.MOROSA)
                creditos_admitidos.append(EstadoCredito.MOROSO)

            from sqlalchemy import or_

            estado_condition = Cuota.estado_cesion == EstadoCuotaCedida.NO_VENDIDA
            if cartera_id:
                estado_condition = or_(
                    Cuota.estado_cesion == EstadoCuotaCedida.NO_VENDIDA,
                    Cuota.id.in_(
                        self.db.query(OperacionCartera.cuota_id).filter(
                            OperacionCartera.cartera_id == cartera_id
                        )
                    ),
                )

            # 2. Build the query
            query = (
                self.db.query(
                    Cuota.id.label("cuota_id"),
                    Cuota.nro_cuota,
                    Cuota.capital,
                    Cuota.interes,
                    Cuota.iva,
                    (Cuota.capital + Cuota.interes).label("subtotal"),
                    Cuota.fecha_vencimiento,
                    Credito.id.label("credito_id"),
                    Credito.cliente_cuil,
                    Credito.fecha_emision,
                    Credito.socio_originador_id,
                    Cartera.id.label("cartera_origen_id"),
                    Cartera.nombre.label("cartera_origen_nombre"),
                )
                .join(Credito, Cuota.credito_id == Credito.id)
                .outerjoin(Cartera, Credito.cartera_id == Cartera.id)
                .filter(
                    Credito.estado.in_(creditos_admitidos),
                    Cuota.estado.in_(cuotas_admitidas),
                    estado_condition,
                )
            )

            # 3. Apply optional filters
            if fecha_emision_desde:
                query = query.filter(
                    Credito.fecha_emision
                    >= normalize_date(fecha_emision_desde, as_type=date)
                )
            if fecha_emision_hasta:
                query = query.filter(
                    Credito.fecha_emision
                    <= normalize_date(fecha_emision_hasta, as_type=date)
                )

            if fecha_vencimiento_desde:
                query = query.filter(
                    Cuota.fecha_vencimiento
                    >= normalize_date(fecha_vencimiento_desde, as_type=date)
                )
            if fecha_vencimiento_hasta:
                query = query.filter(
                    Cuota.fecha_vencimiento
                    <= normalize_date(fecha_vencimiento_hasta, as_type=date)
                )

            if socio_originador_id is not None:
                if isinstance(socio_originador_id, (list, tuple, set)):
                    query = query.filter(
                        Credito.socio_originador_id.in_(socio_originador_id)
                    )
                else:
                    query = query.filter(
                        Credito.socio_originador_id == socio_originador_id
                    )

            # 4. Execute query into pandas DataFrame
            df = pd.read_sql(query.statement, self.db.get_bind())

            if df.empty:
                self.df_cuotas_venta = df
                return df

            # 5. Filter Cuotas Completas (Sin cobranzas asociadas)
            if cuotas_completas:
                from src.database.models import Cobranza

                # Fetch all cuota_id that have at least one Cobranza
                cuotas_con_cobranza_query = (
                    self.db.query(Cobranza.cuota_id)
                    .filter(Cobranza.cuota_id.isnot(None))
                    .distinct()
                )

                cuotas_invalidas = [row[0] for row in cuotas_con_cobranza_query.all()]

                # Exclude any cuota that has a cobranza
                df = df[~df["cuota_id"].isin(cuotas_invalidas)].copy()

            # 6. Normalize date formats
            if not df.empty and "fecha_vencimiento" in df.columns:
                df["fecha_vencimiento"] = pd.to_datetime(
                    df["fecha_vencimiento"]
                ).dt.date
            if not df.empty and "fecha_emision" in df.columns:
                df["fecha_emision"] = pd.to_datetime(df["fecha_emision"]).dt.date

            self.df_cuotas_venta = df
            return df

        except Exception as e:
            raise RuntimeError(f"Error querying available installments for sale: {e}")

    def fetch_installments_from_cartera(self, cartera_id: int) -> pd.DataFrame:
        """
        Fetches the dataframe formatted exactly like fetch_available_installments_for_sale,
        but constrained strictly to the installments associated with an existing Cartera.
        """
        try:
            query = (
                self.db.query(
                    Cuota.id.label("cuota_id"),
                    Cuota.nro_cuota,
                    Cuota.capital,
                    Cuota.interes,
                    Cuota.iva,
                    (Cuota.capital + Cuota.interes).label("subtotal"),
                    Cuota.fecha_vencimiento,
                    Credito.id.label("credito_id"),
                    Credito.cliente_cuil,
                    Credito.fecha_emision,
                    Credito.socio_originador_id,
                    Cartera.id.label("cartera_origen_id"),
                    Cartera.nombre.label("cartera_origen_nombre"),
                )
                .join(Credito, Cuota.credito_id == Credito.id)
                .outerjoin(Cartera, Credito.cartera_id == Cartera.id)
                .join(OperacionCartera, OperacionCartera.cuota_id == Cuota.id)
                .filter(OperacionCartera.cartera_id == cartera_id)
            )

            df = pd.read_sql(query.statement, self.db.get_bind())

            if not df.empty and "fecha_vencimiento" in df.columns:
                df["fecha_vencimiento"] = pd.to_datetime(
                    df["fecha_vencimiento"]
                ).dt.date
            if not df.empty and "fecha_emision" in df.columns:
                df["fecha_emision"] = pd.to_datetime(df["fecha_emision"]).dt.date

            self.df_cuotas_venta = df
            return df

        except Exception as e:
            raise RuntimeError(
                f"Error querying installments for portfolio {cartera_id}: {e}"
            )

    def update_portfolio_sale(
        self,
        cartera_id: int,
        nombre_cartera: str,
        fecha_venta: Union[str, date],
        tna_descuento: float,
        cuit_comprador: str | None = None,
        razon_social_comprador: str | None = None,
        df_seleccion: pd.DataFrame = None,
        recurso: bool = True,
        iva: bool = False,
    ) -> Cartera:
        """
        Updates an existing PENDIENTE portfolio, replacing its installments and recalculating VA.
        """
        if df_seleccion is None:
            df_seleccion = self.df_cuotas_venta

        if df_seleccion is None or df_seleccion.empty:
            raise ValueError("No installments selected for sale.")

        cartera = self.db.query(Cartera).filter(Cartera.id == cartera_id).first()
        if not cartera:
            raise ValueError("Cartera no encontrada.")

        fecha_venta_date = normalize_date(fecha_venta, date)

        # 1. Partner
        socio = self.db.query(SocioComercial)
        if cuit_comprador is None and razon_social_comprador is None:
            raise ValueError("CUIT and Razon Social must be provided.")
        elif cuit_comprador is None:
            socio = socio.filter(
                SocioComercial.razon_social
                == str(razon_social_comprador).strip().upper()
            ).first()
        else:
            socio = socio.filter(
                SocioComercial.cuit == str(cuit_comprador).strip()
            ).first()

        if not socio:
            socio = SocioComercial(
                cuit=str(cuit_comprador).strip(), razon_social=razon_social_comprador
            )
            self.db.add(socio)
            self.db.flush()

        # 2. Update Cartera properties
        cartera.nombre = nombre_cartera
        cartera.socio_id = socio.id
        cartera.fecha_compra = fecha_venta_date
        cartera.tna_descuento = tna_descuento
        cartera.recurso = recurso
        cartera.iva = iva
        cartera.fecha_generacion = date.today()

        # 3. Handle old installments: revert their state
        old_operaciones = (
            self.db.query(OperacionCartera)
            .filter(OperacionCartera.cartera_id == cartera_id)
            .all()
        )
        old_cuotas_ids = [op.cuota_id for op in old_operaciones]

        # We need to revert the old ones that are NOT in the new selection
        new_cuotas_ids = df_seleccion["cuota_id"].tolist()
        cuotas_to_revert = set(old_cuotas_ids) - set(new_cuotas_ids)

        if cuotas_to_revert:
            self.db.query(Cuota).filter(Cuota.id.in_(cuotas_to_revert)).update(
                {"estado_cesion": EstadoCuotaCedida.NO_VENDIDA},
                synchronize_session=False,
            )

        # Delete old mappings
        self.db.query(OperacionCartera).filter(
            OperacionCartera.cartera_id == cartera_id
        ).delete()
        self.db.flush()

        # 4. Insert new mappings
        try:
            operaciones = [
                OperacionCartera(
                    cuota_id=row.cuota_id,
                    cartera_id=cartera.id,
                    cuota_comercializada=True,
                    fecha_registro=fecha_venta_date,
                )
                for row in df_seleccion.itertuples()
            ]
            self.db.bulk_save_objects(operaciones)

            self.db.query(Cuota).filter(Cuota.id.in_(new_cuotas_ids)).update(
                {"estado_cesion": EstadoCuotaCedida.PENDIENTE},
                synchronize_session=False,
            )

            self.db.commit()
            return cartera
        except Exception as e:
            self.db.rollback()
            raise RuntimeError(f"Error updating the sale in the database: {e}")

    def execute_portfolio_sale(
        self,
        nombre_cartera: str,
        fecha_venta: Union[str, date],
        tna_descuento: float,
        cuit_comprador: str | None = None,
        razon_social_comprador: str | None = None,
        df_seleccion: pd.DataFrame = None,
        recurso: bool = True,
        iva: bool = False,
    ) -> Cartera:
        """
        =============================================================================
        Method: execute_portfolio_sale
        Description: Executes the sale transaction, calculating present value for
                     each installment based on the discount rate (TNA) and committing
                     the changes to the database (ACID transaction).
        =============================================================================
        """
        if df_seleccion is None:
            df_seleccion = self.df_cuotas_venta

        if df_seleccion is None or df_seleccion.empty:
            raise ValueError("No installments selected for sale.")

        fecha_venta_date = normalize_date(fecha_venta, date)

        # 1. Partner (Comprador)
        socio = self.db.query(SocioComercial)
        if cuit_comprador is None and razon_social_comprador is None:
            raise ValueError("CUIT and Razon Social must be provided.")
        elif cuit_comprador is None:
            socio = socio.filter(
                SocioComercial.razon_social
                == str(razon_social_comprador).strip().upper()
            ).first()
        else:
            socio = socio.filter(
                SocioComercial.cuit == str(cuit_comprador).strip()
            ).first()

        if not socio:
            socio = SocioComercial(
                cuit=str(cuit_comprador).strip(), razon_social=razon_social_comprador
            )
            self.db.add(socio)
            self.db.flush()

        # 2. Cartera creation
        cartera = Cartera(
            nombre=nombre_cartera,
            socio_id=socio.id,
            fecha_compra=fecha_venta_date,
            tna_descuento=tna_descuento,
            recurso=recurso,
            iva=iva,
            tipo_operacion=TipoOperacionCartera.VENTA,
        )
        self.db.add(cartera)
        self.db.flush()
        self.cartera = cartera

        # 3. Calculate Present Value (Valor Actual) using financial formula
        fecha_venta_pd = pd.to_datetime(fecha_venta_date)
        fechas_vto = pd.to_datetime(df_seleccion["fecha_vencimiento"], errors="coerce")
        dias_vto = (fechas_vto - fecha_venta_pd).dt.days

        # If an installment is already past due (negative days), treat it as 0 days for discounting
        dias_vto = dias_vto.clip(lower=0)

        capital = pd.to_numeric(df_seleccion["capital"], errors="coerce").fillna(0)
        interes = pd.to_numeric(df_seleccion["interes"], errors="coerce").fillna(0)
        flujo_total = capital + interes

        va_calculado = flujo_total / (
            (1 + (tna_descuento * 30 / 365)) ** (dias_vto / 30)
        )
        va_calculado = va_calculado.round(2)

        df_seleccion = df_seleccion.copy()
        df_seleccion["valor_actual_venta"] = va_calculado

        # 4. Database updates (OperacionCartera and Cuota state)
        cuotas_ids = df_seleccion["cuota_id"].tolist()

        try:
            # Create OperacionCartera mapping records
            operaciones = [
                OperacionCartera(
                    cuota_id=row.cuota_id,
                    cartera_id=cartera.id,
                    cuota_comercializada=True,
                    fecha_registro=fecha_venta_date,
                )
                for row in df_seleccion.itertuples()
            ]
            self.db.bulk_save_objects(operaciones)

            # Update Cuotas in bulk
            self.db.query(Cuota).filter(Cuota.id.in_(cuotas_ids)).update(
                {"estado_cesion": EstadoCuotaCedida.PENDIENTE},
                synchronize_session=False,
            )

            self.db.commit()
            print(
                f"✅ Sale registered successfully. Portfolio ID: {cartera.id}, Installments sold: {len(cuotas_ids)}"
            )
            return cartera

        except Exception as e:
            self.db.rollback()
            raise RuntimeError(f"Error registering the sale in the database: {e}")

    def __del__(self):
        """
        Ensures the underlying SQLAlchemy connection pool drops the session
        cleanly if it was created internally when the object lifecycle terminates.
        """
        if (
            hasattr(self, "_own_session")
            and self._own_session
            and hasattr(self, "db")
            and self.db
        ):
            self.db.close()

    def export_to_csv(self):
        """
        Exports the available installments for sale to a CSV file.
        """

        df = self.df_cuotas_venta.copy()
        fecha_venta_pd = pd.to_datetime(self.cartera.fecha_compra)
        fechas_vto = pd.to_datetime(df["fecha_vencimiento"], errors="coerce")
        dias_vto = (fechas_vto - fecha_venta_pd).dt.days
        dias_vto = dias_vto.clip(lower=0)

        capital = pd.to_numeric(df["capital"].round(2), errors="coerce").fillna(0)
        interes = pd.to_numeric(df["interes"].round(2), errors="coerce").fillna(0)
        flujo_total = capital + interes
        va_calculado = round(
            flujo_total
            / ((1 + (self.cartera.tna_descuento * 30 / 365)) ** (dias_vto / 30)),
            2,
        )
        df["valor_actual"] = va_calculado

        query = (
            self.db.query(Cliente, Credito.id.label("ID Operación"))
            .join(Credito, Credito.cliente_cuil == Cliente.cuil)
            .filter(Credito.id.in_(df["credito_id"]))
        )
        df_clts = pd.read_sql(query.statement, self.db.get_bind())
        query = (
            self.db.query(
                Credito,
                Empleador.razon_social,
                Cliente.cbu,
                func.sum(Cuota.capital).label("Capital_Cuotas"),
                func.sum(Cuota.interes).label("Interés"),
                func.sum(Cuota.iva).label("IVA"),
            )
            .join(Cliente, Credito.cliente_cuil == Cliente.cuil)
            .join(Empleador, Cliente.empleador_id == Empleador.id)
            .join(Cuota, Cuota.credito_id == Credito.id)
            .filter(Credito.id.in_(df["credito_id"]))
            .group_by(Credito.id, Empleador.razon_social, Cliente.cbu)
        )
        df_crts = pd.read_sql(query.statement, self.db.get_bind())
        df_crts.drop(columns=["capital"], inplace=True)
        query = self.db.query(Cuota).filter(Cuota.credito_id.in_(df["credito_id"]))
        df_ctas = pd.read_sql(query.statement, self.db.get_bind(), index_col="id")

        column_mapping = {
            "cuil": "CUIL",
            "documento": "Documento",
            "apellido": "Apellido",
            "nombre": "Nombre",
            "fecha_nacimiento": "Fecha Nacimiento",
            "sexo": "Sexo",
            "calle": "Calle",
            "calle_nro": "Calle Nro",
            "piso": "Piso",
            "depto": "Depto",
            "id_provincia": "ID Provincia",
            "id_codigo_postal": "ID Código Postal",
            "localidad": "Localidad",
            "telefono": "Telefono",
            "telefono_2": "Telefono 2",
            "mail": "Mail",
            "remuneracion": "Remuneración",
        }
        

        df_clts.rename(columns=column_mapping, inplace=True)
        df_clts["Remuneración"] = df_clts["Remuneración"].round(2)
        df_clts["Sexo"] = (
            df_clts["Sexo"]
            .astype(str)
            .replace(
                {
                    "SexoEnum.FEMENINO": "F",
                    "SexoEnum.MASCULINO": "M",
                    "FEMENINO": "F",
                    "MASCULINO": "M",
                }
            )
        )

        df_clts = df_clts[
            [
                "ID Operación",
                "CUIL",
                "Documento",
                "Apellido",
                "Nombre",
                "Calle",
                "Calle Nro",
                "Piso",
                "Depto",
                "ID Provincia",
                "ID Código Postal",
                "Localidad",
                "Fecha Nacimiento",
                "Telefono",
                "Sexo",
                "Remuneración",
                "Telefono 2",
                "Mail",
            ]
        ]

        diccionario_renombre = {
            "id": "ID Operación",
            "socio_originador_id": "ID Entidad",
            "tipo_credito": "ID Tipo Operación",
            "Capital_Cuotas": "Capital",
            "fecha_emision": "Fecha Compra",
            "razon_social": "Ente Pagador",
            "cbu": "Número Cuenta CBU",
        }
        df_crts.rename(columns=diccionario_renombre, inplace=True)
        df_crts["Importe Cuota"] = 0.0
        df_crts["Capital Vendido"] = df_crts["ID Operación"].map(
            df.groupby("credito_id")["capital"].sum()
        )
        df_crts["Interés Vendido"] = df_crts["ID Operación"].map(
            df.groupby("credito_id")["interes"].sum()
        )
        df_crts["IVA Vendido"] = (
            df_crts["ID Operación"].map(df.groupby("credito_id")["iva"].sum())
            if self.cartera.iva
            else 0.0
        )
        df_crts["Tasa Compra"] = self.cartera.tna_descuento * 100
        df_crts["Valor Actual"] = df_crts["ID Operación"].map(
            df.groupby("credito_id")["valor_actual"].sum()
        )
        df_crts["ID Tipo Operación"] = df_crts["ID Tipo Operación"].apply(
            lambda x: x.id if isinstance(x, TipoCredito) else x
        )

        df_crts = df_crts[
            [
                "ID Operación",
                "ID Entidad",
                "ID Tipo Operación",
                "Importe Cuota",
                "Capital",
                "Interés",
                "IVA",
                "Capital Vendido",
                "Interés Vendido",
                "IVA Vendido",
                "Fecha Compra",
                "Tasa Compra",
                "Valor Actual",
                "Ente Pagador",
                "Número Cuenta CBU",
            ]
        ]
        for col in ["Importe Cuota", "Capital", "Interés", "IVA", "Capital Vendido", "Interés Vendido", "IVA Vendido", "Valor Actual"]:
            df_crts[col] = df_crts[col].round(2)

        column_mapping = {
            "credito_id": "ID Operación",
            "nro_cuota": "ID Cuota",
            "fecha_vencimiento": "Fecha Vto.",
            "capital": "Capital",
            "interes": "Interés",
            "iva": "IVA",
        }
        df_ctas.rename(columns=column_mapping, inplace=True)
        df_ctas["IVA"] = df_ctas["IVA"] if self.cartera.iva else 0.0
        df_ctas["Fecha Vto. Pago"] = df_ctas["Fecha Vto."]
        df_ctas["Saldo Pendiente"] = df_ctas[["Capital", "Interés", "IVA"]].round(2).sum(axis=1)

        query = (
            self.db.query(Cobranza)
            .filter(Cobranza.fecha <= self.cartera.fecha_generacion)
            .filter(Cobranza.cuota_id.in_(df_ctas.index))
        )
        df_cobr = pd.read_sql(query.statement, self.db.get_bind(), index_col="id")
        df_cobr["iva"] = df_cobr["iva"] if self.cartera.iva else 0.0
        df_cobr["total"] = df_cobr[["capital", "interes", "iva"]].sum(axis=1)

        df_ctas["Valor Actual"] = df_ctas.index.map(
            df.set_index("cuota_id")["valor_actual"]
        ).fillna(0.0)
        df_ctas = df_ctas[
            [
                "ID Operación",
                "ID Cuota",
                "Fecha Vto.",
                "Fecha Vto. Pago",
                "Capital",
                "Interés",
                "IVA",
                "Saldo Pendiente",
                "Valor Actual",
            ]
        ]
        df_cobr = df_cobr.groupby("cuota_id")[["total"]].sum()
        df_ctas["Saldo Pendiente"] = df_ctas["Saldo Pendiente"].sub(df_cobr["total"], fill_value=0)

        for col in ["Capital", "Interés", "IVA", "Saldo Pendiente", "Valor Actual"]:
            df_ctas[col] = df_ctas[col].round(2)

        temp_dir = tempfile.mkdtemp()
        path_creditos = os.path.join(temp_dir, "CREDITOS.csv")
        path_personas = os.path.join(temp_dir, "PERSONAS.CSV")
        path_cuotas = os.path.join(temp_dir, "CUOTAS.CSV")

        df_crts.to_csv(path_creditos, index=False, header=False, sep=",", float_format="%.2f")
        df_clts.to_csv(path_personas, index=False, header=False, sep=",", float_format="%.2f")
        df_ctas.to_csv(path_cuotas, index=False, header=False, sep=",", float_format="%.2f")

        # return df_clts, df_crts, df_ctas
        return {
            "temp_dir": temp_dir,
            "CREDITOS.csv": path_creditos,
            "PERSONAS.CSV": path_personas,
            "CUOTAS.CSV": path_cuotas,
        }

    def export_to_excel(self):
        """
        Exports the available installments for sale to an Excel file.
        """

        pass

    def export(self):
        """
        Export a ZIP with CSV files and a Excel with all the data.
        """
        csv_files_info = self.export_to_csv()

        temp_dir_zip = tempfile.mkdtemp()
        default_name = f"Cartera Nro. {str(self.cartera.id).zfill(2)} - {self.cartera.socio.razon_social} - {self.cartera.fecha_compra} - {self.cartera.tna_descuento:.2%}.zip"

        zip_path = os.path.join(temp_dir_zip, default_name)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(csv_files_info["CREDITOS.csv"], "CREDITOS.CSV")
            zipf.write(csv_files_info["PERSONAS.CSV"], "PERSONAS.CSV")
            zipf.write(csv_files_info["CUOTAS.CSV"], "CUOTAS.CSV")

        self.export_to_excel()
        return zip_path
