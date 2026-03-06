## AWS Setup Guide

This document explains **everything you need to configure in AWS** to run the X‑Tern Agents backend with optional cloud services used in **Milestone 2** and beyond.

Local development works **without AWS** (`USE_AWS=0`), but if you want DynamoDB status tracking, Bedrock explanations, or an AWS Postgres database, follow the steps below.

---

## 1. High‑Level Checklist

- **AWS account** with access to your chosen region (default: `us-east-1`).
- **IAM user or role** with permissions for:
  - `bedrock:InvokeModel` (for the selected Bedrock model, optional).
  - `dynamodb:PutItem` on the status table (optional).
  - Network/database access to your **RDS Postgres** instance (optional).
- **DynamoDB table** for pipeline status updates (optional).
- **Bedrock model** enabled in your region (optional).
- **(Optional) RDS Postgres instance** for production‑style database.
- Environment variables configured for the backend (see section 5).

---

## 2. IAM & Credentials

You can use **either** an IAM user (with access keys) or an IAM role (EC2, ECS, etc.).

- **Minimum permissions for this project:**
  - DynamoDB:
    - `dynamodb:PutItem` on the status table (see section 3).
  - S3 (if you enable pipeline result storage):
    - `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject` on the pipeline results bucket (see section 3b).
  - Bedrock (if you enable LLM explanations):
    - `bedrock:InvokeModel` for the chosen model in the chosen region.
  - RDS:
    - Standard Postgres connectivity; typically managed via security groups rather than IAM.

Configure credentials in one of the standard AWS ways:

- Environment variables (for local dev):
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_SESSION_TOKEN` (if using temporary credentials)
  - `AWS_REGION` (or `AWS_DEFAULT_REGION`)
- Or use an IAM role attached to the compute where the backend runs.

> The code uses the standard AWS SDK and Bedrock client libraries, so **no custom auth mechanism** is required.

---

## 3. DynamoDB Status Table (Optional)

File `backend/app/aws/dynamo_status.py` writes pipeline execution status to DynamoDB when `USE_AWS=1`.

- **Table name**: controlled by `DYNAMO_STATUS_TABLE` (default: `pipeline_status`).
- **Region**: controlled by `AWS_REGION` (default: `us-east-1`).
- **Items written** include:
  - `pipeline_run_id` (string)
  - `step_name` (string)
  - `status` (string: `"started" | "completed" | "failed"`)
  - `ts_iso` (ISO‑8601 timestamp)
  - `details` (optional map/json)

### Recommended table schema

When creating the DynamoDB table:

- **Partition key (HASH)**: `pipeline_run_id` (String)
- **Sort key (RANGE)**: `step_name` (String)

This lets you query all steps for a given pipeline run efficiently.

### Required permissions

The backend needs permission to **put items** into this table:

```json
{
  "Effect": "Allow",
  "Action": ["dynamodb:PutItem"],
  "Resource": "arn:aws:dynamodb:<region>:<account-id>:table/<your-table-name>"
}
```

If you use additional DynamoDB APIs (e.g., reading status), you can expand this policy.

---

## 3b. S3 Bucket for Pipeline Run Artifacts (Optional)

When `USE_AWS=1`, the pipeline runner writes each run's final summary to S3 for audit and replay.

- **Bucket name**: controlled by `S3_BUCKET_NAME` (default: `xtern-agents-bucket`).
- **Key pattern**: `pipeline_runs/{pipeline_run_id}.json`
- **Content**: JSON with `pipeline_run_id`, `disruption_id`, `status`, `ts_iso`, and `final_summary`.

Create an S3 bucket in your region and ensure your IAM principal has:
- `s3:PutObject`
- `s3:GetObject`
- `s3:ListBucket` (for verification scripts)

---

## 4. Bedrock LLM (Optional)

File `backend/app/agents/bedrock_explain.py` adds **human‑friendly explanations** using AWS Bedrock when enabled.

### Bedrock configuration

1. **Enable Bedrock** for your AWS account in the target region (e.g., `us-east-1`).
2. **Request access** to the model you want to use.
   - The example config uses:
     - `BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0`
3. Ensure your IAM principal has:
   - `bedrock:InvokeModel` permission for that model.

### How the code uses Bedrock

- Bedrock is only used when:
  - `USE_AWS=1` **and**
  - `BEDROCK_MODEL_ID` is non‑empty.
- Otherwise, the system falls back to a **deterministic explanation** and continues normally.

---

## 5. Database on AWS (Optional RDS Postgres)

By default, the system uses **SQLite**:

- `DATABASE_URL=sqlite:///./warehouse.db`

For an AWS‑hosted database, you can use **Amazon RDS for PostgreSQL**:

1. Create an RDS Postgres instance (version compatible with SQLAlchemy/Postgres).
2. Create a database (e.g., `warehouse`).
3. Allow your backend to connect:
   - Update the RDS **security group** to allow inbound traffic from your backend host/VPC.
4. Set `DATABASE_URL` accordingly:

```bash
export DATABASE_URL=postgresql://<user>:<password>@<rds-endpoint>:5432/warehouse
```

Schema creation and migrations are handled by the existing backend code (see milestone docs).

---

## 6. Environment Variables (Summary)

These are the key env vars related to AWS and databases (from `MILESTONE_2_COMPLETE.md` and quick starts):

```bash
# Database (required)
export DATABASE_URL=sqlite:///./warehouse.db
# Or for AWS RDS Postgres:
# export DATABASE_URL=postgresql://user:pass@rds-host:5432/warehouse

# AWS Integration (optional)
export USE_AWS=0              # 0=local dev (no AWS calls), 1=AWS enabled
export AWS_REGION=us-east-1   # Must match your AWS region
export DYNAMO_STATUS_TABLE=pipeline_status
export S3_BUCKET_NAME=xtern-agents-bucket   # Pipeline run artifacts when USE_AWS=1

# Bedrock LLM (optional)
export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
```

> If `USE_AWS=0`, AWS‑specific features gracefully **no‑op** and the system still runs end‑to‑end locally.

---

## 7. Putting It All Together

Once AWS is configured, a typical **AWS‑enabled** run from `backend/` looks like:

```bash
export DATABASE_URL=postgresql://user:pass@rds-host:5432/warehouse
export USE_AWS=1
export AWS_REGION=us-east-1
export DYNAMO_STATUS_TABLE=pipeline_status
export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

PYTHONPATH=$(pwd) python scripts/run_pipeline_once.py
```

You should then see:

- DynamoDB items created in the status table for each pipeline step.
- S3 objects at `s3://{bucket}/pipeline_runs/{pipeline_run_id}.json` for each completed or failed run.
- Bedrock‑generated explanations in the pipeline summary (if Bedrock is enabled and reachable).
- All existing local behavior preserved when you switch `USE_AWS` back to `0`.

To verify AWS integration, run:
```bash
USE_AWS=1 AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... \\
S3_BUCKET_NAME=xtern-agents-bucket PYTHONPATH=$(pwd) python scripts/verify_aws_integration.py
```

