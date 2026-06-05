"""
routers/classify.py – User-facing classification API.

POST /api/v1/classify
"""
import logging
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.models.schemas import (
    ClassifyRequest,
    ClassifyResponse,
    MissingFieldsResponse,
)
from app.services.classifier import classify

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Classify"])


@router.post(
    "/classify",
    summary="Classify a user request and extract required data",
    description=(
        "Runs the GLSClass intent classifier on the user message. "
        "Returns HTTP 200 with the downstream payload when all required fields "
        "are available, or HTTP 422 with a `missing_fields` body that the "
        "backend should relay back to the user to collect more data."
    ),
    responses={
        200: {
            "description": "All required fields present – ready to dispatch.",
            "model": ClassifyResponse,
        },
        422: {
            "description": "Required fields missing – ask the user for more info.",
            "model": MissingFieldsResponse,
        },
        500: {"description": "Internal classifier error."},
    },
)
def classify_request(request: ClassifyRequest):
    try:
        result = classify(request)
    except ValueError as exc:
        logger.exception("Classifier error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    if isinstance(result, MissingFieldsResponse):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=result.model_dump(),
        )

    return result
