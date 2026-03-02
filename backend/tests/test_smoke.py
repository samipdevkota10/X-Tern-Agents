"""
Smoke tests to verify basic functionality.
"""
import pytest


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check(self, client):
        """Test that health endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "0.1.0"


class TestCasesEndpoints:
    """Tests for cases CRUD endpoints."""

    def test_create_case(self, client):
        """Test creating a new case."""
        case_data = {
            "title": "Test Case",
            "description": "This is a test case",
            "priority": "high",
        }
        response = client.post("/cases", json=case_data)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Case"
        assert data["description"] == "This is a test case"
        assert data["priority"] == "high"
        assert "id" in data
        assert data["status"] == "open"

    def test_list_cases(self, client):
        """Test listing cases."""
        response = client.get("/cases")
        assert response.status_code == 200
        data = response.json()
        assert "cases" in data
        assert "total" in data
        assert isinstance(data["cases"], list)

    def test_get_case_not_found(self, client):
        """Test getting a non-existent case."""
        response = client.get("/cases/non-existent-id")
        assert response.status_code == 404

    def test_append_decision(self, client):
        """Test appending a decision to a case."""
        # First create a case
        case_data = {
            "title": "Decision Test Case",
            "description": "Case for testing decisions",
        }
        create_response = client.post("/cases", json=case_data)
        case_id = create_response.json()["id"]

        # Then append a decision
        decision_data = {
            "decision": "Approved",
            "made_by": "test@example.com",
            "reason": "Meets all criteria",
            "approved": True,
        }
        response = client.post(f"/cases/{case_id}/decisions", json=decision_data)
        assert response.status_code == 200
        data = response.json()
        assert len(data["decisions"]) == 1
        assert data["decisions"][0]["decision"] == "Approved"
