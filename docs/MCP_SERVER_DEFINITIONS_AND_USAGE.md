# MCP Server Definitions and Usage Examples

**X-Tern Agents – Disruption Response Planner**  
**Version:** 1.1  
**Last Updated:** March 2026

---

## 1. Overview

The Model Context Protocol (MCP) server exposes warehouse and disruption operations as tools. **MCP mode is on by default** (`USE_MCP_SERVER=1`). When enabled, agents call tools through the MCP client; if the MCP package is not installed or the server is unreachable, the tool router **automatically falls back to local tools** so the pipeline never fails.

All agents use the **tool router** (`app.mcp.tool_router`) instead of calling tools directly—agents remain agnostic to MCP vs. local transport.

---

## 2. Running the MCP Server

```bash
cd backend
PYTHONPATH=$(pwd) python scripts/run_mcp_server.py
```

**Transports:**
- **stdio** (default): For local/in-process use
- **SSE**: `MCP_TRANSPORT=sse MCP_PORT=8001 python scripts/run_mcp_server.py`

**Environment:**
| Variable | Default | Description |
|----------|---------|-------------|
| `USE_MCP_SERVER` | `1` | Route tool calls via MCP when `1`; use local tools when `0` |
| `MCP_TRANSPORT` | `stdio` | Transport: `stdio` or `sse` |
| `MCP_PORT` | `8001` | Port for SSE transport |

---

## 3. Tool Definitions

### 3.1 Read Tools (MCP-routed when USE_MCP_SERVER=1)

| Tool | Args | Returns | Description |
|------|------|---------|-------------|
| `read_open_orders` | none | `list[dict]` | All open orders with line items |
| `read_inventory` | dc, sku | `dict` | on_hand, reserved, available for DC+SKU |
| `read_inbound_status` | truck_id | `dict` | Truck ETA, DC, sku_list |
| `read_capacity` | process | `list[dict]` | Capacity for process across DCs |
| `read_disruption` | disruption_id | `dict` | Disruption details |
| `read_substitutions` | skus (list) | `list[dict]` | Substitution options for SKUs |

### 3.2 Write Tools (MCP-routed)

| Tool | Args | Returns | Description |
|------|------|---------|-------------|
| `write_scenarios` | scenarios | `dict` | Insert scenarios; returns `{created: n}` |
| `write_decision_log` | entry | `dict` | Create audit trail entry |
| `update_scenario_scores` | scenario_scores | `dict` | Update score_json for scenarios |

### 3.3 Pipeline Tools (always local)

| Tool | Args | Returns | Description |
|------|------|---------|-------------|
| `create_pipeline_run` | pipeline_run_id, disruption_id | `dict` | Create pipeline run record |
| `update_pipeline_run` | pipeline_run_id, updates | `dict` | Update status, summary |

**Note:** Scenario approval/rejection is handled via FastAPI `POST /api/scenarios/{id}/approve` and `POST /api/scenarios/{id}/reject`, not MCP tools.

---

## 4. Usage Examples

**Always use the tool router.** It routes to MCP when available, else local tools.

### 4.1 Read Open Orders (Python)

```python
from app.mcp.tool_router import read_open_orders

orders = read_open_orders()
for o in orders:
    print(f"Order {o['order_id']} ({o['priority']}) at {o['dc']}")
```

### 4.2 Read Inventory

```python
from app.mcp.tool_router import read_inventory

inv = read_inventory("DC1", "SKU0045")
print(f"Available: {inv['available']} (on_hand={inv['on_hand']}, reserved={inv['reserved']})")
```

### 4.3 Read Disruption

```python
from app.mcp.tool_router import read_disruption

d = read_disruption("bcd6054f-d201-47b1-89be-b42211888a8f")
if "error" in d:
    print(d["error"])
else:
    print(f"Type: {d['type']}, Severity: {d['severity']}, Details: {d['details']}")
```

### 4.4 Write Scenarios

```python
from app.mcp.tool_router import write_scenarios

result = write_scenarios([
    {
        "disruption_id": "abc-123",
        "order_id": "ORD0001",
        "action_type": "delay",
        "plan_json": {
            "summary": "Delay order 2 hours",
            "delay_hours": 2
        },
        "score_json": {
            "cost_impact_usd": 50,
            "sla_risk": 0.1
        }
    }
])
print(f"Created: {result.get('created', 0)}")
```

### 4.5 Write Decision Log

```python
from app.mcp.tool_router import write_decision_log
from datetime import datetime, timezone
import uuid

entry = {
    "log_id": str(uuid.uuid4()),
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "pipeline_run_id": "run-123",
    "agent_name": "SignalIntakeAgent",
    "input_summary": "Disruption abc type=late_truck",
    "output_summary": "Identified 5 impacted orders",
    "confidence_score": 0.9,
    "rationale": "Applied late_truck impact rules",
    "human_decision": "pending"
}
write_decision_log(entry)
```

### 4.6 Approve Scenario (via API, not MCP)

Scenario approval is done via the FastAPI REST API:

```bash
curl -X POST "http://localhost:8000/api/scenarios/{scenario_id}/approve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"note": "Approved"}'
```

---

## 5. MCP Server Schema (JSON Schema)

Example tool schema from `mcp_server/server.py`:

**read_disruption:**
```json
{
  "type": "object",
  "properties": {
    "disruption_id": {
      "type": "string",
      "description": "Disruption identifier"
    }
  },
  "required": ["disruption_id"]
}
```

**write_scenarios:**
```json
{
  "type": "object",
  "properties": {
    "scenarios": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "disruption_id": {"type": "string"},
          "order_id": {"type": "string"},
          "action_type": {"type": "string"},
          "plan_json": {"type": "object"}
        },
        "required": ["disruption_id", "order_id", "action_type", "plan_json"]
      }
    }
  },
  "required": ["scenarios"]
}
```

---

## 6. Tool Router

The tool router (`app/mcp/tool_router.py`) is the single entry point for all tool calls:

1. **When `USE_MCP_SERVER=1`** (default): Try MCP client first.
2. **Fallback**: If MCP package is not installed (`pip install mcp`) or the MCP server is unreachable, automatically use local tool implementations. The pipeline never fails due to MCP unavailability.
3. **When `USE_MCP_SERVER=0`**: Always use local tools.

Logs indicate routing:
- `DEBUG: [MCP] read_disruption: <id>` — routed via MCP
- `WARNING: MCP package not installed... falling back to local tools` — fallback to local

---

## 7. Integration with Agents

Agents import from the tool router and call tools as plain functions:

```python
# signal_intake_agent.py
from app.mcp.tool_router import read_disruption, read_open_orders, write_decision_log

disruption = read_disruption(disruption_id)
all_orders = read_open_orders()
write_decision_log(entry)
```

No `.invoke()` or transport-specific code—the router handles MCP vs. local transparently. With MCP on by default, start the MCP server in a separate terminal for full MCP tool routing; otherwise the system falls back to local tools automatically.
