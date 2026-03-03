# Backend Structure - Milestone 1

## Directory Layout

```
backend/
│
├── app/
│   ├── __init__.py
│   │
│   ├── db/                          ← NEW: Database Layer
│   │   ├── __init__.py
│   │   ├── base.py                  # SQLAlchemy declarative base
│   │   ├── session.py               # Session factory & dependency
│   │   └── models.py                # 9 ORM models (Disruption, Order, etc.)
│   │
│   ├── mcp/                         ← NEW: MCP Tools
│   │   ├── __init__.py
│   │   └── tools.py                 # 9 LangChain @tool functions
│   │
│   ├── routers/                     ← Existing (not modified)
│   │   ├── __init__.py
│   │   ├── health.py
│   │   ├── cases.py
│   │   └── mcp.py
│   │
│   ├── models/                      ← Existing (not modified)
│   ├── aws/                         ← Existing (not modified)
│   ├── config.py
│   └── logging_config.py
│
├── scripts/                         ← NEW: Utility Scripts
│   ├── __init__.py
│   ├── seed_data.py                 # Generate synthetic data
│   ├── quick_tool_test.py           # Test all MCP tools
│   └── inspect_db.py                # Database health check
│
├── requirements.txt                 ← Modified: Added SQLAlchemy, LangChain
├── .env.example                     ← Modified: Added DATABASE_URL
├── warehouse.db                     ← NEW: SQLite database (generated)
├── run_milestone1.sh               ← NEW: Automated test runner
├── MILESTONE_1_README.md           ← NEW: Complete documentation
└── STRUCTURE.md                     ← This file
```

## Database Schema (9 Tables)

```
┌─────────────────┐
│  disruptions    │  ← Supply chain events
├─────────────────┤
│ id (PK)         │
│ type            │──┐
│ severity        │  │
│ timestamp       │  │
│ details_json    │  │
│ status          │  │
└─────────────────┘  │
                     │
┌─────────────────┐  │  ┌─────────────────┐
│     orders      │  │  │    scenarios    │  ← Response plans
├─────────────────┤  │  ├─────────────────┤
│ order_id (PK)   │──┼──│ scenario_id     │
│ priority        │  │  │ disruption_id   │──┘
│ promised_ship   │  │  │ order_id        │
│ cutoff_time     │  │  │ action_type     │
│ dc              │  │  │ plan_json       │
│ status          │  │  │ score_json      │
└─────────────────┘  │  │ status          │
        │            │  │ created_at      │
        │            │  └─────────────────┘
        ▼            │
┌─────────────────┐  │
│  order_lines    │  │
├─────────────────┤  │
│ line_id (PK)    │  │
│ order_id (FK)   │──┘
│ sku             │
│ qty             │
└─────────────────┘

┌─────────────────┐
│   inventory     │  ← Stock levels
├─────────────────┤
│ inv_id (PK)     │
│ dc              │──┐ UNIQUE (dc, sku)
│ sku             │──┘
│ on_hand         │
│ reserved        │
└─────────────────┘

┌─────────────────┐
│ inbound_ships   │  ← Incoming trucks
├─────────────────┤
│ truck_id (PK)   │
│ eta             │
│ dc              │
│ sku_list_json   │
└─────────────────┘

┌─────────────────┐
│    capacity     │  ← DC operations
├─────────────────┤
│ cap_id (PK)     │
│ dc              │
│ process         │
│ capacity/hour   │
│ downtime_flag   │
└─────────────────┘

┌─────────────────┐
│ substitutions   │  ← Product swaps
├─────────────────┤
│ sub_id (PK)     │
│ sku             │
│ substitute_sku  │
│ penalty_cost    │
└─────────────────┘

┌─────────────────┐
│ decision_logs   │  ← Audit trail
├─────────────────┤
│ log_id (PK)     │
│ timestamp       │
│ pipeline_run_id │──┐ INDEX
│ agent_name      │  │
│ input_summary   │  │
│ output_summary  │  │
│ confidence      │  │
│ rationale       │  │
│ human_decision  │  │
│ approver_id     │  │
│ approver_note   │  │
│ override_value  │──┘
└─────────────────┘
```

## MCP Tools (9 Functions)

