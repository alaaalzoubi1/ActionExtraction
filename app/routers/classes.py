"""
routers/classes.py – Admin API for managing service-class definitions.

POST   /api/v1/classes          – add or update a class
GET    /api/v1/classes          – list all classes
DELETE /api/v1/classes/{name}   – remove a class
POST   /api/v1/classes/reset    – restore built-in defaults
"""
from fastapi import APIRouter, HTTPException, status
from app.models.schemas import ClassDefinition, RegisterClassResponse
from app.services import registry
from app.services.registry import reset_to_defaults

router = APIRouter(prefix="/api/v1/classes", tags=["Classes Admin"])


@router.post(
    "",
    response_model=RegisterClassResponse,
    status_code=status.HTTP_200_OK,
    summary="Register or update a service class",
)
def register_class(definition: ClassDefinition) -> RegisterClassResponse:
    registry.upsert(definition)
    return RegisterClassResponse(
        success=True,
        message=f"Class '{definition.name}' saved.",
        classes=registry.list_names(),
    )


@router.get(
    "",
    response_model=list[ClassDefinition],
    status_code=status.HTTP_200_OK,
    summary="List all registered classes",
)
def list_classes() -> list[ClassDefinition]:
    return registry.get_all()


@router.delete(
    "/{name}",
    response_model=RegisterClassResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a class by name",
)
def delete_class(name: str) -> RegisterClassResponse:
    if not registry.delete(name):
        raise HTTPException(status_code=404, detail=f"Class '{name}' not found.")
    return RegisterClassResponse(
        success=True,
        message=f"Class '{name}' deleted.",
        classes=registry.list_names(),
    )


@router.post(
    "/reset",
    response_model=RegisterClassResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset all classes to built-in defaults",
)
def reset_classes() -> RegisterClassResponse:
    reset_to_defaults()
    return RegisterClassResponse(
        success=True,
        message="Classes reset to defaults.",
        classes=registry.list_names(),
    )
