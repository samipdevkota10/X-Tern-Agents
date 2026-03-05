"""
LLM Agent Base - Provides LLM reasoning capabilities for agents.
Uses AWS Bedrock (Claude) for intelligent decision-making.
Falls back to deterministic rules when LLM is not configured.
"""
import json
import os
from abc import ABC, abstractmethod
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage


def get_llm() -> Optional[Any]:
    """
    Get configured LLM instance.
    
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
                "temperature": 0.3,  # Lower for more consistent outputs
                "max_tokens": 4096,
            },
        )
    except ImportError:
        print("langchain_aws not installed, using deterministic mode")
        return None
    except Exception as e:
        print(f"Failed to initialize Bedrock: {e}")
        return None


def get_rag_context(agent_name: str, situation: str, disruption_type: Optional[str] = None) -> str:
    """
    Get RAG context for agent reasoning.
    
    Returns formatted context string from knowledge base.
    """
    try:
        from app.rag import get_knowledge_base
        
        kb = get_knowledge_base()
        if not kb.available:
            return ""
        
        context = kb.get_context_for_agent(agent_name, situation, disruption_type)
        
        parts = []
        
        # Add similar disruptions
        if context.get("similar_disruptions"):
            parts.append("=== SIMILAR PAST DISRUPTIONS ===")
            for d in context["similar_disruptions"][:2]:
                parts.append(f"- {d.get('content', '')[:500]}")
                parts.append(f"  (Similarity: {d.get('similarity', 0):.0%})")
        
        # Add relevant decisions
        if context.get("relevant_decisions"):
            parts.append("\n=== RELEVANT PAST DECISIONS ===")
            for d in context["relevant_decisions"][:2]:
                parts.append(f"- {d.get('content', '')[:400]}")
        
        # Add domain knowledge
        if context.get("domain_knowledge"):
            parts.append("\n=== DOMAIN KNOWLEDGE ===")
            for d in context["domain_knowledge"][:1]:
                parts.append(f"- {d.get('content', '')[:300]}")
        
        return "\n".join(parts) if parts else ""
        
    except Exception as e:
        print(f"RAG context retrieval failed: {e}")
        return ""


class LLMAgent(ABC):
    """
    Base class for LLM-powered agents.
    
    Provides:
    - LLM reasoning with structured output
    - RAG context from knowledge base
    - Fallback to deterministic rules
    - Consistent logging and error handling
    """
    
    def __init__(self, name: str):
        self.name = name
        self.llm = get_llm()
        self.use_llm = self.llm is not None
    
    def reason(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: Optional[dict] = None,
        rag_context: Optional[str] = None,
    ) -> dict:
        """
        Use LLM to reason about data and return structured output.
        
        Args:
            system_prompt: System context for the LLM
            user_prompt: User query with data
            output_schema: Expected JSON schema for output
            rag_context: Optional RAG context from knowledge base
            
        Returns:
            Parsed JSON response from LLM or fallback result
        """
        if not self.use_llm:
            return self.fallback_reason(user_prompt)
        
        try:
            # Enhance prompt with RAG context if available
            enhanced_prompt = user_prompt
            if rag_context:
                enhanced_prompt = f"""
{user_prompt}

--- HISTORICAL CONTEXT FROM KNOWLEDGE BASE ---
{rag_context}
---

Use this historical context to inform your decision, but prioritize the current situation.
"""
            
            # Build messages
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=enhanced_prompt),
            ]
            
            # Invoke LLM
            response = self.llm.invoke(messages)
            content = response.content
            
            # Parse JSON from response
            return self._parse_json_response(content, output_schema)
            
        except Exception as e:
            print(f"LLM reasoning failed for {self.name}: {e}")
            return self.fallback_reason(user_prompt)
    
    def _parse_json_response(self, content: str, schema: Optional[dict]) -> dict:
        """Extract JSON from LLM response."""
        # Try to find JSON in response
        try:
            # Look for JSON block
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            elif "{" in content:
                # Find outermost JSON object
                start = content.index("{")
                end = content.rindex("}") + 1
                json_str = content[start:end]
            else:
                return {"raw_response": content, "parsed": False}
            
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError, IndexError):
            return {"raw_response": content, "parsed": False}
    
    @abstractmethod
    def fallback_reason(self, prompt: str) -> dict:
        """Deterministic fallback when LLM is not available."""
        pass


class ScenarioReasoningAgent(LLMAgent):
    """
    LLM-powered agent for generating disruption response scenarios.
    """
    
    SYSTEM_PROMPT = """You are an expert warehouse operations AI assistant. Your role is to generate 
response scenarios for supply chain disruptions. For each impacted order, propose 2-4 
different response strategies.

IMPORTANT: You must respond with valid JSON only, no other text.

