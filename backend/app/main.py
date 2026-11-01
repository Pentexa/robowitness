"""RoboWitness Backend Application Entrypoint."""

import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.routes_evidence import router as evidence_router
from app.api.routes_failures import router as failures_router
from app.api.routes_health import router as health_router
from app.api.routes_batteries import router as batteries_router
from app.api.routes_imports import router as imports_router
from app.api.routes_admin import router as admin_router
from app.api.routes_local_policies import router as local_policies_router
from app.api.routes_maps import router as maps_router
from app.api.routes_schedules import router as schedules_router
from app.api.routes_policies import router as policies_router
from app.api.routes_robots import router as robots_router
from app.api.routes_runs import router as runs_router
from app.api.routes_scenarios import router as scenarios_router
from app.api.routes_verifications import router as verifications_router
from app.config import settings
from app.db import init_db
from app.errors import ErrorBody, ErrorDetail, ErrorEnvelope, RoboWitnessException
from app.rate_limit import rate_limit_exceeded
from app.security import PUBLIC_PATHS, WRITE_METHODS, authenticate, write_audit


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
        description=(
            "Independent evidence and verification engine for simulated robotics failure fixes"
        ),
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

    # Enterprise auth + audit + hardening middleware. Open local mode when
    # no keys are set. Adds request ids, security headers, optional rate limit.
    @app.middleware("http")
    async def auth_audit_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-Id") or f"req-{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id
        path = request.url.path
        if path.startswith("/api") and path not in PUBLIC_PATHS and request.method != "OPTIONS":
            principal = authenticate(request)
            if principal is None:
                envelope = ErrorEnvelope(
                    error=ErrorBody(
                        code="UNAUTHORIZED",
                        message="Missing or invalid API key (header X-API-Key)",
                    )
                )
                return JSONResponse(status_code=401, content=envelope.model_dump())
            if request.method in WRITE_METHODS and principal.role == "viewer":
                envelope = ErrorEnvelope(
                    error=ErrorBody(
                        code="FORBIDDEN_ROLE",
                        message="Viewer role cannot perform write operations",
                    )
                )
                response = JSONResponse(status_code=403, content=envelope.model_dump())
                write_audit(request, 403)
                return response
            request.state.principal = principal
            if rate_limit_exceeded(principal.actor):
                envelope = ErrorEnvelope(
                    error=ErrorBody(
                        code="RATE_LIMITED",
                        message="Too many requests; slow down (RW_RATE_LIMIT_PER_MIN)",
                    )
                )
                return JSONResponse(status_code=429, content=envelope.model_dump())
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        write_audit(request, response.status_code)
        return response

    # Register Routers under /api
    app.include_router(health_router, prefix="/api")
    app.include_router(scenarios_router, prefix="/api")
    app.include_router(runs_router, prefix="/api")
    app.include_router(failures_router, prefix="/api")
    app.include_router(verifications_router, prefix="/api")
    app.include_router(evidence_router, prefix="/api")
    app.include_router(robots_router, prefix="/api")
    app.include_router(policies_router, prefix="/api")
    app.include_router(batteries_router, prefix="/api")
    app.include_router(imports_router, prefix="/api")
    app.include_router(local_policies_router, prefix="/api")
    app.include_router(maps_router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    app.include_router(schedules_router, prefix="/api")

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
