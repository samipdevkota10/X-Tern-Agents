#!/usr/bin/env python3
"""
Verify AWS integration: DynamoDB pipeline status and S3 pipeline run artifacts.

Usage:
  USE_AWS=1 AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... \\
  S3_BUCKET_NAME=xtern-agents-bucket DYNAMO_STATUS_TABLE=pipeline_status \\
  PYTHONPATH=$(pwd) python scripts/verify_aws_integration.py

Checks:
  1. DynamoDB: Can write/read pipeline status items
  2. S3: Can write/read pipeline run result JSON
  3. Lists recent pipeline_runs/*.json keys in S3 (if any)
  4. Scans recent DynamoDB pipeline_status items (if any)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _aws_kwargs(region: str) -> dict:
    """
    Build boto3 kwargs from environment variables.

    Prefer explicit env credentials when present so a stray AWS_PROFILE doesn't
    unexpectedly override local dev runs.
    """
    kwargs: dict = {"region_name": region}
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    session_token = os.getenv("AWS_SESSION_TOKEN")
    if access_key:
        kwargs["aws_access_key_id"] = access_key
        kwargs["aws_secret_access_key"] = secret_key or ""
        if session_token:
            kwargs["aws_session_token"] = session_token
    return kwargs


def _print_dynamo_table_help(*, table_name: str, region: str) -> None:
    print("  [HINT] DynamoDB table not found.")
    print(f"         Table:  {table_name}")
    print(f"         Region: {region}")
    print("         Fix by creating the table (or set DYNAMO_STATUS_TABLE/AWS_REGION correctly).")
    print("")
    print("         Example create-table command:")
    print(
        f"           aws dynamodb create-table --region {region} "
        f"--table-name {table_name} "
        "--attribute-definitions AttributeName=pipeline_run_id,AttributeType=S AttributeName=step_name,AttributeType=S "
        "--key-schema AttributeName=pipeline_run_id,KeyType=HASH AttributeName=step_name,KeyType=RANGE "
        "--billing-mode PAY_PER_REQUEST"
    )


def check_dynamodb() -> bool:
    """Verify DynamoDB pipeline status writes work."""
    use_aws = os.getenv("USE_AWS", "0") == "1"
    if not use_aws:
        print("  [SKIP] USE_AWS=0 - DynamoDB check skipped")
        return True

    try:
        import boto3
        from botocore.exceptions import ClientError

        table_name = os.getenv("DYNAMO_STATUS_TABLE", "pipeline_status")
        region = os.getenv("AWS_REGION", "us-east-1")

        kwargs = _aws_kwargs(region)
        # Verify the table exists up front to produce a clear error.
        try:
            boto3.client("dynamodb", **kwargs).describe_table(TableName=table_name)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in {"ResourceNotFoundException", "RequestedResourceNotFoundException"}:
                _print_dynamo_table_help(table_name=table_name, region=region)
                return False
            raise

        dynamodb = boto3.resource("dynamodb", **kwargs)
        table = dynamodb.Table(table_name)

        # Write test item
        test_id = "verify-test-" + str(__import__("uuid").uuid4())[:8]
        table.put_item(
            Item={
                "pipeline_run_id": test_id,
                "step_name": "verify_test",
                "status": "test",
                "ts_iso": "2026-01-01T00:00:00Z",
            }
        )
        # Read it back
        got = table.get_item(Key={"pipeline_run_id": test_id, "step_name": "verify_test"})
        if got.get("Item"):
            print(f"  [OK] DynamoDB: wrote and read test item to {table_name}")
            # Delete test item
            table.delete_item(Key={"pipeline_run_id": test_id, "step_name": "verify_test"})
            return True
        print("  [FAIL] DynamoDB: could not read back test item")
        return False
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in {"ResourceNotFoundException", "RequestedResourceNotFoundException"}:
            _print_dynamo_table_help(
                table_name=os.getenv("DYNAMO_STATUS_TABLE", "pipeline_status"),
                region=os.getenv("AWS_REGION", "us-east-1"),
            )
        else:
            print(f"  [FAIL] DynamoDB: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] DynamoDB: {e}")
        return False


def check_s3() -> bool:
    """Verify S3 pipeline run artifact writes work."""
    use_aws = os.getenv("USE_AWS", "0") == "1"
    bucket = os.getenv("S3_BUCKET_NAME", "xtern-agents-bucket")
    if not use_aws:
        print("  [SKIP] USE_AWS=0 - S3 check skipped")
        return True

    try:
        import boto3
        from botocore.exceptions import ClientError

        region = os.getenv("AWS_REGION", "us-east-1")
        kwargs = _aws_kwargs(region)

        s3 = boto3.client("s3", **kwargs)

        # Write test file
        test_key = "pipeline_runs/verify-test.json"
        body = json.dumps({"test": True, "purpose": "integration_verification"})
        s3.put_object(Bucket=bucket, Key=test_key, Body=body.encode(), ContentType="application/json")

        # Read it back
        resp = s3.get_object(Bucket=bucket, Key=test_key)
        content = resp["Body"].read().decode()
        data = json.loads(content)
        if data.get("test"):
            print(f"  [OK] S3: wrote and read test object s3://{bucket}/{test_key}")
            s3.delete_object(Bucket=bucket, Key=test_key)
            return True
        print("  [FAIL] S3: could not read back test object")
        return False
    except ClientError as e:
        print(f"  [FAIL] S3: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] S3: {e}")
        return False


def list_recent_artifacts() -> None:
    """List recent pipeline run artifacts in S3 and DynamoDB (info only)."""
    use_aws = os.getenv("USE_AWS", "0") == "1"
    if not use_aws:
        return

    bucket = os.getenv("S3_BUCKET_NAME", "xtern-agents-bucket")
    table_name = os.getenv("DYNAMO_STATUS_TABLE", "pipeline_status")
    region = os.getenv("AWS_REGION", "us-east-1")

    try:
        import boto3
        from botocore.exceptions import ClientError

        kwargs = _aws_kwargs(region)

        # S3: list pipeline_runs/
        s3 = boto3.client("s3", **kwargs)
        try:
            resp = s3.list_objects_v2(Bucket=bucket, Prefix="pipeline_runs/", MaxKeys=5)
            items = resp.get("Contents", [])
            if items:
                print(f"\n  Recent S3 pipeline run artifacts ({len(items)} shown):")
                for obj in items[:5]:
                    print(f"    - s3://{bucket}/{obj['Key']} ({obj.get('Size', 0)} bytes)")
            else:
                print("\n  No pipeline run artifacts found in S3 (run a pipeline with USE_AWS=1 first)")
        except ClientError as e:
            print(f"\n  Could not list S3: {e}")

        # DynamoDB: scan recent (optional - table may not have GSI for time)
        dynamodb = boto3.resource("dynamodb", **kwargs)
        table = dynamodb.Table(table_name)
        try:
            resp = table.scan(Limit=5)
            items = resp.get("Items", [])
            if items:
                print(f"\n  Recent DynamoDB pipeline status items ({len(items)} shown):")
                for it in items[:5]:
                    rid = it.get("pipeline_run_id", "?")
                    step = it.get("step_name", "?")
                    st = it.get("status", "?")
                    print(f"    - {rid} | {step} | {st}")
            else:
                print("\n  No DynamoDB status items found (run a pipeline with USE_AWS=1 first)")
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in {"ResourceNotFoundException", "RequestedResourceNotFoundException"}:
                print(f"\n  DynamoDB table not found: {table_name} (region {region})")
            else:
                print(f"\n  Could not scan DynamoDB: {e}")

    except Exception as e:
        print(f"\n  Could not list artifacts: {e}")


def main() -> int:
    print("=" * 60)
    print("AWS Integration Verification")
    print("=" * 60)
    print(f"\nUSE_AWS={os.getenv('USE_AWS', '0')}")
    print(f"S3_BUCKET_NAME={os.getenv('S3_BUCKET_NAME', 'xtern-agents-bucket')}")
    print(f"DYNAMO_STATUS_TABLE={os.getenv('DYNAMO_STATUS_TABLE', 'pipeline_status')}")

    print("\n[1] DynamoDB pipeline status")
    ok_dynamo = check_dynamodb()

    print("\n[2] S3 pipeline run artifacts")
    ok_s3 = check_s3()

    list_recent_artifacts()

    print("\n" + "=" * 60)
    if ok_dynamo and ok_s3:
        print("All checks passed.")
        return 0
    print("Some checks failed. Set USE_AWS=1 and configure AWS credentials to enable.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
