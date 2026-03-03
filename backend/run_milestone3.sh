#!/bin/bash
# Milestone 3 Quick Start Script

set -e  # Exit on error

echo "========================================"
echo "  Milestone 3: FastAPI Backend Setup"
echo "========================================"
echo ""

# Navigate to backend directory
cd "$(dirname "$0")"

# Set PYTHONPATH
export PYTHONPATH=$(pwd)

# Check if virtual environment should be used
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# Check if database exists
if [ ! -f "warehouse.db" ]; then
    echo "⚠️  Database not found. Run seed_data.py first:"
    echo "   PYTHONPATH=\$(pwd) python scripts/seed_data.py"
    exit 1
fi

# Check if users exist
echo "🔍 Checking for users..."
USER_COUNT=$(python -c "
from app.db.session import SessionLocal
from app.db.models import User
db = SessionLocal()
try:
    print(db.query(User).count())
finally:
    db.close()
" 2>/dev/null || echo "0")

if [ "$USER_COUNT" = "0" ]; then
    echo "👤 Creating default users..."
    python -c "
from app.db.session import SessionLocal
from app.db.models import User
from app.core.security import get_password_hash
import uuid

db = SessionLocal()
try:
    manager = User(
        user_id=str(uuid.uuid4()),
        username='manager_01',
        hashed_password=get_password_hash('password'),
        role='warehouse_manager',
    )
    db.add(manager)
    
    analyst = User(
        user_id=str(uuid.uuid4()),
        username='analyst_01',
        hashed_password=get_password_hash('password'),
        role='analyst',
    )
    db.add(analyst)
    
    db.commit()
    print('✓ Created default users: manager_01 and analyst_01')
except Exception as e:
    print(f'Error creating users: {e}')
    db.rollback()
finally:
    db.close()
"
else
    echo "✓ Users already exist ($USER_COUNT users)"
fi

echo ""
echo "========================================"
echo "  Starting FastAPI Server"
echo "========================================"
echo ""
echo "Server will start on: http://localhost:8000"
echo "API Documentation: http://localhost:8000/api/docs"
echo ""
echo "Default credentials:"
echo "  Manager: manager_01 / password"
echo "  Analyst: analyst_01 / password"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
