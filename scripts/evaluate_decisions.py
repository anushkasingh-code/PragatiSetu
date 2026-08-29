import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.db.database import Base, engine, SessionLocal
from backend.app.db.models.event import ExtractedEvent
from backend.app.db.models.report import SourceReport
from backend.app.db.models.activity import ScheduleActivity
from backend.app.services.baseline_importer import BaselineImporter
from backend.app.services.decision_service import DecisionService

def evaluate_project_decisions(project_id: str, baseline_file: str, events_file: str):
    db = SessionLocal()
    try:
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
        print(f"=== Safety Decision Routing Evaluation for {project_id} ({total_events} events) ===")

        report_id = f"REP-DEC-EVAL-{project_id}"
        existing_rep = db.query(SourceReport).filter(SourceReport.report_id == report_id).first()
        if not existing_rep:
            rep = SourceReport(
                report_id=report_id,
                project_id=project_id,
                filename=events_file,
                source_type="XLSX",
                report_date=pd.to_datetime("2026-01-05").date(),
                file_hash="evaldechash123",
                file_size=1000,
                stored_path="eval_dec",
                processing_status="VALIDATED"
            )
            db.add(rep)
            db.commit()

        service = DecisionService(db)

        auto_link_count = 0
        correct_auto_link_count = 0
        incorrect_auto_link_count = 0
        human_review_count = 0
        unplanned_review_count = 0
        ignore_count = 0

        for idx, row in df_events.iterrows():
            evt_id = f"EVT-DEC-EVAL-{project_id}-{idx:04d}"
            mapped_act = str(row["mapped_activity_id"]).strip() if pd.notnull(row.get("mapped_activity_id")) else None

            db_evt = db.query(ExtractedEvent).filter(ExtractedEvent.event_id == evt_id).first()
            if not db_evt:
                db_evt = ExtractedEvent(
                    event_id=evt_id,
                    report_id=report_id,
                    raw_text=str(row["raw_text"]),
                    event_date=pd.to_datetime(row["report_date"]).date() if pd.notnull(row.get("report_date")) else None,
                    discipline=str(row["discipline"]) if pd.notnull(row.get("discipline")) else None,
                    identifier=str(row["equipment_or_line_id"]) if pd.notnull(row.get("equipment_or_line_id")) else None,
                    location=str(row["location"]) if pd.notnull(row.get("location")) else None,
                    status=str(row["status"]) if pd.notnull(row.get("status")) else None,
                    extraction_method="RULE_BASED",
                    extraction_version="v1"
                )
                db.add(db_evt)
                db.commit()

            evt, decision = service.make_decision_for_event(evt_id)
            dec_type = decision.decision

            if dec_type == "AUTO_LINK":
                auto_link_count += 1
                if mapped_act and decision.top_activity_id == mapped_act:
                    correct_auto_link_count += 1
                else:
                    incorrect_auto_link_count += 1
            elif dec_type == "HUMAN_REVIEW":
                human_review_count += 1
            elif dec_type == "UNPLANNED_REVIEW":
                unplanned_review_count += 1
            elif dec_type == "IGNORE":
                ignore_count += 1

        auto_link_pct = (auto_link_count / total_events) * 100.0
        human_review_pct = (human_review_count / total_events) * 100.0
        unplanned_pct = (unplanned_review_count / total_events) * 100.0
        ignore_pct = (ignore_count / total_events) * 100.0

        auto_link_precision = (correct_auto_link_count / auto_link_count * 100.0) if auto_link_count > 0 else 0.0
        incorrect_auto_link_rate = (incorrect_auto_link_count / auto_link_count * 100.0) if auto_link_count > 0 else 0.0

        print(f"Project: {project_id}")
        print(f"Total Events: {total_events}")
        print(f"AUTO_LINK Decisions: {auto_link_count} ({auto_link_pct:.2f}%)")
        print(f"  |- AUTO_LINK Precision: {auto_link_precision:.2f}% ({correct_auto_link_count}/{auto_link_count})")
        print(f"  |- Incorrect AUTO_LINK Rate: {incorrect_auto_link_rate:.2f}% ({incorrect_auto_link_count}/{auto_link_count})")
        print(f"HUMAN_REVIEW Decisions: {human_review_count} ({human_review_pct:.2f}%)")
        print(f"UNPLANNED_REVIEW Decisions: {unplanned_review_count} ({unplanned_pct:.2f}%)")
        print(f"IGNORE Decisions: {ignore_count} ({ignore_pct:.2f}%)\n")

    finally:
        db.close()

def main():
    Base.metadata.create_all(bind=engine)
    print("=== PragatiSetu Milestone 5 Decision Evaluation Engine ===\n")
    evaluate_project_decisions("PROJ-ALPHA", "01_baseline_schedule.xlsx", "02_field_report_events.xlsx")
    evaluate_project_decisions("PROJ-BETA", "08_project_beta_baseline.xlsx", "09_project_beta_reports.xlsx")

if __name__ == "__main__":
    main()
