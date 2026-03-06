# Data Persistence – Where Data Lives

## Scenarios

**Storage:** Scenarios are stored in the **database** (SQLite locally, PostgreSQL/RDS in production).

| Layer | Location | When |
|-------|----------|------|
| **Database** | `Scenario` table | Written by `write_scenarios` during pipeline execution |
| **S3** (optional) | `pipeline_runs/{id}.json` | Written when `USE_AWS=1` after pipeline completion |
| **Frontend** | SWR cache + API | Fetched via `GET /api/scenarios` |

**Flow:**
1. Scenario Generator agent produces scenarios during the pipeline.
2. `write_scenarios` (MCP tool) persists them to the `Scenario` table.
3. Tradeoff Scoring updates `score_json` via `update_scenario_scores`.
4. When `USE_AWS=1`, the pipeline runner also writes a copy to S3 for audit.

**Scenarios do not disappear** when you navigate away. They remain in the database. The frontend fetches them via the API; SWR caches them so they stay visible when switching tabs or pages.

---

## Disruptions

**Storage:** Disruptions are stored in the **database** (`Disruption` table).

**Creation:** Disruptions are created **only** when:

1. **Manual creation** – A user clicks **Create** on the [Disruptions](/disruptions) page and fills the form.
2. **Scripts** – `seed_data.py` or E2E tests (`e2e_aws_persistence_test.py`) create test disruptions.

**The pipeline does NOT create disruptions.** It runs on an *existing* disruption. You select a disruption (or enter its ID) and start the pipeline – no new disruption is created.

If you see new disruptions, they come from:
- Creating them manually on the Disruptions page
- Running E2E/seed scripts that create test data

---

## Pipeline Runs

| Storage | Key | Contents |
|---------|-----|----------|
| **Database** | `PipelineRun` table | Status, progress, `final_summary_json`, error_message |
| **DynamoDB** (optional) | `DYNAMO_STATUS_TABLE` | Per-step status when `USE_AWS=1` |
| **S3** (optional) | `pipeline_runs/{id}.json` | Full run result (summary + scenarios) when `USE_AWS=1` |

---

## Decision Logs (Audit)

Stored in the `DecisionLog` table. Written by agents via `write_decision_log` during pipeline execution.
