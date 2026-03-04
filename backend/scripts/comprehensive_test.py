#!/usr/bin/env python3
"""Comprehensive test script for all platform features including LLM routing."""
import requests
import json
import time

BASE_URL = 'http://localhost:8000/api'

def main():
    print('=' * 70)
    print('COMPREHENSIVE TEST OF LLM-DRIVEN ROUTING + ALL FEATURES')
    print('=' * 70)

    # 1. Login
    print('\n[1] LOGIN')
    print('-' * 50)
    resp = requests.post(f'{BASE_URL}/auth/login', json={
        'username': 'manager_01',
        'password': 'password'
    })
    token = resp.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    print(f'✅ Logged in as manager_01')

    # 2. User info
    print('\n[2] USER INFO')
    resp = requests.get(f'{BASE_URL}/auth/me', headers=headers)
    user = resp.json()
    print(f'✅ User: {user["username"]} ({user["role"]})')

    # 3. Dashboard
    print('\n[3] DASHBOARD')
    resp = requests.get(f'{BASE_URL}/dashboard', headers=headers)
    dash = resp.json()
    print(f'✅ Active Disruptions: {dash.get("active_disruptions", 0)}')
    print(f'   Pending Scenarios: {dash.get("pending_scenarios", 0)}')

    # 4. List disruptions
    print('\n[4] DISRUPTIONS')
    resp = requests.get(f'{BASE_URL}/disruptions', headers=headers)
    disruptions = resp.json()
    print(f'✅ Found {len(disruptions)} disruptions')

    # 5. Use existing disruption for pipeline test
    print('\n[5] SELECT DISRUPTION FOR PIPELINE')
    if disruptions:
        disruption_id = disruptions[0]['id']
        print(f'✅ Using disruption {disruption_id}')
    else:
        print('❌ No disruptions available')
        return

    # 6. Run pipeline with LLM routing
    print('\n[6] RUN PIPELINE (LLM ROUTING)')
    print('-' * 50)
    resp = requests.post(f'{BASE_URL}/pipeline/run', json={'disruption_id': disruption_id}, headers=headers)
    run_resp = resp.json()
    pipeline_run_id = run_resp.get('pipeline_run_id')
    print(f'✅ Pipeline started: {pipeline_run_id}')

    # 7. Poll for completion
    print('\n[7] POLLING STATUS...')
    for i in range(30):
        time.sleep(2)
        resp = requests.get(f'{BASE_URL}/pipeline/status/{pipeline_run_id}', headers=headers)
        status = resp.json()
        current = status.get("current_step", "unknown")
        state = status.get("status", "unknown")
        print(f'   Poll {i+1}: {current} - {state}')
        if state in ['completed', 'failed', 'needs_review']:
            break

    # 8. Get final pipeline result
    print('\n[8] PIPELINE RESULT')
    print('-' * 50)
    resp = requests.get(f'{BASE_URL}/pipeline/status/{pipeline_run_id}', headers=headers)
    final = resp.json()
    print(f'Status: {final.get("status")}')
    
    routing_trace = final.get('routing_trace', [])
    if routing_trace:
        print('✅ ROUTING TRACE (LLM decisions):')
        for trace in routing_trace:
            step = trace.get("step", "?")
            decision = trace.get("decision", "?")
            conf = trace.get("confidence", "N/A")
            print(f'   - Step {step}: {decision} (conf: {conf})')
    else:
        print('⚠️  No routing trace available')

    # 9. List scenarios
    print('\n[9] SCENARIOS')
    resp = requests.get(f'{BASE_URL}/scenarios', headers=headers)
    scenarios = resp.json()
    print(f'✅ Total scenarios: {len(scenarios)}')
    if scenarios:
        print('   Recent scenarios:')
        for s in scenarios[:3]:
            print(f'   - {s.get("id", "?")}: {s.get("name", "unnamed")}')

    # 10. Audit logs
    print('\n[10] AUDIT LOGS')
    resp = requests.get(f'{BASE_URL}/audit/logs', headers=headers)
    if resp.status_code == 200:
        logs = resp.json()
        print(f'✅ Found {len(logs)} audit log entries')
    else:
        print(f'⚠️  Audit logs: {resp.status_code}')

    print('\n' + '=' * 70)
    print('ALL TESTS COMPLETED')
    print('=' * 70)
    
    # UI Testing Guide
    print('\n' + '=' * 70)
    print('HOW TO TEST ON THE UI')
    print('=' * 70)
    print('''
1. LOGIN:
   - Go to http://localhost:3000/login
   - Username: manager_01
   - Password: password

2. DASHBOARD (http://localhost:3000/dashboard):
   - See KPIs: active disruptions, pending scenarios
   - Quick stats for warehouse operations

3. DISRUPTIONS (http://localhost:3000/disruptions):
   - Click "+ New Disruption" to create
   - Select type: truck_delay, inventory_shortage, etc.
   - Set severity: low, medium, high
   - Add details JSON (optional)

4. RUN PLANNER:
   - Click any disruption row
   - Click "Run Planner" in the detail sheet
   - Watch the real-time stepper show each agent step
   - See the LLM routing decisions in progress

5. SCENARIOS (http://localhost:3000/scenarios):
   - View generated scenarios
   - See cost, SLA risk, labor impact scores
   - Click to see full scenario details

6. APPROVALS (Manager only):
   - Go to Approvals page
   - Approve or reject scenarios
   - Use bulk approve for multiple

7. AUDIT LOG (http://localhost:3000/audit):
   - View complete decision history
   - See all agent decisions with timestamps
   - Filter by agent or pipeline run

8. ROUTING TRACE (New!):
   - In the pipeline status response
   - Shows each LLM routing decision
   - Includes confidence scores and reasoning
''')

if __name__ == '__main__':
    main()
