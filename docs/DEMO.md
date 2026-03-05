# X-Tern Agents Demo Guide

This guide walks through a complete end-to-end demonstration of the Disruption Response Planner, including the new LLM-driven intelligent routing and optional MCP server mode.

## Prerequisites

- Python 3.11+ with conda/mamba
- Node.js 18+ with pnpm
- AWS credentials (optional, for Bedrock LLM)
- Git

## Quick Setup

### 1. Clone and Setup Environment

```bash
# Clone repository
git clone https://github.com/samipdevkota10/X-Tern-Agents.git
cd X-Tern-Agents

# Create conda environment
conda env create -f environment.yml
conda activate xtern-agents

# Install frontend dependencies
cd frontend && pnpm install && cd ..
```

### 2. Configure Environment

```bash
# Copy example env files
cp backend/.env.example backend/.env
```

Edit `backend/.env`:
```env
# Required
DATABASE_URL=sqlite:///./warehouse.db
JWT_SECRET=your-secure-secret-key-min-32-chars

# For LLM routing (optional but recommended)
USE_AWS=1
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0

# For MCP mode (optional)
USE_MCP_SERVER=0  # Set to 1 to enable MCP
```

### 3. Start Backend

```bash
cd backend

# Seed database with sample data
PYTHONPATH=$(pwd) python scripts/seed_data.py

# Start API server
PYTHONPATH=$(pwd) uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at: http://localhost:8000

### 4. Start Frontend

```bash
cd frontend
pnpm dev
```

Frontend runs at: http://localhost:3000

---

## Demo Walkthrough

### Step 1: Login

1. Open http://localhost:3000
2. Login with:
   - **Manager**: `manager_01` / `password` (full access)
   - **Analyst**: `analyst_01` / `password` (limited access)

### Step 2: View Dashboard

The dashboard shows:
- **KPIs**: Total orders, SLA at risk, approval queue
- **Recent Disruptions**: Latest incidents
- **SLA Risk Chart**: Visual breakdown

### Step 3: Create a Disruption

1. Click **Disruptions** in sidebar
2. Click **+ New Disruption** button
3. Fill in:
   - **Type**: `truck_delay`
   - **Severity**: `high`
   - **Details**: `{"truck_id": "T123", "delay_hours": 4, "affected_dc": "DC1"}`
4. Click **Create**

### Step 4: Run the Planner

1. Click on the new disruption
2. In the detail sheet, click **Run Planner**
3. Watch the real-time stepper show progress:
   - Signal Intake
   - Constraint Builder
   - Scenario Generator (LLM routing may iterate here)
   - Tradeoff Scoring
   - Finalize

**LLM Routing in Action**: With `USE_AWS=1`, the supervisor uses Claude to intelligently decide each next step. Check the logs for routing decisions:

```
INFO: Routing: signal_intake -> constraint_builder (LLM suggested: constraint_builder, override: None, confidence: 0.92)
```

### Step 5: Review Scenarios

1. Click **Scenarios** in sidebar
2. View generated scenarios grouped by order
3. Compare tradeoffs (cost, SLA risk, labor)
4. **Manager only**: Click **Approve** or **Reject** on scenarios

### Step 6: Approve Queue (Manager Only)

1. Click **Approvals** in sidebar
2. Review scenarios needing approval
3. Use **Approve** / **Reject** buttons
4. Or use **Bulk Approve** for multiple

### Step 7: View Audit Logs

1. Click **Audit Log** in sidebar
2. See complete decision history:
   - Agent decisions
   - Human approvals
   - Confidence scores
3. Use filters by agent or pipeline run
4. Click **Export JSON** for compliance records

---

## LLM Routing Details

### What's New

The pipeline now uses **LLM-driven routing** by default:

1. After each agent completes, the supervisor asks Claude: "What should be the next step?"
2. The LLM analyzes the current state and suggests a step
3. Deterministic guardrails validate the suggestion (prerequisites, loop detection)
4. The final step may be overridden if prerequisites are missing

### Routing Trace

Every pipeline run includes a `routing_trace` in the final summary:

```json
{
  "routing_trace": [
    {
      "ts": "2026-03-03T10:15:00Z",
      "from": "start",
      "llm_next": "signal_intake",
      "final": "signal_intake",
      "override": null,
      "confidence": 0.95
    },
    {
      "ts": "2026-03-03T10:15:02Z",
      "from": "signal_intake",
      "llm_next": "constraint_builder",
      "final": "constraint_builder",
      "override": null,
      "confidence": 0.91
    }
  ]
}
```

### Guardrails

Even with LLM routing, these guardrails are always enforced:

| Rule | Behavior |
|------|----------|
| Missing prerequisites | Override to correct step |
| Max steps exceeded | Force finalize with `needs_review` |
| Scenario retries exhausted | Force finalize with `needs_review` |
| Loop detected | Force finalize with `needs_review` |

### Deterministic Fallback

Set `USE_DETERMINISTIC_ROUTING=1` to disable LLM routing and use the legacy fixed-step flow:

```bash
USE_DETERMINISTIC_ROUTING=1 uvicorn app.main:app --reload
```

---

## MCP Mode Demo

MCP (Model Context Protocol) mode runs tool calls through an MCP server, enabling more modular, debuggable, and extensible architectures.

### Step 1: Start MCP Server

```bash
cd backend

