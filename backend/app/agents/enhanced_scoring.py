"""
Enhanced Scoring Algorithm - Multi-factor scoring with confidence intervals.

This module provides robust scoring that can:
1. Validate LLM-generated scores
2. Provide algorithmic scoring when needed
3. Calculate confidence intervals
4. Apply risk adjustments based on historical performance
"""
import math
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class RiskTolerance(Enum):
    """Risk tolerance levels for scoring adjustments."""
    CONSERVATIVE = "conservative"  # Minimize risk, accept higher cost
    BALANCED = "balanced"          # Balance risk and cost
    AGGRESSIVE = "aggressive"      # Accept risk for lower cost


@dataclass
class ScoreFactors:
    """Individual scoring factors with weights and bounds."""
    
    # SLA Risk (higher is worse)
    sla_risk: float = 0.5
    sla_confidence: float = 0.8
    
    # Cost Impact
    cost_impact_usd: float = 0.0
    cost_confidence: float = 0.9
    
    # Labor Impact
    labor_minutes: int = 30
    labor_confidence: float = 0.9
    
    # Execution Complexity (1-5 scale)
    complexity: int = 2
    
    # Reversibility (how easy to undo if wrong)
    reversibility: float = 0.5  # 0 = irreversible, 1 = fully reversible
    
    # Customer Impact (direct effect on customer)
    customer_impact: float = 0.3  # 0 = no impact, 1 = severe
    
    # Time Sensitivity (urgency factor)
    time_pressure: float = 0.5  # 0 = flexible, 1 = critical deadline


@dataclass
class ScoreWeights:
    """Configurable weights for scoring factors."""
    
    sla_risk: float = 0.30
    cost: float = 0.20
    labor: float = 0.10
    complexity: float = 0.10
    reversibility: float = 0.10
    customer_impact: float = 0.15
    time_pressure: float = 0.05
    
    def validate(self) -> bool:
        """Ensure weights sum to 1.0."""
        total = (
            self.sla_risk + self.cost + self.labor + 
            self.complexity + self.reversibility + 
            self.customer_impact + self.time_pressure
        )
        return abs(total - 1.0) < 0.001
    
    @classmethod
    def for_risk_tolerance(cls, tolerance: RiskTolerance) -> "ScoreWeights":
        """Get weights tuned for risk tolerance."""
        if tolerance == RiskTolerance.CONSERVATIVE:
            return cls(
                sla_risk=0.40, cost=0.15, labor=0.05,
                complexity=0.10, reversibility=0.15,
                customer_impact=0.10, time_pressure=0.05
            )
        elif tolerance == RiskTolerance.AGGRESSIVE:
            return cls(
                sla_risk=0.20, cost=0.30, labor=0.15,
                complexity=0.10, reversibility=0.05,
                customer_impact=0.15, time_pressure=0.05
            )
        else:  # BALANCED
            return cls()


@dataclass
class EnhancedScore:
    """Comprehensive score with confidence and risk metrics."""
    
    # Primary score (0-1, lower is better)
    overall_score: float
    
    # Confidence interval
    confidence: float  # 0-1, how confident we are in this score
    score_lower_bound: float  # 95% CI lower
    score_upper_bound: float  # 95% CI upper
    
    # Risk-adjusted score (accounts for uncertainty)
    risk_adjusted_score: float
    
    # Individual factors (all normalized 0-1)
    sla_risk: float
    cost_normalized: float
    labor_normalized: float
    complexity_normalized: float
    reversibility_score: float  # Inverted: higher is better
    customer_impact: float
    time_pressure: float
    
    # Raw values
    cost_impact_usd: float
    labor_minutes: int
    
    # Decision support
    needs_approval: bool
    approval_reasons: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    
    # Source tracking
    scoring_method: str = "algorithmic"  # "llm" or "algorithmic"
    llm_calibrated: bool = False  # True if LLM score was validated/adjusted
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "overall_score": round(self.overall_score, 4),
            "confidence": round(self.confidence, 3),
            "score_range": {
                "lower": round(self.score_lower_bound, 4),
                "upper": round(self.score_upper_bound, 4),
            },
            "risk_adjusted_score": round(self.risk_adjusted_score, 4),
            "factors": {
                "sla_risk": round(self.sla_risk, 3),
                "cost_normalized": round(self.cost_normalized, 3),
                "labor_normalized": round(self.labor_normalized, 3),
                "complexity": round(self.complexity_normalized, 3),
                "reversibility": round(self.reversibility_score, 3),
                "customer_impact": round(self.customer_impact, 3),
                "time_pressure": round(self.time_pressure, 3),
            },
            "raw_values": {
                "cost_impact_usd": round(self.cost_impact_usd, 2),
                "labor_impact_minutes": self.labor_minutes,
            },
            "decision": {
                "needs_approval": self.needs_approval,
                "approval_reasons": self.approval_reasons,
                "risk_factors": self.risk_factors,
            },
            "metadata": {
                "scoring_method": self.scoring_method,
                "llm_calibrated": self.llm_calibrated,
            },
        }


