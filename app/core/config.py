from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Server ────────────────────────────────────────────────────────────────
    port: int = 8000
    host: str = "0.0.0.0"
    log_level: str = "info"

    # ── GLiClass Model (HuggingFace) ──────────────────────────────────────────
    # Any HuggingFace model ID compatible with the gliclass library.
    # Change this in .env without touching any code.
    classifier_model: str = "knowledgator/gliclass-small-v1.0"

    # 'single-label' → picks exactly one class (recommended for routing)
    # 'multi-label'  → can return multiple classes above threshold
    classifier_type: str = "single-label"

    # Minimum score for a label to be considered a match (multi-label only)
    classifier_threshold: float = 0.5

    # Device: 'cpu', 'cuda:0', 'mps', …
    # Defaults to cpu so the service runs everywhere without a GPU.
    classifier_device: str = "cpu"

    # Max input token length fed to the model
    classifier_max_length: int = 512

    # ── Downstream services ───────────────────────────────────────────────────
    summary_service_url: str = "http://summary-service:8001"
    mcq_service_url: str = "http://mcq-service:8002"
    flashcard_service_url: str = "http://flashcard-service:8003"
    tts_service_url: str = "http://tts-service:8004"
    plan_service_url: str = "http://plan-service:8005"
    rag_service_url: str = "http://rag-service:8006"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()