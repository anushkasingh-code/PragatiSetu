import os
from backend.app.services.baseline_importer import BaselineImporter
from backend.app.db.models.project import Project
from backend.app.db.models.wbs import WBSNode
from backend.app.db.models.activity import ScheduleActivity

def test_project_alpha_import(db_session):
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dataset_path = os.path.join(project_root, "dataset", "01_baseline_schedule.xlsx")
    
    assert os.path.exists(dataset_path), "Baseline dataset file missing for test"

    importer = BaselineImporter(db_session)
    stats = importer.import_excel_baseline(dataset_path)

    assert stats["projects_imported"] >= 1
    assert stats["wbs_nodes_imported"] >= 1
    assert stats["activities_imported"] == 75

    proj = db_session.query(Project).filter(Project.project_id == "PROJ-ALPHA").first()
    assert proj is not None
    assert proj.name.startswith("PragatiSetu")

    activities = db_session.query(ScheduleActivity).filter(ScheduleActivity.project_id == "PROJ-ALPHA").all()
    assert len(activities) == 75
