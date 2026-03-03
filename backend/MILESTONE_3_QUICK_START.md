# Milestone 3 Quick Start

## 🚀 Get Started in 3 Commands

```bash
# 1. Seed database (if not already done)
cd backend
PYTHONPATH=$(pwd) python scripts/seed_data.py

# 2. Start API server
./run_milestone3.sh
# Or: uvicorn app.main:app --reload

# 3. Test API (in new terminal)
python scripts/api_smoke_test.py
```

## 📊 What You Get

- **FastAPI server** on http://localhost:8000
- **Interactive API docs** at http://localhost:8000/api/docs
- **JWT authentication** with role-based access
- **20+ REST endpoints** for full disruption response workflow
- **Real execution gating** - scenarios validated before applying changes

## 🔑 Default Credentials

- **Manager**: `manager_01` / `password` (can approve/reject/edit)
- **Analyst**: `analyst_01` / `password` (read-only)

## 🎯 Quick Test Flow

### 1. Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "manager_01", "password": "password"}'
```

Copy the `access_token` from response.

### 2. List Disruptions

```bash
TOKEN="your-token-here"

curl -X GET "http://localhost:8000/api/disruptions?status=open" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Start Pipeline

```bash
curl -X POST http://localhost:8000/api/pipeline/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"disruption_id": "your-disruption-id"}'
```

### 4. Check Status

```bash
curl -X GET http://localhost:8000/api/pipeline/your-run-id/status \
  -H "Authorization: Bearer $TOKEN"
```

### 5. List Pending Scenarios

```bash
curl -X GET http://localhost:8000/api/scenarios/pending \
  -H "Authorization: Bearer $TOKEN"
```

### 6. Approve Scenario

```bash
curl -X POST http://localhost:8000/api/scenarios/scenario-id/approve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"note": "Approved after verification"}'
```

## 🧪 Automated Testing

```bash
# Run full smoke test suite
python scripts/api_smoke_test.py
```

This will:
1. ✓ Login as manager
2. ✓ List disruptions
3. ✓ Start pipeline run
4. ✓ Poll until complete
5. ✓ List pending scenarios
6. ✓ Approve one scenario
7. ✓ Verify audit logs
8. ✓ Check dashboard

## 📚 API Documentation

Visit http://localhost:8000/api/docs for interactive Swagger UI:

1. Click "Authorize" button
2. Login via `/api/auth/login` endpoint
3. Copy `access_token`
4. Paste in authorization dialog
5. Test all endpoints interactively

## 🔍 Key Endpoints

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/api/auth/login` | POST | Login | No |
| `/api/auth/me` | GET | Current user | Yes |
| `/api/disruptions` | GET/POST | Disruptions CRUD | Yes |
| `/api/pipeline/run` | POST | Start pipeline | Yes |
| `/api/pipeline/{id}/status` | GET | Pipeline status | Yes |
| `/api/scenarios` | GET | List scenarios | Yes |
| `/api/scenarios/pending` | GET | Pending with context | Yes |
| `/api/scenarios/{id}/approve` | POST | Approve & apply | Manager |
| `/api/scenarios/{id}/reject` | POST | Reject | Manager |
| `/api/scenarios/{id}/edit` | POST | Edit & re-score | Manager |
| `/api/audit-logs` | GET | Decision logs | Yes |
| `/api/dashboard` | GET | Summary metrics | Yes |

## 🐛 Troubleshooting

### Server won't start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill existing process
pkill -f "uvicorn app.main:app"
```

### Users not created
```bash
# Manually create users
PYTHONPATH=$(pwd) python -c "
from app.db.session import SessionLocal
from app.db.models import User
from app.core.security import get_password_hash
import uuid

db = SessionLocal()
try:
    if db.query(User).count() == 0:
        db.add(User(
            user_id=str(uuid.uuid4()),
            username='manager_01',
            hashed_password=get_password_hash('password'),
            role='warehouse_manager',
        ))
        db.add(User(
            user_id=str(uuid.uuid4()),
            username='analyst_01',
            hashed_password=get_password_hash('password'),
            role='analyst',
        ))
        db.commit()
        print('✓ Users created')
finally:
    db.close()
"
```

### "401 Unauthorized"
- Token expired (24h) - login again
- Check Authorization header: `Bearer <token>`

### "422 Unprocessable Entity" on approval
- **This is expected!** Means constraint violation (e.g., insufficient inventory)
- Proves real execution gating is working
- Try approving a different scenario

## 📖 Learn More

- **Full Documentation**: `MILESTONE_3_README.md`
- **Completion Report**: `../MILESTONE_3_COMPLETE.md`
- **AWS Setup**: `../AWS_SETUP.md`

## ✅ Success Checklist

- [ ] Server starts without errors
- [ ] Can login and get JWT token
- [ ] API docs accessible at /api/docs
- [ ] Can list disruptions
- [ ] Can start pipeline run
- [ ] Can poll pipeline status
- [ ] Can list pending scenarios
- [ ] Can approve/reject scenarios
- [ ] Smoke test passes

---

**Status:** ✅ Ready for Development  
**Next:** Build Next.js frontend (Milestone 4)
