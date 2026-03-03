"""
API smoke test script to verify Milestone 3 implementation.
Tests authentication, pipeline execution, scenario approval, and audit logs.
"""
import sys
import time
from typing import Any, Optional

import requests

# Configuration
BASE_URL = "http://localhost:8000"
MANAGER_USERNAME = "manager_01"
MANAGER_PASSWORD = "password"


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"✓ {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"✗ {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"  {message}")


class APIClient:
    """Simple API client for testing."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.headers: dict[str, str] = {}

    def login(self, username: str, password: str) -> dict[str, Any]:
        """Login and store token."""
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            json={"username": username, "password": password},
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        return data

    def get(self, path: str, **kwargs) -> requests.Response:
        """Make GET request with auth."""
        return requests.get(
            f"{self.base_url}{path}", headers=self.headers, **kwargs
        )

    def post(self, path: str, **kwargs) -> requests.Response:
        """Make POST request with auth."""
        return requests.post(
            f"{self.base_url}{path}", headers=self.headers, **kwargs
        )


def main() -> int:
    """Run smoke tests."""
    print_section("API Smoke Test - Milestone 3")

    client = APIClient(BASE_URL)

    try:
        # Test 1: Health check
        print_section("1. Health Check")
        response = requests.get(f"{BASE_URL}/health")
        response.raise_for_status()
        print_success("API is healthy")

        # Test 2: Login
        print_section("2. Authentication")
        login_data = client.login(MANAGER_USERNAME, MANAGER_PASSWORD)
        print_success(f"Logged in as {MANAGER_USERNAME}")
        print_info(f"Role: {login_data['role']}")
        print_info(f"Token: {login_data['access_token'][:20]}...")

        # Test 3: Get current user
        response = client.get("/api/auth/me")
        response.raise_for_status()
        user_info = response.json()
        print_success(f"User info retrieved: {user_info['username']}")

        # Test 4: List disruptions
        print_section("3. List Disruptions")
        response = client.get("/api/disruptions", params={"status": "open"})
        response.raise_for_status()
        disruptions = response.json()
        print_success(f"Found {len(disruptions)} open disruptions")

        if not disruptions:
            print_error("No open disruptions found. Run seed_data.py first.")
            return 1

        disruption = disruptions[0]
        disruption_id = disruption["id"]
        print_info(f"Using disruption: {disruption_id}")
        print_info(f"Type: {disruption['type']}, Severity: {disruption['severity']}")

        # Test 5: Start pipeline run
        print_section("4. Start Pipeline Run")
        response = client.post(
            "/api/pipeline/run",
            json={"disruption_id": disruption_id},
        )
        response.raise_for_status()
        pipeline_data = response.json()
        pipeline_run_id = pipeline_data["pipeline_run_id"]
        print_success(f"Pipeline started: {pipeline_run_id}")

        # Test 6: Poll pipeline status
        print_section("5. Poll Pipeline Status")
        max_wait = 120  # 2 minutes
        poll_interval = 3  # 3 seconds
        elapsed = 0

        while elapsed < max_wait:
            response = client.get(f"/api/pipeline/{pipeline_run_id}/status")
            response.raise_for_status()
            status_data = response.json()

            status = status_data["status"]
            progress = status_data["progress"]
            current_step = status_data.get("current_step", "unknown")

            print_info(
                f"Status: {status} | Step: {current_step} | Progress: {progress:.0%}"
            )

            if status == "done":
                print_success("Pipeline completed successfully")
                if status_data.get("final_summary_json"):
                    summary = status_data["final_summary_json"]
                    print_info(
                        f"Impacted orders: {summary.get('impacted_orders_count', 0)}"
                    )
                    print_info(
                        f"Scenarios generated: {summary.get('scenarios_count', 0)}"
                    )
                break
            elif status == "failed":
                print_error(f"Pipeline failed: {status_data.get('error_message')}")
                return 1

            time.sleep(poll_interval)
            elapsed += poll_interval
        else:
            print_error(f"Pipeline did not complete within {max_wait} seconds")
            return 1

        # Test 7: List pending scenarios
        print_section("6. List Pending Scenarios")
        response = client.get("/api/scenarios/pending")
        response.raise_for_status()
        pending_scenarios = response.json()
        print_success(f"Found {len(pending_scenarios)} pending scenarios")

        if not pending_scenarios:
            print_error("No pending scenarios found")
            return 1

        # Show first few scenarios
        for i, scenario in enumerate(pending_scenarios[:3], 1):
            print_info(
                f"{i}. {scenario['action_type']} for order {scenario['order_id']} "
                f"(score: {scenario['score_json'].get('overall_score', 'N/A')})"
            )

        # Test 8: Approve a scenario
        print_section("7. Approve Scenario")
        scenario_to_approve = pending_scenarios[0]
        scenario_id = scenario_to_approve["scenario_id"]

        print_info(f"Approving scenario: {scenario_id}")
        print_info(f"Action: {scenario_to_approve['action_type']}")
        print_info(f"Order: {scenario_to_approve['order_id']}")

        response = client.post(
            f"/api/scenarios/{scenario_id}/approve",
            json={"note": "Approved via smoke test"},
        )

        if response.status_code == 422:
            # Constraint violation - this is expected for some scenarios
            error_data = response.json()
            print_info(
                f"Scenario could not be applied (constraint violation): "
                f"{error_data.get('detail', {}).get('error', {}).get('message', 'Unknown')}"
            )
            print_success("Constraint validation working correctly")
        else:
            response.raise_for_status()
            approval_data = response.json()
            print_success(f"Scenario approved: {approval_data['status']}")
            print_info(f"Decision log: {approval_data['decision_log_id']}")

            # Show applied changes
            changes = approval_data.get("applied_changes", {})
            if changes.get("changes"):
                print_info(f"Applied {len(changes['changes'])} changes:")
                for change in changes["changes"][:3]:
                    print_info(f"  - {change}")

        # Test 9: Get audit logs
        print_section("8. Audit Logs")
        response = client.get(
            "/api/audit-logs",
            params={"pipeline_run_id": pipeline_run_id, "limit": 10},
        )
        response.raise_for_status()
        audit_logs = response.json()
        print_success(f"Retrieved {len(audit_logs)} audit log entries")

        # Show some logs
        for i, log in enumerate(audit_logs[:3], 1):
            print_info(
                f"{i}. {log['agent_name']}: {log['human_decision']} "
                f"(confidence: {log['confidence_score']:.2f})"
            )

        # Test 10: Dashboard
        print_section("9. Dashboard Summary")
        response = client.get("/api/dashboard")
        response.raise_for_status()
        dashboard = response.json()
        print_success("Dashboard data retrieved")
        print_info(f"Active disruptions: {dashboard['active_disruptions_count']}")
        print_info(f"Pending scenarios: {dashboard['pending_scenarios_count']}")
        print_info(f"Approval queue: {dashboard['approval_queue_count']}")
        print_info(
            f"Avg SLA risk: {dashboard['avg_sla_risk_pending']:.1%}"
        )
        print_info(
            f"Est. cost impact: ${dashboard['estimated_cost_impact_pending']:.2f}"
        )

        # Success!
        print_section("✅ All Tests Passed")
        print_success("Milestone 3 API is working correctly")
        return 0

    except requests.exceptions.ConnectionError:
        print_error("Could not connect to API. Is the server running?")
        print_info("Start server with: uvicorn app.main:app --reload")
        return 1

    except requests.exceptions.HTTPError as e:
        print_error(f"HTTP error: {e}")
        if e.response is not None:
            print_info(f"Response: {e.response.text}")
        return 1

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
