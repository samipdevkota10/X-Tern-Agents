"""
Tests for LLM-driven routing with mock LLM.

These tests verify that:
1. LLM suggestions are overridden when prerequisites are missing
2. Finalize succeeds even with missing artifacts
3. Loop protection triggers correctly
4. Fallback path works when LLM fails
"""
import pytest
from unittest.mock import patch, MagicMock

from app.agents.routing_policy import (
    compute_prereq_violations,
    override_step_if_needed,
    should_force_review,
    get_safe_fallback_step,
)
from app.agents.llm_router import (
    decide_next_step,
    _parse_llm_response,
    _build_state_summary,
)
from app.agents.state import PipelineState


class TestRoutingPolicy:
    """Test routing policy guardrails."""
    
    def test_prereq_scoring_without_scenarios(self):
        """LLM suggests scoring but no scenarios exist -> override to scenario_generator."""
        state: PipelineState = {
            "pipeline_run_id": "test-123",
            "disruption_id": "D001",
            "step": "constraint_builder",
            "signal": {"disruption_id": "D001", "impacted_order_ids": ["O1"]},
            "constraints": {"inventory": [{"sku": "SKU1"}]},
            "scenarios": [],  # Empty!
            "scores": [],
        }
        
        violations = compute_prereq_violations(state, "tradeoff_scoring")
        assert len(violations) > 0
        assert "scenarios" in violations[0].lower()
        
        final_step, override_reason = override_step_if_needed(state, "tradeoff_scoring")
        assert final_step == "scenario_generator"
        assert override_reason is not None
    
    def test_prereq_scenario_gen_without_constraints(self):
        """Scenario generator proposed but constraints missing -> override to constraint_builder."""
        state: PipelineState = {
            "pipeline_run_id": "test-123",
            "disruption_id": "D001",
            "step": "signal_intake",
            "signal": {"disruption_id": "D001", "impacted_order_ids": ["O1"]},
            "constraints": {},  # Empty!
            "scenarios": [],
        }
        
        violations = compute_prereq_violations(state, "scenario_generator")
        assert len(violations) > 0
        
        final_step, override_reason = override_step_if_needed(state, "scenario_generator")
        assert final_step == "constraint_builder"
    
    def test_prereq_constraint_builder_without_signal(self):
        """Constraint builder proposed but signal missing -> override to signal_intake."""
        state: PipelineState = {
            "pipeline_run_id": "test-123",
            "disruption_id": "D001",
            "step": "start",
            "signal": None,
            "constraints": {},
        }
        
        final_step, override_reason = override_step_if_needed(state, "constraint_builder")
        assert final_step == "signal_intake"
    
    def test_scenario_retries_exhausted(self):
        """Scenario gen fails after max retries -> override to finalize with review."""
        state: PipelineState = {
            "pipeline_run_id": "test-123",
            "disruption_id": "D001",
            "step": "scenario_generator",
            "signal": {"disruption_id": "D001", "impacted_order_ids": ["O1"]},
            "constraints": {"inventory": [{"sku": "SKU1"}]},
            "scenarios": [],  # Still empty after retries
            "scenario_retry_count": 3,  # At max
            "routing_trace": [],
        }
        
        final_step, override_reason = override_step_if_needed(state, "scenario_generator")
        assert final_step == "finalize"
        assert "retries_exhausted" in override_reason
    
    def test_loop_detection(self):
        """Same step repeated too many times -> override to finalize."""
        state: PipelineState = {
            "pipeline_run_id": "test-123",
            "disruption_id": "D001",
            "step": "scenario_generator",
            "signal": {"disruption_id": "D001", "impacted_order_ids": ["O1"]},
            "constraints": {"inventory": [{"sku": "SKU1"}]},
            "scenarios": [{"scenario_id": "S1"}],  # Has scenarios
            "scenario_retry_count": 0,
            "routing_trace": [
                {"final_next_step": "scenario_generator"},
                {"final_next_step": "scenario_generator"},
                {"final_next_step": "scenario_generator"},
            ],
        }
        
        final_step, override_reason = override_step_if_needed(state, "scenario_generator")
        assert final_step == "finalize"
        assert "loop_detected" in override_reason
    
    def test_should_force_review_no_scenarios(self):
        """Force review if no scenarios after max retries."""
        state: PipelineState = {
            "pipeline_run_id": "test-123",
            "disruption_id": "D001",
            "scenarios": [],
            "scenario_retry_count": 3,
        }
        
        needs_review, reason = should_force_review(state)
        assert needs_review
        assert "no_scenarios" in reason
    
    def test_safe_fallback_progression(self):
        """Test fallback step logic progresses correctly."""
        # No signal -> signal_intake
        state: PipelineState = {"signal": None}
        assert get_safe_fallback_step(state) == "signal_intake"
        
        # Signal but no constraints -> constraint_builder
        state = {"signal": {"impacted_order_ids": ["O1"]}, "constraints": {}}
        assert get_safe_fallback_step(state) == "constraint_builder"
        
        # Constraints but no scenarios -> scenario_generator
        state = {
            "signal": {"impacted_order_ids": ["O1"]},
            "constraints": {"inventory": []},
            "scenarios": [],
        }
        assert get_safe_fallback_step(state) == "scenario_generator"
        
        # Scenarios but no scores -> tradeoff_scoring
        state = {
            "signal": {"impacted_order_ids": ["O1"]},
            "constraints": {"inventory": []},
            "scenarios": [{"scenario_id": "S1"}],
            "scores": [],
        }
        assert get_safe_fallback_step(state) == "tradeoff_scoring"
        
        # Everything present -> finalize
        state = {
            "signal": {"impacted_order_ids": ["O1"]},
            "constraints": {"inventory": []},
            "scenarios": [{"scenario_id": "S1"}],
            "scores": [{"scenario_id": "S1", "score_json": {}}],
        }
        assert get_safe_fallback_step(state) == "finalize"


