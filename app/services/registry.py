"""
services/registry.py – in-memory registry for service-class definitions.

Starts with the six built-in classes.  The admin API can update them at
runtime without restarting the container.
"""
from __future__ import annotations
from threading import Lock
from app.models.schemas import ClassDefinition, ServiceClass

_LOCK = Lock()

# ── Default class catalogue ───────────────────────────────────────────────────
_DEFAULT_CLASSES: list[ClassDefinition] = [
    ClassDefinition(
        name=ServiceClass.SUMMARY,
        description=(
            "Generate a concise summary / abstract of a lecture or text passage. "
            "Requires the full lecture content."
        ),
        required_fields=["lecture"],
    ),
    ClassDefinition(
        name=ServiceClass.MCQ,
        description=(
            "Generate multiple-choice questions (MCQs) from a lecture or reading. "
            "Requires the full lecture content."
        ),
        required_fields=["lecture"],
        optional_fields=["num_questions"],
    ),
    ClassDefinition(
        name=ServiceClass.FLASHCARD,
        description=(
            "Generate study flash-cards (front/back) from a lecture. "
            "Requires the full lecture content."
        ),
        required_fields=["lecture"],
        optional_fields=["num_cards"],
    ),
    ClassDefinition(
        name=ServiceClass.TTS,
        description=(
            "Convert lecture text to spoken audio (text-to-speech). "
            "Requires the full lecture content."
        ),
        required_fields=["lecture"],
        optional_fields=["voice", "speed"],
    ),
    ClassDefinition(
        name=ServiceClass.PLAN,
        description=(
            "Generate a structured study plan or learning schedule. "
            "Does NOT need lecture content – needs a date range instead."
        ),
        required_fields=["start_date", "end_date"],
        optional_fields=["topics", "hours_per_day"],
    ),
    ClassDefinition(
        name=ServiceClass.RAG,
        description=(
            "Retrieve-and-generate: answer a question using the knowledge base. "
            "Used when no other class matches."
        ),
        required_fields=["query"],
    ),
]

# ── Registry state ────────────────────────────────────────────────────────────
_registry: dict[ServiceClass, ClassDefinition] = {
    c.name: c for c in _DEFAULT_CLASSES
}


def get_all() -> list[ClassDefinition]:
    with _LOCK:
        return list(_registry.values())


def get(name: ServiceClass) -> ClassDefinition | None:
    with _LOCK:
        return _registry.get(name)


def upsert(definition: ClassDefinition) -> None:
    with _LOCK:
        _registry[definition.name] = definition


def list_names() -> list[ServiceClass]:
    with _LOCK:
        return list(_registry.keys())
