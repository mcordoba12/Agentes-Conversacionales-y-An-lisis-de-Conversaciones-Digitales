"""
PII (Personally Identifiable Information) Detector
Detecta y enmascara datos sensibles: emails, teléfonos, nombres
"""

import re
from typing import List, Dict, Tuple

# ==============================================================================
# PATRONES DE DATOS SENSIBLES
# ==============================================================================

# Email regex (basic)
EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

# Teléfono (varios formatos)
PHONE_PATTERNS = [
    r'\+?1?\s*-?\.?\(?(\d{3})\)?-?\.?\s?(\d{3})-?\.?\s?(\d{4})',  # (123) 456-7890
    r'\b(\d{10})\b',  # 1234567890
    r'\+\d{1,3}\s?\d{1,14}',  # +1234567890
]

# Cédula/ID patterns (Colombia, etc.)
ID_PATTERNS = [
    r'\b(\d{7,10})\b',  # 7-10 digits (ID/Cédula)
]

# Nombres de usuarios conocidos del dataset
# Estos se cargan dinámicamente desde el parquet
KNOWN_USERNAMES = set()


# ==============================================================================
# FUNCIONES DE DETECCIÓN
# ==============================================================================

def detect_pii(text: str) -> Dict[str, List[str]]:
    """
    Detectar tipos de PII en el texto

    Args:
        text: Texto a analizar

    Returns:
        Dict con tipos de PII encontrados y sus valores
    """
    pii_found = {
        "emails": [],
        "phones": [],
        "ids": [],
        "usernames": [],
    }

    # Detectar emails
    emails = re.findall(EMAIL_PATTERN, text)
    pii_found["emails"] = list(set(emails))

    # Detectar teléfonos
    for phone_pattern in PHONE_PATTERNS:
        phones = re.findall(phone_pattern, text)
        # Flatten tuples y normalizar
        for phone_group in phones:
            if isinstance(phone_group, tuple):
                phone = "".join(str(p) for p in phone_group if p)
                if len(phone) >= 10:
                    pii_found["phones"].append(phone)
            else:
                if len(str(phone_group)) >= 10:
                    pii_found["phones"].append(str(phone_group))

    pii_found["phones"] = list(set(pii_found["phones"]))

    # Detectar cédulas/IDs (7-10 dígitos)
    for id_pattern in ID_PATTERNS:
        ids = re.findall(id_pattern, text)
        for id_num in ids:
            if len(str(id_num)) >= 7:
                pii_found["ids"].append(str(id_num))

    pii_found["ids"] = list(set(pii_found["ids"]))

    # Detectar nombres de usuarios conocidos (ignorar strings vacíos)
    for username in KNOWN_USERNAMES:
        if username.strip() and username.lower() in text.lower():
            pii_found["usernames"].append(username)

    return pii_found


def mask_sensitive_data(text: str, replace_char: str = "*") -> Tuple[str, Dict[str, List[str]]]:
    """
    Enmascarar datos sensibles en el texto

    Args:
        text: Texto a procesar
        replace_char: Carácter para enmascarar

    Returns:
        (texto_enmascarado, pii_encontrado)
    """
    masked_text = text
    pii_found = detect_pii(text)

    # Enmascarar emails
    for email in pii_found["emails"]:
        # Mostrar inicio y final: a***@example.com
        parts = email.split("@")
        if len(parts) == 2:
            local, domain = parts
            masked_email = f"{local[0]}{'*' * (len(local)-2)}@{domain}"
            masked_text = masked_text.replace(email, masked_email)
        else:
            masked_text = masked_text.replace(email, email[0] + "*" * (len(email)-2))

    # Enmascarar teléfonos
    for phone in pii_found["phones"]:
        masked_phone = f"***-***-{phone[-4:]}"
        masked_text = masked_text.replace(phone, masked_phone)

    # Enmascarar cédulas/IDs
    for id_num in pii_found["ids"]:
        masked_id = f"***-***-{id_num[-4:]}"
        masked_text = masked_text.replace(id_num, masked_id)

    # Enmascarar nombres de usuario
    for username in pii_found["usernames"]:
        masked_username = f"[USER_{hash(username) % 1000}]"
        masked_text = masked_text.replace(username, masked_username)

    return masked_text, pii_found


def load_usernames_from_loader(loader) -> None:
    """
    Cargar nombres de usuarios conocidos del dataset
    Llamar al inicializar el agente

    Args:
        loader: DataLoader instance
    """
    global KNOWN_USERNAMES

    try:
        if hasattr(loader, "df") and loader.df is not None:
            if "author" in loader.df.columns:
                KNOWN_USERNAMES = set(loader.df["author"].dropna().unique())
    except Exception as e:
        print(f"Warning: Could not load usernames from dataset: {e}")


# ==============================================================================
# ESTADÍSTICAS DE PII
# ==============================================================================

def get_pii_statistics(detections: List[Dict]) -> Dict:
    """
    Generar estadísticas sobre PII detectado en múltiples texts

    Args:
        detections: Lista de resultados de detect_pii()

    Returns:
        Estadísticas agregadas
    """
    total_emails = sum(len(d.get("emails", [])) for d in detections)
    total_phones = sum(len(d.get("phones", [])) for d in detections)
    total_usernames = sum(len(d.get("usernames", [])) for d in detections)

    return {
        "total_pii_found": total_emails + total_phones + total_usernames,
        "emails": total_emails,
        "phones": total_phones,
        "usernames": total_usernames,
        "texts_with_pii": sum(1 for d in detections if any(d.values())),
    }
