import os
from backend.app.services.baseline_importer import BaselineImporter

def test_api_projects_and_activities(client, db_session):
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dataset_path = os.path.join(project_root, "dataset", "01_baseline_schedule.xlsx")
    
    importer = BaselineImporter(db_session)
    importer.import_excel_baseline(dataset_path)

    # 1. GET /projects
    res_proj = client.get("/projects")
    assert res_proj.status_code == 200
    projects = res_proj.json()
    assert len(projects) >= 1
    assert projects[0]["project_id"] == "PROJ-ALPHA"

    # 2. GET /projects/PROJ-ALPHA
    res_single_proj = client.get("/projects/PROJ-ALPHA")
    assert res_single_proj.status_code == 200
    assert res_single_proj.json()["name"].startswith("Project Alpha")

    # 3. GET /projects/PROJ-ALPHA/wbs
    res_wbs = client.get("/projects/PROJ-ALPHA/wbs")
    assert res_wbs.status_code == 200
    wbs_nodes = res_wbs.json()
    assert len(wbs_nodes) >= 1

    # 4. GET /projects/PROJ-ALPHA/activities
    res_acts = client.get("/projects/PROJ-ALPHA/activities")
    assert res_acts.status_code == 200
    activities = res_acts.json()
    assert len(activities) == 75

    # 5. GET /activities/{activity_id}
    first_act_id = activities[0]["activity_id"]
    res_single_act = client.get(f"/activities/{first_act_id}")
    assert res_single_act.status_code == 200
    act_data = res_single_act.json()
    assert act_data["activity_id"] == first_act_id
    assert act_data["project_id"] == "PROJ-ALPHA"
    assert "planned_start" in act_data
    assert "planned_finish" in act_data

    # 6. GET /projects/NONEXISTENT -> 404
    res_404_proj = client.get("/projects/NONEXISTENT_PROJ")
    assert res_404_proj.status_code == 404

    # 7. GET /activities/NONEXISTENT -> 404
    res_404_act = client.get("/activities/NONEXISTENT_ACT")
    assert res_404_act.status_code == 404

def test_delete_project_success(client, db_session):
    # Create a temporary project to delete
    res_create = client.post("/projects", json={
        "project_id": "TEMP-DELETE-TEST",
        "name": "Temporary Delete Test Project",
        "description": "A temp project for delete testing",
        "status": "Planning"
    })
    assert res_create.status_code == 201
    
    # Delete the temporary project
    res = client.delete("/projects/TEMP-DELETE-TEST")
    assert res.status_code == 200
    assert res.json()["message"] == "Project 'TEMP-DELETE-TEST' deleted successfully."

    # Verify cascading delete
    res_proj = client.get("/projects/TEMP-DELETE-TEST")
    assert res_proj.status_code == 404

    res_acts = client.get("/projects/TEMP-DELETE-TEST/activities")
    assert res_acts.status_code == 404

def test_delete_project_not_found(client):
    res = client.delete("/projects/NONEXISTENT_PROJ")
    assert res.status_code == 404
