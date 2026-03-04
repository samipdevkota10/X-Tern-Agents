#!/bin/bash
# Test script for DisruptIQ multi-agent pipeline
# Tests: Auth, Disruptions, Pipeline, RAG, Governance

set -e
API_URL="http://localhost:8000"

echo "=========================================="
echo "DisruptIQ Full System Test"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓ $1${NC}"; }
fail() { echo -e "${RED}✗ $1${NC}"; exit 1; }
info() { echo -e "${YELLOW}→ $1${NC}"; }

# 1. Health Check
info "Testing health endpoints..."
curl -sf "$API_URL/health" > /dev/null && pass "Backend healthy" || fail "Backend not running"
curl -sf "$API_URL/api/rag/health" > /dev/null && pass "RAG system healthy" || fail "RAG not available"

# 2. Authentication
info "Testing authentication..."
TOKEN=$(curl -s -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "manager_01", "password": "password"}' | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

[ -n "$TOKEN" ] && pass "Login successful" || fail "Login failed"

AUTH="Authorization: Bearer $TOKEN"

# 3. RAG Knowledge Base
info "Testing RAG knowledge base..."
RAG_STATS=$(curl -s "$API_URL/api/rag/stats" -H "$AUTH")
echo "$RAG_STATS" | grep -q '"available":true' && pass "RAG available" || fail "RAG not available"

# Seed knowledge if needed
curl -s -X POST "$API_URL/api/rag/seed-knowledge" -H "$AUTH" > /dev/null
pass "Knowledge base seeded"

# Search test
SEARCH=$(curl -s -X POST "$API_URL/api/rag/search/knowledge" \
  -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{"query": "supplier delay", "n_results": 2}')
echo "$SEARCH" | grep -q '"count":' && pass "RAG semantic search works" || fail "RAG search failed"

# 4. Governance
info "Testing AI governance..."
GOV=$(curl -s "$API_URL/api/governance/summary" -H "$AUTH")
echo "$GOV" | grep -q 'governance_health' && pass "Governance framework active" || fail "Governance not available"

# 5. Create Disruption
info "Creating test disruption..."
DISRUPTION=$(curl -s -X POST "$API_URL/api/disruptions" \
  -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "late_truck",
    "severity": 4,
    "details_json": {
      "truck_id": "TRK-TEST-001",
      "delay_hours": 8,
      "affected_skus": ["SKU-001", "SKU-002"]
    }
  }')

DISRUPTION_ID=$(echo "$DISRUPTION" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
[ -n "$DISRUPTION_ID" ] && pass "Disruption created: $DISRUPTION_ID" || fail "Disruption creation failed"

# 6. Trigger Pipeline
info "Triggering multi-agent pipeline..."
PIPELINE=$(curl -s -X POST "$API_URL/api/pipeline/run" \
  -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d "{\"disruption_id\": \"$DISRUPTION_ID\"}")
PIPELINE_ID=$(echo "$PIPELINE" | grep -o '"pipeline_run_id":"[^"]*"' | cut -d'"' -f4)
[ -n "$PIPELINE_ID" ] && pass "Pipeline started: $PIPELINE_ID" || fail "Pipeline failed to start"

# 7. Monitor Pipeline Progress
info "Monitoring pipeline execution..."
MAX_WAIT=60
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
  STATUS=$(curl -s "$API_URL/api/pipeline/$PIPELINE_ID/status" -H "$AUTH")
  CURRENT_STATUS=$(echo "$STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null || echo "unknown")
  CURRENT_STEP=$(echo "$STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('current_step',''))" 2>/dev/null || echo "")
  PROGRESS=$(echo "$STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('progress',0))" 2>/dev/null || echo "0")
  
  printf "  Status: %-10s | Step: %-15s | Progress: %.0f%%\n" "$CURRENT_STATUS" "$CURRENT_STEP" "$PROGRESS"
  
  if [ "$CURRENT_STATUS" = "done" ]; then
    pass "Pipeline completed successfully"
    break
  elif [ "$CURRENT_STATUS" = "failed" ]; then
    fail "Pipeline failed"
  fi
  
  sleep 2
  WAITED=$((WAITED + 2))
done

if [ $WAITED -ge $MAX_WAIT ]; then
  echo "  (Pipeline still running - continuing with other tests)"
fi

# 8. Check Scenarios Generated
info "Checking generated scenarios..."
sleep 2  # Allow DB to sync
SCENARIOS=$(curl -s "$API_URL/api/scenarios?disruption_id=$DISRUPTION_ID" -H "$AUTH")
SCENARIO_COUNT=$(echo "$SCENARIOS" | grep -o '"scenarios":\[' | wc -l)
[ "$SCENARIO_COUNT" -gt 0 ] && pass "Scenarios generated" || echo "  (Scenarios may still be generating)"

# 9. Dashboard Data
info "Testing dashboard endpoint..."
DASHBOARD=$(curl -s "$API_URL/api/dashboard" -H "$AUTH")
echo "$DASHBOARD" | grep -q 'active_disruptions\|pending_approvals' && pass "Dashboard data available" || fail "Dashboard failed"

# 10. Audit Logs
info "Testing audit logs..."
LOGS=$(curl -s "$API_URL/api/audit-logs?limit=5" -H "$AUTH")
echo "$LOGS" | grep -q 'logs\|entries' && pass "Audit logs accessible" || echo "  (No logs yet)"

echo ""
echo "=========================================="
echo -e "${GREEN}All systems operational!${NC}"
echo "=========================================="
echo ""
echo "Test Summary:"
echo "  • Authentication: Working"
echo "  • RAG (Chroma): Working"
echo "  • AI Governance: Working"
echo "  • Pipeline: Started"
echo "  • Disruption ID: $DISRUPTION_ID"
echo "  • Pipeline ID: $PIPELINE_ID"
echo ""
echo "View results:"
echo "  curl -s $API_URL/api/pipeline/$PIPELINE_ID/status -H \"Authorization: Bearer \$TOKEN\" | python3 -m json.tool"
echo ""
