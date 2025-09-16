def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["status"] == "healthy"


def test_dashboard_summary(client, app):
    # Ensure at least one prospect exists
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"
    assert "total_proposals" in payload["data"]
