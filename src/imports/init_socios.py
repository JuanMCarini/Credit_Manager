"""
Commercial Partners Initialization Module
=========================================
Ensures that all commercial partners (originators/buyers) listed in the 
Excel file exist in the database before the main data import proceeds.
"""

import pandas as pd
import warnings
from src.database.models import SocioComercial

def ensure_socios_exist(df_socios: pd.DataFrame):
    """
    Iterates through the provided DataFrame of commercial partners and 
    safely creates them in the database if they do not exist.
    """
    # Verify required columns
    required_cols = ["Razon Social", "CUIT"]
    for col in required_cols:
        if col not in df_socios.columns:
            raise ValueError(f"The 'Socios Comerciales.xlsx' file must contain a '{col}' column.")
    
    # Find max generic CUIT to auto-increment
    from src.database import SessionLocal
    with SessionLocal() as db:
        existing_cuits = [s.cuit for s in db.query(SocioComercial).all() if s.cuit and s.cuit.startswith("5000000")]
        
    if existing_cuits:
        generic_cuit_counter = max([int(c) for c in existing_cuits]) + 1
    else:
        generic_cuit_counter = 50000000001
    
    # Process each row
    for idx, row in df_socios.iterrows():
        razon_social = str(row["Razon Social"]).strip()
        cuit = row["CUIT"]
        
        # Skip rows without a valid name
        if not razon_social or str(razon_social).upper() == 'NAN':
            continue
            
        if pd.isna(cuit) or str(cuit).strip() == "":
            cuit_clean = str(generic_cuit_counter)
            generic_cuit_counter += 1
        else:
            # We clean the CUIT just in case it was typed with hyphens
            cuit_str = str(cuit)
            if cuit_str.endswith(".0"):
                cuit_str = cuit_str[:-2]
            cuit_clean = "".join(filter(str.isdigit, cuit_str))
        try:
            
            # create_socio inherently validates for duplicates and raises ValueError if it exists
            SocioComercial.create_socio(razon_social=razon_social, cuit=cuit_clean)
            print(f"✅ Partner created: {razon_social} (CUIT: {cuit_clean})")
        except ValueError:
            # Safely ignore as it already exists
            pass
        except Exception as e:
            warnings.warn(f"⚠️ Could not create partner '{razon_social}': {e}")
