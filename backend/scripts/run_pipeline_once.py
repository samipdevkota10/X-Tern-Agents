"""
Development runner for multi-agent pipeline.

Environment Variables:
  DATABASE_URL          - Database connection string (default: sqlite:///./warehouse.db)
                         Example for RDS Postgres: postgresql://user:pass@host:5432/dbname
  USE_AWS               - Enable AWS services (0=local dev, 1=AWS) (default: 0)
  AWS_REGION            - AWS region (default: us-east-1)
  DYNAMO_STATUS_TABLE   - DynamoDB table for status tracking (default: pipeline_status)
  BEDROCK_MODEL_ID      - Bedrock model ID for explanations (optional)
                         Example: anthropic.claude-3-sonnet-20240229-v1:0

Usage:
  # Run with specific disruption
  python scripts/run_pipeline_once.py <disruption_id>
  
  # Run with latest open disruption
  python scripts/run_pipeline_once.py

Examples:
  # Local development (SQLite)
  export DATABASE_URL=sqlite:///./warehouse.db
  export USE_AWS=0
  python scripts/run_pipeline_once.py
  
  # AWS RDS + Bedrock
  export DATABASE_URL=postgresql://user:pass@rds-host:5432/warehouse
  export USE_AWS=1
  export AWS_REGION=us-east-1
  export DYNAMO_STATUS_TABLE=pipeline_status
  export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
  python scripts/run_pipeline_once.py abc-123-def
"""
import sys
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.agents.graph import build_graph
from app.db.models import Disruption
from app.db.session import SessionLocal
from app.mcp.tools import create_pipeline_run


def get_latest_open_disruption() -> str | None:
    """
    Get the latest open disruption from the database.
    
    Returns:
        Disruption ID or None if no open disruptions
    """
    db = SessionLocal()
    try:
        stmt = (
            select(Disruption)
            .where(Disruption.status == "open")
            .order_by(Disruption.timestamp.desc())
        )
        disruption = db.execute(stmt).scalar()
        return disruption.id if disruption else None
    finally:
        db.close()


def print_summary(final_summary: dict) -> None:
    """
    Print pipeline execution summary.
    
    Args:
        final_summary: Final summary dictionary
    """
    print("\n" + "=" * 70)
    print("  PIPELINE EXECUTION SUMMARY")
    print("=" * 70)
    
    print(f"\nPipeline Run ID: {final_summary.get('pipeline_run_id', 'N/A')}")
    print(f"Disruption ID:   {final_summary.get('disruption_id', 'N/A')}")
    
    print("\n" + "-" * 70)
    print("  IMPACT ANALYSIS")
    print("-" * 70)
    print(f"Impacted Orders:     {final_summary.get('impacted_orders_count', 0)}")
    print(f"Scenarios Generated: {final_summary.get('scenarios_count', 0)}")
    print(f"Approval Queue:      {final_summary.get('approval_queue_count', 0)}")
    
    kpis = final_summary.get("kpis", {})
    print("\n" + "-" * 70)
    print("  KEY PERFORMANCE INDICATORS")
    print("-" * 70)
    print(f"Estimated Cost:      ${kpis.get('estimated_cost', 0):.2f}")
    print(f"Avg SLA Risk:        {kpis.get('estimated_sla_risk_avg', 0):.1%}")
    print(f"Labor Impact:        {kpis.get('estimated_labor_minutes', 0)} minutes")
    
    recommendations = final_summary.get("recommended_actions", [])
    print("\n" + "-" * 70)
    print(f"  TOP {min(5, len(recommendations))} RECOMMENDED ACTIONS")
    print("-" * 70)
    
    for i, rec in enumerate(recommendations[:5], 1):
        approval_flag = "⚠️  APPROVAL NEEDED" if rec.get("needs_approval") else "✓ Auto-approve"
        print(f"\n{i}. Order: {rec.get('order_id', 'N/A')}")
        print(f"   Action:       {rec.get('action_type', 'N/A')}")
        print(f"   Overall Score: {rec.get('overall_score', 0):.3f}")
        print(f"   Cost Impact:   ${rec.get('cost_impact_usd', 0):.2f}")
        print(f"   SLA Risk:      {rec.get('sla_risk', 0):.1%}")
        print(f"   Status:        {approval_flag}")
    
    # Print explanation if available
    explanation = final_summary.get("explanation")
    if explanation:
        print("\n" + "-" * 70)
        print("  AI EXPLANATION")
        print("-" * 70)
        print(f"\n{explanation}\n")
    
    print("=" * 70 + "\n")


def main() -> int:
    """
    Main execution function.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("\n🚀 Starting Multi-Agent Pipeline Execution\n")
    
    # Get disruption ID from args or use latest
    if len(sys.argv) > 1:
        disruption_id = sys.argv[1]
        print(f"Using specified disruption: {disruption_id}")
    else:
        disruption_id = get_latest_open_disruption()
        if not disruption_id:
            print("❌ No open disruptions found in database")
            return 1
        print(f"Using latest open disruption: {disruption_id}")
    
    # Generate pipeline run ID
    pipeline_run_id = str(uuid.uuid4())
    print(f"Pipeline Run ID: {pipeline_run_id}\n")
    
    # Create pipeline run record
    result = create_pipeline_run.invoke({
        "pipeline_run_id": pipeline_run_id,
        "disruption_id": disruption_id,
    })
    
    if not result.get("ok"):
        print(f"❌ Failed to create pipeline run: {result.get('error')}")
        return 1
    
    print("✓ Pipeline run record created")
    
    # Build graph
    print("✓ Building LangGraph workflow...")
    graph = build_graph()
    
    # Initialize state
    initial_state = {
        "pipeline_run_id": pipeline_run_id,
        "disruption_id": disruption_id,
        "step": "start",
    }
    
    print("✓ Executing pipeline...\n")
    
    try:
        # Execute graph
        final_state = graph.invoke(initial_state)
        
        # Check for errors
        if final_state.get("error"):
            print(f"\n❌ Pipeline failed: {final_state['error']}")
            return 1
        
        # Get final summary
        final_summary = final_state.get("final_summary")
        
        if not final_summary:
            print("\n❌ Pipeline completed but no final summary generated")
            return 1
        
        # Print summary
        print_summary(final_summary)
        
        print("✅ Pipeline execution completed successfully!\n")
        return 0
        
    except Exception as e:
        print(f"\n❌ Pipeline execution failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