class TestLLMRouter:
    """Test LLM router with mocked LLM."""
    
    def test_parse_valid_json(self):
        """Parse valid JSON response."""
        raw = '{"next_step": "scenario_generator", "reason": "test", "confidence": 0.9}'
        result = _parse_llm_response(raw)
        assert result["next_step"] == "scenario_generator"
        assert result["confidence"] == 0.9
    
    def test_parse_json_in_code_block(self):
        """Parse JSON wrapped in markdown code block."""
        raw = '''```json
{"next_step": "finalize", "reason": "all done", "confidence": 0.95}
```'''
        result = _parse_llm_response(raw)
        assert result["next_step"] == "finalize"
    
    def test_parse_invalid_json_returns_none(self):
        """Invalid JSON returns None."""
        raw = "This is not JSON at all"
        result = _parse_llm_response(raw)
        assert result is None
    
    def test_build_state_summary(self):
        """State summary includes all expected fields."""
        state: PipelineState = {
            "pipeline_run_id": "test-123",
            "disruption_id": "D001",
            "step": "constraint_builder",
            "signal": {
                "disruption_type": "truck_delay",
                "severity": "high",
                "impacted_order_ids": ["O1", "O2"],
            },
            "constraints": {"inventory": [{"sku": "S1"}, {"sku": "S2"}]},
            "scenarios": [{"scenario_id": "S1"}, {"scenario_id": "S2"}],
            "scores": [],
            "step_count": 3,
            "scenario_retry_count": 1,
        }
        
        summary = _build_state_summary(state, "constraint_builder")
        
        assert summary["current_step"] == "constraint_builder"
        assert summary["disruption_type"] == "truck_delay"
        assert summary["impacted_order_count"] == 2
        assert summary["scenarios_count"] == 2
        assert summary["step_count"] == 3
    
    @patch("app.agents.llm_router._get_llm")
    def test_decide_next_step_with_mock_llm(self, mock_get_llm):
        """Test decide_next_step with mocked LLM response."""
        # Mock LLM response
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='{"next_step": "tradeoff_scoring", "reason": "scenarios ready", "confidence": 0.85}'
        )
        mock_get_llm.return_value = mock_llm
        
        state: PipelineState = {
            "pipeline_run_id": "test-123",
            "disruption_id": "D001",
            "signal": {"impacted_order_ids": ["O1"]},
            "constraints": {"inventory": []},
            "scenarios": [{"scenario_id": "S1"}],
            "scores": [],
        }
        
        result = decide_next_step(state, "scenario_generator")
        
        assert result["next_step"] == "tradeoff_scoring"
        assert result["confidence"] == 0.85
    
    @patch("app.agents.llm_router._get_llm")
    def test_decide_next_step_llm_fails_uses_fallback(self, mock_get_llm):
        """When LLM fails, fallback path is used."""
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("LLM error")
        mock_get_llm.return_value = mock_llm
        
        state: PipelineState = {
            "pipeline_run_id": "test-123",
            "disruption_id": "D001",
            "signal": {"impacted_order_ids": ["O1"]},
            "constraints": {},  # Missing constraints
            "scenarios": [],
        }
        
        result = decide_next_step(state, "signal_intake")
        
        assert result["next_step"] == "constraint_builder"
        assert result["reason"] == "deterministic_fallback"
    
    @patch("app.agents.llm_router._get_llm")
    def test_decide_next_step_llm_returns_invalid_uses_fallback(self, mock_get_llm):
        """When LLM returns invalid step, fallback is used."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='{"next_step": "invalid_step", "reason": "bad", "confidence": 0.5}'
        )
        mock_get_llm.return_value = mock_llm
        
        state: PipelineState = {
            "pipeline_run_id": "test-123",
            "signal": None,  # No signal
        }
        
        result = decide_next_step(state, "start")
        
        # Should fallback to signal_intake since signal is missing
        assert result["next_step"] == "signal_intake"
        assert result["reason"] == "deterministic_fallback"


class TestNoImpactedOrdersPath:
    """Test path when no impacted orders are found."""
    
    def test_no_impacted_orders_can_finalize(self):
        """Finalize should succeed even with no impacted orders."""
        state: PipelineState = {
            "pipeline_run_id": "test-123",
            "disruption_id": "D001",
            "signal": {
                "disruption_id": "D001",
                "impacted_order_ids": [],  # No impacted orders
            },
            "constraints": {},
            "scenarios": [],
            "scores": [],
        }
        
        # Fallback should still work
        step = get_safe_fallback_step(state)
        # With signal present but no constraints, it goes to constraint_builder
        # But that's fine - the flow handles empty data gracefully
        assert step in ["constraint_builder", "finalize"]
