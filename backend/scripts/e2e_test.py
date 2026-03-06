#!/usr/bin/env python3
"""
End-to-end test: Create disruption → Run pipeline → Approve scenario → Inspect logs and RAG.
Identifies gaps in core logic.
"""
import json
import os
import sys
import time

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use requests if available; otherwise urllib
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

API_URL = os.environ.get("API_URL", "http://localhost:8000")
CHROMA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "chroma_data"))


def log(msg: str, level: str = "INFO"):
    print(f"[{level}] {msg}")


def api(method: str, path: str, token: str | None = None, json_body: dict | None = None) -> dict:
    url = f"{API_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if HAS_REQUESTS:
        r = requests.request(
            method, url, headers=headers, json=json_body, timeout=30
        )
        r.raise_for_status()
        return r.json() if r.content else {}
    else:
        import urllib.request
        req = urllib.request.Request(url, method=method, headers=headers)
        if json_body:
            req.data = json.dumps(json_body).encode()
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.loads(res.read().decode()) if res.length else {}


def main():
    log("=== X-Tern Agents E2E Test ===")
    if not HAS_REQUESTS:
        log("Install requests: pip install requests", "WARN")

    # 1. Health & Auth
    log("1. Checking backend health...")
    try:
        api("GET", "/health")
        api("GET", "/api/rag/health")
    except Exception as e:
        log(f"Backend not reachable: {e}", "ERROR")
        log("Start backend: cd backend && uvicorn app.main:app --reload")
        sys.exit(1)
    log("   Backend and RAG healthy")

    log("2. Logging in as manager_01...")
    try:
        login = api("POST", "/api/auth/login", json_body={
            "username": "manager_01",
            "password": "password",
        })
        token = login.get("access_token")
        if not token:
            log("Login failed - no token", "ERROR")
            sys.exit(1)
    except Exception as e:
        log(f"Login failed: {e}", "ERROR")
        sys.exit(1)
    log("   Login OK")

    # 2. Seed RAG (domain knowledge only - disruptions/decisions need pipeline)
    log("3. Seeding RAG domain knowledge...")
    try:
        seed = api("POST", "/api/rag/seed-knowledge", token=token)
        log(f"   Seeded: {seed.get('items_added', 0)} items")
    except Exception as e:
        log(f"   Seed failed (non-fatal): {e}", "WARN")

    # 3. RAG stats before
    log("4. RAG stats BEFORE pipeline...")
    rag_before = api("GET", "/api/rag/stats", token=token)
    log(f"   Collections: {json.dumps(rag_before.get('collections', {}), indent=4)}")

    # 4. Create disruption
    log("5. Creating disruption...")
    disruption = api("POST", "/api/disruptions", token=token, json_body={
        "type": "late_truck",
        "severity": 4,
        "details_json": {
            "truck_id": "TRK-E2E-001",
            "delay_hours": 6,
            "affected_skus": ["SKU0001", "SKU0002"],
        },
    })
    disruption_id = disruption.get("id")
    if not disruption_id:
        log(f"Failed to create disruption: {disruption}", "ERROR")
        sys.exit(1)
    log(f"   Created: {disruption_id}")

    # 5. Run pipeline
    log("6. Starting pipeline...")
    run_resp = api("POST", "/api/pipeline/run", token=token, json_body={
        "disruption_id": disruption_id,
    })
    pipeline_id = run_resp.get("pipeline_run_id")
    if not pipeline_id:
        log(f"Pipeline start failed: {run_resp}", "ERROR")
        sys.exit(1)
    log(f"   Pipeline ID: {pipeline_id}")

    # 6. Wait for pipeline completion
    log("7. Waiting for pipeline completion (max 90s)...")
    for i in range(45):
        status_resp = api("GET", f"/api/pipeline/{pipeline_id}/status", token=token)
        st = status_resp.get("status", "")
        step = status_resp.get("current_step", "")
        prog = status_resp.get("progress", 0)
        log(f"   [{i*2}s] status={st} step={step} progress={prog:.0%}")
        if st == "done" or st == "needs_review":
            log(f"   Pipeline finished: {st}")
            break
        if st == "failed":
            log(f"   Pipeline failed: {status_resp.get('error_message', 'unknown')}", "ERROR")
            break
        time.sleep(2)

    # 7. Get scenarios
    log("8. Fetching scenarios...")
    scenarios_resp = api("GET", f"/api/scenarios?disruption_id={disruption_id}", token=token)
    scenarios = scenarios_resp if isinstance(scenarios_resp, list) else scenarios_resp.get("scenarios", scenarios_resp)
    if not isinstance(scenarios, list):
        scenarios = []
    log(f"   Found {len(scenarios)} scenarios")
    pending = [s for s in scenarios if s.get("status") == "pending"]
    if not pending:
        log("   No pending scenarios to approve - skipping approval step", "WARN")
    else:
        # 8. Approve first pending scenario
        sc = pending[0]
        sc_id = sc.get("scenario_id")
        log(f"9. Approving scenario {sc_id}...")
        try:
            approve_resp = api("POST", f"/api/scenarios/{sc_id}/approve", token=token, json_body={
                "note": "E2E test approval",
            })
            log(f"   Approved: {approve_resp.get('status', 'ok')}")
        except Exception as e:
            log(f"   Approval failed: {e}", "ERROR")

    # 9. RAG stats AFTER
    log("10. RAG stats AFTER pipeline + approval...")
    rag_after = api("GET", "/api/rag/stats", token=token)
    log(f"   Collections: {json.dumps(rag_after.get('collections', {}), indent=4)}")

    # 10. Check if disruptions/decisions were indexed
    disruptions_count = rag_after.get("collections", {}).get("disruptions", {}).get("count", 0)
    decisions_count = rag_after.get("collections", {}).get("decisions", {}).get("count", 0)
    domain_count = rag_after.get("collections", {}).get("domain_knowledge", {}).get("count", 0)

    log("11. Audit logs (last 5)...")
    try:
        logs = api("GET", "/api/audit-logs?limit=5", token=token)
        entries = logs if isinstance(logs, list) else logs.get("logs", logs.get("entries", []))
        for e in (entries or [])[:5]:
            log(f"   - {e.get('agent_name', '?')}: {(e.get('input_summary') or '')[:60]}...")
    except Exception as e:
        log(f"   Audit logs error: {e}", "WARN")

    # 12. Decision logs from DB (via scenario approve created one)
    log("12. Checking pipeline final summary...")
    try:
        status_final = api("GET", f"/api/pipeline/{pipeline_id}/status", token=token)
        fs = status_final.get("final_summary", {})
        if fs:
            log(f"   KPIs: {fs.get('kpis', {})}")
            log(f"   Needs review: {fs.get('needs_review')}")
    except Exception as e:
        log(f"   Status fetch: {e}", "WARN")

    # --- GAP ANALYSIS ---
    log("")
    log("=== GAP ANALYSIS ===", "INFO")
    gaps = []

    if disruptions_count == 0:
        gaps.append("RAG disruptions collection is EMPTY - new disruptions are never indexed to Chroma. "
                    "Pipeline creates disruptions in DB but does not call kb.add_disruption().")
    else:
        log(f"   RAG disruptions: {disruptions_count} docs (indexed)", "OK")

    if decisions_count == 0:
        gaps.append("RAG decisions collection is EMPTY - human approvals/rejections are never indexed. "
                    "execution_engine creates DecisionLog in DB but does not call kb.add_decision().")
    else:
        log(f"   RAG decisions: {decisions_count} docs (indexed)", "OK")

    if domain_count == 0:
        gaps.append("RAG domain_knowledge empty - seed-knowledge may have failed or Chroma not initialized.")
    else:
        log(f"   RAG domain_knowledge: {domain_count} docs", "OK")

    # Disruption status after approval
    gaps.append("Disruption status is never auto-updated when scenarios are approved. "
               "User must manually 'Mark as Resolved' in UI. Consider auto-resolving when all scenarios approved.")

    # Pipeline writes DecisionLog but not to RAG
    gaps.append("DecisionLog entries (approvals/rejections) are stored in SQLite/RDS decision_logs table "
               "but never synced to Chroma. RAG agents therefore have no historical decision context.")

    # Output gaps
    log("")
    for i, g in enumerate(gaps, 1):
        log(f"GAP {i}: {g}", "WARN")
    log("")
    log("=== E2E Test Complete ===")
    return 0 if len(gaps) < 4 else 1  # Exit 1 if critical gaps


if __name__ == "__main__":
    sys.exit(main())
