from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from xautopilot.config import settings
from xautopilot.database import engine
from xautopilot.routers import (
    analytics,
    auth,
    drafts,
    growth,
    plans,
    profile,
    publish,
    reply_targets,
    schedule,
    sources,
    worker,
    x_account,
)
from xautopilot.services.crypto_service import encryption_key_source
from xautopilot.settings_validation import secrets_configured, validate_settings
from xautopilot.workers.scheduler import start_worker_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging

    log = logging.getLogger("xautopilot")
    config_issues = validate_settings(settings)
    if config_issues:
        message = "Config issues: " + "; ".join(config_issues)
        if settings.app_env in ("staging", "production"):
            raise RuntimeError(message)
        log.warning(message)

    scheduler = None
    if settings.worker_enabled:
        scheduler = start_worker_scheduler()

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1 FROM users LIMIT 1"))
    except ProgrammingError:
        log.warning(
            "Database not migrated — run: cd apps/api && alembic upgrade head"
        )
    except Exception:
        log.warning(
            "Cannot connect to database — is Postgres running? docker compose up postgres -d"
        )

    yield

    if scheduler is not None:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="X-Autopilot API",
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ProgrammingError)
async def database_schema_error(_request: Request, _exc: ProgrammingError):
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Database not ready. Run migrations: cd apps/api && alembic upgrade head",
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception(_request: Request, exc: Exception):
    import logging

    logging.getLogger("xautopilot").exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check API logs for details."},
    )


app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(sources.router)
app.include_router(plans.router)
app.include_router(reply_targets.router)
app.include_router(drafts.router)
app.include_router(schedule.router)
app.include_router(publish.router)
app.include_router(x_account.router)
app.include_router(analytics.router)
app.include_router(growth.router)
app.include_router(worker.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "xautopilot-api"}


@app.get("/health/config")
async def health_config():
    issues = validate_settings(settings)
    return {
        "app_env": settings.app_env,
        "llm_mode": settings.llm_mode,
        "openai_configured": bool(settings.openai_api_key),
        "secrets_ok": secrets_configured(settings),
        "encryption_key_source": encryption_key_source(),
        "issues": issues,
    }


@app.get("/health/ready")
async def health_ready():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1 FROM users LIMIT 1"))
        return {"status": "ready", "database": "ok"}
    except ProgrammingError:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "database": "missing_tables",
                "fix": "cd apps/api && alembic upgrade head",
            },
        )
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "unreachable", "error": str(exc)},
        )
