# Example Decision Logs

**X-Tern Agents – Disruption Response Planner**  
**Version:** 1.0  
**Last Updated:** March 2026

---

## 1. DecisionLog Schema

Each entry in `decision_logs` has:

| Field | Type | Description |
|-------|------|-------------|
| log_id | string | Unique identifier |
| timestamp | string | ISO8601 |
| pipeline_run_id | string | Links to pipeline run |
| agent_name | string | SignalIntakeAgent, ScenarioGenerator, HumanApproval, etc. |
| input_summary | string | Summary of inputs considered |
| output_summary | string | Summary of output/decision |
| confidence_score | float | 0.0–1.0 |
| rationale | string | Reasoning |
| human_decision | string | approved, rejected, edited, pending |
| approver_id | string | User who approved/rejected (if human) |
| approver_note | string | Optional note |
| override_value | string | JSON override (if edited) |

---

## 2. Example: Signal Intake Agent

```json
{
  "log_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2026-03-06T04:15:00.000Z",
  "pipeline_run_id": "0ddf2b97-8832-4b0c-974a-8b5c97ab5911",
  "agent_name": "SignalIntakeAgent",
  "input_summary": "Disruption bcd6054f-d201-47b1-89be-b42211888a8f type=late_truck",
  "output_summary": "Identified 6 impacted orders",
  "confidence_score": 0.90,
  "rationale": "Applied late_truck impact rules to 120 open orders",
  "human_decision": "pending",
  "approver_id": null,
  "approver_note": null,
  "override_value": null
}
```

---

## 3. Example: Scenario Generator Agent

```json
{
  "log_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "timestamp": "2026-03-06T04:15:45.000Z",
  "pipeline_run_id": "0ddf2b97-8832-4b0c-974a-8b5c97ab5911",
  "agent_name": "ScenarioGenerator",
  "input_summary": "Signal with 6 impacted orders, constraints from DC1/DC2",
  "output_summary": "Generated 6 scenarios (delay, substitute, expedite)",
  "confidence_score": 0.85,
  "rationale": "Used rule-based + RAG domain knowledge for late_truck disruption",
  "human_decision": "pending",
  "approver_id": null,
  "approver_note": null,
  "override_value": null
}
```

---

## 4. Example: Human Approval

```json
{
  "log_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "timestamp": "2026-03-06T04:17:30.000Z",
  "pipeline_run_id": "0ddf2b97-8832-4b0c-974a-8b5c97ab5911",
  "agent_name": "HumanApproval",
  "input_summary": "Approve scenario b7367e7b-2851-4020-abe3-f8c7d338b392 (substitute) for order ORD0042",
  "output_summary": "{\"scenario_id\":\"b7367e7b-...\",\"action_type\":\"substitute\",\"changes\":[\"Order ORD0042: substituted SKU0045 → SKU0046\"]}",
  "confidence_score": 1.0,
  "rationale": "Human approval by manager_01",
  "human_decision": "approved",
  "approver_id": "manager_01",
  "approver_note": "E2E test approval",
  "override_value": null
}
```

---

## 5. Example: Human Rejection

```json
{
  "log_id": "d4e5f6a7-b8c9-0123-def0-234567890123",
  "timestamp": "2026-03-06T04:18:00.000Z",
  "pipeline_run_id": "0ddf2b97-8832-4b0c-974a-8b5c97ab5911",
  "agent_name": "HumanApproval",
  "input_summary": "Reject scenario xyz789 (delay) for order ORD0015",
  "output_summary": "Scenario rejected",
  "confidence_score": 1.0,
  "rationale": "Human rejection by manager_01",
  "human_decision": "rejected",
  "approver_id": "manager_01",
  "approver_note": "SLA too tight; customer is VIP, prefer expedite instead",
  "override_value": null
}
```

---

## 6. Example: Pipeline Failure

```json
{
  "log_id": "e5f6a7b8-c9d0-1234-ef01-345678901234",
  "timestamp": "2026-03-06T04:20:00.000Z",
  "pipeline_run_id": "0ddf2b97-8832-4b0c-974a-8b5c97ab5911",
  "agent_name": "SupervisorFailure",
  "input_summary": "Pipeline run 0ddf2b97... for disruption bcd6054f...",
  "output_summary": "Pipeline failed: ValueError: Disruption not found",
  "confidence_score": 0.0,
  "rationale": "Pipeline execution error",
  "human_decision": "pending",
  "approver_id": null,
  "approver_note": null,
  "override_value": null
}
```

---

## 7. Query Examples

**By pipeline run:**
```http
GET /api/audit-logs?pipeline_run_id=0ddf2b97-8832-4b0c-974a-8b5c97ab5911
```

**By human decision:**
```http
GET /api/audit-logs?human_decision=approved
```

**By agent:**
```http
GET /api/audit-logs?agent_name=HumanApproval
```
