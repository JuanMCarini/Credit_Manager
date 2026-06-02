import pandas as pd
from src.database import SessionLocal, Cliente, SexoEnum, EstadoClienteEnum, Provincia, Empleador
# pyrefly: ignore [missing-import]
from .read import df_clientes, df_inventario


# 2. Agrupar df_inventario para evitar duplicación 1-a-muchos (1 fila por cliente)
df_inventario_grouped = df_inventario.groupby("Id. Cliente")[["Org.", "Sueldo Liquido"]].first()

# 3. Realizar el merge limpio sin filas duplicadas
df_clientes = df_clientes.merge(
    df_inventario_grouped, 
    left_index=True, 
    right_index=True, 
    how="left"
)

# 4. Eliminar duplicados en df_clientes (por CUIL y por DNI)
df_clientes = df_clientes.drop_duplicates(subset=['C.U.I.L.']).drop_duplicates(subset=['D.N.I.'])

# Función para unificar y normalizar el valor de la nacionalidad
def normalize_nacionalidad(val):
    if pd.isna(val):
        return None
    val = str(val).strip().upper()
    if val.startswith("ARG") or val == "AR" or "ARGENTIN" in val:
        return "ARGENTINA"
    if val.startswith("URU") or "URUGUAY" in val:
        return "URUGUAYA"
    if val.startswith("PAR") or "PARAGUAY" in val:
        return "PARAGUAYA"
    if val.startswith("BOL") or "BOLIVIA" in val:
        return "BOLIVIANA"
    if val.startswith("CHI") or "CHILE" in val:
        return "CHILENA"
    if val.startswith("BRA") or val.startswith("BR") or "BRASIL" in val:
        return "BRASILEÑA"
    return val

# Abrir sesión
db = SessionLocal()

# 5. Obtener sets de CUILs y DNI/Documentos ya existentes en la base de datos
existing_cuils = {c.cuil for c in db.query(Cliente.cuil).all()}
existing_docs = {c.documento for c in db.query(Cliente.documento).all()}

# 6. Cargar mapas para provincias y empleadores
provincia_map = {p.nombre.upper().strip(): p.id for p in db.query(Provincia).all()}
empleadores_map = {e.razon_social: e.id for e in db.query(Empleador).all()}

# 7. Registrar nuevos empleadores detectados en 'Org.'
if "Org." in df_clientes.columns:
    orgs_unicos = df_clientes["Org."].dropna().unique()
    for org in orgs_unicos:
        org_clean = str(org).strip().upper()
        if org_clean and org_clean not in empleadores_map:
            nuevo_emp = Empleador(razon_social=org_clean)
            db.add(nuevo_emp)
            db.flush()
            empleadores_map[org_clean] = nuevo_emp.id

