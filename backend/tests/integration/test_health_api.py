"""Integration tests for Health and API endpoints."""


def test_get_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["schema_version"] == "1.0"
    assert "db_status" in data
    assert "ai_mode" in data


def test_openapi_schema_generation(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "RoboWitness API"
    assert "/api/health" in schema["paths"]
    assert "/api/scenarios/reference" in schema["paths"]
    assert "/api/runs" in schema["paths"]
    assert "/api/fixes/verify" in schema["paths"]
