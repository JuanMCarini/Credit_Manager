"""
Module: amortization.py
Description: Fixed financial logic for loan amortization with forced due dates.
Author: Juan Martín Carini
Date: 2026-05-11
"""

from datetime import date

import numpy_financial as npf
from dateutil.relativedelta import relativedelta

from src.database.models import Cuota


class AmortizationEngine:
    """
    Engine to calculate French System amortization schedules with forced installment days.
    """

    @staticmethod
    def generate_french_schedule(
        credito_id: int,
        capital: float,
        tna_c_iva: float,
        plazo: int,
        fecha_emision: date,
        dia_vencimiento: int = 28,
        gracia: int = 2,
        tasa_iva: float = 0.21,
        dia_corte: int = 28,
    ):
        """
        Generates a list of Cuota objects with forced payment days (e.g., every 28th).
        """
        # 1. FIX: Ensure rate is decimal for numpy_financial (tna * 30 /365)
        # Periodic monthly rate with VAT
        monthly_rate_c_iva = tna_c_iva * 30 / 365

        # 2. Calculate fixed PMT
        pmt_total = abs(npf.pmt(monthly_rate_c_iva, plazo, capital))

        cuotas_list = []
        remaining_balance = capital

        if fecha_emision.day <= dia_corte:
            gracia -= 1

        for i in range(1, plazo + 1):
            interest_c_iva = abs(npf.ipmt(monthly_rate_c_iva, i, plazo, capital))
            interest_net = interest_c_iva / (1 + tasa_iva)
            iva_amount = interest_c_iva - interest_net

            principal_amort = pmt_total - interest_c_iva

            if i == plazo:
                principal_amort = remaining_balance

            # 3. FIX: Force due date to dia_vencimiento (default 28)
            target_month = fecha_emision + relativedelta(months=i + gracia)
            try:
                # Intentamos forzar el día elegido (ej: 28)
                due_date = target_month.replace(day=dia_vencimiento)
            except ValueError:
                # Caso borde: si el mes no tiene ese día, usamos el último día del mes
                due_date = target_month + relativedelta(day=31)

            nueva_cuota = Cuota(
                credito_id=credito_id,
                nro_cuota=i,
                fecha_vencimiento=due_date,
                capital=round(principal_amort, 2),
                interes=round(interest_net, 2),
                iva=round(iva_amount, 2),
            )

            cuotas_list.append(nueva_cuota)
            remaining_balance -= principal_amort

        return cuotas_list
