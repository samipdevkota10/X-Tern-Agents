# Milestone 3: FastAPI Backend APIs + Auth + Real Execution Gating

## Overview

Milestone 3 implements a production-quality FastAPI backend with JWT authentication, RESTful APIs, and **real human-in-the-loop execution gating**. Scenarios remain as plans until a warehouse manager approves them, at which point changes are applied to the operational database with full constraint validation.

## Key Features

### 1. JWT Authentication with Roles

- **Roles:**
  - `warehouse_manager`: Can approve/reject/edit scenarios and trigger pipelines
  - `analyst`: Read-only access to all data

- **Endpoints:**
  - `POST /api/auth/login`: Login with username/password, returns JWT token
  - `GET /api/auth/me`: Get current user info

- **Default Users:**
  - `manager_01` / `password` (warehouse_manager)
  - `analyst_01` / `password` (analyst)

### 2. REST API Endpoints

#### Disruptions
- `POST /api/disruptions`: Create new disruption
- `GET /api/disruptions`: List disruptions (filter by status)
- `GET /api/disruptions/{id}`: Get disruption details

#### Pipeline Execution
- `POST /api/pipeline/run`: Start pipeline run (background task)
- `GET /api/pipeline/{run_id}/status`: Poll pipeline status and progress

#### Scenarios
- `GET /api/scenarios`: List scenarios (filter by disruption/status, pagination)
- `GET /api/scenarios/pending`: List pending scenarios with context
- `GET /api/scenarios/{id}`: Get scenario details
- `POST /api/scenarios/{id}/approve`: **Approve and apply scenario** (manager only)
- `POST /api/scenarios/{id}/reject`: Reject scenario (manager only)
- `POST /api/scenarios/{id}/edit`: Edit scenario plan and re-score (manager only)

#### Audit Logs
- `GET /api/audit-logs`: List decision logs (filter by pipeline/agent/decision)

#### Dashboard
- `GET /api/dashboard`: Summary metrics and recent decisions

### 3. Real Execution Gating

**Scenarios are only plans until approved.** When a manager approves a scenario:

1. **Validation:** System checks constraints (inventory availability, etc.)
2. **Application:** Changes are applied to operational database:
   - **delay**: Update order status and promised ship time
   - **reroute**: Change order DC and adjust inventory reservations
   - **substitute**: Replace SKU in order lines
   - **resequence**: Update order priority in work queue
3. **Audit:** Decision log entry created with all changes
4. **Failure:** If constraints violated (e.g., insufficient inventory), approval fails with 422 error

This proves **real gating** - the system will reject approvals that violate operational constraints.

## Architecture

```
backend/
├── app/
│   ├── main.py                    # FastAPI app with CORS and startup
│   ├── core/
│   │   ├── config.py              # Settings from environment
│   │   ├── security.py            # JWT and password hashing
│   │   └── deps.py                # Dependency injection (auth, DB)
│   ├── api/
│   │   ├── schemas.py             # Pydantic request/response models
│   │   └── routes/
│   │       ├── auth.py            # Login and user info
│   │       ├── disruptions.py     # Disruption CRUD
│   │       ├── pipeline.py        # Pipeline execution
│   │       ├── scenarios.py       # Scenario approval/rejection/editing
│   │       ├── audit_logs.py      # Decision log queries
│   │       └── dashboard.py       # Dashboard summary
│   ├── services/
│   │   ├── execution_engine.py    # Apply approved scenarios to DB
│   │   └── pipeline_runner.py     # Run LangGraph pipeline in background
│   └── db/
│       └── models.py              # Updated with User, sequence_priority, etc.
└── scripts/
    └── api_smoke_test.py          # End-to-end API test
```

## Database Changes

### New Model: User
- `user_id`, `username`, `hashed_password`, `role`

### Updated Models:
- **Order**: Added `sequence_priority` (int, 1=urgent, 5=normal)
- **PipelineRun**: Added `current_step`, `progress` (0.0-1.0), status now includes "queued"

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

New dependencies added:
- `python-jose[cryptography]` - JWT tokens
- `passlib[bcrypt]` - Password hashing
- `requests` - HTTP client for tests

### 2. Set Environment Variables

```bash
# Copy example
cp .env.example .env

# Edit .env - key variables:
DATABASE_URL=sqlite:///./warehouse.db
JWT_SECRET=your-secret-key-change-in-production-min-32-chars
USE_AWS=0  # Local dev mode
```

### 3. Seed Database (if not already done)

```bash
PYTHONPATH=$(pwd) python scripts/seed_data.py
```

This will also create the new `users` table and seed default users.

### 4. Start API Server

```bash
uvicorn app.main:app --reload
```

Server starts on `http://localhost:8000`

- API docs: http://localhost:8000/api/docs
- Health check: http://localhost:8000/health

### 5. Run Smoke Tests

In a new terminal:

```bash
cd backend
python scripts/api_smoke_test.py
```

