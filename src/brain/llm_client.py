"""Router de LLM — un solo punto para cambiar de proveedor y de modelos.

light() = tareas mecánicas/baratas (evaluar noticias, research, historias).
heavy() = tareas creativas (guiones, carruseles).
Para cambiar de proveedor: setear env LLM_PROVIDER y agregar su adapter aquí.
"""
import os
from src.brain import gemini_client

PROVIDER = os.environ.get("LLM_PROVIDER", "gemini")


def _call_gemini(prompt: str, tier: str, search: bool):
    model = gemini_client.MODEL_PRO if tier == "heavy" else gemini_client.MODEL_FLASH
    config = gemini_client.SEARCH_CONFIG if search else None
    return gemini_client.call(prompt, config=config, model=model)


def _dispatch(prompt: str, tier: str, search: bool):
    if PROVIDER == "gemini":
        return _call_gemini(prompt, tier, search)
    raise NotImplementedError(
        f"Proveedor LLM '{PROVIDER}' no implementado — agrega su adapter en llm_client.py"
    )


def light(prompt: str, search: bool = False):
    return _dispatch(prompt, "light", search)


def heavy(prompt: str, search: bool = False):
    return _dispatch(prompt, "heavy", search)
