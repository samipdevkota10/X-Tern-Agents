"""
Tradeoff Scoring Agent - LLM-Native Architecture.

Primary: LLM analyzes scenarios with RAG context for intelligent scoring.
Assist: EnhancedScorer validates LLM scores and provides multi-factor analysis.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from app.agents.enhanced_scoring import (
    EnhancedScorer,
    RiskTolerance,
    estimate_factors_for_action,
)
from app.agents.llm_agent import get_tradeoff_agent
from app.agents.state import PipelineState
from app.aws.dynamo_status import write_status_safe
from app.mcp.tool_router import update_scenario_scores, write_decision_log


def log_agent_step(
    pipeline_run_id: str,
    agent_name: str,
    input_summary: str,
    output_summary: str,
    confidence_score: float,
    rationale: str,
) -> None:
    """Helper to log agent decision step."""
    entry = {
        "log_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_run_id": pipeline_run_id,
        "agent_name": agent_name,
        "input_summary": input_summary,
        "output_summary": output_summary,
        "confidence_score": confidence_score,
        "rationale": rationale,
        "human_decision": "pending",
        "approver_id": None,
        "approver_note": None,
        "override_value": None,
    }
    write_decision_log(entry)


def _get_rag_context_for_scoring(scenarios: list, signal: dict) -> dict[str, Any]:
    """
    Get RAG context relevant to scoring decisions.
    """
    try:
        from app.rag import get_knowledge_base
        
        kb = get_knowledge_base()
        if not kb.available:
            return {"rag_available": False}
        
        situation = f"Scoring {len(scenarios)} scenarios for severity {signal.get('severity', 3)} {signal.get('type', 'unknown')} disruption"
        
        context = kb.get_context_for_agent(
            agent_name="TradeoffScoring",
            current_situation=situation,
            disruption_type=signal.get("type"),
        )
        context["rag_available"] = True
        
        return context
        
    except Exception as e:
        print(f"RAG context retrieval failed for scoring: {e}")
        return {"rag_available": False, "error": str(e)}


def _determine_risk_tolerance(signal: dict, order_map: dict) -> RiskTolerance:
    """
    Determine appropriate risk tolerance based on context.
    """
    severity = signal.get("severity", 3)
    
    # Check if any critical/VIP orders
    has_critical = any(
        o.get("priority") in ("critical", "vip", "expedite")
        for o in order_map.values()
    )
    
    # High severity or critical orders = conservative
    if severity >= 4 or has_critical:
        return RiskTolerance.CONSERVATIVE
    elif severity <= 2:
        return RiskTolerance.AGGRESSIVE
    else:
        return RiskTolerance.BALANCED


def _build_enhanced_scoring_prompt(
    scenarios: list,
    signal: dict,
    rag_context: dict,
) -> str:
    """
    Build enhanced prompt for LLM scoring with RAG context.
    """
    # Base prompt
    prompt = f"""
Analyze and score these scenarios for a supply chain disruption response.

DISRUPTION CONTEXT:
- Type: {signal.get('type', 'unknown')}
- Severity: {signal.get('severity', 3)}/5
- Impacted orders: {len(signal.get('impacted_orders', []))}
"""

    # Add RAG context
    if rag_context.get("rag_available"):
        if rag_context.get("relevant_decisions"):
            prompt += "\nHISTORICAL DECISION OUTCOMES (what worked before):\n"
            for d in rag_context["relevant_decisions"][:3]:
                prompt += f"  - {d.get('content', 'N/A')[:200]}\n"
        
        if rag_context.get("domain_knowledge"):
            prompt += "\nSCORING GUIDELINES (from domain knowledge):\n"
            for d in rag_context["domain_knowledge"][:2]:
                prompt += f"  - {d.get('content', 'N/A')[:150]}\n"
    
    prompt += f"""

SCENARIOS TO SCORE ({len(scenarios)} total):
"""
    
    for i, s in enumerate(scenarios[:10]):  # Limit for token efficiency
        prompt += f"""
Scenario {i+1}: {s.get('action_type', 'N/A')} for order {s.get('order_id', 'N/A')}
  Plan: {s.get('plan_json', {}).get('summary', 'N/A')}
  Current scores: cost=${s.get('score_json', {}).get('cost_impact_usd', 0)}, SLA risk={s.get('score_json', {}).get('sla_risk', 0)}
"""
    
    prompt += """

For each scenario, provide:
1. Refined cost estimate (considering market conditions, contingencies)
2. Updated SLA risk (0.0-1.0 based on execution complexity)
3. Overall weighted score (0-100, higher = better)
4. Whether human approval is needed
5. Brief rationale

