import os
import pytest
from datetime import date
from backend.app.services.baseline_importer import BaselineImporter
from backend.app.services.decision_service import DecisionService
from backend.app.services.evidence_service import calculate_evidence_completeness
from backend.app.services.decision_policy import evaluate_decision_policy, DecisionEnum
from backend.app.db.models.report import SourceReport
from backend.app.db.models.event import ExtractedEvent
from backend.app.db.models.candidate import MatchCandidate
from backend.app.db.models.decision import MatchDecision
from backend.app.db.models.activity import ScheduleActivity

@pytest.fixture(autouse=True)
def setup_data(db_session):
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dataset_path = os.path.join(project_root, "dataset", "01_baseline_schedule.xlsx")
    if os.path.exists(dataset_path):
        importer = BaselineImporter(db_session)
        importer.import_excel_baseline(dataset_path)

def create_event(db_session, event_id="EVT-DEC-001", raw_text="24P201 spool erection started near Rack B", project_id="PROJ-ALPHA"):
    rep = db_session.query(SourceReport).filter(SourceReport.project_id == project_id).first()
    if not rep:
        rep = SourceReport(
            report_id=f"REP-{project_id}",
            project_id=project_id,
            filename="report.txt",
            source_type="TXT",
            report_date=date(2026, 1, 5),
            file_hash="dummyhashdec",
            file_size=100,
            stored_path="pathdec",
            processing_status="VALIDATED"
        )
        db_session.add(rep)
        db_session.commit()

    evt = ExtractedEvent(
        event_id=event_id,
        report_id=rep.report_id,
        raw_text=raw_text,
        event_date=date(2026, 1, 5),
        discipline="Piping",
        action="erection",
        object="spool",
        identifier="24-P-201",
        location="Rack-B",
        status="STARTED",
        quantity=10.0,
        unit="m",
        extraction_method="RULE_BASED",
        extraction_version="v1"
    )
    db_session.add(evt)
    db_session.commit()
    return evt

class DummyCandidate:
    def __init__(self, overall_score=90.0, identifier_score=100.0, discipline_score=100.0, location_score=100.0, action_score=100.0, fuzzy_score=85.0, semantic_score=90.0, temporal_score=100.0, dependency_score=100.0):
        self.overall_score = overall_score
        self.identifier_score = identifier_score
        self.discipline_score = discipline_score
        self.location_score = location_score
        self.action_score = action_score
        self.fuzzy_score = fuzzy_score
        self.semantic_score = semantic_score
        self.temporal_score = temporal_score
        self.dependency_score = dependency_score
        self.activity_id = "ACT-ALPHA-020"

def test_1_autolink_routing():
    evt = DummyCandidate()
    cands = [DummyCandidate(overall_score=90.0), DummyCandidate(overall_score=60.0)]
    dec, _ = evaluate_decision_policy(evt, cands, evidence_completeness=100.0, top_2_margin=30.0)
    assert dec == DecisionEnum.AUTO_LINK

def test_2_weak_completeness_routes_human_review():
    evt = DummyCandidate()
    cands = [DummyCandidate(overall_score=90.0), DummyCandidate(overall_score=60.0)]
    dec, _ = evaluate_decision_policy(evt, cands, evidence_completeness=50.0, top_2_margin=30.0)
    assert dec == DecisionEnum.HUMAN_REVIEW

def test_3_small_margin_routes_human_review():
    evt = DummyCandidate()
    cands = [DummyCandidate(overall_score=90.0), DummyCandidate(overall_score=88.0)]
    dec, _ = evaluate_decision_policy(evt, cands, evidence_completeness=100.0, top_2_margin=2.0)
    assert dec == DecisionEnum.HUMAN_REVIEW

def test_4_medium_score_routes_human_review():
    cands = [DummyCandidate(overall_score=75.0), DummyCandidate(overall_score=50.0)]
    dec, _ = evaluate_decision_policy(DummyCandidate(), cands, evidence_completeness=100.0, top_2_margin=25.0)
    assert dec == DecisionEnum.HUMAN_REVIEW

def test_5_low_score_routes_unplanned_review():
    cands = [DummyCandidate(overall_score=30.0)]
    dec, _ = evaluate_decision_policy(DummyCandidate(), cands, evidence_completeness=100.0, top_2_margin=10.0)
    assert dec == DecisionEnum.UNPLANNED_REVIEW

def test_6_no_candidates_routes_unplanned_review():
    dec, _ = evaluate_decision_policy(DummyCandidate(), [], evidence_completeness=100.0, top_2_margin=None)
    assert dec == DecisionEnum.UNPLANNED_REVIEW

def test_7_administrative_text_routes_ignore():
    class AdminEvent:
        raw_text = "Site safety meeting held today. Toolbox talk completed."
        identifier = None
    dec, _ = evaluate_decision_policy(AdminEvent(), [], evidence_completeness=0.0, top_2_margin=None)
    assert dec == DecisionEnum.IGNORE

def test_8_evidence_completeness_calculation(db_session):
    evt = create_event(db_session, event_id="EVT-COMP-01")
    score, missing = calculate_evidence_completeness(evt)
    assert score == 100.0
    assert len(missing) == 0

def test_9_missing_evidence_tracking(db_session):
    evt = create_event(db_session, event_id="EVT-MISS-01", raw_text="Spool erection started")
    evt.identifier = None
    evt.location = None
    evt.quantity = None

    score, missing = calculate_evidence_completeness(evt)
    assert "identifier" in missing
    assert "location" in missing
    assert "quantity" in missing