Each scenario should include:
- action_type: one of ["delay", "expedite", "substitute", "reroute", "split", "resequence"]
- plan_json: detailed action plan with specific steps
- rationale: why this scenario makes sense
- estimated_cost_impact: rough cost in USD
- estimated_sla_risk: probability of SLA breach (0.0-1.0)

Consider constraints like:
- Available inventory at other locations
- Substitution options and their penalty costs
- Urgency based on order priority (VIP > expedited > standard)
- Customer impact and satisfaction

Generate exactly 2-3 scenarios per order to keep costs reasonable. Focus on the best options."""

    def __init__(self):
        super().__init__("ScenarioReasoningAgent")
    
    def generate_scenarios(
        self,
        disruption: dict,
        impacted_orders: list[dict],
        constraints: dict,
    ) -> list[dict]:
        """
        Generate scenarios using LLM reasoning.
        
        Args:
            disruption: Disruption details
            impacted_orders: List of affected orders
            constraints: Available inventory, capacity, substitutions
            
        Returns:
            List of scenario dictionaries
        """
        prompt = f"""
Generate response scenarios for this disruption:

DISRUPTION:
{json.dumps(disruption, indent=2, default=str)}

IMPACTED ORDERS (showing first 3):
{json.dumps(impacted_orders[:3], indent=2, default=str)}

AVAILABLE CONSTRAINTS:
- Inventory at other DCs: {json.dumps(constraints.get('available_inventory', [])[:5], indent=2)}
- Substitution options: {json.dumps(constraints.get('substitutions', [])[:3], indent=2)}
- DC Capacity: {json.dumps(constraints.get('capacity', {}), indent=2)}

Generate 2-3 scenarios PER impacted order. Return as JSON array:
{{
  "scenarios": [
    {{
      "order_id": "order_123",
      "disruption_id": "{disruption.get('id', '')}",
      "action_type": "delay|expedite|substitute|reroute|split|resequence",
      "plan_json": {{
        "summary": "One-line summary of this scenario",
        "what_happened": "Clear explanation of the disruption and its impact on this order",
        "what_to_do": "Recommended action to resolve the situation",
        "how_to_handle": "Step-by-step guidance for handling this scenario including resources needed and contingency plans"
      }},
      "score_json": {{
        "cost_impact_usd": 150.00,
        "sla_risk": 0.3,
        "complexity": 2,
        "overall_score": 7.5,
        "needs_approval": false
      }},
      "rationale": "Why this action makes sense"
    }}
  ],
  "reasoning": "Brief explanation of scenario generation logic"
}}
"""
        
        # Get RAG context for better reasoning
        situation_desc = f"{disruption.get('type', 'unknown')} disruption affecting {len(impacted_orders)} orders"
        rag_context = get_rag_context(
            self.name,
            situation_desc,
            disruption.get("type"),
        )
        
        result = self.reason(self.SYSTEM_PROMPT, prompt, rag_context=rag_context)
        
        if "scenarios" in result:
            return result["scenarios"]
        elif isinstance(result.get("raw_response"), str):
            # Fallback if parsing failed
            return self.fallback_reason(prompt).get("scenarios", [])
        else:
            return []
    
    def fallback_reason(self, prompt: str) -> dict:
        """Deterministic scenario generation fallback."""
        # Return empty - let the rules-based generator handle it
        return {"scenarios": [], "fallback": True}


class TradeoffReasoningAgent(LLMAgent):
    """
    LLM-powered agent for evaluating scenario tradeoffs and scoring.
    """
    
    SYSTEM_PROMPT = """You are an expert at evaluating supply chain response scenarios.
Your job is to analyze each scenario and provide:

1. SCORING (all numeric, 0-1 scale unless specified):
   - cost_impact_usd: Estimated total cost (can exceed 0-1)
   - sla_risk: Probability of SLA breach (0.0-1.0)
   - complexity: Implementation difficulty (1-5 scale)
   - overall_score: Weighted composite (0-10, higher = better)

2. RISK ASSESSMENT:
   - needs_approval: True if high-risk decision requiring manager review
   - risk_factors: List of concerns
   - confidence: Your confidence in this assessment (0.0-1.0)

3. RECOMMENDATION:
   - recommended_rank: Priority among scenarios (1 = best)
   - rationale: Why this ranking

Consider business impact, feasibility, and reversibility. Flag scenarios with:
- Cost > $10,000
- SLA risk > 0.5
- Major operational changes

Always respond in valid JSON only."""

    def __init__(self):
        super().__init__("TradeoffReasoningAgent")
    
    def score_scenarios(
        self,
        scenarios: list[dict],
        disruption_severity: int,
    ) -> list[dict]:
        """
        Score and rank scenarios using LLM reasoning.
        
        Args:
            scenarios: Generated scenarios to evaluate
            disruption_severity: 1-5 severity level
            
        Returns:
            Scenarios with score_json updated
        """
        if not scenarios:
            return []
        
        prompt = f"""
