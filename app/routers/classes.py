"""
routers/classes.py – Admin API for managing service-class definitions.

POST /api/v1/classes/register   – add or update a class definition
GET  /api/v1/classes            – list all registered classes
"""
from fastapi import APIRouter, status
from app.models.schemas import ClassDefinition, RegisterClassResponse, ServiceClass
from app.services import registry

router = APIRouter(prefix="/api/v1/classes", tags=["Classes Admin"])


@router.post(
    "/register",
    response_model=RegisterClassResponse,
    status_code=status.HTTP_200_OK,
    summary="Register or update a service-class definition",
    description=(
        "Add a new service class or update an existing one. "
        "Changes take effect immediately without restarting the service."
    ),
)
def register_class(definition: ClassDefinition) -> RegisterClassResponse:
    registry.upsert(definition)
    return RegisterClassResponse(
        success=True,
        message=f"Class '{definition.name}' registered successfully.",
        classes=registry.list_names(),
    )


@router.get(
    "",
    response_model=list[ClassDefinition],
    status_code=status.HTTP_200_OK,
    summary="List all registered service classes",
)
def list_classes() -> list[ClassDefinition]:
    return registry.get_all()
