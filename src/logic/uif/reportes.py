import pandas as pd

from pandas import DataFrame, Period
from sqlalchemy import func

from src.database import SessionLocal
from src.database.models import PerfilTransaccional, Empleador, SocioComercial, ReglasPerfilTransaccional, RiesgoCliente, RepetAuditLog, Cliente, Credito, TipoCredito, Cuota, Cobranza
from src.logic.uif.perfil_transaccional import cuota_afectable
from src.utils import select_directory


def reportes_uif(save: bool = False, year: str | None = None, month: str | None = None) -> tuple[DataFrame, DataFrame, DataFrame, DataFrame]:

    if year and month:
        periodo = Period(f"{year}-{month}", freq="M")
    elif year:
        periodo = Period(f"{year}", freq="Y")
    else:
        periodo = None

    
    try:
        # Abrimos sesión con la base de datos
        db = SessionLocal()

        # Subconsulta para calcular el capital cobrado por cliente
        subq_cob = (
            db.query(
                Credito.cliente_cuil,
                func.sum(Cobranza.capital).label("total_cobrado")
            )
            .join(Cuota, Cuota.credito_id == Credito.id)
            .join(Cobranza, Cobranza.cuota_id == Cuota.id)
        )
        if periodo:
            subq_cob = subq_cob.filter(Cobranza.fecha <= periodo.end_time)
        subq_cob = subq_cob.group_by(Credito.cliente_cuil).subquery()

        query = (db.query(
            Cliente.cuil.label("C.U.I.L"),
            Cliente.documento.label("D.N.I."),
            Cliente.apellido.label("Apellido"),
            Cliente.nombre.label("Nombre"),
            func.min(Credito.fecha_emision).label("Fecha Emisión (Prim. Crto.)"),
            func.max(Credito.fecha_emision).label("Fecha Emisión (Ult. Crto.)"),
            func.count(Credito.id).label("Cantidad de Créditos"),
            func.sum(Credito.capital).label("Capital"),
            (func.sum(Credito.capital) - func.coalesce(func.max(subq_cob.c.total_cobrado), 0)).label("Capital Adeudado"))
                    .join(Credito, Credito.cliente_cuil == Cliente.cuil)
                    .outerjoin(subq_cob, subq_cob.c.cliente_cuil == Cliente.cuil)
                    .group_by(Cliente.cuil)
                    .filter(Credito.tipo_credito != TipoCredito.PENALTY))

        if periodo:
            query = (query.filter(Credito.fecha_emision <= periodo.end_time))
        df_clt = pd.read_sql(query.statement, db.get_bind())


        query = (db.query(
            RiesgoCliente.cuil_cliente.label("C.U.I.L."),
            RiesgoCliente.factor.label("Factor"),
            RiesgoCliente.peso.label("Peso"),
            RiesgoCliente.multiplicador.label("Multiplicador"),
            RiesgoCliente.puntaje.label("Puntaje"),
            RiesgoCliente.update_at.label("Fecha de Actualización")
        ))
        if periodo:
            query = query.filter(RiesgoCliente.update_at <= periodo.end_time)
        df_riesgo_clt = pd.read_sql(query.statement, db.get_bind())
        
        query = (db.query(
            RepetAuditLog.timestamp.label("Fecha de Búsqueda"),
            RepetAuditLog.cuil_cliente.label("C.U.I.L."),
            RepetAuditLog.searched_name.label("Nombre Buscado"),
            RepetAuditLog.is_match.label("Hubo Coincidencia"),
            RepetAuditLog.match_score.label("Puntaje de Coincidencia"),
            RepetAuditLog.matched_record_id.label("ID Registro RePET"),
            RepetAuditLog.user_id.label("ID Usuario")
        ))
        if periodo:
            query = query.filter(RepetAuditLog.timestamp <= periodo.end_time)
        df_repet = pd.read_sql(query.statement, db.get_bind())

        query = (db.query(
            PerfilTransaccional.cuil_cliente.label("C.U.I.L."),
            PerfilTransaccional.periodo.label("Periodo"),
            PerfilTransaccional.ingreso_bruto.label("Ingreso Bruto"),
            PerfilTransaccional.ingreso_neto.label("Ingreso Neto"),
            PerfilTransaccional.asignacion_familiar.label("Asignación Familiar"),
            PerfilTransaccional.horas_extras.label("Horas Extras"),
            PerfilTransaccional.vacaciones.label("Vacaciones"),
            PerfilTransaccional.descuentos_voluntarios.label("Descuentos Voluntarios"),
            PerfilTransaccional.otros.label("Otros"),
            SocioComercial.id.label("Socio ID"),
            SocioComercial.razon_social.label("Socio Comercial"),
            ReglasPerfilTransaccional.sueldo_tipo.label("Regla Sueldo Base"),
            ReglasPerfilTransaccional.asignacion_familiar.label("Regla Asig. Familiar"),
            ReglasPerfilTransaccional.horas_extras.label("Regla Horas Extras"),
            ReglasPerfilTransaccional.vacaciones.label("Regla Vacaciones"),
            ReglasPerfilTransaccional.descuentos_voluntarios.label("Regla Desc. Voluntarios"),
            ReglasPerfilTransaccional.otros.label("Regla Otros"),
            ReglasPerfilTransaccional.cupo.label("Cupo (%)")
        )
                 .outerjoin(Cliente, Cliente.cuil == PerfilTransaccional.cuil_cliente)
                 .outerjoin(Empleador, Empleador.id == Cliente.empleador_id)
                 .outerjoin(SocioComercial, SocioComercial.id == Empleador.socio_comercial_id)
                 .outerjoin(ReglasPerfilTransaccional, ReglasPerfilTransaccional.id_socio_comercial == SocioComercial.id))
        
        if periodo:
            query = query.filter(PerfilTransaccional.periodo <= periodo.end_time)
        df_perf = pd.read_sql(query.statement, db.get_bind())
        if df_perf.empty:
            df_perf["Base"] = pd.Series(dtype=float)
            df_perf["Cuota Afectable"] = pd.Series(dtype=float)
        else:
            df_perf[["Base", "Cuota Afectable"]] = df_perf.apply(lambda row:
                cuota_afectable(row["C.U.I.L."], row["Periodo"], row["Socio ID"]),
                axis=1,
                result_type="expand")

    finally:
        db.close()

    import os
    if save:
        path = select_directory()
        if path:
            # Eliminar timezones de las columnas datetime porque Excel no los soporta
            for df in [df_clt, df_riesgo_clt, df_repet, df_perf]:
                for col in df.select_dtypes(include=['datetimetz']).columns:
                    df[col] = df[col].dt.tz_localize(None)

            file_name = f"reporte_uif_{year}_{month if month else 'anual'}.xlsx"
            file_path = os.path.join(path, file_name)
            with pd.ExcelWriter(file_path) as writer:
                df_clt.to_excel(writer, sheet_name="Clientes", index=False)
                df_riesgo_clt.to_excel(writer, sheet_name="Riesgo Cliente", index=False)
                df_repet.to_excel(writer, sheet_name="Repet Audit Log", index=False)
                df_perf.to_excel(writer, sheet_name="Perfil Transaccional", index=False)

    return df_clt, df_riesgo_clt, df_repet, df_perf