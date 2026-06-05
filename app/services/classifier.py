from __future__ import annotations
import logging
from typing import Any, Dict

from app.core.config import get_settings
from app.models.schemas import (
    ClassDefinition,
    ClassifyRequest,
    ClassifyResponse,
    MissingFieldsResponse,
    ServiceClass,
)
from app.services import registry
from app.services.url_resolver import resolve_url

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Lazy model singleton ──────────────────────────────────────────────────────
_pipeline = None


def _get_pipeline():
    """Load the GLiClass pipeline once and reuse it for every request."""
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    from gliclass import ZeroShotClassificationPipeline
    from gliclass.model import GLiClassModel
    from transformers import AutoTokenizer

    model_id = settings.classifier_model
    logger.info("Loading GLiClass model '%s' on device '%s' …", model_id, settings.classifier_device)

    model = GLiClassModel.from_pretrained(model_id)
    tokenizer = AutoTokenizer.from_pretrained(model_id)

    _pipeline = ZeroShotClassificationPipeline(
        model=model,
        tokenizer=tokenizer,
        classification_type=settings.classifier_type,
        device=settings.classifier_device,
        max_length=settings.classifier_max_length,
        progress_bar=False,
    )
    logger.info("GLiClass model loaded successfully.")
    return _pipeline


# ── Input builder ─────────────────────────────────────────────────────────────

def _build_input_text(request: ClassifyRequest) -> str:
    """
    Combine user_message + flattened context into a single string for the model.
    Context values are appended as 'key: value' pairs so the model has full info.
    """
    parts = [request.user_message.strip()]

    if request.context:
        for key, value in request.context.items():
            if value is not None:
                # Truncate very long values (e.g. full lecture texts) to avoid
                # overflowing the model's max_length
                str_val = str(value)
                if len(str_val) > 300:
                    str_val = str_val[:300] + "…"
                parts.append(f"{key}: {str_val}")

    return " | ".join(parts)


def _build_labels(classes: list[ClassDefinition]) -> list[str]:
    """
    Build the label list fed to GLiClass.
    Each label is 'class_name: description' so the model can leverage semantics.
    """
    return [f"{c.name.value}: {c.description}" for c in classes]


def _label_to_class(label_str: str) -> ServiceClass:
    """Reverse-map 'class_name: description' → ServiceClass enum."""
    class_name = label_str.split(":")[0].strip()
    return ServiceClass(class_name)


# ── Field extractor ───────────────────────────────────────────────────────────

def _extract_fields(
    request: ClassifyRequest,
    class_def: ClassDefinition,
) -> Dict[str, Any]:
    """
    Pull field values from the user message and the context dict.
    Context values are preferred (they are already structured data).
    """
    extracted: Dict[str, Any] = {}
    all_fields = class_def.required_fields + class_def.optional_fields
    context = request.context or {}

    for field in all_fields:
        # 1. Direct key in context
        if field in context and context[field] is not None:
            extracted[field] = context[field]
            continue

        # 2. Simple keyword heuristics for common fields
        msg_lower = request.user_message.lower()

        if field == "lecture":
            # Accept any long-form text provided as 'text', 'content', or 'lecture'
            for alias in ("text", "content", "lecture", "passage"):
                if alias in context and context[alias]:
                    extracted[field] = context[alias]
                    break
            else:
                extracted[field] = None

        elif field == "query":
            extracted[field] = request.user_message

        elif field in ("start_date", "end_date"):
            extracted[field] = context.get(field)  # must be supplied explicitly

        elif field == "num_questions":
            import re
            m = re.search(r"\b(\d+)\s*(question|mcq|quiz)", msg_lower)
            extracted[field] = int(m.group(1)) if m else context.get(field)

        elif field == "num_cards":
            import re
            m = re.search(r"\b(\d+)\s*(card|flash)", msg_lower)
            extracted[field] = int(m.group(1)) if m else context.get(field)

        else:
            extracted[field] = context.get(field)

    return extracted


# ── Main classify function ────────────────────────────────────────────────────

def classify(
    request: ClassifyRequest,
) -> ClassifyResponse | MissingFieldsResponse:
    """
    Classify the user request with GLiClass, extract fields, check completeness.

    Returns:
        ClassifyResponse      (HTTP 200) – all required fields present.
        MissingFieldsResponse (HTTP 422) – required fields missing.
    """
    pipeline = _get_pipeline()
    classes = registry.get_all()

    input_text = _build_input_text(request)
    labels = _build_labels(classes)

    logger.info("Classifying: %.120s", input_text)

    results: list[list[dict]] = pipeline(
        input_text,
        labels,
        threshold=settings.classifier_threshold,
    )

    # results is always a list-of-lists; we passed a single text → results[0]
    predictions = results[0] if results else []

    if not predictions:
        # Nothing above threshold → fall back to RAG
        detected_class = ServiceClass.RAG
        confidence = 0.0
    else:
        # single-label: already one best label; multi-label: take highest score
        best = max(predictions, key=lambda p: p["score"])
        detected_class = _label_to_class(best["label"])
        confidence = round(best["score"], 4)

    logger.info("Detected class: %s (confidence: %.4f)", detected_class, confidence)

    class_def = registry.get(detected_class) or registry.get(ServiceClass.RAG)
    extracted = _extract_fields(request, class_def)

    # Check for missing required fields
    missing = [f for f in class_def.required_fields if extracted.get(f) is None]

    if missing:
        return MissingFieldsResponse(
            detected_class=detected_class,
            missing_fields=missing,
            prompt_message=_build_missing_prompt(detected_class, missing),
        )

    downstream_payload = {k: v for k, v in extracted.items() if v is not None}

    return ClassifyResponse(
        detected_class=detected_class,
        confidence=confidence,
        extracted_data=extracted,
        downstream_payload=downstream_payload,
        downstream_url=resolve_url(detected_class),
    )


# ── Human-friendly missing-field messages ─────────────────────────────────────

_FIELD_PROMPTS: Dict[str, str] = {
    "lecture":        "Please provide the lecture content you'd like to work with.",
    "start_date":     "What start date should the plan begin? (e.g. 2025-06-01)",
    "end_date":       "What end date should the plan finish by? (e.g. 2025-06-30)",
    "query":          "What question would you like to ask?",
    "topics":         "Which topics should the plan cover?",
    "num_questions":  "How many questions would you like to generate?",
    "num_cards":      "How many flash-cards would you like?",
    "voice":          "Which voice should be used for the audio?",
    "speed":          "What playback speed should the audio use?",
    "hours_per_day":  "How many study hours per day should the plan assume?",
}

_CLASS_INTRO: Dict[ServiceClass, str] = {
    ServiceClass.SUMMARY:   "To generate a summary",
    ServiceClass.MCQ:       "To generate multiple-choice questions",
    ServiceClass.FLASHCARD: "To generate flash-cards",
    ServiceClass.TTS:       "To convert the lecture to speech",
    ServiceClass.PLAN:      "To generate a study plan",
    ServiceClass.RAG:       "To answer your question",
}


def _build_missing_prompt(cls: ServiceClass, missing: list[str]) -> str:
    intro = _CLASS_INTRO.get(cls, "To process your request")
    parts = [_FIELD_PROMPTS.get(f, f"Please provide '{f}'.") for f in missing]
    return f"{intro}, I need a bit more information. {' '.join(parts)}"