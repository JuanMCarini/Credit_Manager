"""
Module: csv_importer.py
Description: Robust ETL pipeline for importing purchased portfolios via headerless CSVs.
Author: Juan Martín Carini
Date: 2026-05-12
"""

import math
from datetime import date, datetime

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
    OperacionCartera,
    SexoEnum,
    SocioComercial,
    TipoCobranzaEnum,
)


class PortfolioImporter:
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
        fecha_compra: date,
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
        print("Leyendo archivos CSV...")

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

        # 1. Extracción a variables temporales
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

        # 2. Transformación
        print("Transformando y limpiando datos...")
        df_p["ID Operación"] = df_p["ID Operación"].astype(str).str.strip()
        df_pr["ID Operación"] = df_pr["ID Operación"].astype(str).str.strip()
        df_c["ID Operación"] = df_c["ID Operación"].astype(str).str.strip()

        df_p["CUIL"] = df_p["CUIL"].astype(str).str.replace(r"\D", "", regex=True)

        # 3. Guardado en el estado del objeto (self)
        self.df_personas = df_p.replace({np.nan: None})
        self.df_prestamos = df_pr.replace({np.nan: None})
        self.df_cuotas = df_c.replace({np.nan: None})

    def validation(self) -> None:
        """
        Validates the referential integrity using internal DataFrames.
        """

        # Verificamos que los datos existan usando la @property que creamos
        if not self.data_loaded:
            raise ValueError("Debe ejecutar read_csv() antes de validar.")

        # 2. LOGICAL VALIDATION
        print("Validando integridad de datos...")
        errores_detectados = False

        # Initialize control columns in DataFrames
        self.df_personas["VALIDACION"] = "OK"
        self.df_prestamos["VALIDACION"] = "OK"
        self.df_cuotas["VALIDACION"] = "OK"

        # A. Validation: Orphan Loans (ID Operacion missing in Personas)
        ops_personas = set(self.df_personas["ID Operación"])
        mask_prestamos_huerfanos = ~self.df_prestamos["ID Operación"].isin(ops_personas)

        if mask_prestamos_huerfanos.any():
            self.df_prestamos.loc[mask_prestamos_huerfanos, "VALIDACION"] = (
                "ERROR: ID Operación no encontrado en PERSONAS.CSV"
            )
            errores_detectados = True

        # B. Validation: Capital Consistency (Loans vs Installments)
        # Calculate the sum of installment capital per operation
        capital_cuotas_sum = self.df_cuotas.groupby("ID Operación")["Capital"].sum()
        self.df_prestamos["Capital_Calculado_Cuotas"] = (
            self.df_prestamos["ID Operación"].map(capital_cuotas_sum).fillna(0)
        )

        # Calculate difference (rounded to avoid floating point errors)
        self.df_prestamos["Diferencia_Capital"] = (
            self.df_prestamos["Capital_Calculado_Cuotas"] - self.df_prestamos["Capital"]
        ).round(2)

        mask_dif_capital = self.df_prestamos["Diferencia_Capital"] != 0
        if mask_dif_capital.any():
            self.df_prestamos.loc[mask_dif_capital, "VALIDACION"] = (
                "ERROR: El capital de las cuotas no coincide con el capital del préstamo"
            )
            errores_detectados = True

        # C. Validation: Orphan Installments (Installments without an associated loan)
        ops_prestamos = set(self.df_prestamos["ID Operación"])
        mask_cuotas_huerfanas = ~self.df_cuotas["ID Operación"].isin(ops_prestamos)

        if mask_cuotas_huerfanas.any():
            self.df_cuotas.loc[mask_cuotas_huerfanas, "VALIDACION"] = (
                "ERROR: ID Operación no encontrado en PRESTAMOS.CSV"
            )
            errores_detectados = True

        # D. Validation: Actual Value
        # 1. Asegurar tipos numéricos y aislar cuotas compradas (VA > 0)
        self.df_cuotas["Valor Actual"] = pd.to_numeric(
            self.df_cuotas["Valor Actual"], errors="coerce"
        ).fillna(0)
        mask_compradas = self.df_cuotas["Valor Actual"] > 0

        # 2. Fechas y Días (Convertimos la fecha de Pandas y la cruzamos con la fecha de la DB)
        fecha_compra_pd = pd.to_datetime(self.cartera.fecha_compra)
        fechas_vto = pd.to_datetime(
            self.df_cuotas["Fecha Vto. Pago"], dayfirst=False, errors="coerce"
        )
        dias_vto = (fechas_vto - fecha_compra_pd).dt.days

        # 3. Componentes del flujo
        capital = pd.to_numeric(self.df_cuotas["Capital"], errors="coerce").fillna(0)
        interes = pd.to_numeric(self.df_cuotas["Interés"], errors="coerce").fillna(0)
        flujo_total = capital + interes

        # 4. Cálculo vectorizado (solo se aplica la lógica a las filas compradas)
        tna = self.cartera.tna_descuento
        va = flujo_total / ((1 + (tna * 30 / 365)) ** (dias_vto / 30))

        # 5. Registro y comparación (Tolerancia de 1 peso por posibles redondeos en el CSV original)
        self.df_cuotas.loc[mask_compradas, "VA_Calculado"] = va.round(2)
        self.df_cuotas.loc[mask_compradas, "Diferencia_VA"] = (
            self.df_cuotas["VA_Calculado"] - self.df_cuotas["Valor Actual"]
        ).round(2)

        mask_dif_va = (self.df_cuotas["Diferencia_VA"].abs() > 1.0) & mask_compradas

        if mask_dif_va.any():
            self.df_cuotas.loc[mask_dif_va, "VALIDACION"] = (
                "ERROR: El recálculo del Valor Actual difiere de los archivos"
            )
            errores_detectados = True
        else:
            self.df_cuotas["Valor Actual"] = self.df_cuotas["VA_Calculado"]

        # 3. EXCEL REPORT GENERATION (Only if errors exist)
        if errores_detectados:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_reporte = f"REPORTE_ERRORES_IMPORTACION_{timestamp}.xlsx"

            print(
                f"\n❌ SE ENCONTRARON INCONSISTENCIAS. Generando reporte: {nombre_reporte}"
            )

            with pd.ExcelWriter(nombre_reporte, engine="openpyxl") as writer:
                # Personas Sheet
                self.df_personas.to_excel(writer, sheet_name="PERSONAS", index=False)

                # Prestamos Sheet (Sorted to show errors first)
                self.df_prestamos.sort_values(
                    by="VALIDACION", ascending=False
                ).to_excel(writer, sheet_name="PRESTAMOS", index=False)

                # Cuotas Sheet (Sorted to show errors first)
                self.df_cuotas.sort_values(by="VALIDACION", ascending=False).to_excel(
                    writer, sheet_name="CUOTAS", index=False
                )

            raise RuntimeError(
                f"Validación fallida. Por favor, revise el archivo {nombre_reporte} para corregir los datos."
            )
        else:
            # Drop auxiliary validation columns to return clean DataFrames
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

            print(
                "\n✅ Validación superada exitosamente. Todos los registros son consistentes."
            )

    def check_warnings(self) -> None:
        """
        Commits the instantiated portfolio to the database.
        """

        if not self.data_loaded:
            raise ValueError("Debe ejecutar read_csv() antes de validar.")

        if not self.cartera:
            raise ValueError(
                "No hay cartera instanciada. Ejecute create_portfolio primero."
            )

        print("Ejecutando auditoría de calidad de datos (Alertas Operativas)...")
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
                "Sin datos de contacto. "
            )
            alertas.append(
                f"Hay {clientes_incomunicados} clientes sin teléfono ni mail (Riesgo de cobranza)."
            )

        # 2. Bank Control: Loans without CBU/CVU
        if "CBU/CVU" in self.df_prestamos.columns:
            mask_sin_cbu = self.df_prestamos["CBU/CVU"].isna() | (
                self.df_prestamos["CBU/CVU"] == ""
            )
            prestamos_sin_cuenta = mask_sin_cbu.sum()

            if prestamos_sin_cuenta > 0:
                self.df_prestamos.loc[mask_sin_cbu, "ALERTA_OPERATIVA"] += (
                    "Falta CBU/CVU. "
                )
                alertas.append(f"Falta el CBU/CVU en {prestamos_sin_cuenta} préstamos.")

        # 3. Employer Control: Loans without Ente Pagador
        if "Ente Pagador" in self.df_prestamos.columns:
            mask_sin_ente = self.df_prestamos["Ente Pagador"].isna() | (
                self.df_prestamos["Ente Pagador"] == ""
            )
            prestamos_sin_empleador = mask_sin_ente.sum()

            if prestamos_sin_empleador > 0:
                self.df_prestamos.loc[mask_sin_ente, "ALERTA_OPERATIVA"] += (
                    "Falta Ente Pagador. "
                )
                alertas.append(
                    f"Faltan los datos del Ente Pagador en {prestamos_sin_empleador} préstamos."
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
        mask_relacion = self.df_prestamos["Val. Cuota/Remuneración"] > 0.30

        if mask_remuneracion_nula.any():
            self.df_prestamos.loc[mask_remuneracion_nula, "ALERTA_OPERATIVA"] += (
                "Remuneración nula/faltante. "
            )

        if mask_relacion.any():
            self.df_prestamos.loc[mask_relacion, "ALERTA_OPERATIVA"] += (
                "Cuota supera el 30% del sueldo. "
            )

        operaciones_riesgosas = (mask_remuneracion_nula | mask_relacion).sum()
        if operaciones_riesgosas > 0:
            alertas.append(
                f"Existen {operaciones_riesgosas} operaciones con remuneración nula o relación cuota-ingreso mayor al 30%."
            )

        # 5. Commercial Conditions Control: Fecha Compra y Tasa Compra
        # A. Control de Fecha
        fecha_compra_sistema = pd.to_datetime(self.cartera.fecha_compra).date()
        # Ajustar el parámetro 'dayfirst' si en el CSV la fecha viene como YYYY-MM-DD
        fechas_csv = pd.to_datetime(
            self.df_prestamos["Fecha Compra"], dayfirst=False, errors="coerce"
        ).dt.date

        mask_fecha_distinta = fechas_csv.notna() & (fechas_csv != fecha_compra_sistema)
        prestamos_fecha_distinta = mask_fecha_distinta.sum()

        if prestamos_fecha_distinta > 0:
            self.df_prestamos.loc[mask_fecha_distinta, "ALERTA_OPERATIVA"] += (
                "Fecha Compra difiere del contrato. "
            )
            alertas.append(
                f"Hay {prestamos_fecha_distinta} préstamos con Fecha Compra en el CSV distinta a la ingresada en sistema ({fecha_compra_sistema})."
            )

        # B. Control de Tasa (Convirtiendo decimal a porcentaje)
        tasa_sistema_porcentaje = self.cartera.tna_descuento * 100.0
        tasas_csv = pd.to_numeric(self.df_prestamos["Tasa Compra"], errors="coerce")

        mask_tasa_distinta = tasas_csv.notna() & (
            (tasas_csv - tasa_sistema_porcentaje).abs() > 0.01
        )
        prestamos_tasa_distinta = mask_tasa_distinta.sum()

        if prestamos_tasa_distinta > 0:
            self.df_prestamos.loc[mask_tasa_distinta, "ALERTA_OPERATIVA"] += (
                "Tasa Compra difiere del contrato. "
            )
            alertas.append(
                f"Hay {prestamos_tasa_distinta} préstamos con Tasa Compra en el CSV distinta a la ingresada en sistema ({tasa_sistema_porcentaje}%)."
            )

        # --- EXCEL REPORT GENERATION & CLEANUP ---
        if alertas:
            print("\n⚠️ ALERTAS OPERATIVAS DETECTADAS:")
            for i, alerta in enumerate(alertas, 1):
                print(f"  {i}. {alerta}")

            # 1. Hacemos una copia independiente para no alterar los datos en memoria
            df_personas_alertas = self.df_personas[
                self.df_personas["ALERTA_OPERATIVA"] != ""
            ].copy()

            df_prestamos_alertas = self.df_prestamos[
                self.df_prestamos["ALERTA_OPERATIVA"] != ""
            ].copy()

            # 2. Sanitización ETL: Truncamos celdas con texto corrupto al límite seguro de Excel
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

            print(f"\nGenerando reporte para la administración: {nombre_reporte}")
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
                "✅ Auditoría operativa impecable. No hay datos faltantes ni discrepancias comerciales."
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
        print("  -> Preparando Entes Pagadores (Empleadores)...")
        entes_csv = self.df_prestamos["Ente Pagador"].dropna().unique()

        # Mapeamos los existentes en la base
        empleadores_db = {e.nombre: e.id for e in self.db.query(Empleador).all()}

        nuevos_empleadores = 0
        for ente in entes_csv:
            ente_clean = str(ente).strip().upper()
            if ente_clean not in empleadores_db:
                nuevo_emp = Empleador(razon_social=ente_clean)
                self.db.add(nuevo_emp)
                self.db.flush()  # Flush genera el ID sin hacer commit
                empleadores_db[ente_clean] = nuevo_emp.id
                nuevos_empleadores += 1

        return empleadores_db

    # --- HELPERS BLINDADOS ---
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

        print("  -> Preparando Clientes...")
        clientes_db_cuils = {c[0] for c in self.db.query(Cliente.cuil).all()}

        # Mapeo rápido: ID Operación -> Ente Pagador (desde df_prestamos)
        op_to_ente = self.df_prestamos.set_index("ID Operación")[
            "Ente Pagador"
        ].to_dict()

        for _, row in self.df_personas.drop_duplicates(subset=["CUIL"]).iterrows():
            cuil_clean = str(row["CUIL"]).strip()

            if cuil_clean not in clientes_db_cuils:
                # Normalización de datos crudos
                sex_raw = self.safe_str(row.get("Sexo"))
                if sex_raw:
                    sex_raw = sex_raw.upper()
                sex_enum = (
                    SexoEnum.MASCULINO
                    if sex_raw in ["M", "1"]
                    else (SexoEnum.FEMENINO if sex_raw in ["F", "2"] else SexoEnum.OTRO)
                )

                # --- CORRECCIÓN CRÍTICA DE FECHA (NaT) ---
                f_nac_ts = pd.to_datetime(row.get("Fecha Nacimiento"), errors="coerce")
                f_nac = f_nac_ts.date() if pd.notna(f_nac_ts) else None

                # Búsqueda del Empleador (Casteo extra para evitar IDs corruptos)
                id_op_externo = self.safe_str(row.get("ID Operación"))
                ente_raw = op_to_ente.get(id_op_externo)
                ente_nombre = (
                    self.safe_str(ente_raw).upper() if self.safe_str(ente_raw) else None
                )
                emp_id = self.safe_int(empleadores_map.get(ente_nombre))

                # Extraemos y limpiamos documento
                doc_str = self.safe_str(row.get("Documento"))

                # Instanciación con casteo protegido en la totalidad de las columnas
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

        print("  -> Preparando Créditos...")
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
        print("  -> Preparando Cuotas y Cobranzas Retenidas...")

        for _, row in self.df_cuotas.iterrows():
            id_op_externo = str(row["ID Operación"])

            # Recuperamos el ID interno de la operación
            cred_id_interno = op_to_credito_id.get(id_op_externo)

            if cred_id_interno:
                f_vto = (
                    pd.to_datetime(row["Fecha Vto."], errors="coerce").date()
                    if pd.notna(row["Fecha Vto."])
                    else None
                )

                # Extracción y limpieza de los componentes financieros
                cap = float(row["Capital"]) if pd.notna(row["Capital"]) else 0.0
                int_ = float(row["Interés"]) if pd.notna(row["Interés"]) else 0.0
                iva_ = float(row["IVA"]) if pd.notna(row["IVA"]) else 0.0
                va = (
                    float(row["Valor Actual"]) if pd.notna(row["Valor Actual"]) else 0.0
                )

                if va == 0:
                    estado = EstadoCuota.NO_COMPRADA
                else:
                    estado = EstadoCuota.PENDIENTE

                nueva_cuota = Cuota(
                    credito_id=cred_id_interno,
                    nro_cuota=int(row["ID Cuota"]) if pd.notna(row["ID Cuota"]) else 1,
                    fecha_vencimiento=f_vto,
                    capital=cap,
                    interes=int_,
                    iva=iva_,
                    estado=estado,
                )

                # --- VINCULACIÓN CON OPERACIÓN CARTERA ---
                # Registramos que esta cuota fue adquirida en la cartera actual
                nueva_operacion = OperacionCartera(
                    cartera_id=self.cartera.id,
                    cuota_comercializada=va != 0.0,
                    fecha_registro=self.cartera.fecha_compra,
                )
                nueva_cuota.movimientos_cartera.append(nueva_operacion)

                # Generación automática de la cobranza para cuotas no compradas
                if va == 0:
                    nueva_cobranza = Cobranza(
                        tipo_cobranza=TipoCobranzaEnum.CNC,
                        capital=cap,
                        interes=int_,
                        iva=iva_,
                        # La retención se registra con fecha contable del día de la compra de la cartera
                        fecha=self.cartera.fecha_compra,
                    )
                    # El ORM vincula el cuota_id de la cobranza en memoria antes del flush
                    nueva_cuota.cobranzas.append(nueva_cobranza)

                self.db.add(nueva_cuota)

        # Persiste todas las cuotas y sus cobranzas asociadas de una sola vez
        self.db.flush()

    def save_portfolio(self) -> None:
        """
        Orchestrates the entire database insertion process ensuring atomicity.
        Commits the instantiated portfolio, partner, clients, credits, and installments.
        """
        if not self.data_loaded:
            raise ValueError("Datos no cargados. Ejecute read_csv() primero.")

        if not self.cartera or not self.socio:
            raise ValueError(
                "No hay cartera y/o socio instanciado. Ejecute create_portfolio primero."
            )

        print("\nIniciando volcado a la Base de Datos (Transacción Atómica)...")

        try:
            # 1. Guardar metadatos principales (Socio y Cartera)
            self.db.add(self.socio)
            self.db.flush()

            # 2. VINCULACIÓN CRÍTICA: Le inyectamos a la cartera el ID recién creado
            self.cartera.socio_id = self.socio.id
            self.db.add(self.cartera)
            self.db.flush()  # Necesitamos el ID de la cartera para los créditos

            # 3. Ahora la Cartera tiene un ID válido y no falla
            self.db.add(self.cartera)
            self.db.flush()

            # 4. Tablas de dependencias
            empleadores_map = self._import_employers()
            self._import_clients(empleadores_map)

            # 5. Tablas transaccionales
            op_to_id = self._import_credits()
            self._import_installments(op_to_id)

            # 6. Commit definitivo
            self.db.commit()
            print(
                f"✅ Transacción completada: Cartera '{self.cartera.nombre}' guardada."
            )

        except Exception as e:
            self.db.rollback()
            raise RuntimeError(f"Error en inserción SQL: {e}")
