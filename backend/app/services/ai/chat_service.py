import os
import re
import json
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.config import settings
from backend.app.db.models.project import Project
from backend.app.db.models.activity import ScheduleActivity
from backend.app.db.models.report import SourceReport
from backend.app.db.models.event import ExtractedEvent
from backend.app.db.models.audit import AuditRecord
from backend.app.schemas.ai import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatActivityItem,
    VectorSearchResult
)
from backend.app.services.ai.vector_retriever import search_schedule_activities

logger = logging.getLogger("pragatisetu.chat_service")

def save_groq_api_key(key: str) -> str:
    cleaned = key.strip()
    if not cleaned:
        return ""
    os.environ["GROQ_API_KEY"] = cleaned
    os.environ["GROQ_ENABLED"] = "true"
    if hasattr(settings, "GROQ_API_KEY"):
        settings.GROQ_API_KEY = cleaned
    if hasattr(settings, "GROQ_ENABLED"):
        settings.GROQ_ENABLED = True

    # Persist to disk in standard .env paths
    env_paths = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.getcwd(), "backend", ".env"),
    ]
    for env_path in env_paths:
        try:
            lines = []
            found = False
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if line.startswith("GROQ_API_KEY="):
                            lines.append(f"GROQ_API_KEY={cleaned}\n")
                            found = True
                        elif line.startswith("GROQ_ENABLED="):
                            lines.append("GROQ_ENABLED=true\n")
                        else:
                            lines.append(line)
            if not found:
                lines.append(f"GROQ_API_KEY={cleaned}\n")
                lines.append("GROQ_ENABLED=true\n")
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception as e:
            logger.warning(f"Could not persist key to {env_path}: {e}")
    return cleaned