Return JSON:
{
  "scored_scenarios": [
    {
      "scenario_id": "uuid",
      "score_json": {
        "cost_impact_usd": 123.45,
        "sla_risk": 0.15,
        "weighted_score": 78.5,
        "complexity": 3,
        "needs_approval": false,
        "confidence": 0.85
      },
      "scoring_rationale": "Why this score"
    }
  ]
}
"""
    return prompt


def tradeoff_scoring_node(state: PipelineState) -> dict[str, Any]:
    """
    Tradeoff Scoring Agent node - LLM-Native Architecture.
    
    Flow:
    1. Get RAG context for historical scoring patterns
    2. Determine risk tolerance based on context
    3. Call LLM for intelligent scoring
    4. Validate/calibrate LLM scores with EnhancedScorer
    5. Apply confidence intervals and risk adjustments
    
    Args:
        state: Current pipeline state
        
    Returns:
        State updates with scored scenarios
    """
    pipeline_run_id = state["pipeline_run_id"]
    signal = state.get("signal", {})
    scenarios = state.get("scenarios", [])
    
    write_status_safe(pipeline_run_id, "tradeoff_scoring", "started")
    
    try:
        impacted_orders = signal.get("impacted_orders", [])
        
        # Build order lookup
        order_map = {order["order_id"]: order for order in impacted_orders}
        
        # Step 1: Get RAG context
        rag_context = _get_rag_context_for_scoring(scenarios, signal)
        rag_available = rag_context.get("rag_available", False)
        
        # Step 2: Determine risk tolerance
        risk_tolerance = _determine_risk_tolerance(signal, order_map)
        
        # Step 3: Initialize enhanced scorer
        scorer = EnhancedScorer(risk_tolerance=risk_tolerance)
        
        scored_scenarios = []
        scenario_score_updates = []
        used_llm = False
        llm_validated_count = 0
        llm_adjusted_count = 0
        
        # Step 4: Try LLM-based scoring
        llm_agent = get_tradeoff_agent()
        if llm_agent.use_llm and scenarios:
            try:
                severity = signal.get("severity", 3)
                llm_scored = llm_agent.score_scenarios(scenarios, severity)
                
                if llm_scored:
                    used_llm = True
                    
                    # Step 5: Validate and calibrate each LLM score
                    for llm_scenario in llm_scored:
                        scenario_id = llm_scenario.get("scenario_id")
                        order_id = llm_scenario.get("order_id")
                        order = order_map.get(order_id, {})
                        llm_score = llm_scenario.get("score_json", {})
                        
                        # Estimate factors for validation
                        factors = estimate_factors_for_action(
                            action_type=llm_scenario.get("action_type", "delay"),
                            order_priority=order.get("priority", "standard"),
                            plan=llm_scenario.get("plan_json", {}),
                            order_line_count=len(order.get("lines", [])) or 1,
                        )
                        
                        # Validate LLM score (returns a single EnhancedScore)
                        validated = scorer.validate_llm_score(llm_score, factors)
                        
                        # Track whether calibration/adjustments were applied
                        adjustments = None
                        if validated.llm_calibrated:
                            llm_adjusted_count += 1
                            adjustments = {"llm_calibrated": True}
                        llm_validated_count += 1
                        
                        # Build final score payload in the same shape used elsewhere
                        final_score = {
                            "cost_impact_usd": validated.cost_impact_usd,
                            "sla_risk": validated.sla_risk,
                            "complexity": int(round(validated.complexity_normalized * 5)),
                            "labor_impact_minutes": int(validated.labor_minutes),
                            "overall_score": validated.overall_score,
                            # Back-compat: keep weighted_score alias
                            "weighted_score": validated.overall_score,
                            "needs_approval": validated.needs_approval,
                            "confidence": validated.confidence,
                            "confidence_interval": [
                                validated.score_lower_bound,
                                validated.score_upper_bound,
                            ],
                            "risk_adjusted_score": validated.risk_adjusted_score,
                            "risk_tolerance": risk_tolerance.value,
                            "llm_validated": True,
                            "llm_calibrated": validated.llm_calibrated,
                            "approval_reasons": validated.approval_reasons,
                            "risk_factors": validated.risk_factors,
                            "adjustments_applied": adjustments,
                        }
                        
                        scored_scenario = {**llm_scenario, "score_json": final_score}
                        scored_scenarios.append(scored_scenario)
                        
                        scenario_score_updates.append({
                            "scenario_id": scenario_id,
                            "score_json": final_score,
                        })
                        
            except Exception as e:
                print(f"LLM scoring failed, using enhanced deterministic: {e}")
                scored_scenarios = []  # Reset to trigger fallback
        
        # Step 6: Fallback to enhanced deterministic scoring
        if not scored_scenarios:
            for scenario in scenarios:
                order_id = scenario["order_id"]
                order = order_map.get(order_id, {})
                
                # Estimate scoring factors
                factors = estimate_factors_for_action(
                    action_type=scenario.get("action_type", "delay"),
                    order_priority=order.get("priority", "standard"),
                    plan=scenario.get("plan_json", {}),
                    order_line_count=len(order.get("lines", [])) or 1,
                )
                
                # Get enhanced score
                enhanced = scorer.score(factors)
                
                score = {
                    "cost_impact_usd": enhanced.cost_impact_usd,
                    "sla_risk": enhanced.sla_risk,
                    "complexity": int(round(enhanced.complexity_normalized * 5)),
                    "labor_impact_minutes": int(enhanced.labor_minutes),
                    "overall_score": enhanced.overall_score,
                    # Back-compat: keep weighted_score alias
                    "weighted_score": enhanced.overall_score,
                    "needs_approval": enhanced.needs_approval,
                    "confidence": enhanced.confidence,
                    "confidence_interval": [
                        enhanced.score_lower_bound,
                        enhanced.score_upper_bound,
                    ],
                    "risk_adjusted_score": enhanced.risk_adjusted_score,
                    "risk_tolerance": risk_tolerance.value,
                    "llm_validated": False,
                    "approval_reasons": enhanced.approval_reasons,
                    "risk_factors": enhanced.risk_factors,
                }
                
                scenario_with_score = {**scenario, "score_json": score}
                scored_scenarios.append(scenario_with_score)
                
                scenario_score_updates.append({
                    "scenario_id": scenario["scenario_id"],
                    "score_json": score,
                })
        
        # Update scores in database
        if scenario_score_updates:
            result = update_scenario_scores(scenario_score_updates)
            updated_count = result.get("updated", 0)
        else:
            updated_count = 0
        
        # Count approval needs
        approval_count = sum(
            1 for s in scored_scenarios if s.get("score_json", {}).get("needs_approval", False)
        )
        
        # Calculate average confidence
        confidences = [
            s.get("score_json", {}).get("confidence", 0.8)
            for s in scored_scenarios
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.8
        
        # Build detailed rationale
        if used_llm:
            reasoning_mode = f"LLM + EnhancedScorer validation (risk={risk_tolerance.value})"
            if llm_adjusted_count > 0:
                reasoning_mode += f", {llm_adjusted_count}/{llm_validated_count} scores calibrated"
        else:
            reasoning_mode = f"EnhancedScorer multi-factor analysis (risk={risk_tolerance.value})"
        
        if rag_available and rag_context.get("relevant_decisions"):
            reasoning_mode += f", referenced {len(rag_context['relevant_decisions'])} historical decisions"
        
        log_agent_step(
            pipeline_run_id=pipeline_run_id,
            agent_name="Tradeoff Scoring",
            input_summary=f"{len(scenarios)} scenarios, {risk_tolerance.value} risk tolerance",
            output_summary=f"Scored {len(scored_scenarios)}, {approval_count} need approval, avg confidence {avg_confidence:.2f}",
            confidence_score=avg_confidence,
            rationale=reasoning_mode,
        )
        
        write_status_safe(
            pipeline_run_id,
            "tradeoff_scoring",
            "completed",
            {
                "scenarios_scored": len(scored_scenarios),
                "approval_needed": approval_count,
                "db_updated": updated_count,
                "used_llm": used_llm,
                "llm_validated": llm_validated_count,
                "llm_adjusted": llm_adjusted_count,
                "risk_tolerance": risk_tolerance.value,
                "avg_confidence": avg_confidence,
            },
        )
        
        return {
            "scores": scored_scenarios,
            "step": "tradeoff_scoring",
            "scoring_metadata": {
                "used_llm": used_llm,
                "rag_available": rag_available,
                "risk_tolerance": risk_tolerance.value,
                "avg_confidence": avg_confidence,
            },
        }
        
    except Exception as e:
        write_status_safe(pipeline_run_id, "tradeoff_scoring", "failed", {"error": str(e)})
        return {
            "error": f"Tradeoff scoring failed: {str(e)}",
            "step": "error",
        }
