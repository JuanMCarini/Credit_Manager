"""
Module: amortization.py
Description: Fixed financial logic for loan amortization with forced due dates.
Author: Juan Martín Carini
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
        =============================================================================
        Method: generate_french_schedule
        Description: Generates a list of Cuota objects with forced payment days.
                     Ensures strict cent-level consistency by rounding the total PMT
                     and deriving capital amortization by subtraction. Casts numpy
                     types to native Python floats to prevent rounding exceptions.
        =============================================================================
        """
        monthly_rate_c_iva = tna_c_iva * 30 / 365

        # 1. Cast the theoretical PMT to a native float before rounding
        pmt_teorico = float(abs(npf.pmt(monthly_rate_c_iva, plazo, capital)))
        cuota_fija_total = round(pmt_teorico, 2)

        cuotas_list = []
        remaining_balance = round(float(capital), 2)

        if fecha_emision.day <= dia_corte:
            gracia -= 1

        for i in range(1, plazo + 1):
            # 2. Interest is calculated on the actual remaining balance
            interest_c_iva = float(abs(npf.ipmt(monthly_rate_c_iva, i, plazo, capital)))
            interest_c_iva = round(interest_c_iva, 2)

            # Tax breakdown and rounding
            interest_net = round(interest_c_iva / (1 + tasa_iva), 2)
            iva_amount = round(interest_c_iva - interest_net, 2)
            interest_c_iva_rounded = round(interest_net + iva_amount, 2)

            # 3. Capital is derived by subtraction to square the cents
            principal_amort = round(cuota_fija_total - interest_c_iva_rounded, 2)

            # 4. Final installment adjustment to close the balance at exactly zero
            if i == plazo:
                principal_amort = remaining_balance
                interest_c_iva = cuota_fija_total - principal_amort
                interest_net = round(interest_c_iva / (1 + tasa_iva), 2)
                iva_amount = interest_c_iva - interest_net

            diff = cuota_fija_total - (principal_amort + interest_net + iva_amount)
            diff = round(diff, 2)
            if diff != 0.00:
                raise ValueError(
                    f"\n⚠️ Difference in the installment value no. {i} by $ {diff}."
                )

            target_month = fecha_emision + relativedelta(months=i + gracia)
            try:
                due_date = target_month.replace(day=dia_vencimiento)
            except ValueError:
                due_date = target_month + relativedelta(day=31)

            nueva_cuota = Cuota(
                credito_id=credito_id,
                nro_cuota=i,
                fecha_vencimiento=due_date,
                capital=principal_amort,
                interes=interest_net,
                iva=iva_amount,
            )

            cuotas_list.append(nueva_cuota)
            remaining_balance = round(remaining_balance - principal_amort, 2)

        return cuotas_list
