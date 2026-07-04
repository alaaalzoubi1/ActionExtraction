from __future__ import annotations
import logging

from app.core.config import get_settings
from app.models.schemas import ClassifyRequest, ClassifyResponse
from app.services import registry
from app.services.url_resolver import resolve_url

logger = logging.getLogger(__name__)
settings = get_settings()

_model = None
_tokenizer = None
_id2label: dict[int, str] = {}


# ── Model loader (lazy singleton) ─────────────────────────────────────────────

def _get_model():
    global _model, _tokenizer, _id2label

    if _model is not None:
        return _model, _tokenizer, _id2label

    import json
    from pathlib import Path
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    model_path = settings.model_path()
    logger.info("Loading fine-tuned classifier from '%s' ...", model_path)

    _tokenizer = AutoTokenizer.from_pretrained(str(model_path))
    _model = AutoModelForSequenceClassification.from_pretrained(str(model_path))
    _model.eval()

    label_map_path = Path(model_path) / "label_map.json"
    if label_map_path.exists():
        with open(label_map_path) as f:
            lmap = json.load(f)
            _id2label = {int(k): v for k, v in lmap["id2label"].items()}
    else:
        _id2label = {int(k): v for k, v in _model.config.id2label.items()}

    logger.info("Classifier loaded. Labels: %s", list(_id2label.values()))
    return _model, _tokenizer, _id2label


# ── Main entry point ──────────────────────────────────────────────────────────

def classify(request: ClassifyRequest) -> ClassifyResponse:
    import torch

    model, tokenizer, id2label = _get_model()

    enc = tokenizer(
        request.user_message,
        return_tensors="pt",
        truncation=True,
        padding="max_length",
        max_length=settings.classifier_max_length,
    )

    with torch.no_grad():
        logits = model(**enc).logits

    probs = torch.softmax(logits, dim=1)[0].tolist()
    best_id = int(torch.argmax(logits, dim=1).item())
    detected_name = id2label.get(best_id, "rag")
    confidence = round(probs[best_id], 4)

    logger.info("MiniLM → %s (confidence: %.4f)", detected_name, confidence)

    return ClassifyResponse(
        detected_class=detected_name,
        confidence=confidence,
        downstream_url=resolve_url(detected_name),
    )
