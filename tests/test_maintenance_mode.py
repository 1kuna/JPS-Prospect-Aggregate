from app.database.models import Settings


def test_maintenance_mode_disabled_by_default(admin_client):
    response = admin_client.get("/api/admin/maintenance")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["maintenance_mode"] is False


def test_enable_and_disable_maintenance(admin_client, db_session):
    enable_resp = admin_client.post("/api/admin/maintenance", json={"enabled": True})
    assert enable_resp.status_code == 200
    payload = enable_resp.get_json()
    assert payload["data"]["maintenance_mode"] is True

    setting = db_session.query(Settings).filter_by(key="maintenance_mode").first()
    assert setting is not None
    assert setting.value == "true"

    disable_resp = admin_client.post("/api/admin/maintenance", json={"enabled": False})
    assert disable_resp.status_code == 200
    payload = disable_resp.get_json()
    assert payload["data"]["maintenance_mode"] is False

    setting = db_session.query(Settings).filter_by(key="maintenance_mode").first()
    assert setting.value == "false"


def test_maintenance_mode_blocks_public_requests(admin_client, client):
    admin_client.post("/api/admin/maintenance", json={"enabled": True})

    response = client.get("/api/prospects")
    assert response.status_code == 503
    assert "Down for Maintenance" in response.get_data(as_text=True)

    admin_client.post("/api/admin/maintenance", json={"enabled": False})


def test_admin_endpoints_accessible_during_maintenance(admin_client):
    admin_client.post("/api/admin/maintenance", json={"enabled": True})

    maintenance_resp = admin_client.get("/api/admin/maintenance")
    assert maintenance_resp.status_code == 200
    assert maintenance_resp.get_json()["data"]["maintenance_mode"] is True

    health_resp = admin_client.get("/api/admin/health")
    assert health_resp.status_code == 200
    health_data = health_resp.get_json()
    assert health_data["data"]["maintenance_mode"] is True

    admin_client.post("/api/admin/maintenance", json={"enabled": False})


def test_invalid_toggle_requests(admin_client):
    missing_resp = admin_client.post("/api/admin/maintenance", json={})
    assert missing_resp.status_code == 400
    assert missing_resp.get_json()["message"].startswith("Missing")

    invalid_resp = admin_client.post("/api/admin/maintenance", json={"enabled": "nope"})
    assert invalid_resp.status_code == 400
    assert "must be true or false" in invalid_resp.get_json()["message"]
