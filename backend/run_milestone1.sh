#!/bin/bash
# Helper script to run Milestone 1 seed and tests

BACKEND_DIR="/Users/tanaypatel/Desktop/xtern/X-Tern-Agents/backend"

echo "========================================="
echo "  Milestone 1: Database + MCP Tools"
echo "========================================="
echo ""

# Set PYTHONPATH
export PYTHONPATH=$BACKEND_DIR

# Check if we should reseed
if [ "$1" = "--reseed" ] || [ ! -f "$BACKEND_DIR/warehouse.db" ]; then
    echo "📦 Seeding database..."
    python "$BACKEND_DIR/scripts/seed_data.py"
    if [ $? -ne 0 ]; then
        echo "❌ Seed failed!"
        exit 1
    fi
    echo ""
fi

# Run tool tests
echo "🧪 Running MCP tool tests..."
python "$BACKEND_DIR/scripts/quick_tool_test.py"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Milestone 1 Complete!"
else
    echo ""
    echo "❌ Tests failed!"
    exit 1
fi
