# E2E Test Report & Core Logic Fix Plan

**Date:** March 6, 2026  
**Scope:** Create disruption → Run pipeline → Approve fix → Logs → RAG → Documentation storage

---

## E2E Test Summary

### Flow Executed
1. ✅ **Health check** – Backend and RAG healthy
2. ✅ **Login** – `manager_01` authenticated
3. ✅ **RAG seed** – 4 domain knowledge items seeded via `/api/rag/seed-knowledge`
4. ✅ **Create disruption** – Late truck disruption created (`POST /api/disruptions`)
5. ✅ **Run pipeline** – Pipeline started, completed in ~90s with 6 scenarios
6. ✅ **Approve scenario** – First pending scenario approved successfully
7. ⚠️ **Audit logs** – API returns list directly; E2E test expects `{logs: []}` (minor)
8. ✅ **RAG stats** – Domain knowledge: 5 docs; disruptions/decisions: 0

### RAG Query Test Results
- **Domain knowledge** returns relevant results for:
  - "How do I handle a late truck delivery?" → Supplier Delay Protocol, Demand Surge
  - "What are the SLA requirements for VIP customers?" → SLA Compliance Requirements
  - "Can I substitute a product for an out-of-stock item?" → Product Substitution Rules
  - "Too many orders came in at once?" → Demand Surge, Supplier Delay

---

## Identified Gaps in Core Logic

### GAP 1: Disruptions Never Indexed to RAG (Critical)
**Location:** Pipeline creates disruptions in DB but does not call `kb.add_disruption()`  
**Impact:** RAG agents have no historical disruption context; `search_similar_disruptions` always returns empty.  
**Evidence:** `disruptions` collection count = 0 after full E2E run.

**Where it should happen:**
- Option A: In `pipeline_runner.py` after pipeline completes – index the processed disruption with resolution summary
- Option B: In `signal_intake_agent.py` – index when disruption is read (no resolution yet)
- Option C: When disruption is marked resolved via `PATCH /api/disruptions/{id}` – index with full outcome

**Recommendation:** Option C (on resolve) or Option A (on pipeline complete with partial outcome). Option C gives best data (resolution + outcome).

---

### GAP 2: Decisions Never Indexed to RAG (Critical)
**Location:** `execution_engine.apply_scenario()` creates `DecisionLog` in DB but does not call `kb.add_decision()`  
**Impact:** RAG agents have no historical approval/rejection context; `search_relevant_decisions` always returns empty.  
**Evidence:** `decisions` collection count = 0 after E2E approval.

**Where it should happen:**
- In `execution_engine.apply_scenario()` after `db.commit()` – call `kb.add_decision()` with the log entry
- Similarly in reject flow (`scenarios.py` reject endpoint) – index rejections too

**Recommendation:** Add `kb.add_decision()` call in execution_engine after successful apply, and in reject handler.

---

### GAP 3: Disruption Status Not Auto-Updated (Medium)
**Location:** When scenarios are approved, disruption status stays `open`  
**Impact:** User must manually "Mark as Resolved" in UI. No automatic resolution when all scenarios are handled.  
**Evidence:** E2E test explicitly flags this.

**Where it should happen:**
- In `execution_engine.apply_scenario()` – after apply, check if all scenarios for this disruption are now approved/rejected; if so, set disruption status to `resolved`
- Or: In a batch approval flow – after bulk approve, check and resolve

**Recommendation:** Add helper `_maybe_resolve_disruption(db, disruption_id)` called from `apply_scenario` and reject handler.

---

### GAP 4: DecisionLog → Chroma Sync Missing (Critical)
**Location:** Same as GAP 2 – DecisionLog is DB-only.  
**Impact:** RAG `get_context_for_agent` returns empty `relevant_decisions`; agents cannot learn from past human decisions.

---

### GAP 5: RAG Context Structure Mismatch (Low)
**Location:** `KnowledgeBase._format_results` returns `similarity` (1 - distance); some callers may expect `distance`. Metadata may not include `title` for domain_knowledge.  
**Impact:** `test_rag_queries.py` shows `Distance: 0.0000` and `title: N/A` – format inconsistency.

**Recommendation:** Ensure `_format_results` includes `title` from metadata and optionally `distance` for compatibility.

---

### GAP 6: E2E Test Audit Log Parsing (Low)
**Location:** `e2e_test.py` expects `logs.get("logs", logs.get("entries", []))` but API returns a list directly.  
**Impact:** `'list' object has no attribute 'get'` when iterating audit logs.

**Recommendation:** `entries = logs if isinstance(logs, list) else logs.get("logs", logs.get("entries", []))`

