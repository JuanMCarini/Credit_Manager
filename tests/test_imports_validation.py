import pytest
from datetime import date
from src.database.models import Cliente, Credito, TipoCredito
from src.logic.creditos.origination import LoanOriginator

def test_originate_soft_validation(db_session, dummy_cliente, dummy_socio):
    """
    Test that originate with strict_policy=False will generate observations 
    instead of throwing ValueError when validation fails (e.g. missing fecha_nacimiento).
    """
    originator = LoanOriginator(db_session)
    
    # Intentional lack of data in dummy_cliente for testing the failure mode 
    # (dummy_cliente likely lacks fecha_nacimiento, making it fail policy validation)
    
    credito, observaciones = originator.originate(
        client_cuil=dummy_cliente.cuil,
        capital=50000.0,
        tna_c_iva=0.5,
        term=6,
        partner_id=dummy_socio.id,
        issuance_date=date.today(),
        due_day=28,
        type=TipoCredito.FRANCES,
        commit=False,
        strict_policy=False
    )
    
    # Ensure credit is still returned and valid
    assert credito is not None
    assert credito.capital == 50000.0
    
    # Ensure observations were captured (policy should complain about lack of birth date)
    assert len(observaciones) > 0
    assert any("Política:" in obs for obs in observaciones)

def test_originate_hard_validation(db_session, dummy_cliente, dummy_socio):
    """
    Test that originate with strict_policy=True throws an Exception when validation fails.
    """
    originator = LoanOriginator(db_session)
    
    with pytest.raises(Exception):
        credito = originator.originate(
            client_cuil=dummy_cliente.cuil,
            capital=50000.0,
            tna_c_iva=0.5,
            term=6,
            partner_id=dummy_socio.id,
            issuance_date=date.today(),
            due_day=28,
            type=TipoCredito.FRANCES,
            commit=False,
            strict_policy=True
        )
