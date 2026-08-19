import httpx
import logging
from sqlalchemy.orm import Session
from unidecode import unidecode
from rapidfuzz import process, fuzz
from typing import Dict, Optional

from src.database.models.creditos.repet import RepetPerson, RepetEntity, RepetAuditLog

logger = logging.getLogger(__name__)

# URL base, reemplazar por el path exacto al JSON cuando esté disponible
REPET_JSON_URL = "https://repet.jus.gob.ar/api/v1/personas" # Placeholder
REPET_THRESHOLD = 85.0

def normalize_text(text: str) -> str:
    """Normaliza el texto para búsquedas (minúsculas, sin acentos)."""
    if not text:
        return ""
    return unidecode(text.lower().strip())

async def sync_repet_data(db: Session):
    """Descarga los listados del RePET y actualiza la base de datos."""
    logger.info("Iniciando sincronización con RePET...")
    
    try:
        async with httpx.AsyncClient() as client:
            response_per = await client.get("https://repet.jus.gob.ar/xml/personas.json", timeout=60.0)
            data_per = response_per.json()
            
            response_ent = await client.get("https://repet.jus.gob.ar/xml/entidades.json", timeout=60.0)
            data_ent = response_ent.json()
            
        # Limpiamos tabla actual y repoblamos
        db.query(RepetPerson).delete()
        db.query(RepetEntity).delete()
        
        # Procesar Personas
        for item in data_per:
            names = [
                item.get("FIRST_NAME", ""),
                item.get("SECOND_NAME", ""),
                item.get("THIRD_NAME", ""),
                item.get("FOURTH_NAME", "")
            ]
            full_name = " ".join(n for n in names if n).strip()
            
            documento = None
            docs = item.get("INDIVIDUAL_DOCUMENT", [])
            if docs and isinstance(docs, list):
                for doc in docs:
                    if doc.get("NUMBER"):
                        documento = doc.get("NUMBER")
                        break
            
            if full_name:
                person = RepetPerson(
                    nombre_completo=full_name[:255],
                    nombre_normalizado=normalize_text(full_name)[:255],
                    documento=documento,
                    json_data=str(item)
                )
                db.add(person)
                
            aliases = item.get("INDIVIDUAL_ALIAS", [])
            if aliases and isinstance(aliases, list):
                for alias in aliases:
                    alias_name = alias.get("ALIAS_NAME")
                    if alias_name:
                        person_alias = RepetPerson(
                            nombre_completo=alias_name[:255],
                            nombre_normalizado=normalize_text(alias_name)[:255],
                            documento=documento,
                            json_data=str(item)
                        )
                        db.add(person_alias)
                        
        # Procesar Entidades
        for item in data_ent:
            full_name = item.get("FIRST_NAME", "").strip()
            if full_name:
                entity = RepetEntity(
                    razon_social=full_name[:255],
                    razon_social_normalizada=normalize_text(full_name)[:255],
                    cuit=None,
                    json_data=str(item)
                )
                db.add(entity)
                
            aliases = item.get("ENTITY_ALIAS", [])
            if aliases and isinstance(aliases, list):
                for alias in aliases:
                    alias_name = alias.get("ALIAS_NAME")
                    if alias_name:
                        entity_alias = RepetEntity(
                            razon_social=alias_name[:255],
                            razon_social_normalizada=normalize_text(alias_name)[:255],
                            cuit=None,
                            json_data=str(item)
                        )
                        db.add(entity_alias)

        db.commit()
        logger.info("Sincronización de RePET exitosa. Registros reales descargados.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error sincronizando RePET: {str(e)}")

def screen_person(db: Session, full_name: str, user_id: Optional[int] = None) -> Dict:
    """
    Busca a la persona en la base local del RePET usando Fuzzy Matching.
    Deja registro en la tabla de auditoría.
    """
    target = normalize_text(full_name)
    
    # Extraemos nombres normalizados
    personas = db.query(RepetPerson.id, RepetPerson.nombre_normalizado).all()
    db_names = {p.id: p.nombre_normalizado for p in personas}
    
    if not db_names:
        logger.warning("La tabla de RePET está vacía. Ejecute sync_repet_data().")
        return {"status": "CLEAN", "score": 0, "message": "Listado RePET vacío."}
        
    best_match = process.extractOne(
        target,
        db_names,
        scorer=fuzz.token_set_ratio,
        score_cutoff=REPET_THRESHOLD
    )
    
    is_match = False
    score = 0.0
    matched_id = None
    status = "CLEAN"
    message = "Sin coincidencias en RePET."
    
    if best_match:
        match_string, score, matched_id = best_match
        is_match = True
        status = "ALERT"
        message = "¡Coincidencia encontrada en RePET!"
        
    # Guardamos Pista de Auditoría
    audit_log = RepetAuditLog(
        searched_name=full_name,
        is_match=is_match,
        match_score=score,
        matched_record_id=matched_id,
        user_id=user_id
    )
    db.add(audit_log)
    db.commit()
    
    return {
        "status": status,
        "score": score,
        "message": message,
        "matched_id": matched_id
    }
