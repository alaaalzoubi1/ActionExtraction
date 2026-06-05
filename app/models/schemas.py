"""
models/schemas.py – all request/response Pydantic schemas.
"""
from __future__ import annotations
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Service classes recognised by the classifier
# ─────────────────────────────────────────────────────────────────────────────
class ServiceClass(str, Enum):
    SUMMARY = "summary"
    MCQ = "mcq"
    FLASHCARD = "flashcard"
    TTS = "tts"
    PLAN = "plan"
    RAG = "rag"


# ─────────────────────────────────────────────────────────────────────────────
# Admin API  –  POST /api/v1/classes/register
# ─────────────────────────────────────────────────────────────────────────────
class ClassDefinition(BaseModel):
    """Describes one service class and the fields it needs before dispatch."""
    name: ServiceClass
    description: str = Field(..., description="Human-readable description shown to the LLM.")
    required_fields: list[str] = Field(
        default_factory=list,
        description="Field names that MUST be present before the request can be dispatched.",
    )
    optional_fields: list[str] = Field(default_factory=list)


class RegisterClassResponse(BaseModel):
    success: bool
    message: str
    classes: list[ServiceClass]


# ─────────────────────────────────────────────────────────────────────────────
# User API  –  POST /api/v1/classify
# ─────────────────────────────────────────────────────────────────────────────
class ClassifyRequest(BaseModel):
    user_message: str = Field(..., description="Raw natural-language request from the user.")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Any data the caller already collected (e.g. lecture text, date range).",
    )


class MissingFieldsResponse(BaseModel):
    """Returned when required context is absent. HTTP 422."""
    status: str = "missing_fields"
    detected_class: ServiceClass
    missing_fields: list[str]
    prompt_message: str = Field(
        ...,
        description="Human-friendly question the backend should relay to the user.",
    )


class ClassifyResponse(BaseModel):
    """Returned when all required fields are present. HTTP 200."""
    status: str = "classified"
    detected_class: ServiceClass
    confidence: float = Field(..., ge=0.0, le=1.0)
    extracted_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured data extracted from the user message + context.",
    )
    downstream_payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Ready-to-forward payload for the downstream service.",
    )
    downstream_url: str


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
