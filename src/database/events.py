from sqlalchemy.event import listens_for
from sqlalchemy.orm import Session
from datetime import datetime
from src.database.models import Cobranza, Cuota, Credito, EstadoCuota, TipoCobranzaEnum

# Umbral máximo permitido para considerar una diferencia como "error de redondeo"
ROUNDING_THRESHOLD = 0.05 

@listens_for(Session, "before_flush")
def auto_adjust_rounding_errors(session, flush_context, instances):
    """
    Trigger de aplicación que busca diferencias de redondeo inferiores al umbral
    después de aplicar cobranzas, y genera una cobranza correctora automática.
    """

    # 1. Identificar qué cuotas fueron afectadas por nuevas/modificadas cobranzas en este flush
    affected_cuotas_ids = set()
    
    # Combinamos session.new y session.dirty para buscar cobranzas
    pending_objects = session.new | session.dirty
    
    for obj in pending_objects:
        if isinstance(obj, Cobranza):
            if obj.cuota_id is not None:
                affected_cuotas_ids.add(obj.cuota_id)
            elif obj.cuota is not None and obj.cuota.id is not None:
                affected_cuotas_ids.add(obj.cuota.id)

    # Descartar None en caso de objetos nuevos sin ID persistido aún
    affected_cuotas_ids.discard(None)

    if not affected_cuotas_ids:
        return

    # 2. Procesar cada cuota afectada
    for cuota_id in affected_cuotas_ids:
        # Obtenemos la cuota desde la sesión
        if hasattr(session, "get"):
            cuota = session.get(Cuota, cuota_id)
        else:
            cuota = session.query(Cuota).filter(Cuota.id == cuota_id).first()
            
        if not cuota or cuota.estado == EstadoCuota.NO_COMPRADA:
            continue

        # --- SINCRONIZACIÓN DE MEMORIA ---
        # Aseguramos que cuota.cobranzas tenga las cobranzas pendientes que están en la sesión
        # pero que aún no se han impactado en la base de datos (evitando que el lazy-load las ignore).
        for obj in pending_objects:
            if isinstance(obj, Cobranza) and (obj.cuota_id == cuota_id or obj.cuota == cuota):
                if obj not in session.deleted and obj not in cuota.cobranzas:
                    cuota.cobranzas.append(obj)

        # Evitamos loops si ya existe o se está agregando un ajuste de redondeo para esta cuota
        ya_tiene_ajuste = any(
            getattr(c.tipo_cobranza, "value", c.tipo_cobranza) == "AJUSTE" or getattr(c, "_is_rounding_adjustment", False)
            for c in cuota.cobranzas
        )
        if ya_tiene_ajuste:
            continue

        # 3. Calcular totales esperados de la cuota
        esperado_cap = round(cuota.capital, 2)
        esperado_int = round(cuota.interes, 2)
        esperado_iva = round(cuota.iva, 2)
        esperado_total = round(esperado_cap + esperado_int + esperado_iva, 2)

        # 4. Calcular el acumulado cobrado usando la relación ya sincronizada
        cobrado_cap = round(sum(c.capital for c in cuota.cobranzas if c not in session.deleted), 2)
        cobrado_int = round(sum(c.interes for c in cuota.cobranzas if c not in session.deleted), 2)
        cobrado_iva = round(sum(c.iva for c in cuota.cobranzas if c not in session.deleted), 2)
        cobrado_total = round(cobrado_cap + cobrado_int + cobrado_iva, 2)

        # 5. Calcular la diferencia residual
        dif_total = round(esperado_total - cobrado_total, 2)

        # Si el error está dentro del umbral de redondeo aceptado (ej: entre -0.05 y 0.05)
        if 0 < abs(dif_total) <= ROUNDING_THRESHOLD:
            dif_cap = round(esperado_cap - cobrado_cap, 2)
            dif_int = round(esperado_int - cobrado_int, 2)
            dif_iva = round(esperado_iva - cobrado_iva, 2)

            # Determinamos la fecha del ajuste
            fecha_ajuste = datetime.today().date()
            valid_dates = [c.fecha for c in cuota.cobranzas if c.fecha]
            if valid_dates:
                fecha_ajuste = max(valid_dates)

            # 6. Crear la cobranza correctora
            cobranza_ajuste = Cobranza(
                tipo_cobranza=TipoCobranzaEnum.AJUSTE,
                capital=dif_cap,
                interes=dif_int,
                iva=dif_iva,
                fecha=fecha_ajuste
            )
            # Flag temporal en memoria para evitar procesamiento recursivo
            cobranza_ajuste._is_rounding_adjustment = True
            
            # Asociamos a la relación para que cuota.cobranzas lo contenga
            cuota.cobranzas.append(cobranza_ajuste)
            
            # 7. Forzar la actualización de los estados en la entidad
            # Esto modificará el estado de la cuota a CANCELADA y actualizará el crédito
            cuota.actualizar_estado(fecha_ajuste)
            if cuota.credito:
                cuota.credito.actualizar_estado()