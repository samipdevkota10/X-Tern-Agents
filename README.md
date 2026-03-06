# X-Tern Agents

A full-stack AI-native Disruption Response Planner with FastAPI backend, multi-agent LangGraph pipeline, and Next.js frontend.

**Now featuring LLM-driven intelligent routing and MCP server integration!**

## Documentation

- 📖 [Demo Guide](docs/DEMO.md) - Complete end-to-end demo walkthrough
- 🔒 [Security Policy](SECURITY.md) - Authentication, secrets, and compliance
- 📊 [Problem & Impact](docs/PROBLEM_AND_IMPACT.md) - Business case and ROI
- 🏗️ [Technical Design](docs/TECHNICAL_DESIGN.md) - Architecture and data model
- 🛡️ [Governance & Safety](docs/GOVERNANCE_AND_SAFETY_BRIEF.md) - TRiSM and security
- 💼 [Business Sketch](docs/BUSINESS_SKETCH.md) - Value proposition and ROI
- 📋 [Next Steps & Pilot](docs/NEXT_STEPS_AND_PILOT_PLAN.md) - Roadmap and pilot plan
- 📝 [Example Decision Logs](docs/EXAMPLE_DECISION_LOGS.md) - Audit trail examples
- 🔧 [MCP Server](docs/MCP_SERVER_DEFINITIONS_AND_USAGE.md) - MCP tools and usage
- ☁️ [Deploy on EC2](docs/DEPLOY_EC2.md) - Backend deployment on AWS EC2

## Project Structure

```
├── backend/          # FastAPI + LangGraph + LangChain + AWS SDK
│   ├── app/          # FastAPI application (Milestone 3)
│   ├── scripts/      # Seed data, pipeline runners, tests
│   └── docs/         # Milestone documentation
├── frontend/         # Next.js 14 + TypeScript + Tailwind (Milestone 4)
│   ├── src/app/      # App Router pages
│   ├── src/components/ # Shared + UI components
│   ├── src/lib/      # API client, types, auth
│   └── src/hooks/    # Data fetching hooks
├── docs/             # Project documentation
│   ├── DEMO.md       # Demo walkthrough
│   └── PROBLEM_AND_IMPACT.md  # Business case
├── infra/            # Infrastructure configs
├── environment.yml   # Conda environment (Python + Node.js)
├── SECURITY.md       # Security policy
└── AWS_SETUP.md      # AWS configuration guide
```

## What's New: LLM-Driven Routing

The multi-agent pipeline now uses **intelligent LLM-driven routing** by default:

- **Dynamic step selection**: Claude analyzes state and decides next step
- **Deterministic guardrails**: Prerequisites and loop protection always enforced
- **Routing trace**: Full visibility into routing decisions
- **Graceful degradation**: Falls back to deterministic routing if LLM unavailable

```python
# Example routing trace entry
{
  "from": "signal_intake",
  "llm_next": "constraint_builder",
  "final": "constraint_builder",
  "confidence": 0.92
}
```

## What's New: MCP Server Mode

Enable modular tool architecture with Model Context Protocol:

```bash
# Start MCP server
PYTHONPATH=$(pwd) python scripts/run_mcp_server.py &

# Run with MCP mode
USE_MCP_SERVER=1 uvicorn app.main:app --reload
```

## Milestones

- ✅ **Milestone 1**: Database + MCP Tools ([README](backend/MILESTONE_1_README.md), [Complete](MILESTONE_1_COMPLETE.md))
- ✅ **Milestone 2**: LangGraph Multi-Agent Pipeline ([Quick Start](backend/MILESTONE_2_QUICK_START.md), [Complete](MILESTONE_2_COMPLETE.md))
- ✅ **Milestone 3**: FastAPI Backend APIs + Auth + Execution Gating ([README](backend/MILESTONE_3_README.md), [Complete](MILESTONE_3_COMPLETE.md))
- ✅ **Milestone 4**: Next.js Frontend with Glassmorphism Theme ([README](frontend/MILESTONE_4_README.md), [Complete](MILESTONE_4_COMPLETE.md))

## Setup

### Prerequisites