new_clients = []
for i, row in df_clientes.iterrows():
    # Limpieza de identificadores
    cuil_clean = "".join(filter(str.isdigit, str(row['C.U.I.L.']))) if pd.notna(row['C.U.I.L.']) else None
    doc_clean = "".join(filter(str.isdigit, str(row['D.N.I.']))) if pd.notna(row['D.N.I.']) else None
    
    # CONTROL DE CLAVE ÚNICA: Omitir vacíos o duplicados en DB / lote actual
    if not cuil_clean or not doc_clean:
        continue
    if cuil_clean in existing_cuils or doc_clean in existing_docs:
        continue
        
    cbu_clean = "".join(filter(str.isdigit, str(row['CBU']))) if pd.notna(row['CBU']) else None
    
    # Mapeo de Enums y Fechas
    sex_raw = str(row['SEXO']).strip().upper() if pd.notna(row['SEXO']) else None
    sex_enum = (
        SexoEnum.MASCULINO if sex_raw in ['M', 'MASCULINO', '1']
        else SexoEnum.FEMENINO if sex_raw in ['F', 'FEMENINO', '2']
        else SexoEnum.OTRO if sex_raw
        else None
    )
    
    estado_raw = str(row['ESTADO']).strip().upper() if pd.notna(row['ESTADO']) else None
    estado_enum = (
        EstadoClienteEnum.ACTIVO if estado_raw in ['ACTIVO', 'A']
        else EstadoClienteEnum.MOROSO if estado_raw in ['MOROSO', 'M']
        else EstadoClienteEnum.INCOBRABLE if estado_raw in ['INCOBRABLE', 'I']
        else EstadoClienteEnum.INACTIVO if estado_raw in ['INACTIVO', 'IN']
        else None
    )
    
    f_nac_ts = pd.to_datetime(row['FECHA NACIMIENTO'], errors='coerce') if pd.notna(row['FECHA NACIMIENTO']) else None
    f_nac = f_nac_ts.date() if pd.notna(f_nac_ts) else None
    
    f_est_ts = pd.to_datetime(row['FECHA ESTADO'], errors='coerce') if pd.notna(row['FECHA ESTADO']) else None
    f_est = f_est_ts.date() if pd.notna(f_est_ts) else None
    
    # Asignación de IDs
    prov_name = str(row['PROVINCIA']).strip().upper() if pd.notna(row['PROVINCIA']) else None
    id_provincia = provincia_map.get(prov_name)
    
    emp_name = str(row['Org.']).strip().upper() if pd.notna(row.get('Org.')) else None
    empleador_id = empleadores_map.get(emp_name) if emp_name else None
    
    # Remuneración (Sueldo Líquido)
    try:
        remuneracion = float(row['Sueldo Liquido']) if pd.notna(row.get('Sueldo Liquido')) else 0.0
    except (ValueError, TypeError):
        remuneracion = 0.0
        
    try:
        calle_nro = int(float(row['CALLE NÚMERO'])) if pd.notna(row['CALLE NÚMERO']) else None
    except (ValueError, TypeError):
        calle_nro = None
        
    new_client = Cliente(
        cuil=cuil_clean,
        documento=doc_clean,
        apellido=str(row['APELLIDO']).strip().upper() if pd.notna(row['APELLIDO']) else "",
        nombre=str(row['NOMBRE']).strip().upper() if pd.notna(row['NOMBRE']) else "",
        fecha_nacimiento=f_nac,
        sexo=sex_enum,
        estado_civil=str(row['ESTADO CIVIL']).strip().upper() if pd.notna(row['ESTADO CIVIL']) else None,
        nacionalidad=normalize_nacionalidad(row['NACIONALIDAD']),
        legajo=str(row['LEGAJO']).strip() if pd.notna(row['LEGAJO']) else None,
        estado=estado_enum,
        fecha_estado=f_est,
        cbu=cbu_clean,
        calle=str(row['CALLE']).strip() if pd.notna(row['CALLE']) else None,
        calle_nro=calle_nro,
        piso=str(row['PISO']).strip() if pd.notna(row['PISO']) else None,
        depto=str(row['DEPTO.']).strip() if pd.notna(row['DEPTO.']) else None,
        id_provincia=id_provincia,
        id_codigo_postal=str(row['CÓDIGO POSTAL']).strip() if pd.notna(row['CÓDIGO POSTAL']) else None,
        localidad=str(row['LOCALIDAD']).strip().upper() if pd.notna(row['LOCALIDAD']) else None,
        telefono=str(row['TELÉFONO']).strip() if pd.notna(row['TELÉFONO']) else None,
        telefono_2=str(row['CELULAR']).strip() if pd.notna(row['CELULAR']) else None,
        mail=str(row['E-MAIL']).strip() if pd.notna(row['E-MAIL']) else None,
        remuneracion=remuneracion,
        empleador_id=empleador_id
    )
    new_clients.append(new_client)
    
    # Evitar colisiones en memoria
    existing_cuils.add(cuil_clean)
    existing_docs.add(doc_clean)

# Persistencia
db.add_all(new_clients)
db.commit()
db.close()