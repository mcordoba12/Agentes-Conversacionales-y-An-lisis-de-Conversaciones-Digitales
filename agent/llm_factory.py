"""
LLM Factory — Phase 5: Transfer Learning
Crea el LLM según el provider configurado (openai | ollama)
"""

import config
from langchain_core.language_models.chat_models import BaseChatModel


def create_llm(
    provider: str = None,
    model: str = None,
    temperature: float = None
) -> BaseChatModel:
    """
    Factory: crea el LLM según el provider configurado

    Args:
        provider: "openai" | "ollama" (default: config.LLM_PROVIDER)
        model: nombre del modelo (default: del config según provider)
        temperature: temperatura (default: config.LLM_TEMPERATURE)

    Returns:
        BaseChatModel instancia lista para usar
    """
    provider = provider or config.LLM_PROVIDER
    temperature = temperature if temperature is not None else config.LLM_TEMPERATURE

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        model = model or config.LLM_MODEL
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=config.OPENAI_API_KEY
        )

    elif provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            raise ImportError(
                "langchain-ollama no instalado. Ejecuta: pip install langchain-ollama"
            )
        model = model or config.OLLAMA_MODEL
        return ChatOllama(
            model=model,
            temperature=temperature,
            base_url=config.OLLAMA_BASE_URL
        )

    else:
        raise ValueError(
            f"Provider desconocido: '{provider}'. Valores válidos: openai, ollama"
        )


def get_provider_info() -> dict:
    """Retorna info del provider actual para mostrar en CLI"""
    provider = config.LLM_PROVIDER

    if provider == "openai":
        return {
            "provider": "openai",
            "model": config.LLM_MODEL,
            "temperature": config.LLM_TEMPERATURE,
            "cost_input": "$0.15 / 1M tokens",
            "cost_output": "$0.60 / 1M tokens",
            "local": False,
        }
    elif provider == "ollama":
        return {
            "provider": "ollama",
            "model": config.OLLAMA_MODEL,
            "temperature": config.LLM_TEMPERATURE,
            "cost_input": "FREE (local)",
            "cost_output": "FREE (local)",
            "local": True,
            "base_url": config.OLLAMA_BASE_URL,
        }
    else:
        return {
            "provider": provider,
            "model": "unknown",
            "temperature": config.LLM_TEMPERATURE,
        }
