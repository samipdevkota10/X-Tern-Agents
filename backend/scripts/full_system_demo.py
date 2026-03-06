"""
Full system demo: runs all agents, AWS services, and vector DB end-to-end.
"""
import os
import json
import boto3
import psycopg2
from chromadb import Client as ChromaClient
from chromadb.config import Settings as ChromaSettings
from dotenv import load_dotenv

# Load env vars
load_dotenv()
S3_BUCKET = os.environ.get("S3_BUCKET_NAME", "xtern-agents-bucket")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET = os.environ.get("AWS_SECRET_ACCESS_KEY")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
RDS_URL = os.environ.get("DATABASE_URL")
CHROMA_PATH = os.path.abspath("../chroma_data")

print("=== X-Tern Agents Full System Demo ===\n")

# 1. Generate scenario using Bedrock
print("[Agent] Generating scenario with Bedrock...")
bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION, aws_access_key_id=AWS_KEY, aws_secret_access_key=AWS_SECRET)
body = json.dumps({
    "anthropic_version": "bedrock-2023-05-31",
    "messages": [
        {"role": "user", "content": "Generate a supply chain disruption scenario for demo."}
    ],
    "max_tokens": 100,
    "temperature": 0.7
})
response = bedrock.invoke_model(
    modelId=BEDROCK_MODEL_ID,
    contentType="application/json",
    accept="application/json",
    body=body
)
scenario = json.loads(response["body"].read().decode())["content"][0]["text"]
print(f"  ✓ Scenario: {scenario[:120]}...")

# 2. Score scenario (synthetic scoring)
print("\n[Agent] Scoring scenario...")
score = len(scenario) % 10 + 1  # Fake score for demo
print(f"  ✓ Score: {score}")

# 3. Validate scenario (synthetic validation)
print("\n[Agent] Validating scenario...")
valid = "delay" in scenario.lower() or "disruption" in scenario.lower()
print(f"  ✓ Valid: {valid}")

# 4. Save results to S3
print("\n[AWS] Saving results to S3...")
s3 = boto3.client("s3", region_name=AWS_REGION, aws_access_key_id=AWS_KEY, aws_secret_access_key=AWS_SECRET)
result_key = "demo/scenario_result.json"
result_data = json.dumps({"scenario": scenario, "score": score, "valid": valid})
s3.put_object(Bucket=S3_BUCKET, Key=result_key, Body=result_data.encode())
print(f"  ✓ Saved to S3: {result_key}")

# 5. Save results to RDS
print("\n[AWS] Saving results to RDS...")
import re
match = re.match(r"postgresql://([^:]+):([^@]+)@([^:/]+):(\d+)/(\w+)", RDS_URL)
if match:
    user, password, host, port, db = match.groups()
    conn = psycopg2.connect(dbname=db, user=user, password=password, host=host, port=port)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS scenario_results (id SERIAL PRIMARY KEY, scenario TEXT, score INT, valid BOOL)")
    cur.execute("INSERT INTO scenario_results (scenario, score, valid) VALUES (%s, %s, %s)", (scenario, score, valid))
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM scenario_results")
    count = cur.fetchone()[0]
    print(f"  ✓ scenario_results rows: {count}")
    cur.close()
    conn.close()
else:
    print("  ✗ RDS connection string error")

# 6. Query ChromaDB for context
print("\n[ChromaDB] Querying for similar disruptions...")
chroma = ChromaClient(settings=ChromaSettings(persist_directory=CHROMA_PATH))
if not any(c.name == "disruptions" for c in chroma.list_collections()):
    chroma.create_collection(name="disruptions")
disruptions = chroma.get_collection("disruptions")
results = disruptions.get()
print(f"  ✓ Disruptions docs: {len(results['documents'])}")
if results["documents"]:
    print(f"    - First doc: {results['documents'][0][:120]}...")
else:
    print("    - No docs found")

print("\n=== Demo Complete ===")