This will:
1. Login as manager
2. List disruptions
3. Start pipeline run
4. Poll until complete
5. List pending scenarios
6. Approve one scenario (or verify constraint validation)
7. Check audit logs
8. Verify dashboard data

## API Usage Examples

### Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "manager_01", "password": "password"}'
```

Response:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "role": "warehouse_manager"
}
```

### Start Pipeline

```bash
TOKEN="your-jwt-token"

curl -X POST http://localhost:8000/api/pipeline/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"disruption_id": "abc-123"}'
```

### Approve Scenario

```bash
curl -X POST http://localhost:8000/api/scenarios/{scenario_id}/approve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"note": "Approved - inventory sufficient"}'
```

Success response (200):
```json
{
  "scenario_id": "xyz-789",
  "status": "approved",
  "applied_changes": {
    "scenario_id": "xyz-789",
    "action_type": "reroute",
    "order_id": "ORD0001",
    "changes": [
      {
        "type": "inventory_reserve",
        "dc": "DC2",
        "sku": "SKU0001",
        "qty": 10,
        "old_reserved": 50,
        "new_reserved": 60
      },
      {
        "type": "order_dc_change",
        "field": "dc",
        "old_value": "DC1",
        "new_value": "DC2"
      }
    ],
    "decision_log_id": "log-123"
  },
  "decision_log_id": "log-123"
}
```

Constraint violation (422):
```json
{
  "detail": {
    "error": {
      "code": "EXECUTION_FAILED",
      "message": "Insufficient inventory for SKU SKU0001 at DC2: need 10, available 5"
    }
  }
}
```

## Error Handling

All errors follow consistent structure:

```json
{
  "detail": {
    "error": {
      "code": "ERROR_CODE",
      "message": "Human-readable message",
      "meta": {
        "additional": "context"
      }
    }
  }
}
```

Common error codes:
- `INVALID_CREDENTIALS`: Login failed
- `INVALID_TOKEN`: JWT token invalid or expired
- `INSUFFICIENT_PERMISSIONS`: User lacks required role
- `SCENARIO_NOT_FOUND`: Scenario ID not found
- `SCENARIO_NOT_PENDING`: Scenario already approved/rejected
- `EXECUTION_FAILED`: Constraint violation during approval

## CORS Configuration

Configured to allow:
- `http://localhost:3000`
- `http://localhost:3001`
- `http://127.0.0.1:3000`
- `http://127.0.0.1:3001`

Ready for Next.js frontend (Milestone 4).

## Testing

### Manual Testing with API Docs

Visit http://localhost:8000/api/docs for interactive Swagger UI:
1. Click "Authorize" button
2. Login via `/api/auth/login` endpoint
3. Copy the `access_token` from response
4. Paste into authorization dialog (format: `Bearer <token>`)
5. Test all endpoints interactively

### Automated Testing

```bash
python scripts/api_smoke_test.py
```

Expected output:
```
======================================================================
  API Smoke Test - Milestone 3
======================================================================

======================================================================
  1. Health Check
======================================================================

✓ API is healthy

======================================================================
  2. Authentication
======================================================================

✓ Logged in as manager_01
  Role: warehouse_manager
  Token: eyJhbGciOiJIUzI1NiIs...

...

======================================================================
  ✅ All Tests Passed
======================================================================

✓ Milestone 3 API is working correctly
```

## Production Considerations

### Security
- Change `JWT_SECRET` to a strong random value (min 32 chars)
- Use HTTPS in production
- Implement token refresh mechanism
- Add rate limiting
- Consider API key authentication for service-to-service

### Database
- Use PostgreSQL (AWS RDS) instead of SQLite
- Set `DATABASE_URL=postgresql://user:pass@host:5432/warehouse`
- Implement proper migrations (Alembic)

### Deployment
- Use Gunicorn with multiple workers
- Set `APP_DEBUG=false` in production
- Configure proper logging
- Add health check monitoring
- Use environment-specific CORS origins

## Next Steps

- **Milestone 4**: Next.js frontend with React components
- **Future**: WebSocket support for real-time pipeline updates
- **Future**: Batch approval operations
- **Future**: Advanced filtering and search

## Troubleshooting

### "Could not connect to API"
- Ensure server is running: `uvicorn app.main:app --reload`
- Check port 8000 is not in use

### "401 Unauthorized"
- Token expired (default 24 hours) - login again
- Token format must be `Bearer <token>` in Authorization header

### "422 Unprocessable Entity" on approval
- This is expected for some scenarios (constraint violations)
- Indicates real execution gating is working
- Try approving a different scenario

### "ModuleNotFoundError"
- Install new dependencies: `pip install -r requirements.txt`
- Set PYTHONPATH: `export PYTHONPATH=$(pwd)`

---

**Status:** ✅ Milestone 3 Complete  
**Next:** Milestone 4 - Next.js Frontend