class EnhancedScorer:
    """
    Multi-factor scoring engine with confidence intervals.
    
    Features:
    - Configurable weights by risk tolerance
    - Confidence interval calculation
    - Risk-adjusted scoring (penalizes uncertainty)
    - LLM score validation and calibration
    - Historical performance learning (when data available)
    """
    
    # Normalization caps
    COST_CAP = 2000.0  # $2000 max for normalization
    LABOR_CAP = 480    # 8 hours max for normalization
    
    # Approval thresholds
    SLA_RISK_THRESHOLD = 0.6
    COST_THRESHOLD = 500.0
    COMPLEXITY_THRESHOLD = 4
    
    def __init__(
        self,
        weights: Optional[ScoreWeights] = None,
        risk_tolerance: RiskTolerance = RiskTolerance.BALANCED,
    ):
        self.weights = weights or ScoreWeights.for_risk_tolerance(risk_tolerance)
        self.risk_tolerance = risk_tolerance
        
        if not self.weights.validate():
            raise ValueError("Weights must sum to 1.0")
    
    def score(
        self,
        factors: ScoreFactors,
        order_priority: str = "standard",
        action_type: str = "delay",
        historical_accuracy: Optional[float] = None,
    ) -> EnhancedScore:
        """
        Calculate comprehensive score for a scenario.
        
        Args:
            factors: Individual scoring factors
            order_priority: standard, expedited, vip
            action_type: delay, reroute, substitute, resequence, expedite, split
            historical_accuracy: Optional historical accuracy of similar predictions
            
        Returns:
            EnhancedScore with all metrics
        """
        # Normalize factors
        cost_norm = self._normalize_cost(factors.cost_impact_usd)
        labor_norm = self._normalize_labor(factors.labor_minutes)
        complexity_norm = factors.complexity / 5.0
        reversibility_inverted = 1.0 - factors.reversibility  # Lower is better
        
        # Apply priority multipliers
        priority_mult = self._get_priority_multiplier(order_priority)
        adjusted_sla_risk = min(1.0, factors.sla_risk * priority_mult)
        adjusted_customer_impact = min(1.0, factors.customer_impact * priority_mult)
        
        # Calculate weighted score
        weighted_score = (
            self.weights.sla_risk * adjusted_sla_risk +
            self.weights.cost * cost_norm +
            self.weights.labor * labor_norm +
            self.weights.complexity * complexity_norm +
            self.weights.reversibility * reversibility_inverted +
            self.weights.customer_impact * adjusted_customer_impact +
            self.weights.time_pressure * factors.time_pressure
        )
        
        # Calculate confidence
        base_confidence = self._calculate_confidence(factors)
        if historical_accuracy is not None:
            # Blend with historical accuracy
            confidence = 0.6 * base_confidence + 0.4 * historical_accuracy
        else:
            confidence = base_confidence
        
        # Calculate confidence interval
        uncertainty = (1 - confidence) * 0.3  # Max ±30% uncertainty
        lower_bound = max(0, weighted_score - uncertainty)
        upper_bound = min(1, weighted_score + uncertainty)
        
        # Risk-adjusted score (penalizes uncertainty using Sharpe-like ratio)
        # Higher uncertainty adds penalty to score
        risk_adjusted = self._calculate_risk_adjusted_score(
            weighted_score, confidence, self.risk_tolerance
        )
        
        # Determine approval requirements
        needs_approval, approval_reasons = self._check_approval_requirements(
            factors, order_priority, action_type, weighted_score
        )
        
        # Identify risk factors
        risk_factors = self._identify_risk_factors(factors, action_type)
        
        return EnhancedScore(
            overall_score=weighted_score,
            confidence=confidence,
            score_lower_bound=lower_bound,
            score_upper_bound=upper_bound,
            risk_adjusted_score=risk_adjusted,
            sla_risk=adjusted_sla_risk,
            cost_normalized=cost_norm,
            labor_normalized=labor_norm,
            complexity_normalized=complexity_norm,
            reversibility_score=factors.reversibility,
            customer_impact=adjusted_customer_impact,
            time_pressure=factors.time_pressure,
            cost_impact_usd=factors.cost_impact_usd,
            labor_minutes=factors.labor_minutes,
            needs_approval=needs_approval,
            approval_reasons=approval_reasons,
            risk_factors=risk_factors,
            scoring_method="algorithmic",
            llm_calibrated=False,
        )
    
    def validate_llm_score(
        self,
        llm_score: dict[str, Any],
        factors: ScoreFactors,
        order_priority: str = "standard",
        action_type: str = "delay",
    ) -> EnhancedScore:
        """
        Validate and calibrate an LLM-generated score.
        
        Checks if LLM score is within reasonable bounds and adjusts if needed.
        
        Args:
            llm_score: Score dictionary from LLM
            factors: Calculated factors for validation
            order_priority: Order priority
            action_type: Scenario action type
            
        Returns:
            EnhancedScore with validated/calibrated values
        """
        # Calculate algorithmic score for comparison
        algo_score = self.score(factors, order_priority, action_type)
        
        # Extract LLM values
        llm_overall = llm_score.get("overall_score", 0.5)
        llm_sla_risk = llm_score.get("sla_risk", factors.sla_risk)
        llm_cost = llm_score.get("cost_impact_usd", factors.cost_impact_usd)
        
        # Check if LLM score is within reasonable bounds (±50% of algorithmic)
        deviation = abs(llm_overall - algo_score.overall_score)
        is_reasonable = deviation < 0.3
        
        if is_reasonable:
            # LLM score is reasonable, use it with high confidence
            calibrated_score = llm_overall
            confidence = min(0.95, algo_score.confidence + 0.1)
        else:
            # LLM score is suspicious, blend with algorithmic
            calibrated_score = 0.6 * algo_score.overall_score + 0.4 * llm_overall
            confidence = max(0.5, algo_score.confidence - 0.2)
        
        # Recalculate bounds with calibrated score
        uncertainty = (1 - confidence) * 0.3
        lower_bound = max(0, calibrated_score - uncertainty)
        upper_bound = min(1, calibrated_score + uncertainty)
        
        # Risk adjust
        risk_adjusted = self._calculate_risk_adjusted_score(
            calibrated_score, confidence, self.risk_tolerance
        )
        
        # Use LLM cost if reasonable, else algorithmic
        final_cost = llm_cost if abs(llm_cost - factors.cost_impact_usd) < factors.cost_impact_usd * 0.5 else factors.cost_impact_usd
        
        return EnhancedScore(
            overall_score=calibrated_score,
            confidence=confidence,
            score_lower_bound=lower_bound,
            score_upper_bound=upper_bound,
            risk_adjusted_score=risk_adjusted,
            sla_risk=llm_sla_risk if is_reasonable else algo_score.sla_risk,
            cost_normalized=self._normalize_cost(final_cost),
            labor_normalized=algo_score.labor_normalized,
            complexity_normalized=algo_score.complexity_normalized,
            reversibility_score=algo_score.reversibility_score,
            customer_impact=algo_score.customer_impact,
            time_pressure=algo_score.time_pressure,
            cost_impact_usd=final_cost,
            labor_minutes=algo_score.labor_minutes,
            needs_approval=algo_score.needs_approval,
            approval_reasons=algo_score.approval_reasons,
            risk_factors=algo_score.risk_factors,
            scoring_method="llm",
            llm_calibrated=not is_reasonable,
        )
    
    def _normalize_cost(self, cost_usd: float) -> float:
        """Normalize cost with logarithmic scaling for large values."""
        if cost_usd <= 0:
            return 0.0
        if cost_usd <= self.COST_CAP:
            return cost_usd / self.COST_CAP
        # Logarithmic scaling for costs above cap
        excess = cost_usd - self.COST_CAP
        log_excess = math.log1p(excess / self.COST_CAP) / 3
        return min(1.0, 1.0 + log_excess * 0.2)
    
    def _normalize_labor(self, labor_minutes: int) -> float:
        """Normalize labor with diminishing returns for long tasks."""
        if labor_minutes <= 0:
            return 0.0
        if labor_minutes <= self.LABOR_CAP:
            return labor_minutes / self.LABOR_CAP
        # Diminishing penalty for very long tasks
        excess = labor_minutes - self.LABOR_CAP
        return min(1.0, 1.0 + (excess / self.LABOR_CAP) * 0.1)
    
    def _get_priority_multiplier(self, priority: str) -> float:
        """Get risk multiplier based on order priority."""
        multipliers = {
            "vip": 1.4,
            "expedited": 1.2,
            "standard": 1.0,
        }
        return multipliers.get(priority, 1.0)
    
    def _calculate_confidence(self, factors: ScoreFactors) -> float:
        """Calculate overall confidence from factor confidences."""
        # Weighted average of factor confidences
        confidences = [
            (factors.sla_confidence, 0.4),
            (factors.cost_confidence, 0.3),
            (factors.labor_confidence, 0.3),
        ]
        return sum(c * w for c, w in confidences)
    
    def _calculate_risk_adjusted_score(
        self,
        score: float,
        confidence: float,
        tolerance: RiskTolerance,
    ) -> float:
        """
        Calculate risk-adjusted score that penalizes uncertainty.
        
        Uses a modified Sharpe-like ratio:
        risk_adjusted = score + penalty * (1 - confidence)
        """
        # Penalty factor based on risk tolerance
        penalties = {
            RiskTolerance.CONSERVATIVE: 0.3,
            RiskTolerance.BALANCED: 0.2,
            RiskTolerance.AGGRESSIVE: 0.1,
        }
        penalty = penalties[tolerance]
        
        # Add uncertainty penalty to score (higher score = worse)
        return score + penalty * (1 - confidence)
    
    def _check_approval_requirements(
        self,
        factors: ScoreFactors,
        priority: str,
        action_type: str,
        score: float,
    ) -> tuple[bool, list[str]]:
        """Determine if scenario requires approval and why."""
        reasons = []
        
        if factors.sla_risk > self.SLA_RISK_THRESHOLD:
            reasons.append(f"High SLA risk ({factors.sla_risk:.0%})")
        
        if factors.cost_impact_usd > self.COST_THRESHOLD:
            reasons.append(f"High cost (${factors.cost_impact_usd:,.0f})")
        
        if priority == "vip":
            reasons.append("VIP order requires manager approval")
        
        if action_type == "substitute":
            reasons.append("Substitution requires customer consent verification")
        
        if factors.complexity >= self.COMPLEXITY_THRESHOLD:
            reasons.append(f"High complexity (level {factors.complexity})")
        
        if factors.reversibility < 0.3:
            reasons.append("Low reversibility - difficult to undo")
        
        if score > 0.7:
            reasons.append("Overall risk score exceeds threshold")
        
        return len(reasons) > 0, reasons
    
    def _identify_risk_factors(
        self,
        factors: ScoreFactors,
        action_type: str,
    ) -> list[str]:
        """Identify key risk factors for the scenario."""
        risks = []
        
        if factors.sla_risk > 0.5:
            risks.append("Elevated SLA breach probability")
        
        if factors.customer_impact > 0.5:
            risks.append("Significant customer experience impact")
        
        if factors.time_pressure > 0.7:
            risks.append("Time-critical decision")
        
        if factors.reversibility < 0.3:
            risks.append("Action is difficult to reverse")
        
        if action_type == "reroute":
            risks.append("Cross-DC transfer introduces logistics complexity")
        
        if action_type == "expedite":
            risks.append("Expediting may displace other orders")
        
        return risks


