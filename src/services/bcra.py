from src.utils.files import select_file
import pandas as pd
import time
import logging
import json
import random
from curl_cffi import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Creamos una sesión persistente para mantener las cookies y la conexión Keep-Alive.
# Esto es vital porque los firewalls asignan una cookie de seguimiento en la primera 
# visita y bloquean si ven peticiones aisladas constantes sin devolver esa cookie.
def crear_sesion_bcra() -> requests.Session:
    """
    Crea una nueva sesión con curl_cffi usando un impersonate aleatorio
    y realiza una petición previa para obtener cookies iniciales.
    """
    navegadores = ["chrome110", "chrome116", "chrome120"]
    sesion = requests.Session(impersonate=random.choice(navegadores))
    
    try:
        # Petición pre-flight a la home CON LOS HEADERS POR DEFECTO del navegador
        # para capturar cookies (ej. WAF) sin levantar sospechas (Accept: text/html...).
        sesion.get("https://www.bcra.gob.ar/", timeout=15)
        time.sleep(random.uniform(2.0, 4.0)) # Pausa para evitar ráfagas (WAF)
    except Exception as e:
        logging.debug(f"Pre-flight request falló: {e}")

    # AHORA SÍ, actualizamos los headers para que la API nos responda JSON
    sesion.headers.update({
        "Accept": "application/json",
        "Referer": "https://www.bcra.gob.ar/",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
    })
        
    return sesion

session_bcra = crear_sesion_bcra()

def consultar_cuit_api(cuit: str) -> dict:
    """
    Consulta la API del BCRA utilizando curl_cffi con una sesión persistente.
    """
    url = f"https://api.bcra.gob.ar/CentralDeDeudores/v1.0/Deudas/{cuit}"
    
    try:
        # Usamos la sesión global en vez de requests.get()
        respuesta = session_bcra.get(url, timeout=15)
        
        if respuesta.status_code not in (200, 404):
            return {"CUIT": cuit, "Estado": f"Error HTTP {respuesta.status_code}", "Datos_API": None, "Error": respuesta.text[:200]}
            
        texto_respuesta = respuesta.text.strip()
        
        if not texto_respuesta:
            return {"CUIT": cuit, "Estado": "Sin Deudas / Vacio", "Datos_API": None, "Error": None}
            
        try:
            datos = respuesta.json()
            status_api = datos.get("status")
            
            if status_api == 200:
                return {"CUIT": cuit, "Estado": "Con Deudas", "Datos_API": datos, "Error": None}
            elif status_api == 404:
                return {"CUIT": cuit, "Estado": "Sin Deudas", "Datos_API": None, "Error": None}
            else:
                return {"CUIT": cuit, "Estado": f"Error API {status_api}", "Datos_API": None, "Error": str(datos)}
                
        except json.JSONDecodeError:
            return {"CUIT": cuit, "Estado": "Error Decodificando JSON", "Datos_API": None, "Error": texto_respuesta[:100]}
            
    except requests.errors.RequestsError as e:
        return {"CUIT": cuit, "Estado": "Error de Red (curl_cffi)", "Datos_API": None, "Error": str(e)}
    except Exception as e:
        return {"CUIT": cuit, "Estado": "Error Desconocido", "Datos_API": None, "Error": str(e)}


def consultar_con_reintentos(cuit: str, max_reintentos=10) -> dict:
    """
    Envoltorio inteligente que reintenta la consulta automáticamente si 
    el BCRA nos bloquea temporalmente por superar el límite de peticiones (429) o corta la red.
    """
    global session_bcra
    tiempo_total = 0
    max_tiempo = 20 * 60  # 20 minutos en segundos
    
    for intento in range(max_reintentos):
        respuesta = consultar_cuit_api(str(cuit))
        estado = respuesta.get("Estado")
        
        # Si la consulta fue exitosa (Con Deudas o Sin Deudas), devolvemos el resultado
        if estado in ["Con Deudas", "Sin Deudas", "Sin Deudas / Vacio"]:
            return respuesta
            
        # Aumenta 1 minuto por cada intento (60s, 120s, 180s...)
        espera = (intento + 1) * 60
        
        if tiempo_total + espera > max_tiempo:
            logging.error(f"❌ Imposible consultar CUIT {cuit}: se alcanzaría el límite de 20 min de espera total.")
            return respuesta
            
        logging.warning(f"⚠️ Bloqueo en CUIT {cuit} ({estado}). Intento {intento+1}. Esperando {espera}s...")
        time.sleep(espera) 
        tiempo_total += espera
        
        # Renovamos la sesión criptográfica para borrar cookies "marcadas" por el firewall
        try:
            session_bcra.close()
        except Exception:
            pass
        session_bcra = crear_sesion_bcra()
        logging.info(f"🔄 Sesión reseteada tras el bloqueo. (Tiempo acumulado: {tiempo_total // 60} min)")
        
    # Si superamos los reintentos, devolvemos la última respuesta fallida
    logging.error(f"❌ Imposible consultar CUIT {cuit} después de {max_reintentos} intentos.")
    return respuesta


