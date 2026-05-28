from datetime import date
import pytest
from src.logic.amortization import AmortizationEngine
from src.database.models import Cuota


def test_generate_french_schedule_standard():
    """
    Test a standard schedule generation.
    Checks that all returned items are Cuota instances, the plazo count is correct,
    and the sum of capital equals the original borrowed amount.
    """
    capital = 10000.00
    tna = 0.60
    plazo = 12
    fecha_emision = date(2026, 5, 10)
    
    schedule = AmortizationEngine.generate_french_schedule(
        credito_id=1,
        capital=capital,
        tna_c_iva=tna,
        plazo=plazo,
        fecha_emision=fecha_emision,
        dia_vencimiento=28,
    )
    
    assert len(schedule) == plazo
    assert all(isinstance(c, Cuota) for c in schedule)
    
    # Capital should sum up to exactly the original amount
    total_capital = sum(c.capital for c in schedule)
    assert round(total_capital, 2) == capital


def test_generate_french_schedule_rounding():
    """
    Test with odd capital and rates to check that the engine successfully
    reaches exactly zero balance at the final installment.
    """
    capital = 33333.33
    tna = 0.53421
    plazo = 5
    fecha_emision = date(2026, 5, 15)
    
    schedule = AmortizationEngine.generate_french_schedule(
        credito_id=1,
        capital=capital,
        tna_c_iva=tna,
        plazo=plazo,
        fecha_emision=fecha_emision,
        dia_vencimiento=28,
    )
    
    total_capital = sum(c.capital for c in schedule)
    assert round(total_capital, 2) == capital


def test_generate_french_schedule_forced_date_logic():
    """
    Test that the due dates of installments are forced correctly to the 28th
    of the target months.
    """
    capital = 50000.00
    tna = 0.45
    plazo = 3
    
    # Scenario A: fecha_emision day <= dia_corte (day 15 <= 28)
    # gracia will be decremented by 1 (default grace=2 becomes 1)
    # First installment should be emission + 1 + 1 month = emission + 2 months
    fecha_emision_a = date(2026, 5, 15)
    schedule_a = AmortizationEngine.generate_french_schedule(
        credito_id=1,
        capital=capital,
        tna_c_iva=tna,
        plazo=plazo,
        fecha_emision=fecha_emision_a,
        dia_vencimiento=28,
        gracia=2,
        dia_corte=28,
    )
    
    # May + (1 + 1) = July
    assert schedule_a[0].fecha_vencimiento == date(2026, 7, 28)
    assert schedule_a[1].fecha_vencimiento == date(2026, 8, 28)
    assert schedule_a[2].fecha_vencimiento == date(2026, 9, 28)
    
    # Scenario B: fecha_emision day > dia_corte (day 29 > 28)
    # gracia is kept at 2.
    # First installment should be emission + 2 + 1 month = emission + 3 months
    fecha_emision_b = date(2026, 5, 29)
    schedule_b = AmortizationEngine.generate_french_schedule(
        credito_id=1,
        capital=capital,
        tna_c_iva=tna,
        plazo=plazo,
        fecha_emision=fecha_emision_b,
        dia_vencimiento=28,
        gracia=2,
        dia_corte=28,
    )
    # May + (2 + 1) = August
    assert schedule_b[0].fecha_vencimiento == date(2026, 8, 28)
