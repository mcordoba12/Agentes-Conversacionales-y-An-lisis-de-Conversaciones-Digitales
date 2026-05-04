"""
Prompt Injection Detector
Detecta intentos de manipular el agente a través del prompt
"""

import re
from typing import Tuple

# ==============================================================================
# INYECCIÓN DE PROMPTS - KEYWORDS SOSPECHOSAS
# ==============================================================================

INJECTION_KEYWORDS = {
    # Ignorar instrucciones previas
    "ignore": ["ignore previous", "olvida lo anterior", "ignora las instrucciones"],
    "override": ["override", "bypass", "no hagas caso", "no sigas"],

    # Acceso a system prompt
    "system": ["system prompt", "sistema prompt", "instrucciones del sistema", "tu sistema"],

    # Solicitud de información interna
    "reveal": ["cuéntame tu prompt", "show me your", "show your instructions", "cuál es tu prompt"],

    # Intentos de inyección de código
    "code": ["execute code", "ejecuta código", "run python", "eval(", "exec("],

    # Cambio de role/comportamiento
    "roleplay": ["eres ahora", "ahora eres", "finge que eres", "act as if you are"],

    # Exfiltración de datos
    "exfiltrate": ["envía datos a", "sube información a", "send data to", "leak"],

    # SQL Injection patterns
    "sql": ["sql injection", "union select", "drop table", "delete from", "insert into"],
}

INJECTION_PATTERNS = [
    # Common prompt injection patterns
    r"ignore.*previous|previous.*ignore",
    r"forget.*instruction|instruction.*forget",
    r"you.*are.*actually|actually.*you.*are",
    r"let's.*pretend|pretend.*we",
    r"new.*instruction|instruction.*new",
    r"from.*now.*on|now.*on.*you",
    r"disregard.*prior|prior.*disregard",
    r"instead.*follow|follow.*instead",

    # Spanish patterns
    r"olvida.*anterior|anterior.*olvida",
    r"ya.*no.*sigas|sigas.*ya",
    r"ahora.*eres|eres.*ahora",
    r"finge.*que|que.*finge",
    r"desde.*ahora|ahora.*desde",
]

# ==============================================================================
# DETECCIÓN DE INYECCIONES
# ==============================================================================

def detect_prompt_injection(text: str) -> bool:
    """
    Detectar si el texto contiene un intento de prompt injection

    Args:
        text: Texto a analizar

    Returns:
        True si se detecta inyección, False si es seguro
    """
    text_lower = text.lower().strip()

    # Verificar keywords sospechosas
    for category, keywords in INJECTION_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return True

    # Verificar patrones
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True

    return False


def get_injection_severity(text: str) -> str:
    """
    Evaluar la severidad de un intento de inyección

    Args:
        text: Texto a analizar

    Returns:
        "LOW" | "MEDIUM" | "HIGH" | "SAFE"
    """
    if not detect_prompt_injection(text):
        return "SAFE"

    text_lower = text.lower()

    # HIGH: SQL injection, code execution
    if any(pattern in text_lower for pattern in ["sql", "exec", "eval", "drop table", "union select"]):
        return "HIGH"

    # HIGH: Multiple suspicious patterns
    suspicious_count = sum(1 for pattern in INJECTION_PATTERNS if re.search(pattern, text_lower))
    if suspicious_count >= 2:
        return "HIGH"

    # MEDIUM: Role-switching or system prompt requests
    if any(kw in text_lower for kw in ["system prompt", "ahora eres", "eres ahora", "your instructions"]):
        return "MEDIUM"

    # LOW: Single suspicious keyword
    return "LOW"


# ==============================================================================
# RATE LIMITING (Anti-Abuse)
# ==============================================================================

class RateLimiter:
    """Rate limiter para prevenir abuso"""

    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """
        Args:
            max_requests: Máximo de requests por ventana
            time_window: Ventana de tiempo en segundos
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}  # {user_id: [(timestamp, is_injection), ...]}

    def is_allowed(self, user_id: str) -> Tuple[bool, str]:
        """
        Verificar si el usuario puede hacer una request

        Returns:
            (allowed: bool, reason: str)
        """
        import time

        now = time.time()

        if user_id not in self.requests:
            self.requests[user_id] = []

        # Limpiar requests antiguos
        self.requests[user_id] = [
            (ts, is_inj) for ts, is_inj in self.requests[user_id]
            if now - ts < self.time_window
        ]

        # Contar intentos de inyección en la ventana
        injection_count = sum(1 for _, is_inj in self.requests[user_id] if is_inj)

        if injection_count >= 3:
            return False, "Too many injection attempts. Access temporarily blocked."

        # Contar total de requests
        if len(self.requests[user_id]) >= self.max_requests:
            return False, "Rate limit exceeded. Please wait a moment."

        return True, "OK"

    def record(self, user_id: str, is_injection: bool = False) -> None:
        """Registrar una request"""
        import time
        now = time.time()

        if user_id not in self.requests:
            self.requests[user_id] = []

        self.requests[user_id].append((now, is_injection))
