# X-Tern Agents

A full-stack Disruption Response Planner with FastAPI backend, multi-agent LangGraph pipeline, and React frontend.

## Project Structure

```
├── backend/          # FastAPI + LangGraph + LangChain + AWS SDK
│   ├── app/          # FastAPI application (Milestone 3)
│   ├── scripts/      # Seed data, pipeline runners, tests
│   └── docs/         # Milestone documentation
├── frontend/         # React (Vite) - Coming in Milestone 4
├── infra/            # Infrastructure configs
├── environment.yml   # Conda environment (Python + Node.js)
└── AWS_SETUP.md      # AWS configuration guide
```

## Milestones

- ✅ **Milestone 1**: Database + MCP Tools ([README](backend/MILESTONE_1_README.md), [Complete](MILESTONE_1_COMPLETE.md))
- ✅ **Milestone 2**: LangGraph Multi-Agent Pipeline ([Quick Start](backend/MILESTONE_2_QUICK_START.md), [Complete](MILESTONE_2_COMPLETE.md))
- ✅ **Milestone 3**: FastAPI Backend APIs + Auth + Execution Gating ([README](backend/MILESTONE_3_README.md), [Complete](MILESTONE_3_COMPLETE.md))
- 🚧 **Milestone 4**: Next.js Frontend (Coming soon)

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

### Milestone 3: FastAPI Backend

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

**API Documentation**: http://localhost:8000/api/docs  
**Default Login**: `manager_01` / `password`

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
- **Audit Trail**: Complete decision logging for compliance

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

Coming in Milestone 4:
- **Framework:** Next.js 14 with TypeScript
- **UI Library:** Tailwind CSS + shadcn/ui
- **State Management:** React Query for API calls
- **Authentication**: JWT token management

### Planned Pages

- Login
- Dashboard (metrics + recent decisions)
- Disruptions List
- Pipeline Runs (with real-time status)
- Scenarios Approval Queue
- Audit Log Viewer

## Environment Variables

Copy `.env.example` files to `.env`:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

## License

MIT
