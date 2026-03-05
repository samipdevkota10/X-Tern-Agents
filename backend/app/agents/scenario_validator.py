"""
Scenario Validator - Validates LLM-generated scenarios against business rules.

This module ensures LLM creativity stays within business constraints:
1. Validates action types are allowed
2. Checks inventory availability
3. Verifies substitution rules
4. Ensures capacity constraints
5. Validates cost estimates are reasonable
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from enum import Enum


class ValidationSeverity(Enum):
    """Severity of validation issues."""
    ERROR = "error"      # Scenario cannot proceed
    WARNING = "warning"  # Scenario can proceed with caution
    INFO = "info"        # Informational note


@dataclass
class ValidationIssue:
    """A single validation issue."""
    severity: ValidationSeverity
    code: str
    message: str
    field: Optional[str] = None
    suggested_fix: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "field": self.field,
            "suggested_fix": self.suggested_fix,
        }


@dataclass
class ValidationResult:
    """Result of scenario validation."""
    is_valid: bool
    scenario_id: str
    issues: list[ValidationIssue] = field(default_factory=list)
    auto_corrections: dict[str, Any] = field(default_factory=dict)
    validated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    @property
    def has_errors(self) -> bool:
        return any(i.severity == ValidationSeverity.ERROR for i in self.issues)
    
    @property
    def has_warnings(self) -> bool:
        return any(i.severity == ValidationSeverity.WARNING for i in self.issues)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "scenario_id": self.scenario_id,
            "issues": [i.to_dict() for i in self.issues],
            "auto_corrections": self.auto_corrections,
            "validated_at": self.validated_at,
            "summary": {
                "errors": sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR),
                "warnings": sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING),
                "info": sum(1 for i in self.issues if i.severity == ValidationSeverity.INFO),
            }
        }


class ScenarioValidator:
    """
    Validates LLM-generated scenarios against business rules.
    
    Acts as a guardrail ensuring LLM creativity stays within bounds.
    """
    
    # Allowed action types
    VALID_ACTION_TYPES = {
        "delay", "reroute", "substitute", "resequence", 
        "expedite", "split", "partial_ship", "cancel"
    }
    
    # Action-specific constraints
    ACTION_CONSTRAINTS = {
        "delay": {
            "max_delay_hours": 72,
            "requires_customer_notification": True,
        },
        "reroute": {
            "requires_inventory_check": True,
            "requires_capacity_check": True,
        },
        "substitute": {
            "requires_substitution_rule": True,
            "requires_customer_consent": True,
        },
        "expedite": {
            "max_expedite_cost": 1000.0,
            "displaces_other_orders": True,
        },
        "split": {
            "min_split_ratio": 0.2,  # At least 20% in first shipment
            "max_shipments": 3,
        },
        "cancel": {
            "requires_manager_approval": True,
            "last_resort_only": True,
        },
    }
    
    # Cost reasonability bounds by action type
    COST_BOUNDS = {
        "delay": (0, 200),
        "reroute": (50, 800),
        "substitute": (10, 500),
        "resequence": (20, 300),
        "expedite": (100, 1500),
        "split": (50, 600),
        "partial_ship": (30, 400),
        "cancel": (0, 0),  # No direct cost, refund handled separately
    }
    
    # SLA risk bounds (scenarios with risk outside these are suspicious)
    SLA_RISK_BOUNDS = {
        "delay": (0.2, 0.9),     # Delay always has some risk
        "reroute": (0.1, 0.6),   # Reroute reduces risk
        "substitute": (0.2, 0.7),
        "resequence": (0.05, 0.4),
        "expedite": (0.01, 0.2), # Expedite significantly reduces risk
        "split": (0.15, 0.6),
    }
    
    def __init__(self):
        pass
    
    def validate(
        self,
        scenario: dict[str, Any],
        order: dict[str, Any],
        constraints: dict[str, Any],
        auto_correct: bool = True,
    ) -> ValidationResult:
        """
        Validate a single scenario.
        
        Args:
            scenario: LLM-generated scenario
            order: Order being addressed
            constraints: Available constraints (inventory, capacity, etc.)
            auto_correct: Whether to auto-correct minor issues
            
        Returns:
            ValidationResult with issues and corrections
        """
        scenario_id = scenario.get("scenario_id", str(uuid.uuid4()))
        issues: list[ValidationIssue] = []
        corrections: dict[str, Any] = {}
        
        # 1. Validate action type
        action_type = scenario.get("action_type", "").lower()
        if not action_type:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="MISSING_ACTION_TYPE",
                message="Scenario must have an action_type",
                field="action_type",
            ))
        elif action_type not in self.VALID_ACTION_TYPES:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_ACTION_TYPE",
                message=f"Unknown action type: {action_type}",
                field="action_type",
                suggested_fix=f"Use one of: {', '.join(sorted(self.VALID_ACTION_TYPES))}",
            ))
        
        # 2. Validate required fields
        required_fields = ["disruption_id", "order_id", "plan_json"]
        for field in required_fields:
            if not scenario.get(field):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_REQUIRED_FIELD",
                    message=f"Missing required field: {field}",
                    field=field,
                ))
        
        # Skip further validation if critical errors exist
        if any(i.code in ["MISSING_ACTION_TYPE", "INVALID_ACTION_TYPE"] for i in issues):
            return ValidationResult(
                is_valid=False,
                scenario_id=scenario_id,
                issues=issues,
            )
        
        # 3. Validate action-specific constraints
        action_issues, action_corrections = self._validate_action_constraints(
            action_type, scenario, order, constraints, auto_correct
        )
        issues.extend(action_issues)
        corrections.update(action_corrections)
        
        # 4. Validate cost estimates
        score_json = scenario.get("score_json", {})
        cost_issues, cost_corrections = self._validate_cost_estimate(
            action_type, score_json, auto_correct
        )
        issues.extend(cost_issues)
        corrections.update(cost_corrections)
        
        # 5. Validate SLA risk estimate
        risk_issues, risk_corrections = self._validate_sla_risk(
            action_type, score_json, auto_correct
        )
        issues.extend(risk_issues)
        corrections.update(risk_corrections)
        
        # 6. Validate plan_json structure
        plan_issues = self._validate_plan_structure(scenario.get("plan_json", {}))
        issues.extend(plan_issues)
        
        # 7. Cross-validate with order data
        order_issues = self._validate_against_order(scenario, order)
        issues.extend(order_issues)
        
        # Determine overall validity
        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)
        
        return ValidationResult(
            is_valid=is_valid,
            scenario_id=scenario_id,
            issues=issues,
            auto_corrections=corrections if auto_correct else {},
        )
    
    def validate_batch(
        self,
        scenarios: list[dict[str, Any]],
        orders_by_id: dict[str, dict[str, Any]],
        constraints: dict[str, Any],
        auto_correct: bool = True,
    ) -> tuple[list[dict[str, Any]], list[ValidationResult]]:
        """
        Validate a batch of scenarios.
        
        Args:
            scenarios: List of LLM-generated scenarios
            orders_by_id: Orders indexed by order_id
            constraints: Constraint data
            auto_correct: Whether to auto-correct issues
            
        Returns:
            Tuple of (valid_scenarios, validation_results)
        """
        valid_scenarios = []
        results = []
        
        for scenario in scenarios:
            order_id = scenario.get("order_id", "")
            order = orders_by_id.get(order_id, {})
            
            result = self.validate(scenario, order, constraints, auto_correct)
            results.append(result)
            
            if result.is_valid:
                # Apply auto-corrections
                corrected_scenario = scenario.copy()
                if result.auto_corrections:
                    if "score_json" in result.auto_corrections:
                        corrected_scenario["score_json"] = {
                            **corrected_scenario.get("score_json", {}),
                            **result.auto_corrections["score_json"],
                        }
                valid_scenarios.append(corrected_scenario)
        
        return valid_scenarios, results
    
    def _validate_action_constraints(
        self,
        action_type: str,
        scenario: dict[str, Any],
        order: dict[str, Any],
        constraints: dict[str, Any],
        auto_correct: bool,
    ) -> tuple[list[ValidationIssue], dict[str, Any]]:
        """Validate action-specific business constraints."""
        issues = []
        corrections = {}
        
        action_rules = self.ACTION_CONSTRAINTS.get(action_type, {})
        plan = scenario.get("plan_json", {})
        
        # Reroute: Check inventory at target DC
        if action_type == "reroute" and action_rules.get("requires_inventory_check"):
            target_dc = plan.get("target_dc")
            if target_dc:
                per_order_inv = constraints.get("per_order_inventory", {})
                order_inv = per_order_inv.get(order.get("order_id", ""), {})
                dc_inv = order_inv.get(target_dc, {})
                
                for line in order.get("lines", []):
                    sku = line.get("sku", "")
                    qty = line.get("qty", 0)
                    available = dc_inv.get(sku, {}).get("available", 0)
                    
                    if available < qty:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            code="INSUFFICIENT_INVENTORY",
                            message=f"Insufficient inventory at {target_dc}: {sku} needs {qty}, has {available}",
                            field="plan_json.target_dc",
                            suggested_fix=f"Consider substitute for {sku} or use different DC",
                        ))
        
        # Substitute: Check substitution rules exist
        if action_type == "substitute" and action_rules.get("requires_substitution_rule"):
            sub_sku = plan.get("substitute_sku")
            original_sku = plan.get("original_sku")
            
            if sub_sku and original_sku:
                sub_rules = constraints.get("substitution_rules", [])
                valid_sub = any(
                    r.get("sku") == original_sku and r.get("substitute_sku") == sub_sku
                    for r in sub_rules
                )
                
                if not valid_sub:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="INVALID_SUBSTITUTION",
                        message=f"No approved substitution rule for {original_sku} -> {sub_sku}",
                        field="plan_json.substitute_sku",
                        suggested_fix="Verify substitution is customer-acceptable",
                    ))
        
        # Expedite: Check cost limit
        if action_type == "expedite" and action_rules.get("max_expedite_cost"):
            score = scenario.get("score_json", {})
            cost = score.get("cost_impact_usd", 0)
            max_cost = action_rules["max_expedite_cost"]
            
            if cost > max_cost:
                if auto_correct:
                    corrections["score_json"] = {"cost_impact_usd": max_cost}
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        code="COST_CAPPED",
                        message=f"Expedite cost capped at ${max_cost}",
                        field="score_json.cost_impact_usd",
                    ))
                else:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="EXPEDITE_COST_HIGH",
                        message=f"Expedite cost ${cost} exceeds typical max ${max_cost}",
                        field="score_json.cost_impact_usd",
                    ))
        
        # Delay: Check maximum delay duration
        if action_type == "delay":
            max_hours = action_rules.get("max_delay_hours", 72)
            delay_hours = plan.get("delay_hours", 0)
            
            if delay_hours > max_hours:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="DELAY_TOO_LONG",
                    message=f"Delay of {delay_hours}h exceeds maximum {max_hours}h",
                    field="plan_json.delay_hours",
                    suggested_fix="Consider alternative action like reroute or cancel",
                ))
        
        return issues, corrections
    
    def _validate_cost_estimate(
        self,
        action_type: str,
        score_json: dict[str, Any],
        auto_correct: bool,
    ) -> tuple[list[ValidationIssue], dict[str, Any]]:
        """Validate cost estimate is within reasonable bounds."""
        issues = []
        corrections = {}
        
        cost = score_json.get("cost_impact_usd", 0)
        bounds = self.COST_BOUNDS.get(action_type, (0, 1000))
        min_cost, max_cost = bounds
        
        if cost < min_cost:
            if auto_correct:
                corrections["score_json"] = corrections.get("score_json", {})
                corrections["score_json"]["cost_impact_usd"] = min_cost
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    code="COST_ADJUSTED_UP",
                    message=f"Cost adjusted from ${cost} to minimum ${min_cost}",
                    field="score_json.cost_impact_usd",
                ))
            else:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="COST_SUSPICIOUSLY_LOW",
                    message=f"Cost ${cost} below typical minimum ${min_cost} for {action_type}",
                    field="score_json.cost_impact_usd",
                ))
        
        elif cost > max_cost * 1.5:  # Allow 50% buffer before flagging
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="COST_UNUSUALLY_HIGH",
                message=f"Cost ${cost} significantly above typical max ${max_cost} for {action_type}",
                field="score_json.cost_impact_usd",
                suggested_fix="Verify cost calculation or consider alternative action",
            ))
        
        return issues, corrections
    
    def _validate_sla_risk(
        self,
        action_type: str,
        score_json: dict[str, Any],
        auto_correct: bool,
    ) -> tuple[list[ValidationIssue], dict[str, Any]]:
        """Validate SLA risk estimate is reasonable."""
        issues = []
        corrections = {}
        
        risk = score_json.get("sla_risk", 0.5)
        bounds = self.SLA_RISK_BOUNDS.get(action_type, (0, 1))
        min_risk, max_risk = bounds
        
        if risk < min_risk:
            if auto_correct:
                corrections["score_json"] = corrections.get("score_json", {})
                corrections["score_json"]["sla_risk"] = min_risk
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    code="RISK_ADJUSTED_UP",
                    message=f"SLA risk adjusted from {risk:.0%} to minimum {min_risk:.0%}",
                    field="score_json.sla_risk",
                ))
        
        elif risk > max_risk:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="RISK_UNUSUALLY_HIGH",
                message=f"SLA risk {risk:.0%} above typical max {max_risk:.0%} for {action_type}",
                field="score_json.sla_risk",
                suggested_fix=f"Consider if {action_type} is the right approach",
            ))
        
        return issues, corrections
    
    def _validate_plan_structure(
        self,
        plan_json: dict[str, Any],
    ) -> list[ValidationIssue]:
        """Validate plan_json has required structure."""
        issues = []
        
        recommended_fields = ["summary", "what_happened", "what_to_do", "how_to_handle"]
        missing = [f for f in recommended_fields if not plan_json.get(f)]
        
        if missing:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="INCOMPLETE_PLAN",
                message=f"Plan missing recommended fields: {', '.join(missing)}",
                field="plan_json",
                suggested_fix="Add detailed explanations for better decision support",
            ))
        
        # Check plan isn't too short
        summary = plan_json.get("summary", "")
        if len(summary) < 10:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="SUMMARY_TOO_SHORT",
                message="Plan summary should be more descriptive",
                field="plan_json.summary",
            ))
        
        return issues
    
    def _validate_against_order(
        self,
        scenario: dict[str, Any],
        order: dict[str, Any],
    ) -> list[ValidationIssue]:
        """Cross-validate scenario with order data."""
        issues = []
        
        # Verify order_id matches
        if scenario.get("order_id") != order.get("order_id"):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="ORDER_ID_MISMATCH",
                message="Scenario order_id doesn't match order",
                field="order_id",
            ))
        
        # VIP orders should have appropriate handling
        if order.get("priority") == "vip":
            plan = scenario.get("plan_json", {})
            how_to = plan.get("how_to_handle", "").lower()
            
            if "vip" not in how_to and "priority" not in how_to:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    code="VIP_NOT_MENTIONED",
                    message="VIP order - consider mentioning priority handling",
                    field="plan_json.how_to_handle",
                ))
        
        return issues


# Singleton validator instance
_validator: Optional[ScenarioValidator] = None


def get_validator() -> ScenarioValidator:
    """Get or create the scenario validator singleton."""
    global _validator
    if _validator is None:
        _validator = ScenarioValidator()
    return _validator
