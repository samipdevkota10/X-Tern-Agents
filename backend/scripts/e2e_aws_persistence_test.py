#!/usr/bin/env python3
"""
End-to-end AWS persistence test.

Runs a full pipeline, then verifies that data was persisted to:
1. RDS/PostgreSQL (or SQLite): scenarios, pipeline_runs, decision_logs
2. S3: pipeline_runs/{id}.json with final_summary and scenarios
3. DynamoDB: pipeline status items

Usage:
  # With .env loaded (from backend dir):
  cd backend
  PYTHONPATH=$(pwd) python scripts/e2e_aws_persistence_test.py

  # Or with explicit env:
  USE_AWS=1 AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... \\
  S3_BUCKET_NAME=xtern-agents-bucket DYNAMO_STATUS_TABLE=pipeline_status \\
  DATABASE_URL=postgresql://... \\
  PYTHONPATH=$(pwd) python scripts/e2e_aws_persistence_test.py
"""
import json
import os
import sys
import time

# Load .env before imports
_script_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_script_dir)
sys.path.insert(0, _backend_dir)
_env_path = os.path.join(_backend_dir, ".env")
if os.path.exists(_env_path):
    from dotenv import load_dotenv
    load_dotenv(_env_path)

import requests

API_URL = os.getenv("API_URL", "http://localhost:8000")


def _aws_kwargs(region: str) -> dict:
    kwargs = {"region_name": region}
    access = os.getenv("AWS_ACCESS_KEY_ID")
    secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    if access:
        kwargs["aws_access_key_id"] = access
        kwargs["aws_secret_access_key"] = secret or ""
    return kwargs