- [Conda](https://docs.conda.io/en/latest/miniconda.html) or [Mamba](https://mamba.readthedocs.io/) (recommended for faster installs)
- Git

### Environment Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd X-Tern-Agents
```

2. Create and activate the conda environment:

```bash
# Using conda
conda env create -f environment.yml
conda activate xtern-agents

# OR using mamba (faster)
mamba env create -f environment.yml
mamba activate xtern-agents
```

3. Install frontend dependencies:

```bash
cd frontend
npm install
cd ..
```

4. Configure environment variables:

```bash
# Backend
cp backend/.env.example backend/.env
# Edit backend/.env with your AWS credentials and configuration

# Frontend
cp frontend/.env.example frontend/.env
# Edit frontend/.env if needed
```

## Quick Start

### Full Stack (Milestone 4 + 3)

```bash
# 1. Setup environment (from repo root)
conda env create -f environment.yml
conda activate xtern-agents

# 2. Start backend (terminal 1)
cd backend
./run_milestone3.sh
# Backend runs on http://localhost:8000

# 3. Start frontend (terminal 2)
cd frontend
pnpm install
pnpm dev
# Frontend runs on http://localhost:3000

# 4. Login
# Visit http://localhost:3000
# Manager: manager_01 / password
# Analyst: analyst_01 / password
```

**Frontend**: http://localhost:3000  
**API Documentation**: http://localhost:8000/api/docs  
**Default Login**: `manager_01` / `password`

## Demo (Local)

For a complete end-to-end demonstration, see [docs/DEMO.md](docs/DEMO.md).

Quick demo path:
1. Login as `manager_01`
2. Create a disruption (Disruptions → + New Disruption)
3. Run the planner (click disruption → Run Planner)
4. Watch LLM routing in action (check terminal logs)
5. Review scenarios (Scenarios page)
6. Approve/reject as manager (Approvals page)
7. View audit trail (Audit Log page)

## Demo (MCP Mode)

Run the same demo with MCP server for modular tool architecture:

```bash
# Terminal 1: Start MCP server
cd backend
PYTHONPATH=$(pwd) python scripts/run_mcp_server.py &

# Terminal 2: Start backend with MCP mode
USE_MCP_SERVER=1 PYTHONPATH=$(pwd) uvicorn app.main:app --reload

# Terminal 3: Start frontend
cd frontend && pnpm dev
```

Check logs for MCP tool calls:
```
DEBUG: [MCP] read_disruption: D-20260303-001
DEBUG: [MCP] write_scenarios: 3 scenarios
```

### Milestone 3: FastAPI Backend Only

```bash
# 1. Setup environment (from repo root)
conda env create -f environment.yml
conda activate xtern-agents

# 2. Seed database (if not already done)
cd backend
PYTHONPATH=$(pwd) python scripts/seed_data.py

# 3. Start API server
./run_milestone3.sh
# Or: uvicorn app.main:app --reload

# 4. Test API (in new terminal)
python scripts/api_smoke_test.py
```

### Milestone 2: Multi-Agent Pipeline

```bash
cd backend
PYTHONPATH=$(pwd) USE_AWS=0 python scripts/run_pipeline_once.py
```

### Milestone 1: Database + Tools

```bash
cd backend
./run_milestone1.sh
```

## Backend

- **Framework:** FastAPI with JWT authentication
- **AI/ML:** LangGraph multi-agent system, LangChain, AWS Bedrock (optional)
- **Database:** SQLite (local) or PostgreSQL (AWS RDS)
- **Storage:** Optional AWS S3, DynamoDB for pipeline status

### Key Features

- **JWT Authentication**: Role-based access (warehouse_manager, analyst)
- **REST API**: 20+ endpoints for disruptions, pipeline, scenarios, audit logs
- **Real Execution Gating**: Scenarios validated and applied with constraint checking
- **Multi-Agent Pipeline**: Supervisor pattern with 4 specialized agents
- **LLM-Driven Routing**: Claude-powered intelligent step selection with guardrails
- **MCP Server Mode**: Optional modular tool architecture via MCP protocol
- **Audit Trail**: Complete decision logging with routing trace for compliance

### API Endpoints

- **Auth**: `/api/auth/login`, `/api/auth/me`
- **Disruptions**: `/api/disruptions` (CRUD)
- **Pipeline**: `/api/pipeline/run`, `/api/pipeline/{id}/status`
- **Scenarios**: `/api/scenarios` (list/approve/reject/edit)
- **Audit**: `/api/audit-logs`
- **Dashboard**: `/api/dashboard`

### MCP Tools (Milestone 1)

- `read_open_orders`, `read_inventory`, `read_inbound_status`
- `read_capacity`, `get_pending_scenarios`
- `write_scenarios`, `approve_scenario`, `reject_scenario`
- `write_decision_log`, `read_disruption`, `read_substitutions`

## Frontend

**Tech Stack:**
- **Framework:** Next.js 16.1.6 (App Router)
- **Language:** TypeScript 5.9
- **Styling:** Tailwind CSS v4 + shadcn/ui
- **Data Fetching:** SWR with auto-refresh
- **Authentication**: JWT with role-based access
- **Theme:** Glassmorphism dark with gradient background

### Pages

- **Login**: JWT authentication with username/password
- **Dashboard**: KPIs, SLA risk chart, recent disruptions
- **Disruptions**: Inbox with filters, create dialog, detail sheet
- **Scenarios**: Grouped comparison with approve/reject (manager-only)
- **Approvals**: Manager-only queue with bulk approve
- **Audit Log**: Filterable log with export to JSON
- **Run Planner**: Pipeline trigger with real-time stepper

### Key Features

- **Real-Time Updates**: SWR auto-refresh (10-15s intervals)
- **Pipeline Polling**: 2s updates while running
- **Role-Based UI**: Manager vs Analyst permissions
- **Skeleton Loaders**: No spinners, glass shimmer animation
- **Toast Notifications**: All user actions have feedback
- **Error Handling**: 401 auto-logout, constraint violations

## Environment Variables

Copy `.env.example` files to `.env`:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

### Key Backend Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./warehouse.db` | Database connection string |
| `JWT_SECRET` | (required) | JWT signing key (32+ chars in prod) |
| `USE_AWS` | `0` | Enable AWS services (Bedrock, DynamoDB) |
| `BEDROCK_MODEL_ID` | - | Claude model ID for LLM routing |
| `USE_MCP_SERVER` | `0` | Route tool calls via MCP server |
| `USE_DETERMINISTIC_ROUTING` | `0` | Disable LLM routing (legacy mode) |
| `MAX_PIPELINE_STEPS` | `20` | Max steps before forced finalize |

## License

MIT
