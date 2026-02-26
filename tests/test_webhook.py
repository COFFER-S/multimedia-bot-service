"""
Tests for webhook handling.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_application


@pytest.fixture
def client():
    """Create test client."""
    app = create_application()
    return TestClient(app)


@pytest.fixture
def sample_merge_request_payload():
    """Sample GitLab merge request webhook payload."""
    return {
        "object_kind": "merge_request",
        "event_type": "merge_request",
        "project": {
            "id": 123,
            "name": "Test Project",
            "path_with_namespace": "test-group/test-project"
        },
        "object_attributes": {
            "id": 456,
            "iid": 10,
            "source_branch": "feature/test-feature",
            "target_branch": "main",
            "state": "merged",
            "action": "merge",
            "title": "Test Feature",
            "labels": [
                {"title": "backport-to-release/v1.0", "color": "#428BCA"}
            ]
        }
    }


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "gitlab-backport-bot"


def test_webhook_info(client):
    """Test webhook info endpoint."""
    response = client.get("/webhook/gitlab")
    assert response.status_code == 200
    data = response.json()
    assert "webhook_url" in data
    assert "supported_events" in data


def test_backport_request_validation(client):
    """Test backport request validation."""
    # Missing required fields
    response = client.post("/api/backport", json={})
    assert response.status_code == 422
    
    # Invalid project path format
    response = client.post("/api/backport", json={
        "project_path": "invalid",
        "source_branch": "feature/test",
        "target_branch": "main"
    })
    # Should accept (validation happens during execution)
    assert response.status_code in [200, 500, 503]  # Depends on token config
