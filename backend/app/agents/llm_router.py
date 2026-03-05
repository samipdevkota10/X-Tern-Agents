"""
LLM Router - LLM-driven step routing for the multi-agent pipeline.

This module provides intelligent routing decisions using an LLM to analyze
the current state and determine the optimal next step.
"""
import json
import logging
import os
from typing import Any, Optional

from app.agents.routing_policy import get_safe_fallback_step, ALLOWED_STEPS
from app.agents.state import PipelineState

logger = logging.getLogger(__name__)


def _get_llm():
    """
    Get configured LLM instance for routing decisions.
    
    Returns ChatBedrock if configured, None otherwise.
    """
    use_aws = os.getenv("USE_AWS", "0") == "1"
    model_id = os.getenv("BEDROCK_MODEL_ID", "")
    
    if not use_aws or not model_id:
        return None
    
    try:
        from langchain_aws import ChatBedrock
        
        return ChatBedrock(
            model_id=model_id,
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            model_kwargs={
                "temperature": 0.1,  # Very low for consistent routing
                "max_tokens": 512,   # Small output for routing
            },
        )
    except ImportError:
        logger.warning("langchain_aws not installed, using deterministic routing")
        return None
    except Exception as e:
        logger.warning(f"Failed to initialize Bedrock for routing: {e}")
        return None


def _build_state_summary(state: PipelineState, current_step: str) -> dict[str, Any]:
    """
    Build a compact state summary for LLM routing decision.
    
    Args:
        state: Current pipeline state
        current_step: The step that just completed
        
    Returns:
        Compact dict summarizing state for LLM
    """
    signal = state.get("signal") or {}
    constraints = state.get("constraints") or {}
    scenarios = state.get("scenarios") or []
    scores = state.get("scores") or []
    
    # Extract disruption info (handle None signal)
    disruption_type = None
    severity = None
    impacted_orders = []
    
    if signal and isinstance(signal, dict):
        disruption_type = signal.get("type") or signal.get("disruption_type")
        severity = signal.get("severity")
        impacted_orders = signal.get("impacted_order_ids", []) or signal.get("impacted_orders", [])
    
    impacted_order_count = len(impacted_orders) if impacted_orders else 0
    
    # Count constraints
    constraints_count = 0
    if constraints:
        if isinstance(constraints, dict):
            constraints_count = sum(
                len(v) if isinstance(v, (list, dict)) else 1 
                for v in constraints.values()
            )
        elif isinstance(constraints, list):
            constraints_count = len(constraints)
    
    # Count scenarios
    scenarios_count = len(scenarios)
    
    # Calculate average score confidence if available
    avg_confidence = None
    if scores:
        confidences = [
            s.get("score_json", {}).get("confidence", 0.5)
            for s in scores
            if isinstance(s.get("score_json"), dict)
        ]
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
    
    # Get last error if any
    last_error = state.get("error")
    
    # Get retry counts
    scenario_retry_count = state.get("scenario_retry_count", 0)
    step_count = state.get("step_count", 0)
    
    return {
        "current_step": current_step,
        "disruption_type": disruption_type,
        "severity": severity,
        "impacted_order_count": impacted_order_count,
        "constraints_count": constraints_count,
        "scenarios_count": scenarios_count,
        "scores_count": len(scores),
        "avg_score_confidence": round(avg_confidence, 2) if avg_confidence else None,
        "last_error": last_error,
        "scenario_retry_count": scenario_retry_count,
        "step_count": step_count,
    }


def _build_routing_prompt(state_summary: dict[str, Any]) -> str:
    """
    Build the prompt for LLM routing decision.
    
    Args:
        state_summary: Compact state summary
        
    Returns:
        Prompt string for LLM
    """
    allowed_steps_str = ", ".join(sorted(ALLOWED_STEPS))
    
    prompt = f"""You are a routing controller for a supply chain disruption response pipeline.
Based on the current state, decide the optimal next step.

ALLOWED STEPS: {allowed_steps_str}

PIPELINE FLOW:
1. signal_intake: Processes disruption signal, identifies impacted orders
2. constraint_builder: Gathers inventory, capacity, substitution constraints
3. scenario_generator: Creates response scenarios (reschedule, substitute, expedite, etc.)
4. tradeoff_scoring: Scores scenarios on cost, SLA risk, labor impact
5. finalize: Compiles final recommendations and summary

CURRENT STATE:
{json.dumps(state_summary, indent=2)}

RULES:
- If current_step is "start", return "signal_intake"
- If no impacted orders (impacted_order_count=0), may go to "finalize" early
- If scenarios_count=0 and step is not signal_intake/constraint_builder, need "scenario_generator"
- If scenarios exist but scores_count=0, need "tradeoff_scoring"
- If scores exist, ready to "finalize"
- If scenario_retry_count >= 3 and still no scenarios, force "finalize"

RESPOND WITH ONLY valid JSON in this exact format:
{{"next_step": "step_name", "reason": "brief reason", "confidence": 0.95}}

JSON response:"""
    
    return prompt


def decide_next_step(
    state: PipelineState,
    current_step: str,
) -> dict[str, Any]:
    """
    Use LLM to decide the next pipeline step.
    
    Args:
        state: Current pipeline state
        current_step: The step that just completed
        
    Returns:
        Dict with: next_step, reason, confidence, raw (optional)
    """
    # Build state summary
    state_summary = _build_state_summary(state, current_step)
    
    # Try LLM routing
    llm = _get_llm()
    
    if llm:
        try:
            prompt = _build_routing_prompt(state_summary)
            response = llm.invoke(prompt)
            raw_content = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON response
            parsed = _parse_llm_response(raw_content)
            
            if parsed and parsed.get("next_step") in ALLOWED_STEPS:
                return {
                    "next_step": parsed["next_step"],
                    "reason": parsed.get("reason", "LLM decision"),
                    "confidence": parsed.get("confidence"),
                    "raw": raw_content[:200] if len(raw_content) > 200 else raw_content,
                }
            else:
                logger.warning(f"LLM returned invalid step: {parsed}")
        except Exception as e:
            logger.warning(f"LLM routing failed: {e}")
    
    # Fallback to deterministic routing
    fallback_step = get_safe_fallback_step(state)
    return {
        "next_step": fallback_step,
        "reason": "deterministic_fallback",
        "confidence": None,
        "raw": None,
    }


def _parse_llm_response(raw: str) -> Optional[dict[str, Any]]:
    """
    Parse LLM response JSON.
    
    Args:
        raw: Raw LLM response string
        
    Returns:
        Parsed dict or None if parsing fails
    """
    try:
        # Try direct JSON parse
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown code blocks
    try:
        import re
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
    except (json.JSONDecodeError, AttributeError):
        pass
    
    # Try to find JSON object in the response
    try:
        import re
        json_match = re.search(r'\{[^{}]*"next_step"[^{}]*\}', raw)
        if json_match:
            return json.loads(json_match.group(0))
    except (json.JSONDecodeError, AttributeError):
        pass
    
    return None


def should_use_llm_routing() -> bool:
    """
    Check if LLM routing should be used.
    
    Returns:
        True if LLM routing is enabled (default), False if deterministic
    """
    # Default to LLM routing unless explicitly disabled
    return os.getenv("USE_DETERMINISTIC_ROUTING", "0") != "1"
