"""
Module: csv_importer.py
Description: Robust ETL pipeline for importing purchased portfolios via headerless CSVs.
Author: Juan Martín Carini
Date: 2026-05-12
"""

import math
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

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
    Relacion,
    SexoEnum,
    SocioComercial,
    TipoCobranzaEnum,
)
from src.utils.dates import normalize_date


class PortfolioPurchase:
    """
    Handles the extraction, transformation, and atomic loading of portfolio data.
    """

    def __init__(self):
        """
        Initializes the importer with a database session and empty state containers.
        """
        self.db = SessionLocal()
        self.cartera = None
        self.socio = None

        # State containers for the dataframes
        self.df_personas = None
        self.df_prestamos = None
        self.df_cuotas = None

    @property
    def data_loaded(self) -> bool:
        """
        Property: Returns True if all CSVs have been successfully loaded into memory.
        """
        return all(
            df is not None
            for df in [self.df_personas, self.df_prestamos, self.df_cuotas]
        )

    def create_portfolio(
        self,
        nombre_cartera: str,
        fecha_compra: str | date,
        tna_descuento: float,
        cuit_vendedor: str,
        razon_social_vendedor: str,
        **kwargs,
    ) -> Cartera:
        """
        =============================================================================
        Method: create_portfolio
        Description: Retrieves an existing commercial partner (seller) by CUIT or
                     instantiates a new one in memory. Initializes the portfolio
                     entity to be linked during the atomic insertion phase.
        =============================================================================
        """

        # 0. Normalize date
        fecha_compra = normalize_date(fecha_compra, date)

        # 1. Retrieve or instantiate the selling commercial partner
        self.socio = self.db.query(SocioComercial).filter_by(cuit=cuit_vendedor).first()

        if not self.socio:
            self.socio = SocioComercial(
                cuit=cuit_vendedor, razon_social=razon_social_vendedor
            )

        # 2. Instantiate the portfolio
        cartera = self.db.query(Cartera).filter_by(nombre=nombre_cartera).first()

        if not cartera:
            cartera = Cartera(
                nombre=nombre_cartera,
                # socio_id will be injected dynamically in save_portfolio()
                # after self.socio gets its primary key assigned via flush().
                fecha_compra=fecha_compra,
                tna_descuento=tna_descuento,
                recurso=kwargs.get("recurso", True),
                iva=kwargs.get("iva", False),
                tipo_operacion="COMPRA",
            )

        self.cartera = cartera
        return self.cartera

    def read_csv(
        self, personas_path: str, prestamos_path: str, cuotas_path: str
    ) -> None:
        """
        Reads CSVs and stores the DataFrames internally in the instance (self).
        """
        print("Reading CSV files...")

        cols_personas = [
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
        cols_prestamos = [
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
            "CBU/CVU",
        ]
        cols_cuotas = [
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

        # 1. Extraction to temporary variables
        df_p = pd.read_csv(
            personas_path, sep=",", encoding="latin-1", header=None, names=cols_personas
        )
        df_pr = pd.read_csv(
            prestamos_path,
            sep=",",
            encoding="latin-1",
            header=None,
            names=cols_prestamos,
        )
        df_c = pd.read_csv(
            cuotas_path, sep=",", encoding="latin-1", header=None, names=cols_cuotas
        )

        # 2. Transformation
        print("Transforming and cleaning data...")
        df_p["ID Operación"] = df_p["ID Operación"].astype(str).str.strip()
        df_pr["ID Operación"] = df_pr["ID Operación"].astype(str).str.strip()
        df_c["ID Operación"] = df_c["ID Operación"].astype(str).str.strip()

        df_p["CUIL"] = df_p["CUIL"].astype(str).str.replace(r"\D", "", regex=True)

        # 3. Save into object state (self)
        self.df_personas = df_p.replace({np.nan: None})
        self.df_prestamos = df_pr.replace({np.nan: None})
        self.df_cuotas = df_c.replace({np.nan: None})

    def validation(self) -> None:
        """
        =============================================================================
        Method: validation
        Description: Validates referential integrity, financial consistency, and
                     external geographical/entity mappings across loaded DataFrames.
                     Directly replaces external IDs with native keys upon success,
                     and logs inconsistencies into an Excel report if errors occur.
        Parameters:
            None
        Returns:
            None
        Raises:
            ValueError: If data has not been pre-loaded via read_csv().
            RuntimeError: If data validation fails, generating an Excel error log.
        =============================================================================
        """

        if not self.data_loaded:
            raise ValueError("You must run read_csv() before validating.")

        # 2. LOGICAL VALIDATION
        print("Validating data integrity...")
        errores_detectados = False

        # Initialize control columns in DataFrames
        self.df_personas["VALIDACION"] = "OK"
        self.df_prestamos["VALIDACION"] = "OK"
        self.df_cuotas["VALIDACION"] = "OK"

        # A. Validation: External Province Mapping (Homologación Geográfica)
        if "ID Provincia" in self.df_personas.columns:
            mapeos_db = (
                self.db.query(Relacion.id_foraneo, Relacion.id_local)
                .filter(
                    Relacion.socio_id == self.socio.id, Relacion.tabla == "provincias"
                )
                .all()
            )
            cache_provincias = {
                str(m.id_foraneo).strip(): m.id_local for m in mapeos_db
            }

            id_prov_str = (
                self.df_personas["ID Provincia"]
                .astype(str)
                .str.replace(r"\.0$", "", regex=True)
                .str.strip()
            )

            # Map to a temporary series to evaluate failures without losing original data
            mapped_provincias = id_prov_str.map(cache_provincias)
            mask_prov_error = mapped_provincias.isna()

            if mask_prov_error.any():
                self.df_personas.loc[mask_prov_error, "VALIDACION"] = (
                    "ERROR: ID Provincia not found in external_mappings table"
                )
                errores_detectados = True
            else:
                # If all mappings are successful, we overwrite the original column
                self.df_personas["ID Provincia"] = mapped_provincias
        else:
            self.df_personas["VALIDACION"] = (
                "ERROR: Required column 'ID Provincia' not found"
            )
            errores_detectados = True

        # B. Validation: External Entity Mapping (Homologación de Socios Originadores)
        if "ID Entidad" in self.df_prestamos.columns:
            mapeos_entidades = (
                self.db.query(Relacion.id_foraneo, Relacion.id_local)
                .filter(
                    Relacion.socio_id == self.socio.id,
                    Relacion.tabla == "socios_comerciales",
                )
                .all()
            )
            cache_entidades = {
                str(m.id_foraneo).strip(): m.id_local for m in mapeos_entidades
            }

            id_entidad_str = (
                self.df_prestamos["ID Entidad"]
                .astype(str)
                .str.replace(r"\.0$", "", regex=True)
                .str.strip()
            )

            mapped_entidades = id_entidad_str.map(cache_entidades)
            mask_entidad_error = mapped_entidades.isna()

            if mask_entidad_error.any():
                self.df_prestamos.loc[mask_entidad_error, "VALIDACION"] = (
                    "ERROR: ID Entidad not found in external_mappings table for 'socios_comerciales'"
                )
                errores_detectados = True
            else:
                self.df_prestamos["ID Entidad"] = mapped_entidades
        else:
            self.df_prestamos["VALIDACION"] = (
                "ERROR: Required column 'ID Entidad' not found"
            )
            errores_detectados = True

        # C. Validation: Orphan Loans (ID Operacion missing in Personas)
        ops_personas = set(self.df_personas["ID Operación"])
        mask_prestamos_huerfanos = ~self.df_prestamos["ID Operación"].isin(ops_personas)

        if mask_prestamos_huerfanos.any():
            self.df_prestamos.loc[mask_prestamos_huerfanos, "VALIDACION"] = (
                "ERROR: ID Operación not found in PERSONAS.CSV"
            )
            errores_detectados = True

        # D. Validation: Capital Consistency (Loans vs Installments)
        capital_cuotas_sum = self.df_cuotas.groupby("ID Operación")["Capital"].sum()
        self.df_prestamos["Capital_Calculado_Cuotas"] = (
            self.df_prestamos["ID Operación"].map(capital_cuotas_sum).fillna(0)
        )

        self.df_prestamos["Diferencia_Capital"] = (
            self.df_prestamos["Capital_Calculado_Cuotas"] - self.df_prestamos["Capital"]
        ).round(2)

        mask_dif_capital = self.df_prestamos["Diferencia_Capital"] != 0
        if mask_dif_capital.any():
            self.df_prestamos.loc[mask_dif_capital, "VALIDACION"] = (
                "ERROR: Installment capital does not match the loan capital"
            )
            errores_detectados = True

        # E. Validation: Orphan Installments (Installments without an associated loan)
        ops_prestamos = set(self.df_prestamos["ID Operación"])
        mask_cuotas_huerfanas = ~self.df_cuotas["ID Operación"].isin(ops_prestamos)

        if mask_cuotas_huerfanas.any():
            self.df_cuotas.loc[mask_cuotas_huerfanas, "VALIDACION"] = (
                "ERROR: ID Operación not found in PRESTAMOS.CSV"
            )
            errores_detectados = True

        # F. Validation: Actual Value
        self.df_cuotas["Valor Actual"] = pd.to_numeric(
            self.df_cuotas["Valor Actual"], errors="coerce"
        ).fillna(0)
        mask_compradas = self.df_cuotas["Valor Actual"] > 0

        fecha_compra_pd = pd.to_datetime(self.cartera.fecha_compra)
        fechas_vto = pd.to_datetime(
            self.df_cuotas["Fecha Vto. Pago"], dayfirst=False, errors="coerce"
        )
        dias_vto = (fechas_vto - fecha_compra_pd).dt.days

        capital = pd.to_numeric(self.df_cuotas["Capital"], errors="coerce").fillna(0)
        interes = pd.to_numeric(self.df_cuotas["Interés"], errors="coerce").fillna(0)
        flujo_total = capital + interes

        tna = self.cartera.tna_descuento
        va = flujo_total / ((1 + (tna * 30 / 365)) ** (dias_vto / 30))

        self.df_cuotas.loc[mask_compradas, "VA_Calculado"] = va.round(2)
        self.df_cuotas.loc[mask_compradas, "Diferencia_VA"] = (
            self.df_cuotas["VA_Calculado"] - self.df_cuotas["Valor Actual"]
        ).round(2)

        mask_dif_va = (self.df_cuotas["Diferencia_VA"].abs() > 1.0) & mask_compradas

        if mask_dif_va.any():
            self.df_cuotas.loc[mask_dif_va, "VALIDACION"] = (
                "ERROR: The Present Value recalculation differs from the files"
            )
            errores_detectados = True
        else:
            self.df_cuotas["Valor Actual"] = self.df_cuotas["VA_Calculado"]

        # G. Validation: IVA Consistency
        if self.cartera.iva:
            iva_cuotas = pd.to_numeric(self.df_cuotas["IVA"], errors="coerce").fillna(0)
            interes_cuotas = pd.to_numeric(
                self.df_cuotas["Interés"], errors="coerce"
            ).fillna(0)

            mask_iva_inconsistente = (iva_cuotas == 0) & (interes_cuotas > 0)

            if mask_iva_inconsistente.any():
                self.df_cuotas.loc[mask_iva_inconsistente, "VALIDACION"] = (
                    "ERROR: Installment has no IVA but has interest, while portfolio includes IVA"
                )
                errores_detectados = True

        # 3. EXCEL REPORT GENERATION
        if errores_detectados:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_reporte = f"REPORTE_ERRORES_IMPORTACION_{timestamp}.xlsx"

            print(f"\n❌ INCONSISTENCIES FOUND. Generating report: {nombre_reporte}")

            with pd.ExcelWriter(nombre_reporte, engine="openpyxl") as writer:
                self.df_personas.to_excel(writer, sheet_name="PERSONAS", index=False)

                self.df_prestamos.sort_values(
                    by="VALIDACION", ascending=False
                ).to_excel(writer, sheet_name="PRESTAMOS", index=False)

                self.df_cuotas.sort_values(by="VALIDACION", ascending=False).to_excel(
                    writer, sheet_name="CUOTAS", index=False
                )

            raise RuntimeError(
                f"Validation failed. Please review the file {nombre_reporte} to correct the data."
            )
        else:
            # Final cleanup of auxiliary control columns
            self.df_personas.drop(columns=["VALIDACION"], inplace=True)
            self.df_prestamos.drop(
                columns=[
                    "VALIDACION",
                    "Capital_Calculado_Cuotas",
                    "Diferencia_Capital",
                ],
                inplace=True,
            )
            self.df_cuotas.drop(
                columns=["VALIDACION", "VA_Calculado", "Diferencia_VA"], inplace=True
            )

            print("\n✅ Validation passed successfully. All records are consistent.")

    def check_warnings(self) -> None:
        """
        Commits the instantiated portfolio to the database.
        """

        if not self.data_loaded:
            raise ValueError("You must run read_csv() before validating.")

        if not self.cartera:
            raise ValueError("No portfolio instantiated. Run create_portfolio first.")

        print("Executing data quality audit (Operational Alerts)...")
        alertas = []

        # Initialize warning tracking columns
        self.df_personas["ALERTA_OPERATIVA"] = ""
        self.df_prestamos["ALERTA_OPERATIVA"] = ""

        # 1. Contact Control: Persons without phone or email
        mask_sin_telefono = self.df_personas["Telefono"].isna() | (
            self.df_personas["Telefono"] == ""
        )
        mask_sin_telefono_2 = self.df_personas["Telefono 2"].isna() | (
            self.df_personas["Telefono 2"] == ""
        )
        mask_sin_mail = self.df_personas["Mail"].isna() | (
            self.df_personas["Mail"] == ""
        )

        mask_incomunicados = mask_sin_telefono & mask_sin_telefono_2 & mask_sin_mail
        clientes_incomunicados = mask_incomunicados.sum()

        if clientes_incomunicados > 0:
            self.df_personas.loc[mask_incomunicados, "ALERTA_OPERATIVA"] += (
                "No contact data. "
            )
            alertas.append(
                f"There are {clientes_incomunicados} clients without phone or email (Collection risk)."
            )

        # 2. Bank Control: Loans without CBU/CVU
        if "CBU/CVU" in self.df_prestamos.columns:
            mask_sin_cbu = self.df_prestamos["CBU/CVU"].isna() | (
                self.df_prestamos["CBU/CVU"] == ""
            )
            prestamos_sin_cuenta = mask_sin_cbu.sum()

            if prestamos_sin_cuenta > 0:
                self.df_prestamos.loc[mask_sin_cbu, "ALERTA_OPERATIVA"] += (
                    "Missing CBU/CVU. "
                )
                alertas.append(f"CBU/CVU is missing in {prestamos_sin_cuenta} loans.")

        # 3. Employer Control: Loans without Ente Pagador
        if "Ente Pagador" in self.df_prestamos.columns:
            mask_sin_ente = self.df_prestamos["Ente Pagador"].isna() | (
                self.df_prestamos["Ente Pagador"] == ""
            )
            prestamos_sin_empleador = mask_sin_ente.sum()

            if prestamos_sin_empleador > 0:
                self.df_prestamos.loc[mask_sin_ente, "ALERTA_OPERATIVA"] += (
                    "Missing Payer Entity. "
                )
                alertas.append(
                    f"Payer Entity data is missing in {prestamos_sin_empleador} loans."
                )

        # 4. Remuneration Control: Debt-to-Income Ratio
        remuneracion_map = self.df_personas.drop_duplicates(
            subset=["ID Operación"]
        ).set_index("ID Operación")["Remuneración"]
        self.df_prestamos["Remuneración"] = self.df_prestamos["ID Operación"].map(
            remuneracion_map
        )

        remuneracion_segura = pd.to_numeric(
            self.df_prestamos["Remuneración"], errors="coerce"
        ).replace({0.0: np.nan})
        self.df_prestamos["Val. Cuota/Remuneración"] = (
            pd.to_numeric(self.df_prestamos["Importe Cuota"], errors="coerce")
            / remuneracion_segura
        )

        mask_remuneracion_nula = self.df_prestamos["Remuneración"].isna() | (
            self.df_prestamos["Remuneración"] == 0.0
        )
        mask_relacion = self.df_prestamos["Val. Cuota/Remuneración"] > 0.40

        if mask_remuneracion_nula.any():
            self.df_prestamos.loc[mask_remuneracion_nula, "ALERTA_OPERATIVA"] += (
                "Null/missing remuneration. "
            )

        if mask_relacion.any():
            self.df_prestamos.loc[mask_relacion, "ALERTA_OPERATIVA"] += (
                "Installment exceeds 30% of salary. "
            )

        operaciones_riesgosas = (mask_remuneracion_nula | mask_relacion).sum()
        if operaciones_riesgosas > 0:
            alertas.append(
                f"There are {operaciones_riesgosas} operations with null remuneration or installment-to-income ratio greater than 30%."
            )

        # 5. Commercial Conditions Control: Fecha Compra y Tasa Compra
        # A. Date Control
        fecha_compra_sistema = pd.to_datetime(self.cartera.fecha_compra).date()
        # Adjust the 'dayfirst' parameter if the CSV date is YYYY-MM-DD
        fechas_csv = pd.to_datetime(
            self.df_prestamos["Fecha Compra"], dayfirst=False, errors="coerce"
        ).dt.date

        mask_fecha_distinta = fechas_csv.notna() & (fechas_csv != fecha_compra_sistema)
        prestamos_fecha_distinta = mask_fecha_distinta.sum()

        if prestamos_fecha_distinta > 0:
            self.df_prestamos.loc[mask_fecha_distinta, "ALERTA_OPERATIVA"] += (
                "Purchase Date differs from contract. "
            )
            alertas.append(
                f"There are {prestamos_fecha_distinta} loans with a CSV Purchase Date different from the system ({fecha_compra_sistema})."
            )

        # B. Rate Control (Converting decimal to percentage)
        tasa_sistema_porcentaje = self.cartera.tna_descuento * 100.0
        tasas_csv = pd.to_numeric(self.df_prestamos["Tasa Compra"], errors="coerce")

        mask_tasa_distinta = tasas_csv.notna() & (
            (tasas_csv - tasa_sistema_porcentaje).abs() > 0.01
        )
        prestamos_tasa_distinta = mask_tasa_distinta.sum()

        if prestamos_tasa_distinta > 0:
            self.df_prestamos.loc[mask_tasa_distinta, "ALERTA_OPERATIVA"] += (
                "Purchase Rate differs from contract. "
            )
            alertas.append(
                f"There are {prestamos_tasa_distinta} loans with a CSV Purchase Rate different from the system ({tasa_sistema_porcentaje}%)."
            )

        # --- EXCEL REPORT GENERATION & CLEANUP ---
        if alertas:
            print("\n⚠️ OPERATIONAL ALERTS DETECTED:")
            for i, alerta in enumerate(alertas, 1):
                print(f"  {i}. {alerta}")

            # 1. Make an independent copy to avoid altering in-memory data
            df_personas_alertas = self.df_personas[
                self.df_personas["ALERTA_OPERATIVA"] != ""
            ].copy()

            df_prestamos_alertas = self.df_prestamos[
                self.df_prestamos["ALERTA_OPERATIVA"] != ""
            ].copy()

            # 2. ETL Sanitization: Truncate corrupt text cells to Excel's safe limit
            for col in df_personas_alertas.select_dtypes(include=["object"]):
                df_personas_alertas[col] = (
                    df_personas_alertas[col].astype(str).str[:32000]
                )

            for col in df_prestamos_alertas.select_dtypes(include=["object"]):
                df_prestamos_alertas[col] = (
                    df_prestamos_alertas[col].astype(str).str[:32000]
                )

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_reporte = f"ALERTAS_OPERATIVAS_CARTERA_{timestamp}.xlsx"

            print(f"\nGenerating report for administration: {nombre_reporte}")
            with pd.ExcelWriter(nombre_reporte, engine="openpyxl") as writer:
                if not df_personas_alertas.empty:
                    df_personas_alertas.to_excel(
                        writer, sheet_name="CONTACTO_FALTANTE", index=False
                    )
                if not df_prestamos_alertas.empty:
                    df_prestamos_alertas.to_excel(
                        writer, sheet_name="RIESGO_Y_BANCARIO", index=False
                    )
        else:
            print(
                "✅ Impeccable operational audit. No missing data or commercial discrepancies."
            )

        # Drop temporary tracking columns on the original DataFrames
        self.df_personas.drop(columns=["ALERTA_OPERATIVA"], inplace=True)
        self.df_prestamos.drop(
            columns=["ALERTA_OPERATIVA", "Remuneración", "Val. Cuota/Remuneración"],
            inplace=True,
        )

    def _import_employers(self) -> dict:
        """
        Extracts unique employers from the loans DataFrame, inserts new ones,
        and returns a mapping dictionary of {name: id}.
        """
        print("  -> Preparing Payer Entities (Employers)...")
        entes_csv = self.df_prestamos["Ente Pagador"].dropna().unique()

        # Map existing ones in the database
        empleadores_db = {e.razon_social: e.id for e in self.db.query(Empleador).all()}

        nuevos_empleadores = 0
        for ente in entes_csv:
            ente_clean = str(ente).strip().upper()
            if ente_clean not in empleadores_db:
                nuevo_emp = Empleador(razon_social=ente_clean)
                self.db.add(nuevo_emp)
                self.db.flush()  # Flush generates the ID without committing
                empleadores_db[ente_clean] = nuevo_emp.id
                nuevos_empleadores += 1

        return empleadores_db

    # --- BULLETPROOF HELPERS ---
    @staticmethod
    def safe_int(val):
        if pd.isna(val):
            return None
        try:
            f = float(val)
            if math.isnan(f):
                return None
            return int(f)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def safe_str(val):
        if pd.isna(val):
            return None
        s = str(val).strip()
        if s.lower() in ["", "nan", "nat", "none", "<na>"]:
            return None
        return s

    @staticmethod
    def safe_float(val):
        if pd.isna(val):
            return 0.0
        try:
            f = float(val)
            if math.isnan(f):
                return 0.0
            return f
        except (ValueError, TypeError):
            return 0.0

    def _import_clients(self, empleadores_map: dict) -> None:
        """
        =============================================================================
        Method: _import_clients
        Description: Extracts unique clients from the persons DataFrame and inserts them.
                     Implements math.isnan() based bulletproof casting to neutralize
                     any NaN variation from real-world CSV files before SQL insertion,
                     preventing ValueError exceptions.
        =============================================================================
        """
        import pandas as pd

        print("  -> Preparing Clients...")
        clientes_db_cuils = {c[0] for c in self.db.query(Cliente.cuil).all()}

        # Quick mapping: Operation ID -> Payer Entity (from df_prestamos)
        op_to_ente = self.df_prestamos.set_index("ID Operación")[
            "Ente Pagador"
        ].to_dict()

        for _, row in self.df_personas.drop_duplicates(subset=["CUIL"]).iterrows():
            cuil_clean = str(row["CUIL"]).strip()

            if cuil_clean not in clientes_db_cuils:
                # Normalization of raw data
                sex_raw = self.safe_str(row.get("Sexo"))
                if sex_raw:
                    sex_raw = sex_raw.upper()
                sex_enum = (
                    SexoEnum.MASCULINO
                    if sex_raw in ["M", "1"]
                    else (SexoEnum.FEMENINO if sex_raw in ["F", "2"] else SexoEnum.OTRO)
                )

                # --- CRITICAL DATE CORRECTION (NaT) ---
                f_nac_ts = pd.to_datetime(row.get("Fecha Nacimiento"), errors="coerce")
                f_nac = f_nac_ts.date() if pd.notna(f_nac_ts) else None

                # Employer search (Extra casting to avoid corrupt IDs)
                id_op_externo = self.safe_str(row.get("ID Operación"))
                ente_raw = op_to_ente.get(id_op_externo)
                ente_nombre = (
                    self.safe_str(ente_raw).upper() if self.safe_str(ente_raw) else None
                )
                emp_id = self.safe_int(empleadores_map.get(ente_nombre))

                # Extract and clean document
                doc_str = self.safe_str(row.get("Documento"))

                # Instantiation with protected casting in all columns
                nuevo_cliente = Cliente(
                    cuil=cuil_clean,
                    documento=doc_str.replace(r"\D", "") if doc_str else None,
                    apellido=self.safe_str(row.get("Apellido")).upper()
                    if self.safe_str(row.get("Apellido"))
                    else "",
                    nombre=self.safe_str(row.get("Nombre")).upper()
                    if self.safe_str(row.get("Nombre"))
                    else "",
                    calle=self.safe_str(row.get("Calle")),
                    calle_nro=self.safe_int(row.get("Calle Nro")),
                    piso=self.safe_str(row.get("Piso")),
                    depto=self.safe_str(row.get("Depto")),
                    id_provincia=self.safe_int(row.get("ID Provincia")),
                    id_codigo_postal=self.safe_str(row.get("ID Código Postal")),
                    localidad=self.safe_str(row.get("Localidad")),
                    fecha_nacimiento=f_nac,
                    telefono=self.safe_str(row.get("Telefono")),
                    telefono_2=self.safe_str(row.get("Telefono 2")),
                    mail=self.safe_str(row.get("Mail")),
                    remuneracion=self.safe_float(row.get("Remuneración")),
                    empleador_id=emp_id,
                    sexo=sex_enum,
                )
                self.db.add(nuevo_cliente)
                clientes_db_cuils.add(cuil_clean)

        self.db.flush()

    def _import_credits(self) -> dict:
        """
        Inserts loans into the database.
        Calculates the original TNA using numpy_financial.rate based on the original capital,
        installment amount, and term. Issuance date defaults to the portfolio purchase date.

        Returns:
            dict: A mapping dictionary of {external_operation_id: internal_credit_id}.
        """
        import numpy_financial as npf

        print("  -> Preparing Credits...")
        op_to_credito_id = {}

        for _, row in self.df_prestamos.iterrows():
            id_op_externo = str(row["ID Operación"])

            persona_row = self.df_personas[
                self.df_personas["ID Operación"] == id_op_externo
            ].iloc[0]

            # Rule: Issuance date defaults to the portfolio purchase date
            f_emision = self.cartera.fecha_compra

            # Parameters for numpy_financial.rate
            plazo = len(self.df_cuotas[self.df_cuotas["ID Operación"] == id_op_externo])
            capital_original = (
                float(row["Capital"]) if pd.notna(row["Capital"]) else 0.0
            )
            importe_cuota = (
                float(row["Importe Cuota"]) if pd.notna(row["Importe Cuota"]) else 0.0
            )

            # Calculate TNA (Annual Nominal Rate)
            # The rate function requires pmt (payment) and pv (present value) to have opposite signs.
            tna_calculada = 0.0
            if plazo > 0 and capital_original > 0 and importe_cuota > 0:
                tasa_mensual = npf.rate(
                    nper=plazo, pmt=-importe_cuota, pv=capital_original, fv=0
                )

                # Check for convergence failures (returns nan)
                if pd.notna(tasa_mensual) and tasa_mensual > 0:
                    tna_calculada = float(tasa_mensual * 365 / 30)

            nuevo_credito = Credito(
                id_externo=id_op_externo,
                cliente_cuil=persona_row["CUIL"],
                cartera_id=self.cartera.id,
                socio_originador_id=int(row["ID Entidad"])
                if pd.notna(row["ID Entidad"])
                else None,
                capital=float(row["Capital Vendido"])
                if pd.notna(row["Capital Vendido"])
                else 0.0,
                tna_c_iva=tna_calculada,
                plazo=plazo,
                fecha_emision=f_emision,
                estado=EstadoCredito.ACTIVO,
            )
            self.db.add(nuevo_credito)
            self.db.flush()

            op_to_credito_id[id_op_externo] = nuevo_credito.id

        return op_to_credito_id

    def _import_installments(self, op_to_credito_id: dict) -> None:
        """
        Inserts installments mapping to internal system IDs.
        Automatically generates a 'CUOTA NO COMPRADA' collection event
        for installments with a Present Value (Valor Actual) of 0,
        linking them to the corresponding installment via ORM relationships.
        """
        print("  -> Preparing Installments and Retained Collections...")

        for _, row in self.df_cuotas.iterrows():
            id_op_externo = str(row["ID Operación"])

            # Retrieve internal operation ID
            cred_id_interno = op_to_credito_id.get(id_op_externo)

            if cred_id_interno:
                f_vto = (
                    pd.to_datetime(row["Fecha Vto."], errors="coerce").date()
                    if pd.notna(row["Fecha Vto."])
                    else None
                )

                # Extraction and cleaning of financial components
                cap = float(row["Capital"]) if pd.notna(row["Capital"]) else 0.0
                int_ = float(row["Interés"]) if pd.notna(row["Interés"]) else 0.0
                iva_ = float(row["IVA"]) if pd.notna(row["IVA"]) else 0.0
                va = (
                    float(row["Valor Actual"]) if pd.notna(row["Valor Actual"]) else 0.0
                )

                if va == 0:
                    estado = EstadoCuota.NO_COMPRADA
                    estado_cesion = EstadoCuotaCedida.NO_COMPRADA
                else:
                    estado = EstadoCuota.PENDIENTE
                    estado_cesion = EstadoCuotaCedida.NO_VENDIDA

                nueva_cuota = Cuota(
                    credito_id=cred_id_interno,
                    nro_cuota=int(row["ID Cuota"]) if pd.notna(row["ID Cuota"]) else 1,
                    fecha_vencimiento=f_vto,
                    capital=cap,
                    interes=int_,
                    iva=iva_,
                    estado=estado,
                    estado_cesion=estado_cesion,
                )

                # --- LINK WITH PORTFOLIO OPERATION ---
                # Record that this installment was acquired in the current portfolio
                nueva_operacion = OperacionCartera(
                    cartera_id=self.cartera.id,
                    cuota_comercializada=va != 0.0,
                    fecha_registro=self.cartera.fecha_compra,
                )
                nueva_cuota.movimientos_cartera.append(nueva_operacion)

                # Automatic collection generation for unpurchased installments
                if va == 0:
                    nueva_cobranza = Cobranza(
                        tipo_cobranza=TipoCobranzaEnum.CNC,
                        capital=cap,
                        interes=int_,
                        iva=iva_,
                        # The retention is recorded with accounting date of the portfolio purchase date
                        fecha=self.cartera.fecha_compra,
                    )
                    # The ORM links the collection's cuota_id in memory before flush
                    nueva_cuota.cobranzas.append(nueva_cobranza)

                self.db.add(nueva_cuota)

        # Persist all installments and their associated collections at once
        self.db.flush()

    def save_portfolio(self) -> None:
        """
        Orchestrates the entire database insertion process ensuring atomicity.
        Commits the instantiated portfolio, partner, clients, credits, and installments.
        """
        if not self.data_loaded:
            raise ValueError("Data not loaded. Run read_csv() first.")

        if not self.cartera or not self.socio:
            raise ValueError(
                "No portfolio and/or partner instantiated. Run create_portfolio first."
            )

        print("\nStarting dump to the Database (Atomic Transaction)...")

        try:
            # 1. Save main metadata (Partner and Portfolio)
            self.db.add(self.socio)
            self.db.flush()

            # 2. CRITICAL LINKING: Inject the newly created ID into the portfolio
            self.cartera.socio_id = self.socio.id
            self.db.add(self.cartera)
            self.db.flush()  # We need the portfolio ID for the credits

            # 3. Now the Portfolio has a valid ID and won't fail
            self.db.add(self.cartera)
            self.db.flush()

            # 4. Dependency tables
            empleadores_map = self._import_employers()
            self._import_clients(empleadores_map)

            # 5. Transaction tables
            op_to_id = self._import_credits()
            self._import_installments(op_to_id)

            # 6. Final commit
            self.db.commit()
            print(f"✅ Transaction completed: Portfolio '{self.cartera.nombre}' saved.")

        except Exception as e:
            self.db.rollback()
            raise RuntimeError(f"SQL insertion error: {e}")

    def request_portfolio_paths() -> dict:
        """
        =============================================================================
        Function: request_portfolio_paths
        Description: Interactively prompts the user to input file paths for the
                     required CSV files ('personas', 'prestamos', 'cuotas').
                     Validates the existence of each file before accepting the input.
        Returns:
            dict: A dictionary containing the validated absolute or relative paths
                  mapped to their respective keys.
        =============================================================================
        """

        paths = {}
        archivos_requeridos = {
            "personas": "PERSONAS (ej: ../data/PERSONAS.CSV)",
            "prestamos": "PRESTAMOS (ej: ../data/PRESTAMOS.CSV)",
            "cuotas": "CUOTAS (ej: ../data/CUOTAS.CSV)",
        }

        print("\n--- Portfolio File Upload Wizard ---")

        for clave, descripcion in archivos_requeridos.items():
            while True:
                # Request the path and clean up spaces or accidental quotes
                ruta_ingresada = (
                    input(f"📁 Enter the path for {descripcion}: ").strip().strip("\"'")
                )
                ruta_obj = Path(ruta_ingresada)

                # Verify that the path exists and is effectively a file
                if ruta_obj.exists() and ruta_obj.is_file():
                    # Save the path resolving its absolute location
                    paths[clave] = str(ruta_obj.resolve())
                    print(f"   ✔️ File detected: {ruta_obj.name}\n")
                    break
                else:
                    print(
                        f"   ❌ Error: No file found at path '{ruta_ingresada}'. Try again.\n"
                    )

        print("--- Path loading completed successfully ---")
        return paths

    def process_full_portfolio(
        self,
        portfolio_name: str,
        portfolio_date: str,
        rate: float,
        cuit: int | str,
        company_name: str,
        paths: dict | None = None,
        recurso: bool = True,
        iva: bool = False,
    ) -> bool:
        """
        =============================================================================
        Method: process_full_portfolio
        Description: Orchestrates the end-to-end portfolio importation process.
                     If no paths dictionary is provided, it automatically invokes
                     the interactive native file selection dialogs.
        Parameters:
            portfolio_name (str): The descriptive name of the portfolio.
            portfolio_date (str | datetime): The acquisition or creation date.
            rate (float): The base interest or discount rate for the portfolio.
            cuit (int | str): The commercial partner's Tax ID (CUIT).
            company_name (str): The name of the commercial partner.
            paths (dict | None): Optional dictionary with keys 'personas',
                                 'prestamos', and 'cuotas'. Defaults to None.
            recurso (bool): Indicates if the portfolio has recourse. Defaults to True.
            iva (bool): Indicates if tax (IVA) is applied. Defaults to False.
        Returns:
            bool: True if the entire process completes successfully, False otherwise.
        =============================================================================
        """
        # 1. If no paths were passed, interactive prompt is activated
        if paths is None:
            from src.utils.files import ask_portfolio_paths

            paths = ask_portfolio_paths()

            # If the user canceled the window selection, we abort cleanly
            if paths == {} or paths is None:
                print(
                    f"❌ Ingestion aborted: Required files not provided for '{portfolio_name}'."
                )
                return False

        try:
            # 2. Guard Clause: Validate required dictionary structure before operating
            required_keys = {"personas", "prestamos", "cuotas"}
            missing_keys = required_keys - set(paths.keys())
            if missing_keys:
                print(
                    f"❌ Error: The 'paths' dictionary is missing required keys: {missing_keys}"
                )
                return False

            # 3. Portfolio entity creation and linking with Commercial Partner
            self.create_portfolio(
                nombre_cartera=portfolio_name,
                fecha_compra=portfolio_date,
                tna_descuento=rate,
                cuit_vendedor=cuit,
                razon_social_vendedor=company_name,
                recurso=recurso,
                iva=iva,
            )

            # 4. Read and load mapped CSV files from the paths dictionary
            self.read_csv(
                personas_path=paths["personas"],
                prestamos_path=paths["prestamos"],
                cuotas_path=paths["cuotas"],
            )

            # 5. Execution of the referential integrity and type validation engine
            self.validation()

            # 6. Verification of alerts or non-blocking inconsistencies
            self.check_warnings()

            # 7. Final persistence of clean data to the database
            self.save_portfolio()

            print(
                f"✅ Ingestion process finished successfully for portfolio: '{portfolio_name}'"
            )
            return True

        except Exception as e:
            print(
                f"❌ Critical failure during importation of portfolio '{portfolio_name}': {e}"
            )
            return False
