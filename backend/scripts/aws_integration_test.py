"""
Integration test for AWS pipelines: S3, Bedrock, RDS, ChromaDB
"""
import os
import boto3
import json
import psycopg2
from chromadb import Client as ChromaClient
from chromadb.config import Settings as ChromaSettings

# ENV VARS
S3_BUCKET = os.environ.get("S3_BUCKET_NAME", "xtern-agents-bucket")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET = os.environ.get("AWS_SECRET_ACCESS_KEY")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
RDS_URL = os.environ.get("DATABASE_URL")
CHROMA_PATH = os.path.abspath("../chroma_data")

print("=== AWS Integration Test ===\n")

# S3 TEST
print("[S3] Uploading test file...")
s3 = boto3.client("s3", region_name=AWS_REGION, aws_access_key_id=AWS_KEY, aws_secret_access_key=AWS_SECRET)
try:
    s3.put_object(Bucket=S3_BUCKET, Key="demo/test.txt", Body=b"Hello AWS S3! Demo file.")
    print("  ✓ Uploaded test.txt")
    resp = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix="demo/")
    print(f"  ✓ Objects in demo/: {[obj['Key'] for obj in resp.get('Contents', [])]}")
    file_obj = s3.get_object(Bucket=S3_BUCKET, Key="demo/test.txt")
    print(f"  ✓ Downloaded: {file_obj['Body'].read().decode()}")
except Exception as e:
    print(f"  ✗ S3 error: {e}")

# BEDROCK TEST
print("\n[Bedrock] Running model inference...")
bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION, aws_access_key_id=AWS_KEY, aws_secret_access_key=AWS_SECRET)
try:
    # Use Messages API for Claude Sonnet 4.5 with anthropic_version
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [
            {"role": "user", "content": "Say hello for the demo."}
        ],
        "max_tokens": 50,
        "temperature": 0.7
    })
    response = bedrock.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=body
    )
    print("  ✓ Bedrock response:", response["body"].read().decode())
except Exception as e:
    print(f"  ✗ Bedrock error: {e}")

# RDS TEST
print("\n[RDS] Connecting and checking demo table...")
import re
from dotenv import load_dotenv
load_dotenv()
try:
    # Parse RDS_URL for password
    match = re.match(r"postgresql://([^:]+):([^@]+)@([^:/]+):(\d+)/(\w+)", os.environ.get("DATABASE_URL", ""))
    if not match:
        raise Exception("DATABASE_URL format error")
    user, password, host, port, db = match.groups()
    conn = psycopg2.connect(
        dbname=db,
        user=user,
        password=password,
        host=host,
        port=port
    )
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS demo_table (id SERIAL PRIMARY KEY, name TEXT)")
    cur.execute("SELECT COUNT(*) FROM demo_table")
    count = cur.fetchone()[0]
    print(f"  ✓ demo_table rows: {count}")
    if count == 0:
        cur.execute("INSERT INTO demo_table (name) VALUES ('Demo Row')")
        conn.commit()
        print("  ✓ Inserted demo row")
    cur.close()
    conn.close()
except Exception as e:
    print(f"  ✗ RDS error: {e}")

# CHROMADB TEST
print("\n[ChromaDB] Checking collections...")
try:
    chroma = ChromaClient(settings=ChromaSettings(persist_directory=CHROMA_PATH))
    colls = chroma.list_collections()
    print(f"  ✓ Collections: {[c.name for c in colls]}")
        for cname in ["disruptions", "decisions", "scenarios", "domain_knowledge"]:
            if not any(c.name == cname for c in colls):
                chroma.create_collection(name=cname)
                print(f"      ✓ Created collection {cname}")
            coll = chroma.get_collection(cname)
            docs = coll.get()["documents"]
            print(f"    - {cname}: {len(docs)} docs")
            if len(docs) == 0:
                if cname == "disruptions":
                    doc = {
                        "type": "network outage",
                        "severity": 5,
                        "timestamp": "2026-03-05T12:00:00Z",
                        "impact": "Critical service disruption affecting 80% of users",
                        "description": "Synthetic disruption: major network outage in region US-East-1",
                        "author": "system",
                        "tags": ["network", "outage", "critical"]
                    }
                elif cname == "decisions":
                    doc = {
                        "decision_id": "demo_decision_1",
                        "rationale": "Restore service by rerouting traffic",
                        "options": ["reroute", "wait", "notify users"],
                        "outcome": "Traffic rerouted, partial recovery",
                        "timestamp": "2026-03-05T12:05:00Z",
                        "author": "system",
                        "tags": ["incident response", "network"]
                    }
                elif cname == "scenarios":
                    doc = {
                        "scenario_id": "demo_scenario_1",
                        "description": "Synthetic scenario: sudden spike in user logins during outage",
                        "context": "Users attempt to access service during network outage",
                        "created_at": "2026-03-05T12:10:00Z",
                        "author": "system",
                        "tags": ["login", "outage", "user behavior"]
                    }
                elif cname == "domain_knowledge":
                    doc = {
                        "fact": "Best practice: reroute traffic during network outages to minimize impact",
                        "rule": "If outage severity > 3, initiate reroute",
                        "source": "Synthetic domain knowledge base",
                        "created_at": "2026-03-05T12:15:00Z",
                        "author": "system",
                        "tags": ["best practice", "network"]
                    }
                coll.add(documents=[str(doc)], ids=[f"demo_{cname}_1"])
                print(f"      ✓ Added enhanced synthetic doc to {cname}")
except Exception as e:
    print(f"  ✗ ChromaDB error: {e}")

print("\n=== Integration Test Complete ===")
