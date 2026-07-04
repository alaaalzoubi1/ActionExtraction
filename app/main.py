"""
main.py – FastAPI application factory.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import classes, classify
from app.services.registry import init_db

settings = get_settings()
logging.basicConfig(level=settings.log_level.upper())


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logging.getLogger(__name__).info("GLSClass Orchestrator started.")
    yield


app = FastAPI(
    title="GLSClass Orchestrator",
    description="Intent-classification service that routes user requests to downstream services.",
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


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "version": "1.0.0"}