def test_10_threshold_exactly_85_70_12():
    cands = [DummyCandidate(overall_score=85.0), DummyCandidate(overall_score=73.0)]
    dec, _ = evaluate_decision_policy(DummyCandidate(), cands, evidence_completeness=70.0, top_2_margin=12.0)
    assert dec == DecisionEnum.AUTO_LINK

def test_11_below_threshold_score_84():
    cands = [DummyCandidate(overall_score=84.0), DummyCandidate(overall_score=70.0)]
    dec, _ = evaluate_decision_policy(DummyCandidate(), cands, evidence_completeness=70.0, top_2_margin=14.0)
    assert dec == DecisionEnum.HUMAN_REVIEW

def test_12_below_threshold_completeness_69():
    cands = [DummyCandidate(overall_score=85.0), DummyCandidate(overall_score=70.0)]
    dec, _ = evaluate_decision_policy(DummyCandidate(), cands, evidence_completeness=69.0, top_2_margin=15.0)
    assert dec == DecisionEnum.HUMAN_REVIEW

def test_13_below_threshold_margin_11():
    cands = [DummyCandidate(overall_score=85.0), DummyCandidate(overall_score=74.0)]
    dec, _ = evaluate_decision_policy(DummyCandidate(), cands, evidence_completeness=70.0, top_2_margin=11.0)
    assert dec == DecisionEnum.HUMAN_REVIEW

def test_14_single_candidate_handling():
    cands = [DummyCandidate(overall_score=90.0)]
    dec, _ = evaluate_decision_policy(DummyCandidate(), cands, evidence_completeness=90.0, top_2_margin=None)
    assert dec == DecisionEnum.AUTO_LINK

def test_15_decision_service_execution(db_session):
    evt = create_event(db_session, event_id="EVT-SERVICE-01")
    service = DecisionService(db_session)
    evt_out, dec = service.make_decision_for_event("EVT-SERVICE-01")

    assert dec is not None
    assert dec.decision in ["AUTO_LINK", "HUMAN_REVIEW", "UNPLANNED_REVIEW", "IGNORE"]
    assert dec.match_confidence >= 0.0
    assert dec.evidence_completeness >= 0.0

def test_16_decision_persistence(db_session):
    create_event(db_session, event_id="EVT-PERSIST-DEC")
    service = DecisionService(db_session)
    service.make_decision_for_event("EVT-PERSIST-DEC")

    persisted = db_session.query(MatchDecision).filter(MatchDecision.event_id == "EVT-PERSIST-DEC").first()
    assert persisted is not None
    assert persisted.decision_id is not None

def test_17_idempotency_upserts_single_record(db_session):
    create_event(db_session, event_id="EVT-IDEMP-DEC")
    service = DecisionService(db_session)
    
    service.make_decision_for_event("EVT-IDEMP-DEC")
    cnt1 = db_session.query(MatchDecision).filter(MatchDecision.event_id == "EVT-IDEMP-DEC").count()

    service.make_decision_for_event("EVT-IDEMP-DEC")
    cnt2 = db_session.query(MatchDecision).filter(MatchDecision.event_id == "EVT-IDEMP-DEC").count()

    assert cnt1 == 1
    assert cnt2 == 1

def test_18_scoring_and_matcher_versions(db_session):
    create_event(db_session, event_id="EVT-VER-DEC")
    service = DecisionService(db_session)
    _, dec = service.make_decision_for_event("EVT-VER-DEC")

    assert dec.matcher_version == "v1"
    assert dec.scoring_policy_version == "v1"

def test_19_derived_reasons_output(db_session):
    create_event(db_session, event_id="EVT-REASON-DEC")
    service = DecisionService(db_session)
    _, dec = service.make_decision_for_event("EVT-REASON-DEC")

    assert dec.reasons is not None
    assert isinstance(dec.reasons, list) and len(dec.reasons) > 0

def test_20_zero_schedule_modification_guarantee(db_session):
    # Retrieve initial state of all activities
    initial_activities = db_session.query(ScheduleActivity).all()
    initial_states = {a.activity_id: (a.actual_start, a.actual_finish, a.percent_complete, a.status) for a in initial_activities}

    evt = create_event(db_session, event_id="EVT-NO-MUTATE")
    service = DecisionService(db_session)
    service.make_decision_for_event("EVT-NO-MUTATE")

    current_activities = db_session.query(ScheduleActivity).all()
    current_states = {a.activity_id: (a.actual_start, a.actual_finish, a.percent_complete, a.status) for a in current_activities}

    assert initial_states == current_states

def test_21_api_create_decision(client, db_session):
    create_event(db_session, event_id="EVT-API-DEC")
    res = client.post("/events/EVT-API-DEC/decision")
    assert res.status_code == 200
    body = res.json()
    assert body["decision"] in ["AUTO_LINK", "HUMAN_REVIEW", "UNPLANNED_REVIEW", "IGNORE"]
    assert "reasons" in body

def test_22_api_get_decision(client, db_session):
    create_event(db_session, event_id="EVT-API-GET-DEC")
    client.post("/events/EVT-API-GET-DEC/decision")

    res = client.get("/events/EVT-API-GET-DEC/decision")
    assert res.status_code == 200
    assert res.json()["event_id"] == "EVT-API-GET-DEC"

def test_23_api_nonexistent_event(client):
    res = client.post("/events/NONEXISTENT-EVT-ID/decision")
    assert res.status_code == 404

def test_24_api_get_nonexistent_decision(client, db_session):
    create_event(db_session, event_id="EVT-NO-DEC-YET")
    res = client.get("/events/EVT-NO-DEC-YET/decision")
    assert res.status_code == 404