def get_effective_groq_api_key(runtime_key: Optional[str] = None) -> str:
    """
    Dynamically inspects runtime input, os.environ, settings, registry, and .env files to retrieve GROQ_API_KEY.
    """
    if runtime_key and runtime_key.strip():
        return save_groq_api_key(runtime_key.strip())

    key = os.getenv("GROQ_API_KEY", "").strip()
    if key:
        return key

    key = getattr(settings, "GROQ_API_KEY", "").strip()
    if key:
        return key

    # Check Windows Registry for system or user environment variables
    try:
        import winreg
        for root_h, subkey in [
            (winreg.HKEY_CURRENT_USER, r"Environment"),
            (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")
        ]:
            try:
                with winreg.OpenKey(root_h, subkey) as k:
                    val, _ = winreg.QueryValueEx(k, "GROQ_API_KEY")
                    if val and str(val).strip():
                        save_groq_api_key(str(val).strip())
                        return str(val).strip()
            except OSError:
                pass
    except Exception:
        pass

    # Check common .env paths
    potential_paths = [
        ".env",
        os.path.join(os.getcwd(), ".env"),
        "backend/.env",
        os.path.join(os.getcwd(), "backend", ".env"),
        os.path.join(os.path.dirname(os.getcwd()), ".env"),
        os.path.expanduser("~/.env"),
    ]
    for ep in potential_paths:
        if os.path.exists(ep):
            try:
                with open(ep, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GROQ_API_KEY=") and not line.startswith("#"):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if val:
                                return val
            except Exception:
                pass

    return ""

def get_groq_key_status() -> Dict[str, Any]:
    key = get_effective_groq_api_key()
    configured = bool(key and len(key) > 5)
    masked = f"{key[:7]}...{key[-4:]}" if configured and len(key) >= 12 else ("Configured" if configured else "")
    model = os.getenv("GROQ_MODEL", getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile"))
    return {
        "configured": configured,
        "source": "groq" if configured else "local_rag",
        "model": model if configured else "PragatiSetu Local Dynamic Engine",
        "masked_key": masked or None
    }

class PragatiSetuChatService:
    """
    Intelligent Conversational AI Copilot for PragatiSetu.
    Grounded in live database state and vector schedule embeddings.
    Seamlessly utilizes Groq LLM if GROQ_API_KEY is present, or a deeply dynamic,
    non-hardcoded local data synthesis engine if not.
    """

    def generate_chat_reply(
        self,
        payload: ChatRequest,
        db: Session
    ) -> ChatResponse:
        project_id = payload.project_id or "PROJ-ALPHA"

        # Determine latest query
        latest_query = ""
        if payload.message and payload.message.strip():
            latest_query = payload.message.strip()
        elif payload.messages:
            user_msgs = [m for m in payload.messages if m.role == "user"]
            if user_msgs:
                latest_query = user_msgs[-1].content.strip()

        if not latest_query:
            latest_query = "Provide an executive overview of project status and activities"

        # 1. Fetch live Project Stats from SQLite
        project = db.query(Project).filter(Project.project_id == project_id).first()
        proj_name = project.name if project else f"Project {project_id}"

        activities_query = db.query(ScheduleActivity).filter(ScheduleActivity.project_id == project_id)
        total_activities = activities_query.count()
        completed_activities = activities_query.filter(ScheduleActivity.status == "COMPLETED").count()
        in_progress_activities = activities_query.filter(ScheduleActivity.status == "IN_PROGRESS").count()
        not_started_activities = activities_query.filter(ScheduleActivity.status == "NOT_STARTED").count()

        avg_pct = db.query(func.avg(ScheduleActivity.percent_complete)).filter(
            ScheduleActivity.project_id == project_id
        ).scalar() or 0.0
        overall_progress = round(float(avg_pct), 1)

        total_reports = db.query(SourceReport).filter(SourceReport.project_id == project_id).count()

        # 2. Retrieve Candidate Activities via Vector Search
        retrieved_vector: List[VectorSearchResult] = []
        try:
            retrieved_vector = search_schedule_activities(
                project_id=project_id,
                query=latest_query,
                top_k=payload.top_k or 4
            )
        except Exception as e:
            logger.warning(f"Vector search in chat service: {e}")

        # Fallback keyword lookup if vector search returned empty
        candidate_ids = [r.activity_id for r in retrieved_vector]
        if not candidate_ids:
            words = [w for w in re.findall(r'\b[A-Za-z0-9_-]{3,}\b', latest_query)
                     if w.lower() not in ('what', 'show', 'project', 'schedule', 'status', 'tell', 'about', 'alpha', 'beta')]
            if words:
                fallback_acts = db.query(ScheduleActivity).filter(
                    ScheduleActivity.project_id == project_id,
                    ScheduleActivity.description.ilike(f"%{words[0]}%")
                ).limit(4).all()
                candidate_ids = [a.activity_id for a in fallback_acts]

        # 3. Retrieve full activity objects from DB for candidates
        activity_items: List[ChatActivityItem] = []
        act_db_map = {}
        if candidate_ids:
            db_acts = db.query(ScheduleActivity).filter(
                ScheduleActivity.project_id == project_id,
                ScheduleActivity.activity_id.in_(candidate_ids)
            ).all()
            act_db_map = {a.activity_id: a for a in db_acts}

        for cid in candidate_ids:
            a = act_db_map.get(cid)
            if a:
                sim = 0.85
                for vr in retrieved_vector:
                    if vr.activity_id == cid:
                        sim = vr.similarity
                        break
                activity_items.append(ChatActivityItem(
                    activity_id=a.activity_id,
                    description=a.description,
                    wbs_id=a.wbs_id or a.activity_id,
                    percent_complete=float(a.percent_complete or 0.0),
                    status=a.status,
                    similarity=round(sim, 2),
                    discipline=a.discipline
                ))

        # 4. Check for Groq API Key
        groq_api_key = get_effective_groq_api_key(payload.api_key)
        model_name = os.getenv("GROQ_MODEL", getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile"))

        if groq_api_key:
            try:
                from groq import Groq  # type: ignore
                client = Groq(api_key=groq_api_key)

                # Build Grounded Context Block
                context_activities_str = ""
                for item in activity_items:
                    context_activities_str += (
                        f"- Activity ID: {item.activity_id} | WBS: {item.wbs_id}\n"
                        f"  Description: {item.description}\n"
                        f"  Discipline: {item.discipline} | Status: {item.status} | Progress: {item.percent_complete}%\n"
                    )

                # Fetch discipline breakdown
                disciplines_breakdown = db.query(
                    ScheduleActivity.discipline,
                    func.count(ScheduleActivity.activity_id),
                    func.avg(ScheduleActivity.percent_complete)
                ).filter(
                    ScheduleActivity.project_id == project_id
                ).group_by(ScheduleActivity.discipline).all()
                disc_summary = ", ".join([
                    f"{d[0] or 'General'}: {d[1]} activities (avg {round(float(d[2] or 0), 1)}%)"
                    for d in disciplines_breakdown
                ])

                system_prompt = (
                    "You are PragatiSetu AI Copilot, a senior construction, oil & gas, and infrastructure project management AI.\n"
                    "You assist site supervisors, project managers, and planners in monitoring schedule progress, "
                    "interpreting field daily progress reports (DPRs), and linking field events to WBS activities.\n\n"
                    f"ACTIVE PROJECT CONTEXT:\n"
                    f"- Platform Name: PragatiSetu\n"
                    f"- Project: {proj_name} (ID: {project_id})\n"
                    f"- Overall Progress: {overall_progress}%\n"
                    f"- Total Activities: {total_activities} (Completed: {completed_activities}, In-Progress: {in_progress_activities}, Not Started: {not_started_activities})\n"
                    f"- Discipline Breakdown: {disc_summary}\n"
                    f"- Total Ingested Reports: {total_reports}\n\n"
                    f"RELEVANT SCHEDULE ACTIVITIES (FROM VECTOR DB):\n"
                    f"{context_activities_str or 'No specific activity matched.'}\n\n"
                    "INSTRUCTIONS:\n"
                    "1. Address the user's specific inquiry directly with natural, intelligent, analytical reasoning.\n"
                    "2. Ground your answers strictly in the real project context provided above. Do not invent fake activity numbers.\n"
                    "3. When referring to specific activities, use their exact Activity ID in backticks (e.g. `PIP-201`, `CIV-105`).\n"
                    "4. Include actionable next steps, schedule implications, or relevant page links (e.g. [Schedule](/schedule), [Reports](/reports), [Review Queue](/review-queue), [Audit Trail](/audit-trail)) where appropriate.\n"
                    "5. Format your response cleanly using GitHub-flavored markdown with headers, bullet points, and bold metrics."
                )

                messages_payload = [{"role": "system", "content": system_prompt}]
                if payload.messages:
                    for m in payload.messages[-8:]:
                        messages_payload.append({"role": m.role, "content": m.content})
                else:
                    messages_payload.append({"role": "user", "content": latest_query})

                completion = client.chat.completions.create(
                    model=model_name,
                    messages=messages_payload,
                    temperature=0.3,
                    max_tokens=850
                )

                raw_reply = completion.choices[0].message.content or ""
                mentioned_ids = [cid for cid in candidate_ids if cid in raw_reply]

                return ChatResponse(
                    reply=raw_reply,
                    grounded_candidates=mentioned_ids or candidate_ids[:4],
                    activities=activity_items,
                    project_id=project_id,
                    source="groq",
                    model=model_name
                )

            except Exception as e:
                logger.warning(f"Groq Chat call failed: {e}. Falling back to dynamic local RAG engine.")

        # 5. Local Dynamic Grounded RAG Engine (Zero hardcoding, deeply data-driven)
        reply = self._generate_local_grounded_reply(
            query=latest_query,
            project_id=project_id,
            proj_name=proj_name,
            overall_progress=overall_progress,
            total_activities=total_activities,
            completed_activities=completed_activities,
            in_progress_activities=in_progress_activities,
            not_started_activities=not_started_activities,
            total_reports=total_reports,
            activity_items=activity_items,
            db=db
        )

        return ChatResponse(
            reply=reply,
            grounded_candidates=[a.activity_id for a in activity_items[:4]],
            activities=activity_items,
            project_id=project_id,
            source="local_rag",
            model="PragatiSetu Local Dynamic Engine"
        )

    def _generate_local_grounded_reply(
        self,
        query: str,
        project_id: str,
        proj_name: str,
        overall_progress: float,
        total_activities: int,
        completed_activities: int,
        in_progress_activities: int,
        not_started_activities: int,
        total_reports: int,
        activity_items: List[ChatActivityItem],
        db: Session
    ) -> str:
        """
        Dynamically synthesizes grounded analytical responses by querying live SQLite state,
        WBS baseline records, field reports, and review events.
        """
        q = query.lower()

        # 1. Check for specific Activity ID mentions (e.g., PIP-201, CIV-105, ELE-301)
        act_id_matches = re.findall(r'\b[A-Za-z]{2,4}-\d{2,4}\b', query)
        if act_id_matches:
            target_id = act_id_matches[0].upper()
            act = db.query(ScheduleActivity).filter(
                ScheduleActivity.project_id == project_id,
                ScheduleActivity.activity_id.ilike(target_id)
            ).first()
            if act:
                # Find related field events
                related_events = db.query(ExtractedEvent).filter(
                    ExtractedEvent.identifier == act.activity_id
                ).limit(3).all()

                event_summary = ""
                if related_events:
                    event_summary = "\n".join([
                        f"  - Event on {e.event_date or 'recent'}: *{e.raw_text}* (Status: `{e.status}`, Progress: {e.percent_complete or 0}%)"
                        for e in related_events
                    ])
                else:
                    event_summary = "  - No specific field events directly tagged to this activity ID yet."

                return (
                    f"### 🎯 Activity Profile: **`{act.activity_id}`**\n\n"
                    f"- **Description:** {act.description}\n"
                    f"- **WBS Node:** `{act.wbs_id or act.activity_id}`\n"
                    f"- **Discipline:** **{act.discipline or 'General'}**\n"
                    f"- **Current Progress:** **{act.percent_complete}%** [{act.status}]\n"
                    f"- **Planned Timeline:** {act.planned_start or 'N/A'} to {act.planned_finish or 'N/A'}\n"
                    f"- **Actual Dates:** {act.actual_start or 'Not started'} to {act.actual_finish or 'In progress'}\n\n"
                    f"**Recent Field Reports & Events:**\n"
                    f"{event_summary}\n\n"
                    f"You can view this activity directly in the interactive Gantt chart on the [Schedule](/schedule) page."
                )

        # 2. Check for Specific Discipline Inquiries (Civil, Piping, Electrical, etc.)
        disciplines = ["civil", "piping", "electrical", "instrumentation", "mechanical", "structural", "safety"]
        matched_disc = next((d for d in disciplines if d in q), None)
        if matched_disc:
            disc_acts = db.query(ScheduleActivity).filter(
                ScheduleActivity.project_id == project_id,
                ScheduleActivity.discipline.ilike(f"%{matched_disc}%")
            ).all()

            if disc_acts:
                total_disc = len(disc_acts)
                done_disc = [a for a in disc_acts if a.status == "COMPLETED"]
                prog_disc = [a for a in disc_acts if a.status == "IN_PROGRESS"]
                not_started_disc = [a for a in disc_acts if a.status == "NOT_STARTED"]
                disc_avg = round(sum(float(a.percent_complete or 0.0) for a in disc_acts) / total_disc, 1)

                top_in_prog = "\n".join([
                    f"- **`{a.activity_id}`** ({a.description}): **{a.percent_complete}%**"
                    for a in prog_disc[:4]
                ]) if prog_disc else "- None currently in progress."

                return (
                    f"### 🏗️ **{matched_disc.capitalize()}** Discipline Performance: **{proj_name}**\n\n"
                    f"- **Total Activities:** **{total_disc}**\n"
                    f"- **Average Discipline Progress:** **{disc_avg}%**\n"
                    f"- **Status Breakdown:** ✅ **{len(done_disc)}** Completed | ⏳ **{len(prog_disc)}** In Progress | ⏸️ **{len(not_started_disc)}** Not Started\n\n"
                    f"**Active In-Progress Work Packages:**\n"
                    f"{top_in_prog}\n\n"
                    f"Track the critical path for {matched_disc.capitalize()} tasks in the [Schedule](/schedule) tab."
                )

        # 3. Check for Delays, Conflicts, or Review Queue Inquiries
        if any(w in q for w in ["delay", "conflict", "review", "lag", "behind", "issue", "problem", "risk"]):
            delayed_acts = db.query(ScheduleActivity).filter(
                ScheduleActivity.project_id == project_id,
                ScheduleActivity.percent_complete < 100,
                ScheduleActivity.percent_complete > 0
            ).order_by(ScheduleActivity.percent_complete.asc()).limit(5).all()

            delayed_list = "\n".join([
                f"- **`{a.activity_id}`** ({a.description}) — {a.discipline or 'General'}: **{a.percent_complete}%**"
                for a in delayed_acts
            ]) if delayed_acts else "- All in-progress activities are currently proceeding on track."

            return (
                f"### ⚠️ Schedule & Risk Analysis: **{proj_name}**\n\n"
                f"Active work packages with partial progress requiring close monitoring:\n\n"
                f"{delayed_list}\n\n"
                f"Field progress discrepancies or ambiguous daily logs are queued for supervisor confirmation in the "
                f"[Review Queue](/review-queue) before altering baseline completion percentages."
            )

        # 4. Check for Completed Tasks
        if any(w in q for w in ["completed", "finished", "done", "accomplished"]):
            completed_acts = db.query(ScheduleActivity).filter(
                ScheduleActivity.project_id == project_id,
                ScheduleActivity.status == "COMPLETED"
            ).limit(6).all()

            comp_list = "\n".join([
                f"- **`{a.activity_id}`** ({a.description}) — {a.discipline or 'General'}: **100%**"
                for a in completed_acts
            ]) if completed_acts else "- No completed activities recorded yet."

            return (
                f"### ✅ Completed Activities: **{proj_name}**\n\n"
                f"A total of **{completed_activities}** activities have reached 100% completion:\n\n"
                f"{comp_list}\n\n"
                f"View all milestones and closed WBS nodes on the [Schedule](/schedule) view."
            )

        # 5. Check for Daily Reports, DPR, or Voice Ingestion Inquiries
        if any(w in q for w in ["voice", "audio", "upload", "dpr", "report", "file", "ingest"]):
            recent_reports = db.query(SourceReport).filter(
                SourceReport.project_id == project_id
            ).order_by(SourceReport.created_at.desc()).limit(3).all()

            reports_list = "\n".join([
                f"- `{r.filename}` (Status: **{r.processing_status}**, Ingested: {r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else 'Recent'})"
                for r in recent_reports
            ]) if recent_reports else "- No reports ingested yet."

            return (
                f"### 🎙️ Field Reports & Voice Capture: **{proj_name}**\n\n"
                f"- **Total Field Reports Ingested:** **{total_reports}**\n\n"
                f"**Recent Daily Reports:**\n"
                f"{reports_list}\n\n"
                f"**How Field Ingestion Works in PragatiSetu:**\n"
                f"1. **Voice Input:** Use the microphone on the [Reports](/reports) page to speak daily updates hands-free. Transcription is processed automatically.\n"
                f"2. **DPR File Upload:** Upload PDF, Excel, or text daily progress reports for multi-event entity extraction.\n"
                f"3. **WBS Linking:** Field events are matched against baseline activities using semantic vector similarity.\n"
                f"4. **Audit Trail:** Every update is stamped in the [Audit Trail](/audit-trail) with cryptographic hashes."
            )

        # 6. Check for Audit Trail / Cryptographic Hash Inquiries
        if any(w in q for w in ["audit", "hash", "traceability", "sha-256", "cryptographic", "clear audit"]):
            audit_count = db.query(AuditRecord).filter(AuditRecord.project_id == project_id).count()
            return (
                f"### 🛡️ PragatiSetu Cryptographic Audit Trail\n\n"
                f"- **Recorded Audit Entries:** **{audit_count}**\n"
                f"- **Tamper-Evidence:** Every approved schedule update is chained using SHA-256 hashes.\n"
                f"- **Accountability:** Captures the reviewer identity, timestamp, previous vs new completion values, and AI confidence score.\n"
                f"- **Audit Maintenance:** You can inspect all ledger records or clear completed audit batches on the [Audit Trail](/audit-trail) page."
            )

        # 7. Check if Vector Retrieval matched specific activities for this query
        if activity_items:
            cards_summary = []
            for act in activity_items[:4]:
                cards_summary.append(
                    f"- **`{act.activity_id}`** — **{act.description}**\n"
                    f"  - Discipline: **{act.discipline or 'General'}** | WBS: `{act.wbs_id}`\n"
                    f"  - Progress: **{act.percent_complete}%** | Status: `{act.status}` | Similarity: `{act.similarity}`"
                )
            matched_text = "\n".join(cards_summary)

            return (
                f"### 🔍 Retrieved Schedule Activities for *\"{query}\"*\n\n"
                f"Identified **{len(activity_items)}** relevant WBS activities from the schedule index:\n\n"
                f"{matched_text}\n\n"
                f"Click any activity card below to inspect the full schedule breakdown on the [Schedule](/schedule) page."
            )

        # 8. Dynamic General Overview
        disciplines_breakdown = db.query(
            ScheduleActivity.discipline,
            func.count(ScheduleActivity.activity_id),
            func.avg(ScheduleActivity.percent_complete)
        ).filter(
            ScheduleActivity.project_id == project_id
        ).group_by(ScheduleActivity.discipline).all()

        disc_lines = "\n".join([
            f"  - **{d[0] or 'General'}**: {d[1]} activities (avg **{round(float(d[2] or 0), 1)}%** complete)"
            for d in disciplines_breakdown
        ]) if disciplines_breakdown else "  - No discipline data available."

        return (
            f"### 📊 Project Overview: **{proj_name}** (`{project_id}`)\n\n"
            f"- **Overall Schedule Progress:** **{overall_progress}%**\n"
            f"- **Total WBS Activities:** **{total_activities}**\n"
            f"  - ✅ Completed: **{completed_activities}**\n"
            f"  - ⏳ In Progress: **{in_progress_activities}**\n"
            f"  - ⏸️ Not Started: **{not_started_activities}**\n"
            f"- **Discipline Performance:**\n"
            f"{disc_lines}\n"
            f"- **Ingested Field Reports:** **{total_reports}** daily reports\n\n"
            f"You can ask me to analyze specific disciplines (Civil, Piping, Electrical), track delayed activities, explain WBS codes, or review recent daily reports."
        )
