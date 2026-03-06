#!/bin/bash
#
# Deploy X-Tern Agents backend on EC2.
# Run this script ON the EC2 instance after cloning the repo.
#
# Usage:
#   cd ~/X-Tern-Agents
#   chmod +x infra/ec2/deploy_backend.sh
#   ./infra/ec2/deploy_backend.sh
#
# Prerequisites: Python 3.11+, git
# Optional: Set EC2_PUBLIC_IP before running to auto-configure CORS
#
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
CURRENT_USER="${SUDO_USER:-$USER}"
HOME_DIR=$(eval echo "~$CURRENT_USER")

echo "=== X-Tern Backend EC2 Deployment ==="
echo "Repo root: $REPO_ROOT"
echo "Backend:   $BACKEND_DIR"
echo "User:      $CURRENT_USER"
echo ""

# Check Python (prefer 3.11, fallback to any python3)
if command -v python3.11 &>/dev/null; then
    PYTHON=python3.11
elif command -v python3 &>/dev/null; then
    PYTHON=python3
else
    echo "Error: python3 not found. Install with: sudo apt install python3.11 python3.11-venv"
    exit 1
fi
echo "Using Python: $PYTHON ($($PYTHON --version 2>&1))"

# Create venv
echo ""
echo "1. Creating virtual environment..."
cd "$BACKEND_DIR"
if [ ! -d .venv ]; then
    $PYTHON -m venv .venv
    echo "   Created .venv"
else
    echo "   .venv exists"
fi
source .venv/bin/activate

# Install dependencies
echo ""
echo "2. Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "   Done"

# Create .env if missing
echo ""
echo "3. Configuring environment..."
if [ ! -f .env ]; then
    cp .env.example .env 2>/dev/null || true
    if [ ! -f .env ]; then
        echo "   No .env.example found. Creating minimal .env..."
        cat > .env << 'ENVEOF'
DATABASE_URL=sqlite:///./warehouse.db
JWT_SECRET=change-me-in-production-min-32-chars
USE_MCP_SERVER=0
USE_AWS=0
ENVEOF
    fi
    echo "   Created .env from template - REVIEW AND EDIT BEFORE PRODUCTION"
else
    echo "   .env exists"
fi

# Ensure ChromaDB persist dir exists
mkdir -p "$BACKEND_DIR/chroma_data"

# Add CORS if EC2_PUBLIC_IP set
if [ -n "$EC2_PUBLIC_IP" ]; then
    echo "   Adding CORS origins for http://$EC2_PUBLIC_IP:3000 and :8000"
    if ! grep -q "CORS_ORIGINS_EXTRA" .env 2>/dev/null; then
        echo "" >> .env
        echo "# CORS for EC2 frontend" >> .env
        echo "CORS_ORIGINS_EXTRA=http://$EC2_PUBLIC_IP:3000,http://$EC2_PUBLIC_IP:8000,https://$EC2_PUBLIC_IP:3000,https://$EC2_PUBLIC_IP:8000" >> .env
    fi
fi

# Seed data if DB doesn't exist
echo ""
echo "4. Seeding database (if needed)..."
if [ ! -f "$BACKEND_DIR/warehouse.db" ]; then
    PYTHONPATH="$BACKEND_DIR" python scripts/seed_data.py && echo "   Seeded successfully" || echo "   Seed failed - run manually: cd backend && PYTHONPATH=. python scripts/seed_data.py"
else
    echo "   Database exists, skipping seed"
fi

# Install systemd service
echo ""
echo "5. Installing systemd service..."
SERVICE_FILE="/etc/systemd/system/xtern-backend.service"
# Use actual paths (replace %i and %h for concrete user)
cat > /tmp/xtern-backend.service << SERVICEEOF
[Unit]
Description=X-Tern Agents Backend API
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$BACKEND_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$BACKEND_DIR"
EnvironmentFile=$BACKEND_DIR/.env
ExecStart=$BACKEND_DIR/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICEEOF

sudo mv /tmp/xtern-backend.service "$SERVICE_FILE"
sudo systemctl daemon-reload
sudo systemctl enable xtern-backend
echo "   Service installed"

# Start
echo ""
echo "6. Starting backend..."
sudo systemctl restart xtern-backend
sleep 2
if sudo systemctl is-active --quiet xtern-backend; then
    echo "   Backend is running"
    echo ""
    echo "=== Deployment complete ==="
    echo "  API:    http://$(curl -s -m 2 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo 'localhost'):8000"
    echo "  Docs:   http://localhost:8000/api/docs"
    echo "  Health: http://localhost:8000/health"
    echo ""
    echo "  Logs:   sudo journalctl -u xtern-backend -f"
else
    echo "   ERROR: Service failed to start. Check: sudo journalctl -u xtern-backend -n 50"
    exit 1
fi
