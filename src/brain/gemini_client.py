"""Cliente Gemini centralizado — único punto de configuración del modelo,
retry y grounding. Evita duplicar la lógica en evaluator/script_generator/scripts.
"""
from google import genai
from google.genai import types
from google.genai.errors import ServerError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

# Modelo por defecto. Cambiar aquí lo cambia en todo el proyecto.
MODEL = "gemini-2.5-flash"

# Config de búsqueda en Google (grounding). Solo para contenido que necesita
# datos actuales de internet — NO para temas del banco interno.
SEARCH_CONFIG = types.GenerateContentConfig(
    tools=[types.Tool(google_search=types.GoogleSearch())]
)

_client = None


def get_client():
    global _client
    if _client is None:
        from src.config import settings
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(60),
    retry=retry_if_exception_type(ServerError),
    reraise=True,
)
def call(contents: str, config=None, model: str = MODEL):
    """Llama a Gemini con retry automático ante errores 503/UNAVAILABLE."""
    client = get_client()
    return client.models.generate_content(model=model, contents=contents, config=config)
