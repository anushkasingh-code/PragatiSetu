def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"

def test_database_connectivity(db_session):
    from sqlalchemy import text
    result = db_session.execute(text("SELECT 1")).scalar()
    assert result == 1
