#!/bin/bash
# Comprehensive platform test script

BASE_URL="http://localhost:8000/api"

echo "======================================================================"
echo "        COMPREHENSIVE PLATFORM TEST - ALL FEATURES"
echo "======================================================================"

# 1. Login
echo ""
echo "[1] LOGIN"
echo "----------------------------------------------------------------------"
TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"manager_01","password":"password"}' | jq -r '.access_token')
echo "✅ Logged in as manager_01"
echo "   Token: ${TOKEN:0:30}..."

# 2. User Info
echo ""
echo "[2] USER INFO"
echo "----------------------------------------------------------------------"
curl -s "$BASE_URL/auth/me" -H "Authorization: Bearer $TOKEN" | jq '{username, role}'

# 3. Dashboard
echo ""
echo "[3] DASHBOARD"
echo "----------------------------------------------------------------------"
curl -s "$BASE_URL/dashboard" -H "Authorization: Bearer $TOKEN" | jq

# 4. Disruptions
echo ""
echo "[4] DISRUPTIONS"
echo "----------------------------------------------------------------------"
DISRUPTIONS=$(curl -s "$BASE_URL/disruptions" -H "Authorization: Bearer $TOKEN")
echo "Total disruptions: $(echo $DISRUPTIONS | jq 'length')"
echo "First 3:"
echo $DISRUPTIONS | jq '.[0:3] | .[] | {id, type, severity}'

# 5. Select disruption for pipeline
echo ""
echo "[5] SELECT DISRUPTION FOR PIPELINE"
echo "----------------------------------------------------------------------"
DISRUPTION_ID=$(echo $DISRUPTIONS | jq -r '.[0].id')
echo "✅ Selected: $DISRUPTION_ID"

# 6. Check LLM routing is enabled
echo ""
echo "[6] LLM ROUTING STATUS"
echo "----------------------------------------------------------------------"
echo "USE_AWS: ${USE_AWS:-not set}"
echo "BEDROCK_MODEL_ID: ${BEDROCK_MODEL_ID:-not set}"

# 7. Run pipeline
echo ""
echo "[7] RUN PIPELINE (Creating new run)"
echo "----------------------------------------------------------------------"
RUN_RESPONSE=$(curl -s -X POST "$BASE_URL/pipeline/run" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"disruption_id\":\"$DISRUPTION_ID\"}")
PIPELINE_RUN_ID=$(echo $RUN_RESPONSE | jq -r '.pipeline_run_id')
echo "✅ Pipeline started: $PIPELINE_RUN_ID"

# 8. Poll for completion
echo ""
echo "[8] POLLING PIPELINE STATUS"
echo "----------------------------------------------------------------------"
for i in {1..15}; do
  sleep 3
  STATUS=$(curl -s "$BASE_URL/pipeline/$PIPELINE_RUN_ID/status" -H "Authorization: Bearer $TOKEN")
  CURRENT=$(echo $STATUS | jq -r '.current_step // "unknown"')
  STATE=$(echo $STATUS | jq -r '.status // "unknown"')
  echo "   Poll $i: $CURRENT - $STATE"
  
  if [[ "$STATE" == "completed" || "$STATE" == "failed" || "$STATE" == "needs_review" ]]; then
    break
  fi
done

# 9. Final status
echo ""
echo "[9] FINAL PIPELINE STATUS"
echo "----------------------------------------------------------------------"
FINAL=$(curl -s "$BASE_URL/pipeline/$PIPELINE_RUN_ID/status" -H "Authorization: Bearer $TOKEN")
echo $FINAL | jq

# 10. Scenarios
echo ""
echo "[10] SCENARIOS"
echo "----------------------------------------------------------------------"
SCENARIOS=$(curl -s "$BASE_URL/scenarios" -H "Authorization: Bearer $TOKEN")
echo "Total scenarios: $(echo $SCENARIOS | jq 'length')"

# 11. Audit logs
echo ""
echo "[11] AUDIT LOGS"
echo "----------------------------------------------------------------------"
AUDIT=$(curl -s "$BASE_URL/audit/logs" -H "Authorization: Bearer $TOKEN")
if [[ $(echo $AUDIT | jq 'type') == '"array"' ]]; then
  echo "Total audit entries: $(echo $AUDIT | jq 'length')"
else
  echo "Audit response: $(echo $AUDIT | jq -c)"
fi

echo ""
echo "======================================================================"
echo "                    ALL TESTS COMPLETED"
echo "======================================================================"

# UI Testing Guide
cat << 'GUIDE'

====================================================================== 
                    HOW TO TEST ON THE UI
======================================================================

1. LOGIN (http://localhost:3000/login):
   - Username: manager_01
   - Password: password

2. DASHBOARD (http://localhost:3000/dashboard):
   - See active disruptions count
   - See pending scenarios count
   - View recent activity

3. DISRUPTIONS (http://localhost:3000/disruptions):
   - Click "+ New Disruption" to create
   - Select type: truck_delay, machine_down, inventory_shortage, etc.
   - Set severity: 1 (low) to 5 (critical)
   - Add details JSON (optional)

4. RUN PLANNER:
   - Click any disruption row to open detail sheet
   - Click "Run Planner" button
   - Watch the real-time stepper showing agent progress
   - LLM router decides next steps dynamically

5. SCENARIOS (http://localhost:3000/scenarios):
   - View generated scenarios by order
   - See cost, SLA risk, labor impact scores
   - Compare different scenarios

6. APPROVALS (http://localhost:3000/approvals):
   - Manager-only page
   - Approve or reject pending scenarios
   - Bulk approve multiple scenarios

7. AUDIT LOG (http://localhost:3000/audit):
   - View complete decision history
   - See all agent decisions with timestamps
   - Export to JSON

8. NEW: ROUTING TRACE:
   - In pipeline status, check routing_trace field
   - Shows LLM routing decisions with confidence
   - Shows any guardrail overrides

GUIDE