# Start MCP server via stdio (in background)
PYTHONPATH=$(pwd) python scripts/run_mcp_server.py &

# Or via SSE transport
MCP_TRANSPORT=sse MCP_PORT=8001 PYTHONPATH=$(pwd) python scripts/run_mcp_server.py &
```

### Step 2: Run Backend with MCP

```bash
# Enable MCP mode
USE_MCP_SERVER=1 PYTHONPATH=$(pwd) uvicorn app.main:app --reload
```

### Step 3: Run Same Demo

Follow the same demo steps above. The only difference is that tool calls (read_disruption, write_scenarios, etc.) now go through the MCP server.

### Step 4: Check MCP Logs

Look for MCP debug logs:

```
DEBUG: [MCP] read_disruption: D-20260303-001
DEBUG: [MCP] write_scenarios: 3 scenarios
DEBUG: [MCP] write_decision_log: Supervisor
```

### MCP Smoke Test

Verify MCP tools work correctly:

```bash
# Test local mode
PYTHONPATH=$(pwd) python scripts/test_mcp_smoke.py

# Test MCP mode (requires MCP server running)
USE_MCP_SERVER=1 PYTHONPATH=$(pwd) python scripts/test_mcp_smoke.py
```

---

## Troubleshooting

### LLM Routing Not Working

1. Check `USE_AWS=1` is set
2. Verify AWS credentials are configured
3. Check Bedrock model access in your region
4. Review logs for LLM errors

### MCP Connection Failed

1. Ensure MCP server is running
2. Check `USE_MCP_SERVER=1` is set
3. Verify `mcp` package is installed: `pip install mcp`

### Pipeline Stuck

1. Check `MAX_PIPELINE_STEPS` (default 20)
2. Review routing trace for loops
3. Check for `needs_review: true` in final summary

### Database Errors

1. Ensure database is seeded: `python scripts/seed_data.py`
2. Check `DATABASE_URL` in `.env`

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_AWS` | `0` | Enable AWS services (Bedrock, DynamoDB) |
| `BEDROCK_MODEL_ID` | - | Claude model ID for LLM routing |
| `USE_MCP_SERVER` | `0` | Route tool calls through MCP server |
| `USE_DETERMINISTIC_ROUTING` | `0` | Disable LLM routing (legacy mode) |
| `MAX_PIPELINE_STEPS` | `20` | Maximum steps before forced finalize |
| `MAX_SCENARIO_RETRIES` | `3` | Retries for empty scenario generation |

---

## API Endpoints (Quick Reference)

- `POST /api/auth/login` - Get JWT token
- `GET /api/disruptions` - List disruptions
- `POST /api/disruptions` - Create disruption
- `POST /api/pipeline/run` - Start pipeline
- `GET /api/pipeline/{id}/status` - Pipeline status
- `GET /api/scenarios` - List scenarios
- `POST /api/scenarios/{id}/approve` - Approve scenario
- `GET /api/audit-logs` - Audit log entries
- `GET /api/dashboard` - Dashboard KPIs

Full API docs: http://localhost:8000/api/docs
