# Milestone 1: Database + MCP Tools

## Overview

Milestone 1 implements the foundational data layer for the Disruption Response Planner. This includes:
- SQLAlchemy ORM models for all warehouse/supply chain entities
- Deterministic synthetic seed data
- LangChain MCP tools for reading/writing the database
- Comprehensive test suite

## Directory Structure

```
backend/
├── app/
│   ├── db/
│   │   ├── base.py          # SQLAlchemy declarative base
│   │   ├── session.py       # Database session management
│   │   └── models.py        # All ORM models
│   └── mcp/
│       └── tools.py         # LangChain @tool decorated functions
├── scripts/
│   ├── seed_data.py         # Synthetic data generation
│   └── quick_tool_test.py   # Tool validation tests
├── requirements.txt         # Python dependencies
├── .env.example            # Environment configuration template
└── warehouse.db            # SQLite database (generated)
```

## Database Schema

### Tables

1. **disruptions** - Warehouse/supply chain disruptions
   - Types: late_truck, stockout, machine_down
   - Severity levels: 1-5
   - JSON details field for type-specific data

2. **orders** - Customer orders
   - Priority levels: standard, expedited, vip
   - Statuses: open, planned, shipped, delayed
   - Cutoff times for same-day shipping

3. **order_lines** - Individual line items per order
   - Links to orders table
   - SKU and quantity

4. **inventory** - DC inventory levels
   - On-hand and reserved quantities
   - Unique constraint on DC + SKU

5. **inbound_shipments** - Incoming truck deliveries
   - ETA tracking
   - JSON SKU list with quantities

6. **capacity** - DC operational capacity
   - Process types: picking, packing, shipping
   - Downtime flags

7. **substitutions** - Product substitution options
   - Penalty costs for swaps

8. **scenarios** - Response plan proposals
   - Action types: delay, reroute, substitute, resequence
   - JSON plan and score fields
   - Links to disruptions and orders

9. **decision_logs** - Audit trail of all decisions
   - Agent name and pipeline run tracking
   - Human approval/rejection tracking
   - Confidence scores and rationale

### Indexes

- `disruptions.type` - Fast filtering by disruption type
- `scenarios.status` - Quick pending scenario queries
- `decision_logs.pipeline_run_id` - Trace decisions by run

## Synthetic Data

The seed script (`scripts/seed_data.py`) generates deterministic test data:

- **200 SKUs** (SKU0001-SKU0200)
- **400 inventory records** (2 DCs × 200 SKUs)
- **120 open orders** with 2-7 lines each (572 total lines)
- **40 product substitutions** with penalty costs
- **8 inbound truck shipments** with ETAs within 8 hours
- **6 capacity records** (2 DCs × 3 processes)
- **6 disruptions** (2 of each type)

Uses `random.seed(42)` for reproducibility.

## MCP Tools

All tools are exposed via `@tool` from `langchain_core.tools` and use SQLAlchemy sessions safely.

### Query Tools

1. **read_open_orders()** → `list[dict]`
   - Returns all open orders with line items
   - Includes promised ship times and cutoffs

2. **read_inventory(dc, sku)** → `dict`
   - Returns on_hand, reserved, and available quantities
   - Safe handling of missing inventory

3. **read_inbound_status(truck_id)** → `dict`
   - Returns truck ETA, DC, and SKU list
   - Decodes JSON payload

4. **read_capacity(process)** → `list[dict]`
   - Returns capacity for all DCs for given process
   - Includes downtime flags

5. **get_pending_scenarios()** → `list[dict]`
   - Returns scenarios with full disruption + order context
   - Joined queries with eager loading

### Write Tools

6. **write_scenarios(scenarios)** → `dict`
   - Bulk insert scenario proposals
   - Validates required fields
   - Returns count created

7. **approve_scenario(scenario_id, approver, note)** → `dict`
   - Updates scenario status to approved
   - Creates decision log entry
   - Returns log ID

8. **reject_scenario(scenario_id, approver, note)** → `dict`
   - Updates scenario status to rejected
   - Creates decision log entry
   - Returns log ID

9. **write_decision_log(entry)** → `dict`
   - Inserts audit log entry
   - Validates all required fields
   - Returns log ID

### Helper Functions

- **json_dumps(obj)** - Safe JSON encoding with error handling
- **json_loads(text)** - Safe JSON decoding with error handling
- **ensure_iso8601(dt)** - Convert datetime to ISO8601 string

## Running the Code

### 1. Install Dependencies

**Option A – Conda (recommended, from repo root):**

```bash
# From X-Tern-Agents/
conda env create -f environment.yml
conda activate xtern-agents
# Or: mamba env create -f environment.yml && mamba activate xtern-agents
cd backend
```

**Option B – pip only:**

```bash
cd backend
pip install -r requirements.txt
```

### 2. Generate Seed Data

```bash
cd backend
PYTHONPATH=/Users/tanaypatel/Desktop/xtern/X-Tern-Agents/backend python scripts/seed_data.py
```

**Output:**
```
=== Starting Seed Data Generation ===
✓ Tables created
✓ Generated 200 SKUs
✓ Created 400 inventory records
✓ Created 120 orders with 572 order lines
✓ Created 40 substitution records
✓ Created 8 inbound shipments
✓ Created 6 capacity records
✓ Created 6 disruptions
✓ Seed data generation complete!
```

### 3. Test MCP Tools

```bash
cd backend
PYTHONPATH=/Users/tanaypatel/Desktop/xtern/X-Tern-Agents/backend python scripts/quick_tool_test.py
```

**Tests:**
- Read open orders
- Check inventory
- Query inbound truck status
- Fetch capacity data
- Create scenarios
- Approve/reject scenarios
- Write decision logs
- Verify decision log count

All tests should pass with exit code 0.

## Configuration

Environment variables (see `.env.example`):

```bash
# Database
DATABASE_URL=sqlite:///./warehouse.db
```

Defaults to `sqlite:///./warehouse.db` if not set.

## Code Quality Features

✅ **Type hints everywhere** - Full mypy compatibility  
✅ **Docstrings** - All functions documented  
✅ **Small functions** - Single responsibility principle  
✅ **Error handling** - Try/except with rollback  
✅ **No global sessions** - Session management via context  
✅ **SQLAlchemy 2.0 style** - Modern ORM patterns  
✅ **JSON helper functions** - Safe encode/decode  
✅ **Timezone-aware datetimes** - No deprecation warnings  

## Next Steps (Future Milestones)

- **Milestone 2:** LangGraph agents for disruption analysis
- **Milestone 3:** FastAPI REST endpoints
- **Milestone 4:** React frontend integration
- **Milestone 5:** Agent orchestration and human-in-the-loop workflows

## Notes

- SQLite is used for simplicity and offline operation
- JSON fields stored as TEXT (SQLite compatible)
- Foreign keys have CASCADE deletes configured
- All UUIDs generated deterministically in seed data
- Decision logs track full audit trail for compliance
