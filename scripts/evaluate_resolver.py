import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.db.database import Base, engine, SessionLocal
from backend.app.db.models.event import ExtractedEvent
from backend.app.db.models.report import SourceReport
from backend.app.services.baseline_importer import BaselineImporter
from backend.app.services.candidate_generator_service import CandidateGeneratorService

def evaluate_project(project_id: str, baseline_file: str, events_file: str):
    db = SessionLocal()
    try:
        # Import baseline schedule
        baseline_path = os.path.join(PROJECT_ROOT, "dataset", baseline_file)
        if os.path.exists(baseline_path):
            importer = BaselineImporter(db)
            importer.import_excel_baseline(baseline_path)

        events_path = os.path.join(PROJECT_ROOT, "dataset", events_file)
        if not os.path.exists(events_path):
            print(f"[ERROR] Events dataset not found at: {events_path}")
            return

        df_events = pd.read_excel(events_path)
        total_events = len(df_events)
        print(f"--- Evaluating Resolver Candidate Generation for {project_id} ({total_events} events) ---")

        # Create dummy source report for evaluation
        report_id = f"REP-EVAL-{project_id}"
        existing_rep = db.query(SourceReport).filter(SourceReport.report_id == report_id).first()
        if not existing_rep:
            rep = SourceReport(
                report_id=report_id,
                project_id=project_id,
                filename=events_file,
                source_type="XLSX",
                report_date=pd.to_datetime("2026-01-05").date(),
                file_hash="evalhash123",
                file_size=1000,
                stored_path="eval",
                processing_status="VALIDATED"
            )
            db.add(rep)
            db.commit()

        generator = CandidateGeneratorService(db)
        top_1_hits = 0
        top_3_hits = 0
        coverage_hits = 0

        for idx, row in df_events.iterrows():
            evt_id = f"EVT-EVAL-{project_id}-{idx:04d}"
            mapped_act = str(row.get("ground_truth_activity_id") or row.get("mapped_activity_id") or "").strip() or None

            # Create or update ExtractedEvent
            db_evt = db.query(ExtractedEvent).filter(ExtractedEvent.event_id == evt_id).first()
            if not db_evt:
                db_evt = ExtractedEvent(
                    event_id=evt_id,
                    report_id=report_id,
                    raw_text=str(row["raw_text"]),
                    event_date=pd.to_datetime(row["report_date"]).date() if pd.notnull(row.get("report_date")) else None,
                    discipline=str(row.get("reported_discipline") or row.get("discipline") or "").strip() or None,
                    identifier=str(row.get("ground_truth_identifier") or row.get("equipment_or_line_id") or "").strip() or None,
                    location=str(row.get("ground_truth_location") or row.get("location") or "").strip() or None,
                    status=str(row.get("ground_truth_status") or row.get("status") or "").strip() or None,
                    extraction_method="RULE_BASED",
                    extraction_version="v1"
                )
                db.add(db_evt)
                db.commit()

            evt, candidates, margin = generator.generate_candidates_for_event(evt_id, top_n=5)

            if len(candidates) > 0:
                coverage_hits += 1

            candidate_act_ids = [c.activity_id for c in candidates]

            if mapped_act and len(candidate_act_ids) > 0 and candidate_act_ids[0] == mapped_act:
                top_1_hits += 1

            if mapped_act and mapped_act in candidate_act_ids[:3]:
                top_3_hits += 1

        top_1_acc = (top_1_hits / total_events) * 100.0
        top_3_rec = (top_3_hits / total_events) * 100.0
        cov_pct = (coverage_hits / total_events) * 100.0

        print(f"Project: {project_id}")
        print(f"Total Ground-Truth Events: {total_events}")
        print(f"Candidate Coverage: {cov_pct:.2f}% ({coverage_hits}/{total_events})")
        print(f"Top-1 Candidate Accuracy: {top_1_acc:.2f}% ({top_1_hits}/{total_events})")
        print(f"Top-3 Candidate Recall: {top_3_rec:.2f}% ({top_3_hits}/{total_events})\n")

    finally:
        db.close()

def evaluate_all():
    Base.metadata.create_all(bind=engine)
    print("=== PragatiSetu Milestone 4 — Resolver Evaluation Engine ===\n")
    evaluate_project("PROJ-ALPHA", "01_baseline_schedule.xlsx", "02_field_report_events.xlsx")
    evaluate_project("PROJ-BETA", "08_project_beta_baseline.xlsx", "09_project_beta_reports.xlsx")

if __name__ == "__main__":
    evaluate_all()
