"""RoboWitness Backend Application Entrypoint."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.routes_evidence import router as evidence_router
from app.api.routes_failures import router as failures_router
from app.api.routes_health import router as health_router
from app.api.routes_runs import router as runs_router
from app.api.routes_scenarios import router as scenarios_router
from app.api.routes_verifications import router as verifications_router
from app.config import settings
from app.db import init_db
from app.errors import ErrorBody, ErrorDetail, ErrorEnvelope, RoboWitnessException

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database and artifacts root
    init_db()
    settings.artifacts_path.mkdir(parents=True, exist_ok=True)
    (settings.artifacts_path / "runs").mkdir(parents=True, exist_ok=True)
    (settings.artifacts_path / "verifications").mkdir(parents=True, exist_ok=True)
    yield

def create_app() -> FastAPI:
    app = FastAPI(
        title="RoboWitness API",
        version="1.0.0",
        description="Independent evidence and verification engine for simulated robotics failure fixes",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list or ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Routers under /api
    app.include_router(health_router, prefix="/api")
    app.include_router(scenarios_router, prefix="/api")
    app.include_router(runs_router, prefix="/api")
    app.include_router(failures_router, prefix="/api")
    app.include_router(verifications_router, prefix="/api")
    app.include_router(evidence_router, prefix="/api")

    # Custom Error Handlers
    @app.exception_handler(RoboWitnessException)
    async def robowitness_exception_handler(request: Request, exc: RoboWitnessException):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        details = [
            ErrorDetail(field=".".join(str(loc) for loc in err["loc"]), reason=err["msg"])
            for err in exc.errors()
        ]
        envelope = ErrorEnvelope(
            error=ErrorBody(
                code="VALIDATION_ERROR",
                message="Request payload failed schema validation",
                details=details,
            )
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=envelope.model_dump(),
        )

    return app

app = create_app()
