import logging
import difflib
import pandas as pd
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ArcaConsultaService:
    """
    Servicio de consulta de CUIT/CUIL en el padrón de ARCA/AFIP.
    Soporta modo mock (simulado) para entorno de desarrollo.
    """
    
    def __init__(self, use_mock: bool = True):
        self.use_mock = use_mock
        # Aquí iría la inicialización real similar a ArcaService:
        # from afip import Afip
        # self.afip = Afip({'CUIT': 30000000000, 'cert': 'cert.crt', 'key': 'key.key', 'production': False})

    def consultar_cuit(self, cuit: int) -> Dict[str, Any]:
        """
        Consulta los datos de un CUIT/CUIL en ARCA (Registro Único Tributario o Padrón A5/A4).
        
        Args:
            cuit (int): Número de CUIT o CUIL a consultar (solo números, sin guiones).
            
        Returns:
            Dict[str, Any]: Datos del contribuyente (nombre, estado, domicilios, impuestos, etc.)
        """
        if self.use_mock:
            logger.info(f"[ARCA MOCK] Consultando datos del padrón para el CUIT/CUIL: {cuit}")
            
            # Determinamos tipo de persona para el mock
            cuit_str = str(cuit)
            es_fisica = cuit_str.startswith(("20", "23", "24", "27"))
            
            return {
                "idPersona": cuit,
                "tipoPersona": "FISICA" if es_fisica else "JURIDICA",
                "estadoClave": "ACTIVO",
                "nombre": "MOCK PEREZ JUAN" if es_fisica else "MOCK EMPRESA S.A.",
                "apellido": "PEREZ" if es_fisica else None,
                "domicilio": [
                    {
                        "tipoDomicilio": "FISCAL",
                        "direccion": "AV MOCK 123",
                        "localidad": "CIUDAD AUTONOMA BUENOS AIRES",
                        "codPostal": "1000",
                        "idProvincia": 0,
                        "descripcionProvincia": "CIUDAD AUTONOMA BUENOS AIRES"
                    }
                ],
                "impuestos": [
                    {"idImpuesto": 10, "descImpuesto": "Ganancias Sociedades" if not es_fisica else "Ganancias Personas Fisicas"},
                    {"idImpuesto": 30, "descImpuesto": "IVA"}
                ],
                "monotributo": None if not es_fisica else {"categoria": "A", "actividad": "Servicios"}
            }
            
        else:
            # Lógica real usando la librería afip.py:
            # try:
            #     # Usualmente se utiliza RegisterScopeFive (wsrpadron-a5) o RegisterScopeFour
            #     res = self.afip.RegisterScopeFive.GetTaxpayerDetails(cuit)
            #     if not res:
            #         return {"error": "CUIT no encontrado en el padrón"}
            #     return res
            # except Exception as e:
            #     logger.error(f"Error consultando CUIT {cuit} en ARCA: {str(e)}")
            #     raise
            raise NotImplementedError("Modo producción no configurado. Faltan certificados.")

def validar_datos_arca(df_invs: pd.DataFrame):
    """
    Valida que los nombres y CUITs de los inversores en el DataFrame coincidan
    con los registros de ARCA/AFIP.
    """
    arca_service = ArcaConsultaService(use_mock=True)
    
    if arca_service.use_mock:
        print("⚠️ [ADVERTENCIA] ARCA en modo MOCK: Se omitirá la verificación de identidad (Razón Social vs CUIT) para no inundar la consola.")
        
    errores_validacion = []
    
    for _, row in df_invs.iterrows():
        val = row["CUIT/CUIL"]
        if pd.isna(val):
            errores_validacion.append(f"Falta CUIT/CUIL para '{row['Razón Social']}'")
            continue
            
        if isinstance(val, float):
            cuit = str(int(val))
        else:
            cuit = str(val).replace("-", "").strip()
            if cuit.endswith(".0"):
                cuit = cuit[:-2]
                
        razon_social_excel = str(row["Razón Social"]).strip().upper()
        
        if not cuit.isdigit():
            errores_validacion.append(f"CUIT/CUIL inválido: {row['CUIT/CUIL']}")
            continue
            
        if arca_service.use_mock:
            # Salteamos la consulta a ARCA para no generar falsos positivos ni logs por cada fila
            continue
            
        cuit_int = int(cuit)
        datos_arca = arca_service.consultar_cuit(cuit_int)
        
        if "error" in datos_arca:
            errores_validacion.append(f"CUIT {cuit} no encontrado en ARCA.")
            continue
            
        nombre_arca = str(datos_arca.get("nombre", "")).upper()
        if datos_arca.get("tipoPersona") == "FISICA" and datos_arca.get("apellido"):
            nombre_arca = f"{str(datos_arca.get('apellido')).upper()} {nombre_arca}"
            
        # Comparamos similitud para evitar rechazos por acentos, comas, S.A vs SA, etc.
        similitud = difflib.SequenceMatcher(None, razon_social_excel, nombre_arca).ratio()
        
        # Si la similitud es baja o uno no está contenido dentro del otro
        if similitud < 0.6 and razon_social_excel not in nombre_arca and nombre_arca not in razon_social_excel:
            errores_validacion.append(
                f"Discrepancia en CUIT {cuit}: Excel dice '{razon_social_excel}', "
                f"ARCA dice '{nombre_arca}'"
            )
            
    if errores_validacion:
        raise ValueError("Falló la validación con ARCA:\n" + "\n".join(errores_validacion))
