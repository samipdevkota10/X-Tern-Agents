"""
Deterministic scoring functions for scenario evaluation.
"""
from typing import Any


def calculate_cost_impact(
    action_type: str,
    order_priority: str,
    penalty_cost: float = 0.0,
    transfer_distance: int = 0,
) -> float:
    """
    Calculate cost impact in USD for a scenario.
    
    Args:
        action_type: One of delay, reroute, substitute, resequence
        order_priority: standard, expedited, vip
        penalty_cost: Substitution penalty cost if applicable
        transfer_distance: Distance factor for reroute (0=same DC, 1=cross-DC)
        
    Returns:
        Estimated cost impact in USD
    """
    base_costs = {
        "delay": {"standard": 20, "expedited": 35, "vip": 50},
        "reroute": 100 + (transfer_distance * 400),  # Base + transfer
        "substitute": penalty_cost + 15,  # Penalty + handling
        "resequence": 30,  # Overtime/priority handling
    }
    
    if action_type == "delay":
        return base_costs["delay"].get(order_priority, 25)
    elif action_type == "reroute":
        return base_costs["reroute"]
    elif action_type == "substitute":
        return base_costs["substitute"]
    elif action_type == "resequence":
        return base_costs["resequence"]
    
    return 0.0


def calculate_sla_risk(
    action_type: str,
    order_priority: str,
    cutoff_exceeded: bool,
    availability_sufficient: bool,
) -> float:
    """
    Calculate SLA risk score (0..1, higher is worse).
    
    Args:
        action_type: One of delay, reroute, substitute, resequence
        order_priority: standard, expedited, vip
        cutoff_exceeded: Whether action causes cutoff violation
        availability_sufficient: Whether inventory/capacity is sufficient
        
    Returns:
        SLA risk score between 0 and 1
    """
    base_risk = {
        "delay": 0.7 if cutoff_exceeded else 0.3,
        "reroute": 0.4 if availability_sufficient else 0.6,
        "substitute": 0.5,
        "resequence": 0.2 if availability_sufficient else 0.5,
    }
    
    risk = base_risk.get(action_type, 0.5)
    
    # VIP amplification
    if order_priority == "vip":
        risk = min(1.0, risk * 1.3)
    elif order_priority == "expedited":
        risk = min(1.0, risk * 1.15)
    
    return risk


def calculate_labor_impact(action_type: str, order_line_count: int = 1) -> int:
    """
    Calculate labor impact in minutes.
    
    Args:
        action_type: One of delay, reroute, substitute, resequence
        order_line_count: Number of order lines affected
        
    Returns:
        Estimated labor minutes
    """
    base_minutes = {
        "delay": 5,  # Minimal - just update system
        "reroute": 45,  # Transfer coordination
        "substitute": 25,  # Find and pick substitute
        "resequence": 60,  # Reprioritize queue
    }
    
    base = base_minutes.get(action_type, 30)
    return base + (order_line_count * 5)  # Additional time per line


def normalize_cost(cost_usd: float, cap: float = 1000.0) -> float:
    """
    Normalize cost to 0..1 range.
    
    Args:
        cost_usd: Cost in USD
        cap: Maximum cost for normalization
        
    Returns:
        Normalized cost (0..1)
    """
    return min(cost_usd / cap, 1.0)


def normalize_labor(labor_minutes: int, cap: int = 240) -> float:
    """
    Normalize labor minutes to 0..1 range.
    
    Args:
        labor_minutes: Labor time in minutes
        cap: Maximum minutes for normalization (default 4 hours)
        
    Returns:
        Normalized labor (0..1)
    """
    return min(labor_minutes / cap, 1.0)


def calculate_overall_score(
    sla_risk: float,
    cost_impact_usd: float,
    labor_impact_minutes: int,
    sla_weight: float = 0.55,
    cost_weight: float = 0.30,
    labor_weight: float = 0.15,
) -> float:
    """
    Calculate weighted overall score (lower is better).
    
    Args:
        sla_risk: SLA risk score (0..1)
        cost_impact_usd: Cost in USD
        labor_impact_minutes: Labor time in minutes
        sla_weight: Weight for SLA risk (default 0.55)
        cost_weight: Weight for cost (default 0.30)
        labor_weight: Weight for labor (default 0.15)
        
    Returns:
        Overall score (0..1, lower is better)
    """
    norm_cost = normalize_cost(cost_impact_usd)
    norm_labor = normalize_labor(labor_impact_minutes)
    
    return (sla_weight * sla_risk) + (cost_weight * norm_cost) + (labor_weight * norm_labor)


def needs_approval(
    sla_risk: float,
    cost_impact_usd: float,
    order_priority: str,
    action_type: str,
    sla_threshold: float = 0.6,
    cost_threshold: float = 500.0,
) -> bool:
    """
    Determine if scenario needs human approval.
    
    Args:
        sla_risk: SLA risk score
        cost_impact_usd: Cost in USD
        order_priority: standard, expedited, vip
        action_type: delay, reroute, substitute, resequence
        sla_threshold: SLA risk threshold for approval (default 0.6)
        cost_threshold: Cost threshold for approval (default 500)
        
    Returns:
        True if approval needed, False otherwise
    """
    return (
        sla_risk > sla_threshold
        or cost_impact_usd > cost_threshold
        or order_priority == "vip"
        or action_type == "substitute"
    )


def score_scenario(
    action_type: str,
    order_priority: str,
    plan: dict[str, Any],
    order_line_count: int = 1,
) -> dict[str, Any]:
    """
    Complete scoring for a single scenario.
    
    Args:
        action_type: One of delay, reroute, substitute, resequence
        order_priority: standard, expedited, vip
        plan: Plan JSON dict with scenario-specific parameters
        order_line_count: Number of order lines (default 1)
        
    Returns:
        Score dictionary with all metrics
    """
    # Extract scenario-specific parameters
    penalty_cost = plan.get("penalty_cost", 0.0)
    transfer_distance = 1 if plan.get("target_dc") else 0
    cutoff_exceeded = plan.get("cutoff_exceeded", False)
    availability_sufficient = plan.get("availability_sufficient", True)
    
    # Calculate metrics
    cost_impact = calculate_cost_impact(
        action_type, order_priority, penalty_cost, transfer_distance
    )
    sla_risk = calculate_sla_risk(
        action_type, order_priority, cutoff_exceeded, availability_sufficient
    )
    labor_impact = calculate_labor_impact(action_type, order_line_count)
    
    # Normalized values
    norm_cost = normalize_cost(cost_impact)
    norm_labor = normalize_labor(labor_impact)
    
    # Overall score
    overall = calculate_overall_score(sla_risk, cost_impact, labor_impact)
    
    # Approval flag
    requires_approval = needs_approval(sla_risk, cost_impact, order_priority, action_type)
    
    return {
        "cost_impact_usd": round(cost_impact, 2),
        "sla_risk": round(sla_risk, 3),
        "labor_impact_minutes": labor_impact,
        "normalized_cost": round(norm_cost, 3),
        "normalized_labor": round(norm_labor, 3),
        "overall_score": round(overall, 3),
        "needs_approval": requires_approval,
    }
