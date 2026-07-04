"""
config.py – central configuration.
All tuneable values live here; change .env without touching code.
"""
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Server ────────────────────────────────────────────────────────────────
    port: int = 8000
    host: str = "0.0.0.0"
    log_level: str = "info"

    # ── Fine-tuned classifier model ───────────────────────────────────────────
    # Path to the fine-tuned MiniLM model folder produced by the training notebook.
    # Can be a local relative/absolute path or a HuggingFace Hub model ID.
    classifier_model: str = "training/model"

    # Inference device: 'cpu' | 'cuda:0' | 'mps'
    classifier_device: str = "cpu"

    # Max token length fed to the model
    classifier_max_length: int = 128

    # ── Downstream services ───────────────────────────────────────────────────
    summary_service_url:   str = "http://summary-service:8001"
    mcq_service_url:       str = "http://mcq-service:8002"
    flashcard_service_url: str = "http://flashcard-service:8003"
    tts_service_url:       str = "http://tts-service:8004"
    plan_service_url:      str = "http://plan-service:8005"
    rag_service_url:       str = "http://rag-service:8006"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def model_path(self) -> Path:
        """
        Resolve the classifier model path.
        Relative paths are resolved from the project root (parent of app/).
        """
        p = Path(self.classifier_model)
        if p.is_absolute():
            return p
        # Resolve relative to project root regardless of cwd
        root = Path(__file__).resolve().parent.parent.parent
        return root / p


@lru_cache
def get_settings() -> Settings:
    return Settings()