def estimate_factors_for_action(
    *,
    action_type: str,
    order: Optional[dict[str, Any]] = None,
    disruption: Optional[dict[str, Any]] = None,
    constraints: Optional[dict[str, Any]] = None,
    # Back-compat (used by tradeoff_scoring_agent.py)
    order_priority: str = "standard",
    plan: Optional[dict[str, Any]] = None,
    order_line_count: int = 1,
) -> ScoreFactors:
    """
    Estimate scoring factors for a given action type.
    
    This provides baseline estimates that can be refined by LLM.
    """
    if order is None:
        order = {"priority": order_priority, "lines": [None] * max(1, int(order_line_count or 1))}
    if disruption is None:
        disruption = {}
    if constraints is None:
        constraints = {}

    priority = order.get("priority") or order_priority or "standard"
    priority_mult = {
        "critical": 1.5,
        "vip": 1.4,
        "expedite": 1.3,
        "expedited": 1.3,
        "standard": 1.0,
        "low": 0.7,
    }.get(priority, 1.0)
    order_lines = max(1, len(order.get("lines") or [1]))
    
    # Base estimates by action type
    base_estimates = {
        "delay": {
            "sla_risk": 0.6,
            "cost": 30,
            "labor": 10,
            "complexity": 1,
            "reversibility": 0.9,
            "customer_impact": 0.4,
        },
        "reroute": {
            "sla_risk": 0.3,
            "cost": 150,
            "labor": 45,
            "complexity": 3,
            "reversibility": 0.6,
            "customer_impact": 0.2,
        },
        "substitute": {
            "sla_risk": 0.4,
            "cost": 50,
            "labor": 30,
            "complexity": 2,
            "reversibility": 0.3,
            "customer_impact": 0.6,
        },
        "resequence": {
            "sla_risk": 0.2,
            "cost": 40,
            "labor": 20,
            "complexity": 2,
            "reversibility": 0.8,
            "customer_impact": 0.1,
        },
        "expedite": {
            "sla_risk": 0.15,
            "cost": 200,
            "labor": 60,
            "complexity": 3,
            "reversibility": 0.4,
            "customer_impact": 0.1,
        },
        "split": {
            "sla_risk": 0.35,
            "cost": 100,
            "labor": 50,
            "complexity": 4,
            "reversibility": 0.2,
            "customer_impact": 0.5,
        },
    }
    
    base = base_estimates.get(action_type, base_estimates["delay"])
    
    # Adjust SLA risk based on disruption severity
    severity = disruption.get("severity", 3)
    severity_mult = 0.8 + (severity * 0.1)  # 0.9 to 1.3
    adjusted_sla_risk = min(1.0, base["sla_risk"] * severity_mult)
    
    # Adjust cost based on order size
    cost_mult = 1 + (order_lines - 1) * 0.1
    adjusted_cost = base["cost"] * cost_mult
    
    # Time pressure from cutoff proximity
    # This would ideally be calculated from actual datetime
    time_pressure = 0.5 if severity >= 4 else 0.3

    # If we have a scenario plan, use deterministic adjustments where available.
    # This keeps EnhancedScorer factor estimation consistent with scenario fields.
    if plan is not None and action_type in {"delay", "reroute", "substitute", "resequence"}:
        try:
            from app.agents.scoring import (
                calculate_cost_impact,
                calculate_labor_impact,
                calculate_sla_risk,
            )

            penalty_cost = float(plan.get("penalty_cost", 0.0) or 0.0)
            transfer_distance = 1 if plan.get("target_dc") else 0
            cutoff_exceeded = bool(plan.get("cutoff_exceeded", False))
            availability_sufficient = bool(plan.get("availability_sufficient", True))

            adjusted_cost = float(
                calculate_cost_impact(action_type, priority, penalty_cost, transfer_distance)
            )
            adjusted_sla_risk = float(
                calculate_sla_risk(action_type, priority, cutoff_exceeded, availability_sufficient)
            )
            labor = int(calculate_labor_impact(action_type, int(order_line_count or order_lines or 1)))
            base = {**base, "labor": labor}

            if cutoff_exceeded:
                time_pressure = max(time_pressure, 0.8)
        except Exception:
            # If deterministic scoring isn't available for some reason, keep baseline estimates.
            pass
    
    # Adjust customer_impact based on order priority (higher priority = higher impact)
    adjusted_customer_impact = min(1.0, base["customer_impact"] * priority_mult)
    
    return ScoreFactors(
        sla_risk=adjusted_sla_risk,
        sla_confidence=0.75,  # Moderate confidence for estimates
        cost_impact_usd=adjusted_cost,
        cost_confidence=0.8,
        labor_minutes=int(base["labor"]),
        labor_confidence=0.85,
        complexity=base["complexity"],
        reversibility=base["reversibility"],
        customer_impact=adjusted_customer_impact,
        time_pressure=time_pressure,
    )


# Singleton scorer instance
_scorer: Optional[EnhancedScorer] = None


def get_scorer(risk_tolerance: RiskTolerance = RiskTolerance.BALANCED) -> EnhancedScorer:
    """Get or create the enhanced scorer singleton."""
    global _scorer
    if _scorer is None or _scorer.risk_tolerance != risk_tolerance:
        _scorer = EnhancedScorer(risk_tolerance=risk_tolerance)
    return _scorer
