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
        assert data["version"] == "1.0.0"


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root(self, client):
        """Test that root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["version"] == "1.0.0"
        assert "docs" in data


class TestDisruptionEndpoints:
    """Tests for disruption API endpoints."""

    def test_get_disruption_not_found(self, client):
        """Test getting a non-existent disruption."""
        response = client.get("/api/disruptions/non-existent-id")
        # Either 404 (not found) or 401 (unauthorized) is acceptable
        assert response.status_code in [404, 401]

    def test_list_disruptions(self, client):
        """Test listing disruptions."""
        response = client.get("/api/disruptions")
        # Should return 200 (empty list) or require auth
        assert response.status_code in [200, 401]
