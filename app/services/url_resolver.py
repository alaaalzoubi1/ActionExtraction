"""
url_resolver.py – maps class name to downstream service URL.
Falls back to RAG URL for unknown classes.
"""
from app.core.config import get_settings

_settings = get_settings()

_URL_MAP: dict[str, str] = {
    "summary":   "summary_service_url",
    "mcq":       "mcq_service_url",
    "flashcard": "flashcard_service_url",
    "tts":       "tts_service_url",
    "plan":      "plan_service_url",
    "rag":       "rag_service_url",
}


def resolve_url(class_name: str) -> str:
    attr = _URL_MAP.get(class_name, "rag_service_url")
    return getattr(_settings, attr, _settings.rag_service_url)