---

### GAP 7: Pipeline Writes to RAG Only on Completion (Design)
**Location:** Pipeline runner does not index disruptions at any point.  
**Note:** This is the root cause of GAP 1. Resolution happens via implementing GAP 1 fix.

---

## How the RAG Agent Works (Current Behavior)

1. **Collections:**
   - `disruptions` – Past disruptions with resolution/outcome (currently empty)
   - `decisions` – Human approvals/rejections with rationale (currently empty)
   - `domain_knowledge` – Supply chain best practices (seeded via `/api/rag/seed-knowledge`)
   - `scenarios` – Generated scenarios (not actively used in indexing)

2. **RAG Usage in Pipeline:**
   - `scenario_generator_agent` – Calls `kb.get_context_for_agent("ScenarioGenerator", situation, disruption_type)` → uses domain_knowledge only (disruptions/decisions empty)
   - `tradeoff_scoring_agent` – Same pattern
   - `llm_agent.get_rag_context()` – Formats similar_disruptions, relevant_decisions, domain_knowledge → only domain_knowledge has data

3. **Storage:**
   - **SQLite/RDS:** disruptions, scenarios, decision_logs, pipeline_runs, orders, etc.
   - **Chroma:** domain_knowledge (seeded), disruptions (empty), decisions (empty)
   - **S3 (USE_AWS=1):** `pipeline_runs/{id}.json` – final summary
   - **DynamoDB (USE_AWS=1):** pipeline status per step

---

## Fix Plan (Priority Order)

| # | Gap | Effort | Files | Action |
|---|-----|--------|-------|--------|
| 1 | GAP 2: Index decisions to RAG | Medium | `execution_engine.py`, `scenarios.py` | Call `kb.add_decision()` after approve and after reject |
| 2 | GAP 1: Index disruptions to RAG | Medium | `disruptions.py` (PATCH), optional: `pipeline_runner` | On PATCH status→resolved, call `kb.add_disruption()` with resolution summary |
| 3 | GAP 3: Auto-resolve disruption | Small | `execution_engine.py`, `scenarios.py` | Add `_maybe_resolve_disruption(db, disruption_id)` when all scenarios handled |
| 4 | GAP 6: E2E audit log parsing | Trivial | `e2e_test.py` | Handle list response from audit-logs API |
| 5 | GAP 5: RAG format consistency | Low | `knowledge_base.py`, `test_rag_queries.py` | Add title/distance to formatted results if needed |

---

## Implementation Notes

### For GAP 2 (Index decisions)
```python
# In execution_engine.apply_scenario(), after db.commit():
from app.rag import get_knowledge_base
kb = get_knowledge_base()
if kb.available:
    kb.add_decision(
        decision_id=log_id,
        pipeline_run_id=plan.get("pipeline_run_id", "manual"),
        agent_name="HumanApproval",
        decision_type="approve",
        input_context=f"Approve scenario {scenario_id} ({action_type}) for order {scenario.order_id}",
        output_decision=json.dumps(changes_summary),
        human_action="approved",
        rationale=approver_note or f"Approved by {approver_id}",
    )
```

### For GAP 1 (Index disruptions on resolve)
```python
# In disruptions.py update_disruption_status(), when request.status == "resolved":
if request.status == "resolved" and kb.available:
    # Build resolution summary from recent decision logs or pipeline
    kb.add_disruption(
        disruption_id=disruption_id,
        disruption_type=disruption.type,
        severity=disruption.severity,
        description=details_desc,
        impact_summary=impact_from_scenarios,
        resolution="Marked resolved by user",
        outcome="Pending post-hoc assessment",
    )
```

### For GAP 3 (Auto-resolve)
```python
def _maybe_resolve_disruption(db, disruption_id: str) -> None:
    """If all scenarios for this disruption are approved or rejected, set disruption status to resolved."""
    pending = db.query(Scenario).filter(
        Scenario.disruption_id == disruption_id,
        Scenario.status == "pending",
    ).count()
    if pending == 0:
        d = db.query(Disruption).filter(Disruption.id == disruption_id).first()
        if d and d.status == "open":
            d.status = "resolved"
            db.commit()
```

---

## Acceptance Criteria

- [ ] After E2E run, `disruptions` collection has ≥ 1 doc (when at least one disruption resolved)
- [ ] After E2E run, `decisions` collection has ≥ 1 doc (when scenario approved)
- [ ] When all scenarios for a disruption are approved/rejected, disruption status becomes `resolved`
- [ ] E2E test passes without audit log parsing error
- [ ] RAG query for "late truck" returns similar past disruptions (once indexed)