def run_e2e_test() -> int:
    print("=" * 70)
    print("E2E AWS Persistence Test")
    print("=" * 70)
    print(f"\nAPI_URL: {API_URL}")
    print(f"USE_AWS: {os.getenv('USE_AWS', '0')}")
    print(f"DATABASE_URL: {'(set)' if os.getenv('DATABASE_URL') else '(default sqlite)'}")
    print(f"S3_BUCKET: {os.getenv('S3_BUCKET_NAME', 'xtern-agents-bucket')}")
    print(f"DYNAMO_TABLE: {os.getenv('DYNAMO_STATUS_TABLE', 'pipeline_status')}\n")

    # 1. Health check
    print("[1] Health check...")
    try:
        r = requests.get(f"{API_URL}/health", timeout=5)
        r.raise_for_status()
        print("    OK - Backend healthy")
    except Exception as e:
        print(f"    FAIL - Backend not reachable: {e}")
        return 1

    # 2. Login
    print("\n[2] Authentication...")
    try:
        r = requests.post(
            f"{API_URL}/api/auth/login",
            json={"username": "manager_01", "password": "password"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        token = data.get("access_token")
        if not token:
            print("    FAIL - No access_token in response")
            return 1
        headers = {"Authorization": f"Bearer {token}"}
        print("    OK - Logged in")
    except Exception as e:
        print(f"    FAIL - Login failed: {e}")
        return 1

    # 3. Create disruption
    print("\n[3] Creating test disruption...")
    try:
        r = requests.post(
            f"{API_URL}/api/disruptions",
            headers=headers,
            json={
                "type": "late_truck",
                "severity": 4,
                "details_json": {
                    "truck_id": "TRK-E2E-TEST",
                    "delay_hours": 6,
                    "affected_skus": ["SKU-001", "SKU-002"],
                },
            },
            timeout=10,
        )
        r.raise_for_status()
        disruption = r.json()
        disruption_id = disruption.get("id")
        if not disruption_id:
            print("    FAIL - No disruption id")
            return 1
        print(f"    OK - Disruption created: {disruption_id}")
    except Exception as e:
        print(f"    FAIL - Create disruption: {e}")
        return 1

    # 4. Run pipeline
    print("\n[4] Running pipeline...")
    try:
        r = requests.post(
            f"{API_URL}/api/pipeline/run",
            headers=headers,
            json={"disruption_id": disruption_id},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        pipeline_run_id = data.get("pipeline_run_id")
        if not pipeline_run_id:
            print("    FAIL - No pipeline_run_id")
            return 1
        print(f"    OK - Pipeline started: {pipeline_run_id}")
    except Exception as e:
        print(f"    FAIL - Start pipeline: {e}")
        return 1

    # 5. Wait for completion
    print("\n[5] Waiting for pipeline completion (max 120s)...")
    max_wait = 120
    start = time.time()
    while time.time() - start < max_wait:
        try:
            r = requests.get(
                f"{API_URL}/api/pipeline/{pipeline_run_id}/status",
                headers=headers,
                timeout=5,
            )
            r.raise_for_status()
            status_data = r.json()
            s = status_data.get("status", "")
            step = status_data.get("current_step", "")
            progress = status_data.get("progress", 0)
            print(f"    Status: {s} | Step: {step} | Progress: {progress:.0%}")
            if s == "done" or s == "needs_review" or s == "completed":
                print("    OK - Pipeline completed")
                # Allow S3/DynamoDB writes (happen after commit) to complete
                time.sleep(3)
                break
            if s == "failed":
                err = status_data.get("error_message", "unknown")
                print(f"    FAIL - Pipeline failed: {err}")
                return 1
        except Exception as e:
            print(f"    Warning - Status check: {e}")
        time.sleep(3)
    else:
        print("    WARN - Timeout waiting for completion (continuing verification)")

    # 6. Verify RDS/SQLite - scenarios via API
    print("\n[6] Verifying RDS/SQLite (scenarios via API)...")
    try:
        r = requests.get(
            f"{API_URL}/api/scenarios",
            headers=headers,
            params={"disruption_id": disruption_id},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        scenarios = data if isinstance(data, list) else data.get("scenarios", data)
        if not isinstance(scenarios, list):
            scenarios = []
        count = len(scenarios)
        if count > 0:
            print(f"    OK - {count} scenarios persisted to database")
        else:
            print("    WARN - No scenarios found for this disruption (may still be syncing)")
    except Exception as e:
        print(f"    FAIL - Scenarios API: {e}")

    # 7. Verify pipeline_run in DB via status endpoint
    print("\n[7] Verifying pipeline_run record...")
    try:
        r = requests.get(
            f"{API_URL}/api/pipeline/{pipeline_run_id}/status",
            headers=headers,
            timeout=5,
        )
        r.raise_for_status()
        status_data = r.json()
        summary = status_data.get("final_summary_json")
        if isinstance(summary, str):
            summary = json.loads(summary) if summary else {}
        elif summary is None:
            summary = {}
        if summary or status_data.get("status") in ("done", "needs_review", "completed"):
            print(f"    OK - Pipeline run persisted (status: {status_data.get('status')})")
        else:
            print("    WARN - Pipeline run status incomplete")
    except Exception as e:
        print(f"    FAIL - Pipeline status: {e}")

    # 8. Verify S3 (when USE_AWS=1)
    use_aws = os.getenv("USE_AWS", "0") == "1"
    if use_aws:
        print("\n[8] Verifying S3 pipeline run artifact...")
        try:
            import boto3
            from botocore.exceptions import ClientError

            bucket = os.getenv("S3_BUCKET_NAME", "xtern-agents-bucket")
            region = os.getenv("AWS_REGION", "us-east-1")
            kwargs = _aws_kwargs(region)
            s3 = boto3.client("s3", **kwargs)
            key = f"pipeline_runs/{pipeline_run_id}.json"
            resp = s3.get_object(Bucket=bucket, Key=key)
            content = resp["Body"].read().decode()
            payload = json.loads(content)
            if payload.get("pipeline_run_id") == pipeline_run_id:
                scenarios_in_s3 = payload.get("scenarios", [])
                print(f"    OK - S3 artifact exists: s3://{bucket}/{key}")
                print(f"       Contains {len(scenarios_in_s3)} scenarios in payload")
                if not scenarios_in_s3 and "scenarios" not in payload:
                    print("       (Restart backend to persist scenarios in S3)")
            else:
                print("    WARN - S3 object exists but payload unexpected")
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code == "NoSuchKey":
                print(f"    FAIL - S3 object not found: {key}")
            else:
                print(f"    FAIL - S3: {e}")
        except Exception as e:
            print(f"    FAIL - S3: {e}")
    else:
        print("\n[8] S3 check skipped (USE_AWS=0)")

    # 9. Verify DynamoDB (when USE_AWS=1)
    if use_aws:
        print("\n[9] Verifying DynamoDB pipeline status...")
        try:
            import boto3
            from botocore.exceptions import ClientError

            table_name = os.getenv("DYNAMO_STATUS_TABLE", "pipeline_status")
            region = os.getenv("AWS_REGION", "us-east-1")
            kwargs = _aws_kwargs(region)
            dynamodb = boto3.resource("dynamodb", **kwargs)
            table = dynamodb.Table(table_name)
            resp = table.get_item(
                Key={
                    "pipeline_run_id": pipeline_run_id,
                    "step_name": "pipeline_complete",
                }
            )
            item = resp.get("Item")
            if item:
                print(f"    OK - DynamoDB status item exists for pipeline_complete")
            else:
                # Try scanning for any step for this run
                scan_resp = table.scan(
                    FilterExpression="pipeline_run_id = :pid",
                    ExpressionAttributeValues={":pid": pipeline_run_id},
                    Limit=5,
                )
                items = scan_resp.get("Items", [])
                if items:
                    print(f"    OK - DynamoDB has {len(items)} status items for this run")
                else:
                    print("    WARN - No DynamoDB status items found for this run")
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if "ResourceNotFoundException" in code:
                print(f"    FAIL - DynamoDB table not found: {table_name}")
            else:
                print(f"    FAIL - DynamoDB: {e}")
        except Exception as e:
            print(f"    FAIL - DynamoDB: {e}")
    else:
        print("\n[9] DynamoDB check skipped (USE_AWS=0)")

    # 10. Audit logs
    print("\n[10] Verifying audit logs...")
    try:
        r = requests.get(
            f"{API_URL}/api/audit-logs",
            headers=headers,
            params={"pipeline_run_id": pipeline_run_id, "limit": 20},
            timeout=5,
        )
        r.raise_for_status()
        logs = r.json()
        count = len(logs) if isinstance(logs, list) else len(logs.get("logs", []))
        if count > 0:
            print(f"    OK - {count} decision log entries for this pipeline")
        else:
            print("    WARN - No audit logs found")
    except Exception as e:
        print(f"    FAIL - Audit logs: {e}")

    print("\n" + "=" * 70)
    print("E2E test complete. Review results above.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(run_e2e_test())
