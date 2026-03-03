"""
Optional Bedrock LLM integration for generating human-friendly explanations.
Falls back to deterministic explanations if Bedrock is not configured.
"""
import os
from typing import Any


def generate_explanation(summary_dict: dict[str, Any]) -> str:
    """
    Generate a human-friendly explanation of the pipeline results.
    
    Uses AWS Bedrock if configured, otherwise returns deterministic explanation.
    
    Args:
        summary_dict: Final summary dictionary with recommendations
        
    Returns:
        Human-readable explanation string
    """
    # Check if Bedrock is enabled
    use_aws = os.getenv("USE_AWS", "0") == "1"
    bedrock_model_id = os.getenv("BEDROCK_MODEL_ID", "")
    
    if use_aws and bedrock_model_id:
        try:
            return _generate_bedrock_explanation(summary_dict, bedrock_model_id)
        except Exception as e:
            # Fall back to deterministic on any error
            print(f"Bedrock explanation failed: {e}, using fallback")
            return _generate_fallback_explanation(summary_dict)
    else:
        return _generate_fallback_explanation(summary_dict)


def _generate_bedrock_explanation(summary_dict: dict[str, Any], model_id: str) -> str:
    """
    Generate explanation using AWS Bedrock.
    
    Args:
        summary_dict: Summary data
        model_id: Bedrock model identifier
        
    Returns:
        LLM-generated explanation
    """
    try:
        from langchain_aws import ChatBedrock
        
        # Initialize Bedrock chat model
        llm = ChatBedrock(
            model_id=model_id,
            region_name=os.getenv("AWS_REGION", "us-east-1"),
        )
        
        # Create prompt
        prompt = f"""You are an AI assistant explaining disruption response recommendations to warehouse managers.

Disruption Summary:
- Disruption ID: {summary_dict.get('disruption_id', 'N/A')}
- Impacted Orders: {summary_dict.get('impacted_orders_count', 0)}
- Scenarios Generated: {summary_dict.get('scenarios_count', 0)}
- Approval Queue: {summary_dict.get('approval_queue_count', 0)}

Top Recommendations:
{_format_recommendations(summary_dict.get('recommended_actions', []))}

KPIs:
- Estimated Cost: ${summary_dict.get('kpis', {}).get('estimated_cost', 0):.2f}
- Avg SLA Risk: {summary_dict.get('kpis', {}).get('estimated_sla_risk_avg', 0):.2%}
- Labor Minutes: {summary_dict.get('kpis', {}).get('estimated_labor_minutes', 0)}

Provide a concise 2-3 sentence explanation of these recommendations for a warehouse manager. Focus on the key actions and their business impact."""

        response = llm.invoke(prompt)
        return response.content
        
    except ImportError:
        # langchain_aws not installed
        return _generate_fallback_explanation(summary_dict)
    except Exception as e:
        raise Exception(f"Bedrock API error: {str(e)}")


def _generate_fallback_explanation(summary_dict: dict[str, Any]) -> str:
    """
    Generate deterministic explanation without LLM.
    
    Args:
        summary_dict: Summary data
        
    Returns:
        Deterministic explanation string
    """
    impacted = summary_dict.get("impacted_orders_count", 0)
    scenarios = summary_dict.get("scenarios_count", 0)
    approval_needed = summary_dict.get("approval_queue_count", 0)
    
    recommendations = summary_dict.get("recommended_actions", [])
    top_action = recommendations[0] if recommendations else {}
    action_type = top_action.get("action_type", "delay")
    
    kpis = summary_dict.get("kpis", {})
    total_cost = kpis.get("estimated_cost", 0)
    avg_sla_risk = kpis.get("estimated_sla_risk_avg", 0)
    
    explanation = (
        f"Analysis of disruption {summary_dict.get('disruption_id', 'N/A')} identified "
        f"{impacted} impacted orders. Generated {scenarios} response scenarios across "
        f"multiple action types. "
    )
    
    if approval_needed > 0:
        explanation += (
            f"{approval_needed} scenarios require human approval due to high risk or cost. "
        )
    
    explanation += (
        f"Top recommendation is '{action_type}' with estimated cost impact of "
        f"${total_cost:.2f} and average SLA risk of {avg_sla_risk:.1%}. "
    )
    
    if avg_sla_risk > 0.6:
        explanation += "High SLA risk requires immediate attention. "
    elif avg_sla_risk < 0.3:
        explanation += "Low SLA risk indicates manageable impact. "
    
    return explanation


def _format_recommendations(recommendations: list[dict[str, Any]]) -> str:
    """
    Format recommendations for prompt.
    
    Args:
        recommendations: List of recommendation dicts
        
    Returns:
        Formatted string
    """
    if not recommendations:
        return "No recommendations available"
    
    lines = []
    for i, rec in enumerate(recommendations[:5], 1):
        lines.append(
            f"{i}. Order {rec.get('order_id', 'N/A')}: "
            f"{rec.get('action_type', 'N/A')} "
            f"(Score: {rec.get('overall_score', 0):.3f})"
        )
    
    return "\n".join(lines)
