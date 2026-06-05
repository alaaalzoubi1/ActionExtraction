"""
services/url_resolver.py – maps a ServiceClass to its downstream URL.
"""
from app.models.schemas import ServiceClass
from app.core.config import get_settings

_settings = get_settings()

_URL_MAP = {
    ServiceClass.SUMMARY:   lambda: _settings.summary_service_url,
    ServiceClass.MCQ:       lambda: _settings.mcq_service_url,
    ServiceClass.FLASHCARD: lambda: _settings.flashcard_service_url,
    ServiceClass.TTS:       lambda: _settings.tts_service_url,
    ServiceClass.PLAN:      lambda: _settings.plan_service_url,
    ServiceClass.RAG:       lambda: _settings.rag_service_url,
}


def resolve_url(cls: ServiceClass) -> str:
    resolver = _URL_MAP.get(cls)
    if resolver is None:
        return _settings.rag_service_url
    return resolver()
