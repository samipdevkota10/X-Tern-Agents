"""
Agent Security Guard Module
Implements runtime security checks for AI agent inputs and outputs.

This module provides:
- Input sanitization: Remove sensitive data before agent processing
- Output validation: Ensure agent outputs are within safety bounds
- Confidence assessment: Flag low-confidence outputs for review
- Action whitelisting: Only allow pre-approved action types
"""

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class SecurityCheckResult:
    """Result of a security check operation."""
    passed: bool
    check_name: str
    violations: list[str]
    checked_at: datetime
    output_hash: str | None = None
    
    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "check_name": self.check_name,
            "violations": self.violations,
            "checked_at": self.checked_at.isoformat(),
            "output_hash": self.output_hash,
        }


class AgentSecurityGuard:
    """
    AI TRiSM: Security guard for multi-agent pipeline.
    
    Provides runtime security checks to ensure agents operate within
    defined safety boundaries and don't expose sensitive data.
    """
    
    # Allowed action types that agents can propose
    ALLOWED_ACTIONS = [
        "delay",
        "reroute", 
        "substitute",
        "resequence",
        "expedite",
        "split",
        "cancel",
        "hold",
    ]
    
    # Cost thresholds for automatic approval vs. escalation
    AUTO_APPROVE_COST_LIMIT = 5000  # USD
    MANAGER_APPROVAL_LIMIT = 50000  # USD
    EXECUTIVE_APPROVAL_LIMIT = 100000  # USD
    
    # SLA risk thresholds
    AUTO_APPROVE_SLA_LIMIT = 0.3
    MANAGER_APPROVAL_SLA_LIMIT = 0.7
    
    # Fields to always redact
    SENSITIVE_FIELDS = [
        "password",
        "token",
        "secret",
        "api_key",
        "ssn",
        "social_security",
        "credit_card",
        "card_number",
        "cvv",
        "pin",
        "private_key",
        "access_key",
    ]
    
    def validate_scenario_bounds(self, scenario: dict) -> SecurityCheckResult:
        """
        Ensure agent-generated scenarios don't exceed safety limits.
        
        Checks:
        - Cost impact within reasonable bounds
        - SLA risk is valid percentage (0-1)
        - Action type is whitelisted
        - Required fields are present
        """
        violations = []
        
        # Get score data
        score_json = scenario.get("score_json", {})
        if isinstance(score_json, str):
            import json
            try:
                score_json = json.loads(score_json)
            except (json.JSONDecodeError, TypeError):
                score_json = {}
        
        # Cost sanity check (prevent unrealistically high values)
        cost = score_json.get("cost_impact_usd", 0) or 0
        if cost < 0:
            violations.append(f"Negative cost impact not allowed: ${cost}")
        if cost > 1000000:  # $1M cap
            violations.append(f"Cost impact exceeds maximum: ${cost:,.0f} > $1,000,000")
        
        # SLA risk bounds check
        sla_risk = score_json.get("sla_risk", 0) or 0
        if sla_risk < 0 or sla_risk > 1:
            violations.append(f"SLA risk out of bounds [0,1]: {sla_risk}")
        
        # Action type whitelist check
        action_type = scenario.get("action_type", "")
        if action_type and action_type not in self.ALLOWED_ACTIONS:
            violations.append(f"Unauthorized action type: '{action_type}'")
        
        # Required fields check
        required_fields = ["action_type", "plan_json"]
        missing = [f for f in required_fields if not scenario.get(f)]
        if missing:
            violations.append(f"Missing required fields: {missing}")
        
        return SecurityCheckResult(
            passed=len(violations) == 0,
            check_name="scenario_bounds_validation",
            violations=violations,
            checked_at=datetime.now(timezone.utc),
            output_hash=hashlib.sha256(str(scenario).encode()).hexdigest()[:16],
        )
    
    def assess_agent_risk(
        self, 
        agent_name: str, 
        output: dict, 
        confidence: float
    ) -> dict:
        """
        Assess risk level of agent output and determine if human review needed.
        
        Args:
            agent_name: Name of the agent that produced the output
            output: The agent's output data
            confidence: Agent's confidence score (0-1)
            
        Returns:
            Risk assessment with review requirements
        """
        risk_level = "low"
        requires_review = False
        review_reason = None
        escalation_path = None
        
        # Low confidence always requires review
        if confidence < 0.5:
            risk_level = "critical"
            requires_review = True
            review_reason = f"Very low confidence: {confidence:.2f}"
            escalation_path = "senior_manager"
        elif confidence < 0.7:
            risk_level = "high"
            requires_review = True
            review_reason = f"Low confidence: {confidence:.2f}"
            escalation_path = "warehouse_manager"
        elif confidence < 0.85:
            risk_level = "medium"
            # Only require review for decision-making agents
            if agent_name in ["scenario_generator", "tradeoff_scoring"]:
                requires_review = True
                review_reason = f"Moderate confidence for critical agent: {confidence:.2f}"
                escalation_path = "warehouse_manager"
        
        # Check output size (large outputs may indicate issues)
        output_size = len(str(output))
        if output_size > 100000:
            risk_level = "high" if risk_level == "low" else risk_level
            requires_review = True
            review_reason = f"Unusually large output: {output_size} chars"
        
        return {
            "agent": agent_name,
            "risk_level": risk_level,
            "confidence": confidence,
            "requires_human_review": requires_review,
            "review_reason": review_reason,
            "escalation_path": escalation_path,
            "output_hash": hashlib.sha256(str(output).encode()).hexdigest()[:16],
            "assessed_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def sanitize_agent_input(self, input_data: dict) -> dict:
        """
        Remove sensitive data and sanitize inputs before agent processing.
        
        Operations:
        - Redact sensitive fields (passwords, tokens, etc.)
        - Truncate overly long values
        - Remove potential injection patterns
        """
        sanitized = {}
        
        for key, value in input_data.items():
            # Check if field name is sensitive
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                sanitized[key] = "[REDACTED]"
                continue
            
            # Handle string values
            if isinstance(value, str):
                # Truncate very long strings
                if len(value) > 10000:
                    sanitized[key] = value[:10000] + "[TRUNCATED]"
                # Remove potential script injection
                elif re.search(r"<script|javascript:|data:", value, re.IGNORECASE):
                    sanitized[key] = re.sub(
                        r"<script.*?>.*?</script>|javascript:|data:",
                        "[REMOVED]",
                        value,
                        flags=re.IGNORECASE | re.DOTALL
                    )
                else:
                    sanitized[key] = value
            
            # Recursively sanitize nested dicts
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_agent_input(value)
            
            # Recursively sanitize lists
            elif isinstance(value, list):
                sanitized[key] = [
                    self.sanitize_agent_input(item) if isinstance(item, dict) else item
                    for item in value
                ]
            
            else:
                sanitized[key] = value
        
        return sanitized
    
    def determine_approval_path(self, scenario: dict) -> dict:
        """
        Determine the required approval path based on scenario risk.
        
        Returns approval requirements with escalation chain.
        """
        score_json = scenario.get("score_json", {})
        if isinstance(score_json, str):
            import json
            try:
                score_json = json.loads(score_json)
            except (json.JSONDecodeError, TypeError):
                score_json = {}
        
        cost = score_json.get("cost_impact_usd", 0) or 0
        sla_risk = score_json.get("sla_risk", 0) or 0
        
        # Determine approval level
        if cost > self.EXECUTIVE_APPROVAL_LIMIT or sla_risk > 0.95:
            return {
                "auto_approve": False,
                "required_role": "executive",
                "escalation_chain": ["warehouse_manager", "senior_manager", "executive"],
                "reason": f"High impact: cost=${cost:,.0f}, SLA risk={sla_risk:.1%}",
                "priority": "critical",
            }
        elif cost > self.MANAGER_APPROVAL_LIMIT or sla_risk > self.MANAGER_APPROVAL_SLA_LIMIT:
            return {
                "auto_approve": False,
                "required_role": "senior_manager",
                "escalation_chain": ["warehouse_manager", "senior_manager"],
                "reason": f"Elevated impact: cost=${cost:,.0f}, SLA risk={sla_risk:.1%}",
                "priority": "high",
            }
        elif cost > self.AUTO_APPROVE_COST_LIMIT or sla_risk > self.AUTO_APPROVE_SLA_LIMIT:
            return {
                "auto_approve": False,
                "required_role": "warehouse_manager",
                "escalation_chain": ["warehouse_manager"],
                "reason": f"Moderate impact: cost=${cost:,.0f}, SLA risk={sla_risk:.1%}",
                "priority": "normal",
            }
        else:
            return {
                "auto_approve": True,
                "required_role": None,
                "escalation_chain": [],
                "reason": f"Low impact: cost=${cost:,.0f}, SLA risk={sla_risk:.1%}",
                "priority": "low",
            }
    
    def generate_audit_hash(self, data: Any) -> str:
        """
        Generate a tamper-evident hash for audit trail.
        """
        content = str(data).encode()
        return hashlib.sha256(content).hexdigest()
    
    def validate_agent_chain(self, decision_logs: list[dict]) -> SecurityCheckResult:
        """
        Validate that agents executed in proper sequence.
        
        Expected order: signal_intake -> constraint_builder -> scenario_generator -> tradeoff_scoring
        """
        violations = []
        
        expected_order = [
            "supervisor",
            "signal_intake", 
            "constraint_builder", 
            "scenario_generator", 
            "tradeoff_scoring"
        ]
        
        # Extract agent sequence from logs
        agent_sequence = [
            log.get("agent_name") 
            for log in sorted(decision_logs, key=lambda x: x.get("timestamp", ""))
            if log.get("agent_name") in expected_order
        ]
        
        # Check first agent
        if agent_sequence and agent_sequence[0] not in ["supervisor", "signal_intake"]:
            violations.append(f"Invalid starting agent: {agent_sequence[0]}")
        
        # Check for unauthorized agents
        all_agents = set(log.get("agent_name", "") for log in decision_logs)
        unauthorized = all_agents - set(expected_order) - {""}
        if unauthorized:
            violations.append(f"Unauthorized agents in chain: {unauthorized}")
        
        return SecurityCheckResult(
            passed=len(violations) == 0,
            check_name="agent_chain_validation",
            violations=violations,
            checked_at=datetime.now(timezone.utc),
        )


def get_security_guard() -> AgentSecurityGuard:
    """Get singleton instance of security guard."""
    return AgentSecurityGuard()
