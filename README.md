# X-Tern Agents

A full-stack AI-native Disruption Response Planner with FastAPI backend, multi-agent LangGraph pipeline, and Next.js frontend.

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
├── infra/            # Infrastructure configs
├── environment.yml   # Conda environment (Python + Node.js)
└── AWS_SETUP.md      # AWS configuration guide
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

## License

MIT
