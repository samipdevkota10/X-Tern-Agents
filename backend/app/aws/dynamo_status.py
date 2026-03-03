"""
DynamoDB status writer for pipeline execution tracking.
Gracefully no-ops if AWS is not configured.
"""
import os
from datetime import datetime, timezone
from typing import Any, Optional


def write_status(
    pipeline_run_id: str,
    step_name: str,
    status: str,
    details: Optional[dict[str, Any]] = None,
) -> bool:
    """
    Write pipeline status update to DynamoDB.
    
    Args:
        pipeline_run_id: Pipeline run identifier
        step_name: Name of the current step
        status: Status string (started, completed, failed)
        details: Optional additional details
        
    Returns:
        True if write succeeded, False otherwise (including no-op)
    """
    use_aws = os.getenv("USE_AWS", "0") == "1"
    
    if not use_aws:
        # Local dev mode - no-op
        return False
    
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        table_name = os.getenv("DYNAMO_STATUS_TABLE", "pipeline_status")
        region = os.getenv("AWS_REGION", "us-east-1")
        
        dynamodb = boto3.resource("dynamodb", region_name=region)
        table = dynamodb.Table(table_name)
        
        item = {
            "pipeline_run_id": pipeline_run_id,
            "step_name": step_name,
            "status": status,
            "ts_iso": datetime.now(timezone.utc).isoformat(),
        }
        
        if details:
            item["details"] = details
        
        table.put_item(Item=item)
        return True
        
    except ImportError:
        # boto3 not installed - no-op
        return False
    except ClientError as e:
        # AWS error - log but don't crash
        print(f"DynamoDB write failed: {e}")
        return False
    except Exception as e:
        # Any other error - log but don't crash
        print(f"Unexpected error writing to DynamoDB: {e}")
        return False


def write_status_safe(
    pipeline_run_id: str,
    step_name: str,
    status: str,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """
    Safe wrapper for write_status that never raises exceptions.
    
    Args:
        pipeline_run_id: Pipeline run identifier
        step_name: Name of the current step
        status: Status string
        details: Optional additional details
    """
    try:
        write_status(pipeline_run_id, step_name, status, details)
    except Exception as e:
        # Silently ignore all errors
        print(f"DynamoDB status write failed (non-fatal): {e}")
