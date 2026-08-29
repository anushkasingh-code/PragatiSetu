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

__all__ = [
    "projects_router",
    "reports_router",
    "events_router",
    "candidates_router",
    "decisions_router",
    "apply_router",
    "reviews_router",
    "dashboard_router",
    "timeline_router",
    "audit_router",
    "placeholders_router",
    "voice_router"
]
