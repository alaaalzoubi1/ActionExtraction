"""
routers/classify.py – User-facing classification endpoint.
Always returns 200 — the caller handles missing fields.
"""
import logging
from fastapi import APIRouter, HTTPException, status
from app.models.schemas import ClassifyRequest, ClassifyResponse
from app.services.classifier import classify

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Classify"])


@router.post(
    "/classify",
    response_model=ClassifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Classify a user request",
    description=(
        "Detects intent and extracts available fields. "
        "Always returns 200 — check `required_fields` vs `extracted_data` "
        "to determine what to ask the user next."
    ),
)
def classify_request(request: ClassifyRequest) -> ClassifyResponse:
    try:
        return classify(request)
    except Exception as exc:
        logger.exception("Classifier error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc