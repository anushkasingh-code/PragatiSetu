import logging
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.config import settings
from backend.app.db.database import get_db, Base, engine
from backend.app.api.projects import router as projects_router
from backend.app.api.reports import router as reports_router
from backend.app.api.events import router as events_router
from backend.app.api.candidates import router as candidates_router
from backend.app.api.decisions import router as decisions_router
from backend.app.api.apply import router as apply_router
from backend.app.api.reviews import router as reviews_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.api.timeline import router as timeline_router
from backend.app.api.audit import router as audit_router
from backend.app.api.placeholders import router as placeholders_router
from backend.app.api.voice import router as voice_router
from backend.app.api.ai import router as ai_router
from backend.app.services.ai.vector_store import get_chroma_client

# Configure Application Logging
log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("pragatisetu")

# Ensure database tables exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="PragatiSetu — Standalone REST API backend bridging baseline project schedules and field progress reports.",
    version="1.0.0"
)

# Configurable CORS Middleware
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()] if hasattr(settings, "CORS_ORIGINS") else ["*"]
# Security: allow_credentials=True is INCOMPATIBLE with allow_origins=["*"]
# Only allow credentials when specific origins are configured
_cors_allow_credentials = len(cors_origins) > 0 and cors_origins != ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=_cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standardized Error Response Exception Handler with Backward Compatibility
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    code_map = {
        400: "BAD_REQUEST",
        404: "RESOURCE_NOT_FOUND",
        409: "RESOURCE_CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        500: "INTERNAL_SERVER_ERROR"
    }
    err_code = code_map.get(exc.status_code, "API_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error": {
                "code": err_code,
                "message": exc.detail if isinstance(exc.detail, str) else "Request failed.",
                "details": exc.detail if isinstance(exc.detail, dict) else {}
            }
        }
    )

@app.exception_handler(Exception)
async def custom_generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": str(exc) if settings.DEBUG else "An unexpected server error occurred.",
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(exc) if settings.DEBUG else "An unexpected server error occurred.",
                "details": {}
            }
        }
    )

# Include Routers
app.include_router(projects_router, prefix=settings.API_V1_STR)
app.include_router(reports_router, prefix=settings.API_V1_STR)
app.include_router(events_router, prefix=settings.API_V1_STR)
app.include_router(candidates_router, prefix=settings.API_V1_STR)
app.include_router(decisions_router, prefix=settings.API_V1_STR)
app.include_router(apply_router, prefix=settings.API_V1_STR)
app.include_router(reviews_router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router, prefix=settings.API_V1_STR)
app.include_router(timeline_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)
app.include_router(placeholders_router, prefix=settings.API_V1_STR)
app.include_router(voice_router, prefix=settings.API_V1_STR)
app.include_router(ai_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint evaluating application and real database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = f"error: {str(e)}"
    try:
        client = get_chroma_client()
        client.heartbeat()
        vector_status = "ready"
    except Exception as e:
        vector_status = f"degraded: {str(e)}"

    return {
        "status": "ok",
        "app": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "vector_store": vector_status
    }
