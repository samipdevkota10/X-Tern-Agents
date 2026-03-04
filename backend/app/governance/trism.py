"""
AI TRiSM: Trust, Risk, and Security Management Framework
Based on Gartner's AI TRiSM principles for responsible AI governance.

This module implements:
- TRUST: Model explainability, output consistency, human override tracking
- RISK: Risk assessment, confidence thresholds, escalation paths
- SECURITY: Data lineage, PII detection, prompt injection prevention
- MANAGEMENT: Evaluation records, approval workflows, audit trails
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class RiskLevel(Enum):
    """Risk classification levels for AI outputs."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class HarmCategory(Enum):
    """Categories of potential harm from AI decisions."""
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    SAFETY = "safety"
    COMPLIANCE = "compliance"
    REPUTATIONAL = "reputational"


@dataclass
class TRiSMEvaluation:
    """
    Comprehensive evaluation record for AI governance.
    Each pipeline run should produce one TRiSMEvaluation.
    """
    
    # Identifiers
    evaluation_id: str
    pipeline_run_id: str
    evaluated_at: datetime
    
    # TRUST Metrics
    model_explainability_score: float  # 0-1, how interpretable is output
    output_consistency_score: float     # 0-1, deterministic behavior
    human_override_rate: float          # % of decisions humans changed
    rationale_provided: bool            # Did agents explain their reasoning?
    
    # RISK Assessment
    risk_level: RiskLevel
    potential_harm_category: HarmCategory
    confidence_threshold_met: bool
    max_cost_impact: float
    max_sla_risk: float
    
    # SECURITY Checks
    data_lineage_tracked: bool          # Can we trace input sources?
    pii_detected: bool
    prompt_injection_detected: bool
    input_sanitized: bool
    output_validated: bool
    
    # MANAGEMENT
    approval_required: bool
    escalation_path: Optional[str]
    evaluated_by: str = "trism_framework"
    
    # Detailed findings
    trust_findings: list[str] = field(default_factory=list)
    risk_findings: list[str] = field(default_factory=list)
    security_findings: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert evaluation to dictionary for API response."""
        return {
            "evaluation_id": self.evaluation_id,
            "pipeline_run_id": self.pipeline_run_id,
            "evaluated_at": self.evaluated_at.isoformat(),
            "trust": {
                "explainability_score": self.model_explainability_score,
                "consistency_score": self.output_consistency_score,
                "human_override_rate": self.human_override_rate,
                "rationale_provided": self.rationale_provided,
                "findings": self.trust_findings,
            },
            "risk": {
                "level": self.risk_level.value,
                "harm_category": self.potential_harm_category.value,
                "confidence_threshold_met": self.confidence_threshold_met,
                "max_cost_impact_usd": self.max_cost_impact,
                "max_sla_risk": self.max_sla_risk,
                "findings": self.risk_findings,
            },
            "security": {
                "data_lineage_tracked": self.data_lineage_tracked,
                "pii_detected": self.pii_detected,
                "prompt_injection_detected": self.prompt_injection_detected,
                "input_sanitized": self.input_sanitized,
                "output_validated": self.output_validated,
                "findings": self.security_findings,
            },
            "management": {
                "approval_required": self.approval_required,
                "escalation_path": self.escalation_path,
                "evaluated_by": self.evaluated_by,
            },
        }


class AIGovernanceFramework:
    """
    Implements AI TRiSM for DisruptIQ multi-agent system.
    
    This framework evaluates each pipeline run against governance criteria
    and produces audit-ready evaluation records.
    """
    
    # Configuration thresholds
    CONFIDENCE_THRESHOLD = 0.7
    HIGH_COST_THRESHOLD = 50000  # USD
    HIGH_SLA_RISK_THRESHOLD = 0.8
    CRITICAL_SLA_RISK_THRESHOLD = 0.95
    
    # PII detection patterns
    PII_PATTERNS = [
        (r'\b\d{3}-\d{2}-\d{4}\b', "SSN"),
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "Email"),
        (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', "Credit Card"),
        (r'\b\d{3}[\s-]?\d{3}[\s-]?\d{4}\b', "Phone Number"),
    ]
    
    # Prompt injection indicators
    INJECTION_INDICATORS = [
        "ignore previous",
        "disregard instructions",
        "new instructions",
        "system:",
        "admin override",
        "bypass",
        "jailbreak",
    ]
    
    def evaluate_pipeline_run(
        self,
        pipeline_run_id: str,
        scenarios: list[dict],
        decision_logs: list[dict],
    ) -> TRiSMEvaluation:
        """
        Perform comprehensive TRiSM evaluation of a pipeline run.
        
        Args:
            pipeline_run_id: Unique identifier for the pipeline run
            scenarios: List of generated scenarios with scores
            decision_logs: List of agent decision log entries
            
        Returns:
            TRiSMEvaluation with all metrics and findings
        """
        evaluation_id = f"eval-{hashlib.sha256(pipeline_run_id.encode()).hexdigest()[:12]}"
        
        trust_findings = []
        risk_findings = []
        security_findings = []
        
        # === TRUST EVALUATION ===
        explainability = self._calc_explainability(decision_logs, trust_findings)
        consistency = self._calc_consistency(scenarios, trust_findings)
        override_rate = self._calc_override_rate(scenarios, trust_findings)
        rationale_provided = self._check_rationale(decision_logs, trust_findings)
        
        # === RISK EVALUATION ===
        risk_level, max_cost, max_sla = self._assess_risk(scenarios, risk_findings)
        confidence_met = self._check_confidence(decision_logs, risk_findings)
        harm_category = self._determine_harm_category(scenarios, risk_findings)
        
        # === SECURITY EVALUATION ===
        pii_found = self._scan_for_pii(scenarios, decision_logs, security_findings)
        injection_found = self._detect_prompt_injection(decision_logs, security_findings)
        input_sanitized = self._verify_input_sanitization(decision_logs, security_findings)
        output_validated = self._verify_output_validation(scenarios, security_findings)
        
        # === MANAGEMENT DECISIONS ===
        approval_required = (
            risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            or pii_found
            or injection_found
            or not confidence_met
        )
        
        escalation_path = None
        if risk_level == RiskLevel.CRITICAL:
            escalation_path = "senior_manager"
        elif risk_level == RiskLevel.HIGH:
            escalation_path = "warehouse_manager"
        elif pii_found or injection_found:
            escalation_path = "security_team"
        
        return TRiSMEvaluation(
            evaluation_id=evaluation_id,
            pipeline_run_id=pipeline_run_id,
            evaluated_at=datetime.now(timezone.utc),
            model_explainability_score=explainability,
            output_consistency_score=consistency,
            human_override_rate=override_rate,
            rationale_provided=rationale_provided,
            risk_level=risk_level,
            potential_harm_category=harm_category,
            confidence_threshold_met=confidence_met,
            max_cost_impact=max_cost,
            max_sla_risk=max_sla,
            data_lineage_tracked=True,  # We always track via decision_logs
            pii_detected=pii_found,
            prompt_injection_detected=injection_found,
            input_sanitized=input_sanitized,
            output_validated=output_validated,
            approval_required=approval_required,
            escalation_path=escalation_path,
            trust_findings=trust_findings,
            risk_findings=risk_findings,
            security_findings=security_findings,
        )
    
    def _calc_explainability(
        self, 
        logs: list[dict], 
        findings: list[str]
    ) -> float:
        """
        Calculate explainability score based on rationale presence.
        Each agent should provide reasoning for its decisions.
        """
        if not logs:
            findings.append("No decision logs available for explainability analysis")
            return 0.0
        
        with_rationale = sum(
            1 for log in logs 
            if log.get("rationale") and len(str(log["rationale"])) > 10
        )
        score = with_rationale / len(logs)
        
        if score < 0.5:
            findings.append(f"Low explainability: only {with_rationale}/{len(logs)} agents provided rationale")
        elif score < 0.8:
            findings.append(f"Moderate explainability: {with_rationale}/{len(logs)} agents provided rationale")
        else:
            findings.append(f"Good explainability: {with_rationale}/{len(logs)} agents provided rationale")
        
        return round(score, 3)
    
    def _calc_consistency(
        self, 
        scenarios: list[dict], 
        findings: list[str]
    ) -> float:
        """
        Check output consistency - all scenarios should have required fields.
        """
        if not scenarios:
            findings.append("No scenarios generated for consistency check")
            return 0.0
        
        required_fields = ["action_type", "plan_json", "score_json", "status"]
        valid_count = 0
        
        for scenario in scenarios:
            if all(scenario.get(f) is not None for f in required_fields):
                valid_count += 1
        
        score = valid_count / len(scenarios)
        
        if score < 1.0:
            invalid = len(scenarios) - valid_count
            findings.append(f"Consistency issue: {invalid} scenarios missing required fields")
        else:
            findings.append(f"All {len(scenarios)} scenarios have consistent structure")
        
        return round(score, 3)
    
    def _calc_override_rate(
        self, 
        scenarios: list[dict], 
        findings: list[str]
    ) -> float:
        """
        Calculate what percentage of AI decisions were overridden by humans.
        High override rate may indicate model issues.
        """
        if not scenarios:
            return 0.0
        
        edited = sum(1 for s in scenarios if s.get("status") == "edited")
        rejected = sum(1 for s in scenarios if s.get("status") == "rejected")
        
        override_rate = (edited + rejected) / len(scenarios)
        
        if override_rate > 0.5:
            findings.append(f"High override rate: {override_rate:.1%} of scenarios edited/rejected")
        elif override_rate > 0.2:
            findings.append(f"Moderate override rate: {override_rate:.1%} of scenarios edited/rejected")
        else:
            findings.append(f"Low override rate: {override_rate:.1%} - AI decisions generally accepted")
        
        return round(override_rate, 3)
    
    def _check_rationale(
        self, 
        logs: list[dict], 
        findings: list[str]
    ) -> bool:
        """Check if all critical agents provided rationale."""
        critical_agents = ["scenario_generator", "tradeoff_scoring"]
        
        for agent in critical_agents:
            agent_logs = [l for l in logs if l.get("agent_name") == agent]
            if agent_logs:
                has_rationale = any(
                    l.get("rationale") and len(str(l["rationale"])) > 10 
                    for l in agent_logs
                )
                if not has_rationale:
                    findings.append(f"Critical agent '{agent}' did not provide rationale")
                    return False
        
        return True
    
    def _assess_risk(
        self, 
        scenarios: list[dict], 
        findings: list[str]
    ) -> tuple[RiskLevel, float, float]:
        """
        Assess overall risk level based on scenario impacts.
        Returns: (risk_level, max_cost_impact, max_sla_risk)
        """
        if not scenarios:
            findings.append("No scenarios to assess for risk")
            return RiskLevel.LOW, 0.0, 0.0
        
        max_cost = 0.0
        max_sla = 0.0
        
        for scenario in scenarios:
            score_json = scenario.get("score_json", {})
            if isinstance(score_json, str):
                import json
                try:
                    score_json = json.loads(score_json)
                except (json.JSONDecodeError, TypeError):
                    score_json = {}
            
            cost = score_json.get("cost_impact_usd", 0) or 0
            sla = score_json.get("sla_risk", 0) or 0
            
            max_cost = max(max_cost, float(cost))
            max_sla = max(max_sla, float(sla))
        
        # Determine risk level
        if max_sla > self.CRITICAL_SLA_RISK_THRESHOLD:
            risk_level = RiskLevel.CRITICAL
            findings.append(f"CRITICAL: SLA risk {max_sla:.1%} exceeds {self.CRITICAL_SLA_RISK_THRESHOLD:.0%}")
        elif max_cost > self.HIGH_COST_THRESHOLD and max_sla > self.HIGH_SLA_RISK_THRESHOLD:
            risk_level = RiskLevel.CRITICAL
            findings.append(f"CRITICAL: High cost (${max_cost:,.0f}) AND high SLA risk ({max_sla:.1%})")
        elif max_cost > self.HIGH_COST_THRESHOLD:
            risk_level = RiskLevel.HIGH
            findings.append(f"HIGH RISK: Cost impact ${max_cost:,.0f} exceeds threshold")
        elif max_sla > self.HIGH_SLA_RISK_THRESHOLD:
            risk_level = RiskLevel.HIGH
            findings.append(f"HIGH RISK: SLA risk {max_sla:.1%} exceeds {self.HIGH_SLA_RISK_THRESHOLD:.0%}")
        elif max_cost > self.HIGH_COST_THRESHOLD * 0.5 or max_sla > 0.5:
            risk_level = RiskLevel.MEDIUM
            findings.append(f"MEDIUM RISK: Elevated cost (${max_cost:,.0f}) or SLA risk ({max_sla:.1%})")
        else:
            risk_level = RiskLevel.LOW
            findings.append(f"LOW RISK: Cost ${max_cost:,.0f}, SLA risk {max_sla:.1%}")
        
        return risk_level, max_cost, max_sla
    
    def _check_confidence(
        self, 
        logs: list[dict], 
        findings: list[str]
    ) -> bool:
        """Check if all agent confidence scores meet threshold."""
        if not logs:
            return True
        
        low_confidence = [
            (l.get("agent_name"), l.get("confidence_score", 1.0))
            for l in logs
            if l.get("confidence_score", 1.0) < self.CONFIDENCE_THRESHOLD
        ]
        
        if low_confidence:
            for agent, conf in low_confidence:
                findings.append(
                    f"Agent '{agent}' below confidence threshold: {conf:.2f} < {self.CONFIDENCE_THRESHOLD}"
                )
            return False
        
        findings.append(f"All agents meet confidence threshold ({self.CONFIDENCE_THRESHOLD})")
        return True
    
    def _determine_harm_category(
        self, 
        scenarios: list[dict], 
        findings: list[str]
    ) -> HarmCategory:
        """Determine primary harm category based on scenario types."""
        action_types = [s.get("action_type", "") for s in scenarios]
        
        # Financial harm indicators
        if any("reorder" in a or "expedite" in a for a in action_types):
            findings.append("Potential financial harm: scenarios involve cost-increasing actions")
            return HarmCategory.FINANCIAL
        
        # Operational harm indicators
        if any("delay" in a or "reroute" in a for a in action_types):
            findings.append("Potential operational harm: scenarios affect delivery timelines")
            return HarmCategory.OPERATIONAL
        
        # Safety harm indicators  
        if any("substitute" in a for a in action_types):
            findings.append("Potential compliance harm: product substitutions may require approval")
            return HarmCategory.COMPLIANCE
        
        return HarmCategory.OPERATIONAL
    
    def _scan_for_pii(
        self, 
        scenarios: list[dict], 
        logs: list[dict],
        findings: list[str]
    ) -> bool:
        """Scan for personally identifiable information in outputs."""
        combined_text = str(scenarios) + str(logs)
        
        found_pii = []
        for pattern, pii_type in self.PII_PATTERNS:
            if re.search(pattern, combined_text):
                found_pii.append(pii_type)
        
        if found_pii:
            findings.append(f"PII DETECTED: {', '.join(found_pii)}")
            return True
        
        findings.append("No PII detected in outputs")
        return False
    
    def _detect_prompt_injection(
        self, 
        logs: list[dict],
        findings: list[str]
    ) -> bool:
        """Detect potential prompt injection attempts in inputs."""
        combined_text = str(logs).lower()
        
        found_indicators = [
            ind for ind in self.INJECTION_INDICATORS
            if ind in combined_text
        ]
        
        if found_indicators:
            findings.append(f"PROMPT INJECTION INDICATORS: {', '.join(found_indicators)}")
            return True
        
        findings.append("No prompt injection indicators detected")
        return False
    
    def _verify_input_sanitization(
        self, 
        logs: list[dict],
        findings: list[str]
    ) -> bool:
        """Verify that inputs were properly sanitized."""
        # Check if any inputs contain obvious unsanitized data
        for log in logs:
            input_summary = str(log.get("input_summary", ""))
            
            # Check for overly long inputs (potential attack)
            if len(input_summary) > 10000:
                findings.append("Input sanitization concern: oversized input detected")
                return False
            
            # Check for script tags or SQL
            if re.search(r"<script|SELECT\s+\*|DROP\s+TABLE", input_summary, re.IGNORECASE):
                findings.append("Input sanitization concern: potential injection detected")
                return False
        
        findings.append("Input sanitization verified")
        return True
    
    def _verify_output_validation(
        self, 
        scenarios: list[dict],
        findings: list[str]
    ) -> bool:
        """Verify that outputs are within valid bounds."""
        for scenario in scenarios:
            # Check action type is valid
            valid_actions = ["delay", "reroute", "substitute", "resequence", "expedite", "split"]
            action = scenario.get("action_type", "")
            
            if action and action not in valid_actions:
                findings.append(f"Output validation failed: invalid action type '{action}'")
                return False
            
            # Check scores are within bounds
            score_json = scenario.get("score_json", {})
            if isinstance(score_json, str):
                import json
                try:
                    score_json = json.loads(score_json)
                except (json.JSONDecodeError, TypeError):
                    continue
            
            sla_risk = score_json.get("sla_risk", 0)
            if sla_risk is not None and (sla_risk < 0 or sla_risk > 1):
                findings.append(f"Output validation failed: SLA risk {sla_risk} out of bounds [0,1]")
                return False
        
        findings.append("Output validation passed")
        return True


def get_governance_framework() -> AIGovernanceFramework:
    """Get singleton instance of governance framework."""
    return AIGovernanceFramework()
