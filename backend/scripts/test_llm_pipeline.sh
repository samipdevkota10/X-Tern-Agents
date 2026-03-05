#!/bin/bash
# Test LLM pipeline and check used_llm flag

TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"manager_01","password":"password"}' | jq -r '.access_token')

DISRUPTION_ID=$(curl -s http://localhost:8000/api/disruptions \
  -H "Authorization: Bearer $TOKEN" | jq -r '.[0].id')

echo "Running pipeline for disruption: $DISRUPTION_ID"

PIPELINE_ID=$(curl -s -X POST http://localhost:8000/api/pipeline/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"disruption_id\":\"$DISRUPTION_ID\"}" | jq -r '.pipeline_run_id')

echo "Pipeline ID: $PIPELINE_ID"
echo "Waiting for completion..."

for i in {1..25}; do
  sleep 3
  STATUS=$(curl -s "http://localhost:8000/api/pipeline/$PIPELINE_ID/status" \
    -H "Authorization: Bearer $TOKEN")
  STATE=$(echo "$STATUS" | jq -r '.status // "?"')
  STEP=$(echo "$STATUS" | jq -r '.current_step // "?"')
  echo "[$i] $STEP - $STATE"
  if [[ "$STATE" == "done" || "$STATE" == "completed" || "$STATE" == "failed" ]]; then
    break
  fi
done

echo ""
echo "=== Check latest scenarios for used_llm flag ==="
curl -s "http://localhost:8000/api/scenarios?limit=5" \
  -H "Authorization: Bearer $TOKEN" | jq '.[0:5] | .[] | {order_id, action_type, used_llm, llm_rationale}'
