"""
main.py – FastAPI application factory.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import classes, classify

settings = get_settings()
logging.basicConfig(level=settings.log_level.upper())


@asynccontextmanager
async def lifespan(app: FastAPI):          # noqa: ARG001
    logging.getLogger(__name__).info(
        "GLSClass Orchestrator started on %s:%s", settings.host, settings.port
    )
    yield


app = FastAPI(
    title="GLSClass Orchestrator",
    description=(
        "Intent-classification service that routes user requests to the correct "
        "downstream service. Two API groups:\n\n"
        "- **Classes Admin** (`/api/v1/classes`) – register / list service classes.\n"
        "- **Classify** (`/api/v1/classify`) – classify a user message and obtain a "
        "downstream payload."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(classes.router)
app.include_router(classify.router)


@app.get("/health", tags=["Health"], summary="Health check")
def health():
    return {"status": "ok", "version": "1.0.0"}