### Query Tools (Read-Only)
```python
@tool
def read_open_orders() -> list[dict]
    """Get all open orders with line items"""

@tool
def read_inventory(dc: str, sku: str) -> dict
    """Check inventory: on_hand, reserved, available"""

@tool
def read_inbound_status(truck_id: str) -> dict
    """Get truck ETA and SKU list"""

@tool
def read_capacity(process: str) -> list[dict]
    """Get capacity for process across DCs"""

@tool
def get_pending_scenarios() -> list[dict]
    """List scenarios awaiting approval"""
```

### Write Tools (State-Changing)
```python
@tool
def write_scenarios(scenarios: list[dict]) -> dict
    """Bulk insert response scenarios"""

@tool
def approve_scenario(scenario_id: str, approver: str, note: str) -> dict
    """Approve scenario + create decision log"""

@tool
def reject_scenario(scenario_id: str, approver: str, note: str) -> dict
    """Reject scenario + create decision log"""

@tool
def write_decision_log(entry: dict) -> dict
    """Create audit trail entry"""
```

## Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                    Seed Data Script                      │
│                 (scripts/seed_data.py)                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   SQLAlchemy ORM      │
         │   (app/db/models.py)  │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   SQLite Database     │
         │   (warehouse.db)      │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   MCP Tools           │
         │   (app/mcp/tools.py)  │
         │   [@tool decorator]   │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   LangChain Agents    │
         │   (Future: Milestone 2)│
         └───────────────────────┘
```

## Test Flow

```
./run_milestone1.sh
    │
    ├─► python scripts/seed_data.py
    │       ├─ Drop/recreate tables
    │       ├─ Generate 200 SKUs
    │       ├─ Create 400 inventory records
    │       ├─ Generate 120 orders (572 lines)
    │       ├─ Create 40 substitutions
    │       ├─ Generate 8 inbound shipments
    │       ├─ Create 6 capacity records
    │       └─ Generate 6 disruptions
    │
    └─► python scripts/quick_tool_test.py
            ├─ Test read_open_orders()
            ├─ Test read_inventory()
            ├─ Test read_inbound_status()
            ├─ Test read_capacity()
            ├─ Test write_scenarios()
            ├─ Test get_pending_scenarios()
            ├─ Test approve_scenario()
            ├─ Test reject_scenario()
            ├─ Test write_decision_log()
            └─ Verify decision_logs count
```

## Key Features

### Type Safety
- ✅ `Mapped[str]`, `Mapped[int]`, `Mapped[datetime]`
- ✅ Type hints on all function signatures
- ✅ mypy-compatible code

### Error Handling
- ✅ Try/except in all tools
- ✅ DB rollback on errors
- ✅ Session cleanup in finally blocks
- ✅ JSON encode/decode with error wrapping

### JSON Management
- ✅ JSON stored as TEXT (SQLite compatible)
- ✅ Helper functions: `json_dumps()`, `json_loads()`
- ✅ Error handling for malformed JSON

### Session Management
- ✅ SessionLocal factory
- ✅ No global sessions
- ✅ Context managers via `get_db()`
- ✅ Proper cleanup with try/finally

### Testing
- ✅ Deterministic seed (random.seed=42)
- ✅ All 9 tools tested
- ✅ Exit codes (0=success, 1=failure)
- ✅ Health check script (inspect_db.py)

## Dependencies Added

```txt
sqlalchemy>=2.0.0        # ORM
langchain-core>=0.1.0    # @tool decorator
```

## Environment Variables

```bash
DATABASE_URL=sqlite:///./warehouse.db
```

## Usage Examples

### Seed Database
```bash
cd backend
PYTHONPATH=$(pwd) python scripts/seed_data.py
```

### Test Tools
```bash
cd backend
PYTHONPATH=$(pwd) python scripts/quick_tool_test.py
```

### Inspect Database
```bash
cd backend
PYTHONPATH=$(pwd) python scripts/inspect_db.py
```

### Full Test Suite
```bash
cd backend
./run_milestone1.sh --reseed
```

## Next Steps

Ready for:
- **Milestone 2:** LangGraph multi-agent workflows
- **Milestone 3:** FastAPI REST API endpoints
- **Milestone 4:** React frontend integration
