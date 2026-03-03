# Milestone 2 Quick Start

## 🚀 Run the Pipeline in 3 Steps

```bash
# 1. Install new dependencies
cd backend
pip install langgraph langchain-aws psycopg2-binary

# 2. Set environment (local dev)
export DATABASE_URL=sqlite:///./warehouse.db
export USE_AWS=0

# 3. Run pipeline
PYTHONPATH=$(pwd) python scripts/run_pipeline_once.py
```

## 📊 What Happens

The pipeline will:
1. ✅ Read latest open disruption from DB
2. ✅ Identify 10 impacted orders
3. ✅ Gather inventory/capacity constraints
4. ✅ Generate 20-30 response scenarios
5. ✅ Score each scenario (cost/SLA/labor)
6. ✅ Flag scenarios needing approval
7. ✅ Produce final recommendations
8. ✅ Log all decisions to database

## 🎯 Expected Output

```
🚀 Starting Multi-Agent Pipeline Execution

Using latest open disruption: abc-123-def
Pipeline Run ID: xyz-789-ghi

✓ Pipeline run record created
✓ Building LangGraph workflow...
✓ Executing pipeline...

======================================================================
  PIPELINE EXECUTION SUMMARY
======================================================================

Impacted Orders:     10
Scenarios Generated: 26
Approval Queue:      10

Estimated Cost:      $797.78
Avg SLA Risk:        36.7%
Labor Impact:        1320 minutes

TOP 5 RECOMMENDED ACTIONS:
1. Order: ORD0001 → resequence (Score: 0.166, Cost: $30, SLA: 20%)
2. Order: ORD0002 → resequence (Score: 0.166, Cost: $30, SLA: 20%)
...

✅ Pipeline execution completed successfully!
```

## 🔍 Verify Results

```bash
# Check scenarios created
sqlite3 warehouse.db "SELECT COUNT(*) FROM scenarios;"

# Check decision logs
sqlite3 warehouse.db "SELECT agent_name, output_summary FROM decision_logs ORDER BY timestamp DESC LIMIT 5;"

# Check pipeline status
sqlite3 warehouse.db "SELECT status, disruption_id FROM pipeline_runs ORDER BY started_at DESC LIMIT 1;"
```

## 🌐 AWS Mode (Optional)

```bash
# Set AWS environment
export DATABASE_URL=postgresql://user:pass@rds-host:5432/warehouse
export USE_AWS=1
export AWS_REGION=us-east-1
export DYNAMO_STATUS_TABLE=pipeline_status
export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Run pipeline
PYTHONPATH=$(pwd) python scripts/run_pipeline_once.py
```

See `AWS_SETUP.md` for a full checklist of the AWS resources and permissions you may want to configure.

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'langgraph'"
```bash
pip install langgraph langchain-aws
```

### "No open disruptions found"
```bash
# Re-seed database
PYTHONPATH=$(pwd) python scripts/seed_data.py
```

### "Pipeline completed but no final summary"
Check decision logs:
```bash
sqlite3 warehouse.db "SELECT agent_name, output_summary FROM decision_logs WHERE pipeline_run_id='<your-run-id>';"
```

## 📚 Learn More

- **Full Documentation:** `MILESTONE_2_COMPLETE.md`
- **Architecture:** See agent flow diagram in complete doc
- **Scoring Logic:** `backend/app/agents/scoring.py`
- **Scenario Rules:** `backend/app/agents/rules.py`

## 🎓 Key Concepts

**Agents:**
- SignalIntakeAgent: Finds impacted orders
- ConstraintBuilderAgent: Gathers constraints
- ScenarioGeneratorAgent: Creates response options
- TradeoffScoringAgent: Scores scenarios
- Supervisor: Orchestrates flow

**Scoring:**
- overall_score = 0.55×sla_risk + 0.30×cost + 0.15×labor
- Lower score = better option

**Approval Needed If:**
- SLA risk > 60% OR
- Cost > $500 OR
- VIP order OR
- Substitute action

---

**Ready to build?** Run the pipeline and check the results!
