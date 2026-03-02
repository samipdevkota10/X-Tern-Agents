# X-Tern Agents

A full-stack application with FastAPI backend, React frontend, and MCP (Model Context Protocol) server layer.

## Project Structure

```
├── backend/          # FastAPI + LangChain + AWS SDK
├── frontend/         # React (Vite)
├── infra/            # Infrastructure configs
├── docker-compose.yml
├── Makefile
└── README.md
```

## Quick Start

### Development

```bash
# Start all services
make dev

# Start backend only
make backend

# Start frontend only
make frontend

# Run tests
make test

# Format code
make fmt
```

### Docker

```bash
docker-compose up --build
```

## Backend

- **Framework:** FastAPI
- **AI/ML:** LangChain, AWS Bedrock
- **Database:** DynamoDB
- **Storage:** S3

### Endpoints

- `GET /health` - Health check
- `POST /cases` - Create a new case
- `GET /cases` - List all cases
- `POST /cases/{id}/decisions` - Append decision log

### MCP Tools

- `read_case_state` - Read current case state
- `write_decision_record` - Write decision to log
- `compute_risk_score` - Calculate risk score

## Frontend

- **Framework:** React 18 + Vite
- **Routing:** React Router
- **State:** React Context

### Pages

- Login (placeholder)
- Case List
- Case Detail (timeline view)
- Approval Modal (HITL - Human In The Loop)

## Environment Variables

Copy `.env.example` files to `.env`:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

## License

MIT
