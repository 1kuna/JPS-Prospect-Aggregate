"""
Test maintenance mode functionality.
"""

import pytest
from app.database.models import Settings


def test_maintenance_mode_disabled_by_default(client, db_session):
    """Test that maintenance mode is disabled by default."""
    response = client.get('/api/admin/maintenance')
    assert response.status_code == 200
    data = response.get_json()
    assert data['maintenance_mode'] is False


def test_enable_maintenance_mode(client, db_session):
    """Test enabling maintenance mode."""
    # Enable maintenance mode
    response = client.post('/api/admin/maintenance', json={'enabled': True})
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['maintenance_mode'] is True
    
    # Verify it's enabled
    response = client.get('/api/admin/maintenance')
    assert response.status_code == 200
    data = response.get_json()
    assert data['maintenance_mode'] is True


def test_disable_maintenance_mode(client, db_session):
    """Test disabling maintenance mode."""
    # First enable it
    client.post('/api/admin/maintenance', json={'enabled': True})
    
    # Then disable it
    response = client.post('/api/admin/maintenance', json={'enabled': False})
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['maintenance_mode'] is False
    
    # Verify it's disabled
    response = client.get('/api/admin/maintenance')
    assert response.status_code == 200
    data = response.get_json()
    assert data['maintenance_mode'] is False


def test_maintenance_mode_blocks_regular_requests(client, db_session):
    """Test that maintenance mode blocks regular requests."""
    # Enable maintenance mode
    client.post('/api/admin/maintenance', json={'enabled': True})
    
    # Try to access a regular endpoint - should get maintenance page
    response = client.get('/api/prospects')
    assert response.status_code == 503
    assert 'Down for Maintenance' in response.get_data(as_text=True)


def test_admin_endpoints_work_during_maintenance(client, db_session):
    """Test that admin endpoints still work during maintenance mode."""
    # Enable maintenance mode
    client.post('/api/admin/maintenance', json={'enabled': True})
    
    # Admin endpoints should still work
    response = client.get('/api/admin/maintenance')
    assert response.status_code == 200
    data = response.get_json()
    assert data['maintenance_mode'] is True
    
    # Health check should work
    response = client.get('/api/admin/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert data['maintenance_mode'] is True


def test_invalid_maintenance_toggle_request(client, db_session):
    """Test invalid requests to maintenance toggle."""
    # Missing enabled parameter
    response = client.post('/api/admin/maintenance', json={})
    assert response.status_code == 400
    
    # Invalid enabled parameter
    response = client.post('/api/admin/maintenance', json={'enabled': 'invalid'})
    assert response.status_code == 400


def test_settings_database_interaction(client, db_session):
    """Test that maintenance mode properly interacts with database."""
    # Enable maintenance mode
    client.post('/api/admin/maintenance', json={'enabled': True})
    
    # Check database directly
    setting = db_session.query(Settings).filter_by(key='maintenance_mode').first()
    assert setting is not None
    assert setting.value == 'true'
    
    # Disable maintenance mode
    client.post('/api/admin/maintenance', json={'enabled': False})
    
    # Check database again
    setting = db_session.query(Settings).filter_by(key='maintenance_mode').first()
    assert setting is not None
    assert setting.value == 'false'