"""
schemas.py – request/response Pydantic schemas.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ClassDefinition(BaseModel):
    name:            str       = Field(..., description="Unique class identifier, e.g. 'summary'")
    required_fields: List[str] = Field(default_factory=list)
    optional_fields: List[str] = Field(default_factory=list)


class RegisterClassResponse(BaseModel):
    success: bool
    message: str
    classes: List[str]


class ClassifyRequest(BaseModel):
    user_message: str
    context: Optional[Dict[str, Any]] = None


class ClassifyResponse(BaseModel):
    status:         str   = "classified"
    detected_class: str
    confidence:     float
    downstream_url: str


class HealthResponse(BaseModel):
    status:  str = "ok"
    version: str = "1.0.0"