Evaluate and score these response scenarios for a severity {disruption_severity} disruption.

SCENARIOS TO EVALUATE:
{json.dumps(scenarios[:10], indent=2, default=str)}

For each scenario, provide scoring. Return JSON:
{{
  "scored_scenarios": [
    {{
      "scenario_id": "existing_id_or_index",
      "score_json": {{
        "cost_impact_usd": 500.00,
        "sla_risk": 0.25,
        "complexity": 2,
        "overall_score": 8.0,
        "needs_approval": false,
        "labor_impact_minutes": 30
      }},
      "risk_assessment": {{
        "risk_level": "low|medium|high|critical",
        "risk_factors": ["factor1"],
        "confidence": 0.85
      }},
      "recommended_rank": 1,
      "rationale": "Why this score"
    }}
  ],
  "best_scenario_index": 0,
  "overall_recommendation": "Brief summary of recommended approach"
}}
"""
        
        # Get RAG context for past similar decisions
        situation_desc = f"Evaluating {len(scenarios)} scenarios for severity {disruption_severity} disruption"
        rag_context = get_rag_context(self.name, situation_desc)
        
        result = self.reason(self.SYSTEM_PROMPT, prompt, rag_context=rag_context)
        
        if "scored_scenarios" in result:
            # Merge scores back into original scenarios
            scored = result["scored_scenarios"]
            for i, scenario in enumerate(scenarios):
                if i < len(scored):
                    scenario["score_json"] = scored[i].get("score_json", {})
                    scenario["llm_rationale"] = scored[i].get("rationale", "")
            return scenarios
        else:
            return self.fallback_reason(prompt).get("scenarios", scenarios)
    
    def fallback_reason(self, prompt: str) -> dict:
        """Deterministic scoring fallback."""
        return {"scenarios": [], "fallback": True}


class SignalAnalysisAgent(LLMAgent):
    """
    LLM-powered agent for analyzing disruption signals and identifying impacts.
    """
    
    SYSTEM_PROMPT = """You are an expert at analyzing supply chain disruptions.
Given a disruption event and list of orders, identify which orders are impacted and why.

Consider:
- Disruption type (late_truck, stockout, machine_down)
- Order priority (VIP orders are critical)
- Timing (orders close to cutoff are more urgent)
- Resource dependencies (which orders need the affected resource)

Respond with valid JSON only."""

    def __init__(self):
        super().__init__("SignalAnalysisAgent")
    
    def analyze_impact(
        self,
        disruption: dict,
        orders: list[dict],
    ) -> dict:
        """
        Analyze disruption impact using LLM reasoning.
        
        Args:
            disruption: Disruption details
            orders: All open orders
            
        Returns:
            Impact analysis with impacted order IDs
        """
        prompt = f"""
Analyze this disruption and identify impacted orders:

DISRUPTION:
{json.dumps(disruption, indent=2, default=str)}

OPEN ORDERS (first 15):
{json.dumps(orders[:15], indent=2, default=str)}

Identify which orders are impacted and explain the reasoning.

Return JSON:
{{
  "impacted_order_ids": ["order1", "order2"],
  "impact_summary": "Brief description of overall impact",
  "severity_assessment": "critical|high|medium|low",
  "urgency_ranking": [
    {{"order_id": "X", "urgency": "critical", "reason": "VIP customer with tight deadline"}}
  ],
  "estimated_revenue_at_risk": 50000.00,
  "recommended_response_priority": "immediate|urgent|normal|low"
}}
"""
        
        result = self.reason(self.SYSTEM_PROMPT, prompt)
        
        if "impacted_order_ids" in result:
            return result
        else:
            return self.fallback_reason(prompt)
    
    def fallback_reason(self, prompt: str) -> dict:
        """Return empty for rules-based fallback."""
        return {"impacted_order_ids": [], "fallback": True}


# Singleton instances
_scenario_agent: Optional[ScenarioReasoningAgent] = None
_tradeoff_agent: Optional[TradeoffReasoningAgent] = None
_signal_agent: Optional[SignalAnalysisAgent] = None


def get_scenario_agent() -> ScenarioReasoningAgent:
    """Get singleton ScenarioReasoningAgent."""
    global _scenario_agent
    if _scenario_agent is None:
        _scenario_agent = ScenarioReasoningAgent()
    return _scenario_agent


def get_tradeoff_agent() -> TradeoffReasoningAgent:
    """Get singleton TradeoffReasoningAgent."""
    global _tradeoff_agent
    if _tradeoff_agent is None:
        _tradeoff_agent = TradeoffReasoningAgent()
    return _tradeoff_agent


def get_signal_agent() -> SignalAnalysisAgent:
    """Get singleton SignalAnalysisAgent."""
    global _signal_agent
    if _signal_agent is None:
        _signal_agent = SignalAnalysisAgent()
    return _signal_agent
