# X-Tern Agents – Architecture Diagram

Multi-agent disruption response planner built with FastAPI, LangGraph, and Next.js. **LLM (AWS Bedrock) is the default** for routing, scenario generation, and tradeoff scoring; deterministic rules provide fallback when LLM is unavailable. Diagrams use [Mermaid](https://mermaid.js.org/) and render in GitHub, VS Code, and most markdown viewers.

---

## 1. System Context

High-level view of system components and external integrations.

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        Browser[Browser]
    end

    subgraph Frontend["Frontend (Next.js 16)"]
        Pages[App Router Pages]
        Hooks[SWR Hooks]
        Components[UI Components]
        API[api.ts Client]
    end

    subgraph Backend["Backend (FastAPI)"]
        REST[JWT REST API]
        Pipeline[Pipeline Runner]
        Agents[LangGraph Agents LLM-first]
    end

    subgraph Data["Data & External"]
        DB[(SQLite / RDS)]
        Chroma[(ChromaDB RAG)]
        S3[(AWS S3)]
        Dynamo[(DynamoDB)]
        Bedrock["AWS Bedrock (LLM default)"]
    end

    Browser --> Frontend
    Frontend -->|REST + JWT| REST
    REST --> Pipeline
    Pipeline --> Agents
    Backend --> DB
    Backend --> Chroma
    Backend -->|optional| S3
    Backend -->|optional| Dynamo
    Backend -->|LLM default| Bedrock
```

---

## 2. Backend Layers

```mermaid
flowchart TB
    subgraph API["API Routes"]
        auth[/auth]
        disruptions[/disruptions]
        pipeline[/pipeline]
        scenarios[/scenarios]
        audit[/audit-logs]
        dashboard[/dashboard]
        governance[/governance]
        rag[/rag]
    end

    subgraph Services["Services"]
        pipeline_runner[Pipeline Runner]
        execution_engine[Execution Engine]
    end

    subgraph Agents["LangGraph Agents (LLM default)"]
        router["Router (LLM)"]
        signal[Signal Intake]
        constraint[Constraint Builder]
        scenario["Scenario Generator (LLM)"]
        tradeoff["Tradeoff Scoring (LLM)"]
        finalizer[Finalizer]
    end

    subgraph Tools["MCP / Tools"]
        read[read_*]
        write[write_scenarios, write_decision_log]
        update[update_scenario_scores]
    end

    subgraph Persistence["Persistence"]
        SQL[(SQLAlchemy)]
    end

    API --> pipeline_runner
    pipeline_runner --> Agents
    Agents --> Tools
    Tools --> SQL
```

**LLM usage:** Router, Scenario Generator, and Tradeoff Scoring use AWS Bedrock (Claude) by default. Rules-based fallback runs when `USE_AWS=0` or Bedrock is unavailable.

---

## 3. Pipeline Flow (LangGraph)

Router-driven orchestration with **LLM as default** for routing decisions. Each domain agent returns to the Router; the Router (LLM or fallback rules) decides the next step or routes to the Finalizer.

```mermaid
flowchart LR
    subgraph Pipeline["LangGraph Pipeline (LLM-first)"]
        direction TB
        R(["Router (LLM)"])
        SI[Signal Intake]
        CB[Constraint Builder]
        SG["Scenario Generator (LLM)"]
        TS["Tradeoff Scoring (LLM)"]
        F[Finalizer]
    end

    R -->|"signal_intake"| SI
    R -->|"constraint_builder"| CB
    R -->|"scenario_generator"| SG
    R -->|"tradeoff_scoring"| TS
    R -->|"finalizer"| F
    R -->|"END"| E([END])

    SI --> R
    CB --> R
    SG --> R
    TS --> R

    F --> E
```

**State flow:**
- `signal` → `constraints` → `scenarios` → `scores` → `final_summary`
- Routing metadata: `step_count`, `max_steps`, `needs_review`, `routing_trace`
- LLM agents: Router, Scenario Generator, Tradeoff Scoring (fallback: deterministic rules)

---

## 4. Data Model (Core Entities)

```mermaid
erDiagram
    Disruption ||--o{ Order : affects
    Disruption ||--o{ Scenario : generates
    Order ||--o{ Scenario : has_scenarios
    PipelineRun ||--o{ Scenario : produces
    PipelineRun ||--o{ DecisionLog : logs
    User ||--o{ DecisionLog : approves

    Disruption {
        uuid id PK
        string type
        int severity
        json details_json
        string status
    }

    Order {
        string order_id PK
        uuid disruption_id FK
        string status
        datetime promised_ship_time
    }

    Scenario {
        uuid scenario_id PK
        uuid disruption_id FK
        string order_id FK
        string action_type
        json plan_json
        json score_json
        string status
    }

    PipelineRun {
        uuid pipeline_run_id PK
        uuid disruption_id FK
        string status
        json final_summary_json
    }

    DecisionLog {
        uuid log_id PK
        uuid pipeline_run_id FK
        string agent_name
        string rationale
        string human_decision
    }
```

---

## 5. Frontend Structure

```mermaid
flowchart TB
    subgraph Pages["App Router Pages"]
        login["/login"]
        dashboard["/dashboard"]
        disruptions["/disruptions"]
        run["/run"]
        scenarios["/scenarios"]
        approvals["/approvals"]
        approved["/approved"]
        audit["/audit"]
    end

    subgraph Hooks["Data Hooks"]
        useDisruptions
        useScenarios
        usePipelineStatus
        useAuditLogs
        useAgentActivity
    end

    subgraph API["API Client"]
        apiFetch
        listScenarios
        startPipeline
        getPipelineStatus
    end

    Pages --> Hooks
    Hooks --> API
    API -->|"/api/*"| Backend[FastAPI Backend]
```

---

## 6. AWS Integration

```mermaid
flowchart LR
    subgraph Backend["Backend"]
        runner[Pipeline Runner]
        agents[Agents]
    end

    subgraph AWS["AWS Services"]
        S3[S3 Bucket]
        Dynamo[DynamoDB]
        Bedrock["Bedrock (LLM default)"]
    end

    runner -->|"optional"| S3
    agents -->|"optional"| Dynamo
    agents -->|"LLM default"| Bedrock
```

| Service   | Purpose                          | Config              | When          |
|----------|-----------------------------------|---------------------|---------------|
| Bedrock  | LLM (routing, scenarios, scoring, explanation) | `BEDROCK_MODEL_ID`  | Default when `USE_AWS=1` |
| S3       | Pipeline run JSON (summary + scenarios) | `S3_BUCKET_NAME`    | When `USE_AWS=1` |
| DynamoDB | Per-step pipeline status          | `DYNAMO_STATUS_TABLE` | When `USE_AWS=1` |
| RDS      | Production PostgreSQL             | `DATABASE_URL`      | Optional       |

---

## 7. Request Flow (Run Pipeline)

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant API as FastAPI
    participant PR as Pipeline Runner
    participant G as LangGraph
    participant DB as Database

    U->>F: Click "Run Pipeline"
    F->>API: POST /api/pipeline/run
    API->>DB: Create PipelineRun (queued)
    API->>PR: Background task
    API-->>F: 202 {pipeline_run_id}

    loop Poll status
        F->>API: GET /api/pipeline/{id}/status
        API->>DB: Read PipelineRun
        API-->>F: status, progress
    end

    par Pipeline execution
        PR->>G: graph.invoke(state)
        G->>G: Router (LLM) → Agents (LLM) → Tools
        G->>DB: write_scenarios, write_decision_log
        PR->>DB: Update PipelineRun (done)
    end

    F->>API: GET /api/scenarios?disruption_id=...
    API->>DB: Query Scenario
    API-->>F: Scenarios list
```

---

## 8. Project Layout

```
X-Tern Agents/
├── backend/
│   ├── app/
│   │   ├── api/routes/      # FastAPI routers
│   │   ├── agents/          # LangGraph nodes
│   │   ├── aws/             # S3, DynamoDB, Bedrock
│   │   ├── core/            # config, deps, security
│   │   ├── db/               # models, session
│   │   ├── governance/       # TRiSM
│   │   ├── mcp/              # tools, tool_router
│   │   ├── rag/              # ChromaDB knowledge base
│   │   └── services/        # pipeline_runner, execution_engine
│   ├── scripts/             # e2e, verify, seed
│   └── main.py
├── frontend/
│   └── src/
│       ├── app/              # Next.js App Router pages
│       ├── components/       # shared + ui
│       ├── hooks/            # useScenarios, usePipelineStatus, etc.
│       └── lib/              # api, auth, types
├── docs/
├── infra/
└── Makefile
```

---

## 9. LLM-First Architecture

```mermaid
flowchart TB
    subgraph Agents["Agents"]
        Router[Router]
        SG[Scenario Generator]
        TS[Tradeoff Scoring]
    end

    subgraph LLM["LLM (AWS Bedrock - Default)"]
        Claude[Claude via Bedrock]
    end

    subgraph Fallback["Fallback (when LLM unavailable)"]
        Rules[Deterministic Rules]
    end

    Router -->|"primary"| Claude
    Router -.->|"fallback"| Rules
    SG -->|"primary"| Claude
    SG -.->|"fallback"| Rules
    TS -->|"primary"| Claude
    TS -.->|"fallback"| Rules
```

**Configuration:** Set `USE_AWS=1`, `BEDROCK_MODEL_ID`, and AWS credentials. Without them, agents use rules-based fallback automatically.

---

*Generated for X-Tern Agents. LLM (Bedrock) is the default. View in GitHub or any Mermaid-compatible markdown viewer.*