def procesar_respuesta_bcra(resultado_api: dict) -> list:
    """
    Toma el diccionario crudo devuelto por la API y lo 'aplana' 
    en una lista de diccionarios, ideal para un DataFrame.
    """
    filas = []
    
    # Si hubo error o no tiene deudas, guardamos al menos el registro vacío
    if resultado_api.get("Estado") != "Con Deudas" or not resultado_api.get("Datos_API"):
        filas.append({
            "cuit": resultado_api.get("CUIT"),
            "denominacion": None,
            "estado_consulta": resultado_api.get("Estado"),
            "error_consulta": resultado_api.get("Error"),
            "periodo": None,
            "entidad": None,
            "situacion": None,
            "monto": None,
            "dias_atraso": None
        })
        return filas

    # Si tiene deudas, extraemos los datos
    datos = resultado_api["Datos_API"]["results"]
    cuit = datos.get("identificacion")
    denominacion = datos.get("denominacion")
    
    for periodo_data in datos.get("periodos", []):
        periodo = periodo_data.get("periodo")
        
        for entidad_data in periodo_data.get("entidades", []):
            filas.append({
                "cuit": cuit,
                "denominacion": denominacion,
                "estado_consulta": resultado_api.get("Estado"),
                "error_consulta": None,
                "periodo": periodo,
                "entidad": entidad_data.get("entidad"),
                "situacion": entidad_data.get("situacion"),
                "monto": entidad_data.get("monto"),
                "dias_atraso": entidad_data.get("diasAtrasoPago")
            })
            
    return filas


def obtener_datos_bcra(path=None):
    """
    Lee un archivo Excel con CUILs, consulta la API del BCRA para cada uno
    y devuelve un DataFrame con los resultados consolidados.
    """
    # 1. Leer el archivo
    # Si no se pasa un 'path' como argumento, se llama a 'select_file()'
    if path is None:
        path = select_file()
        
    df = pd.read_excel(path, sheet_name="CSV PERSONAS", index_col="ID Operación")

    # 2. Obtener CUILs únicos
    cuits_unicos = df["CUIL"].dropna().unique() # Añadido dropna() por si hay celdas vacías
    total_cuits = len(cuits_unicos)

    # --- CALCULO DE TIEMPO ESTIMADO ---
    # Promedio de pausa es 16.5s (random entre 14 y 19) + ~1s de peticion = 17.5s por CUIT
    # Además, cada 8 CUITs se suma 1 minuto extra de descanso, y ~3s extra de pre-flight
    segundos_base = total_cuits * 17.5
    segundos_descanso = (total_cuits // 8) * 60.0
    segundos_rotacion = ((total_cuits - 1) // 8) * 3.0 if total_cuits > 1 else 0
    
    segundos_estimados = int(segundos_base + segundos_descanso + segundos_rotacion)
    
    horas = segundos_estimados // 3600
    minutos = (segundos_estimados % 3600) // 60
    
    if horas > 0:
        tiempo_str = f"{horas} horas y {minutos} minutos"
    else:
        tiempo_str = f"{minutos} minutos y {segundos_estimados % 60} segundos"
        
    print("\n" + "="*55)
    print(f"📊 Se van a procesar {total_cuits} CUITs únicos.")
    print(f"⏱️  Tiempo estimado: ~ {tiempo_str}")
    print(f"   (Incluye pausas aleatorias obligatorias antibloqueo)")
    print("="*55)
    
    confirmacion = input("¿Desea iniciar el proceso? (s/n): ").strip().lower()
    if confirmacion not in ['s', 'si', 'y', 'yes']:
        logging.info("Proceso cancelado por el usuario.")
        return pd.DataFrame() # Retorna DataFrame vacio para no romper si el usuario lo cancela

    logging.info(f"Iniciando consulta de {total_cuits} CUITs/CUILs únicos...")

    datos_totales = []

    # 3. Bucle de consultas
    global session_bcra
    for i, cuil in enumerate(cuits_unicos, start=1):
        logging.info(f"{i}/{total_cuits} - Procesando CUIT: {cuil}")
        
        # ROTACIÓN PROACTIVA DE SESIÓN: Evitamos llegar al límite de 10 peticiones
        if i > 1 and (i - 1) % 8 == 0:
            logging.info("🔄 Rotando sesión (simulando nuevo usuario) para esquivar límite del BCRA...")
            try:
                session_bcra.close()
            except Exception:
                pass
            session_bcra = crear_sesion_bcra()
            
        # Usamos la función con reintentos automáticos
        respuesta = consultar_con_reintentos(cuil)
        
        # Extendemos la lista principal con los registros aplanados
        datos_totales.extend(procesar_respuesta_bcra(respuesta))
        
        # PAUSA BASE DE SEGURIDAD ALEATORIA entre consultas exitosas para no saturar la API
        # Límite irrompible del BCRA por IP: requiere un promedio > 15s para procesos largos
        pausa = random.uniform(14.0, 19.0)
        
        # Descanso extra de 1 minuto cada 8 consultas para enfriar el límite por IP
        if i % 8 == 0:
            logging.info("⏳ Descanso adicional de 1 minuto tras 8 consultas...")
            pausa += 60.0
            
        time.sleep(pausa)

    # 4. Convertir a DataFrame y configurar el índice
    df_bcra = pd.DataFrame(datos_totales)

    # Es buena práctica verificar si quedó vacío antes de setear el index
    if not df_bcra.empty:
        df_bcra.set_index(["cuit"], inplace=True)

    logging.info("¡Proceso finalizado con éxito!")
    
    return df_bcra
