"""
FastAPI Application Gateway Entry Point.
Initializes CORS middleware, lifespan startup/shutdown lifecycle, uniform exception handlers,
and registers all 6 modular API route domains under /api/v1/.
"""
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from typing import AsyncGenerator, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

try:
    from dotenv import load_dotenv
    # Load .env file from project root
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

from src.api.routes import (
    analytics,
    epa,
    ingest,
    meta,
    observations,
    spatial,
    stream,
)
from src.infrastructure.repositories import BaselineRepository, PersistentRepository
from src.pipelines.scheduler import PipelineOrchestrator
from src.pipelines.staging_buffer import ChronometricStagingBuffer
from src.services.analytics_service import AnalyticsService
from src.services.ingestion_service import IngestionService
from src.services.observation_service import ObservationService
from src.services.precomputation_service import PrecomputationService
from src.services.spatial_service import SpatialService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("paq.api")


def init_app_state(app: FastAPI, base_dir: Optional[Path] = None) -> None:
    """Initializes repository and application domain services in app.state if not present."""
    if not hasattr(app.state, "repo") or app.state.repo is None:
        if base_dir is None:
            base_dir = Path(__file__).resolve().parent.parent.parent / "data" / "baseline"

        use_db = os.getenv("USE_DATABASE_BACKEND", "true").lower() in ("true", "1", "yes")
        repo = None
        if use_db:
            try:
                repo = PersistentRepository(baseline_dir=base_dir)
                logger.info("Initialized PersistentRepository backed by PostgreSQL 16 & TimescaleDB.")
            except Exception as e:
                logger.warning(f"Could not initialize PersistentRepository: {e}. Falling back to BaselineRepository.")
                repo = BaselineRepository(baseline_dir=base_dir)
        else:
            repo = BaselineRepository(baseline_dir=base_dir)

        app.state.repo = repo
        obs_svc = ObservationService(repo=repo)
        spat_svc = SpatialService(repo=repo)
        anal_svc = AnalyticsService(repo=repo)
        app.state.observation_service = obs_svc
        app.state.spatial_service = spat_svc
        app.state.analytics_service = anal_svc
        app.state.ingestion_service = IngestionService(repo=repo)

        staging_buffer = ChronometricStagingBuffer(repository=repo)
        precomp_service = PrecomputationService(
            repository=repo,
            spatial_service=spat_svc,
            analytics_service=anal_svc,
        )
        orchestrator = PipelineOrchestrator(
            repository=repo,
            staging_buffer=staging_buffer,
            precomputation_service=precomp_service,
            mode="simulation",
        )
        app.state.staging_buffer = staging_buffer
        app.state.precomputation_service = precomp_service
        app.state.orchestrator = orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan event context manager.
    Loads baseline datasets into high-performance in-memory repository on startup (~1.5s).
    Initializes application services, starts background pipeline orchestrator, and mounts them on app.state.
    """
    logger.info("Punjab Air Quality API Gateway: Initializing lifespan...")

    init_app_state(app)
    repo = app.state.repo
    orchestrator = getattr(app.state, "orchestrator", None)
    if orchestrator:
        await orchestrator.start()

    logger.info(
        f"API Gateway startup ready: {repo.count_stations()} stations, "
        f"{repo.count_districts()} districts, {len(repo.get_timeline_timestamps())} historical hours indexed."
    )

    yield

    logger.info("Punjab Air Quality API Gateway: Shutting down lifespan...")
    if orchestrator:
        await orchestrator.stop()


def create_application() -> FastAPI:
    """Application factory for Punjab Air Quality FastAPI Gateway."""
    app = FastAPI(
        title="Punjab Air Quality Information System API",
        description="High-performance environmental telemetry, spatial IDW interpolation, and transboundary advection intelligence platform.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )

    # CORS Middleware Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Exception Handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning(f"Request validation error on {request.url.path}: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "error_type": "ValidationError",
                "message": "The request parameters failed validation schema checks.",
                "details": exc.errors(),
            },
        )

    # Healthcheck Route
    @app.get("/health", tags=["Health"], summary="System Liveness and Health Status")
    async def healthcheck() -> dict:
        return {
            "status": "healthy",
            "service": "punjab-air-quality-api",
            "version": "1.0.0",
        }

    # Mount Route Modules under /api/v1/
    app.include_router(meta.router)
    app.include_router(observations.router)
    app.include_router(spatial.router)
    app.include_router(analytics.router)
    app.include_router(ingest.router)
    app.include_router(stream.router)
    app.include_router(epa.router)

    # Mount Static Frontend Assets & Root Delivery
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    static_dir = frontend_dir / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", include_in_schema=False)
    @app.get("/index.html", include_in_schema=False)
    async def serve_index():
        html_file = frontend_dir / "dashboard.html"
        if not html_file.exists():
            html_file = frontend_dir / "index.html"
        if html_file.exists():
            return FileResponse(html_file)
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"message": "Frontend dashboard not found"})

    # Initialize in-memory state
    init_app_state(app)

    return app


app = create_application()
