#!/usr/bin/env python
"""
Comprehensive tests for new LLM-native architecture modules.
"""
import sys
sys.path.insert(0, "/Users/samipdevkota/Desktop/X-Tern Agents/backend")

def test_enhanced_scoring():
    """Test EnhancedScorer module."""
    print("=== Testing EnhancedScorer ===")
    
    from app.agents.enhanced_scoring import (
        EnhancedScorer,
        ScoreFactors,
        RiskTolerance,
        estimate_factors_for_action,
    )
    
    # Test 1: Basic scoring
    scorer = EnhancedScorer(risk_tolerance=RiskTolerance.BALANCED)
    factors = ScoreFactors(
        sla_risk=0.3,
        cost_impact_usd=150.0,
        labor_minutes=45,
        complexity=3,
        reversibility=0.6,
        customer_impact=0.2,
        time_pressure=0.4
    )
    result = scorer.score(factors)
    print(f"✓ Basic score: {result.overall_score:.2f}, confidence: {result.confidence:.2f}")
    print(f"  CI: [{result.score_lower_bound:.2f}, {result.score_upper_bound:.2f}]")
    print(f"  Risk-adjusted: {result.risk_adjusted_score:.2f}")
    print(f"  Needs approval: {result.needs_approval}")
    assert 0 <= result.overall_score <= 1.0
    assert 0 <= result.confidence <= 1.0
    
    # Test 2: Risk tolerance variations
    print("\n  Risk tolerance comparison:")
    for risk in [RiskTolerance.CONSERVATIVE, RiskTolerance.BALANCED, RiskTolerance.AGGRESSIVE]:
        s = EnhancedScorer(risk_tolerance=risk)
        r = s.score(factors)
        print(f"  ✓ {risk.value}: overall={r.overall_score:.2f}, risk_adj={r.risk_adjusted_score:.2f}")
        assert r.risk_adjusted_score is not None
    
    # Test 3: estimate_factors_for_action
    print("\n  Action factor estimation:")
    test_order = {"order_id": "ord-1", "priority": "standard", "lines": [{"sku": "SKU-A"}]}
    test_disruption = {"type": "capacity_shortage", "severity": 3}
    test_constraints = {}
    for action in ["delay", "reroute", "substitute", "expedite", "split"]:
        factors_est = estimate_factors_for_action(
            action_type=action,
            order=test_order,
            disruption=test_disruption,
            constraints=test_constraints
        )
        print(f"  ✓ {action}: cost=${factors_est.cost_impact_usd:.0f}, sla_risk={factors_est.sla_risk:.2f}, complexity={factors_est.complexity}")
    
    # Test 4: LLM score validation
    print("\n  LLM validation tests:")
    llm_score = {
        "overall_score": 0.45,
        "cost_impact_usd": 500.0,
        "sla_risk": 0.25,
        "complexity": 3,
        "needs_approval": False
    }
    validated = scorer.validate_llm_score(llm_score, factors)
    print(f"  ✓ LLM validation: overall={validated.overall_score:.2f}, confidence={validated.confidence:.2f}")
    print(f"  ✓ LLM calibrated: {validated.llm_calibrated}")
    assert validated.overall_score >= 0 and validated.overall_score <= 1.0
    
    # Test 5: High-risk scenario
    high_risk_factors = ScoreFactors(
        sla_risk=0.85,
        cost_impact_usd=2000.0,
        labor_minutes=180,
        complexity=5,
        reversibility=0.1,
        customer_impact=0.8,
        time_pressure=0.9
    )
    high_risk_result = scorer.score(high_risk_factors)
    print(f"\n  ✓ High-risk scenario: needs_approval={high_risk_result.needs_approval}")
    assert high_risk_result.needs_approval == True
    
    print("\n✅ All EnhancedScorer tests passed!")


def test_scenario_validator():
    """Test ScenarioValidator module."""
    print("\n=== Testing ScenarioValidator ===")
    
    from app.agents.scenario_validator import get_validator, ValidationSeverity
    
    validator = get_validator()
    
    # Test 1: Valid scenario
    valid_scenario = {
        "scenario_id": "test-001",
        "disruption_id": "dis-001",
        "order_id": "ord-001",
        "action_type": "reroute",
        "plan_json": {
            "summary": "Reroute to DC-WEST",
            "what_happened": "DC-EAST capacity exceeded",
            "what_to_do": "Ship from DC-WEST",
        },
        "score_json": {
            "cost_impact_usd": 150.0,
            "sla_risk": 0.2,
            "complexity": 3,
        },
    }
    order = {
        "order_id": "ord-001",
        "priority": "standard",
        "lines": [{"sku": "SKU-A", "qty": 5}],
    }
    constraints = {
        "available_inventory": [{"sku": "SKU-A", "qty": 10, "dc": "DC-WEST"}],
        "substitution_rules": [],
    }
    
    result = validator.validate(valid_scenario, order, constraints)
    print(f"✓ Valid scenario: is_valid={result.is_valid}, issues={len(result.issues)}")
    assert result.is_valid
    
    # Test 2: Invalid action type
    invalid_action = {**valid_scenario, "action_type": "teleport"}
    result = validator.validate(invalid_action, order, constraints)
    print(f"✓ Invalid action type: is_valid={result.is_valid}, issues={len(result.issues)}")
    assert not result.is_valid
    assert any("action_type" in str(i) for i in result.issues)
    
    # Test 3: Out-of-bounds cost
    high_cost = {
        **valid_scenario,
        "score_json": {**valid_scenario["score_json"], "cost_impact_usd": 999999.0},
    }
    result = validator.validate(high_cost, order, constraints)
    print(f"✓ Out-of-bounds cost: has_warnings={result.has_warnings}")
    
    # Test 4: Invalid SLA risk
    bad_sla = {
        **valid_scenario,
        "score_json": {**valid_scenario["score_json"], "sla_risk": 1.5},
    }
    result = validator.validate(bad_sla, order, constraints)
    print(f"✓ Invalid SLA risk: is_valid={result.is_valid}, issues={len(result.issues)}")
    assert len(result.issues) > 0  # Should flag out-of-bounds SLA risk
    
    # Test 5: Batch validation
    scenarios = [valid_scenario, invalid_action]
    valid, results = validator.validate_batch(scenarios, {"ord-001": order}, constraints)
    print(f"✓ Batch validation: {len(valid)} valid out of {len(scenarios)}")
    assert len(valid) == 1
    
    # Test 6: Auto-correction
    correctable = {
        **valid_scenario,
        "score_json": {**valid_scenario["score_json"], "sla_risk": -0.1},
    }
    valid, results = validator.validate_batch([correctable], {"ord-001": order}, constraints, auto_correct=True)
    print(f"✓ Auto-correction: corrected={len(valid)}")
    if valid:
        corrected_risk = valid[0].get("score_json", {}).get("sla_risk", -1)
        print(f"  Corrected sla_risk from -0.1 to {corrected_risk}")
        assert corrected_risk >= 0
    
    print("\n✅ All ScenarioValidator tests passed!")


def test_agent_integration():
    """Test agent node imports and basic structure."""
    print("\n=== Testing Agent Integration ===")
    
    # Test imports
    try:
        from app.agents.scenario_generator_agent import (
            scenario_generator_node,
            _get_rag_context_for_scenario_gen,
            _generate_seed_scenarios,
            _build_enhanced_llm_prompt,
        )
        print("✓ scenario_generator_agent imports OK")
    except ImportError as e:
        print(f"✗ scenario_generator_agent import failed: {e}")
        raise
    
    try:
        from app.agents.tradeoff_scoring_agent import (
            tradeoff_scoring_node,
            _get_rag_context_for_scoring,
            _determine_risk_tolerance,
            _build_enhanced_scoring_prompt,
        )
        print("✓ tradeoff_scoring_agent imports OK")
    except ImportError as e:
        print(f"✗ tradeoff_scoring_agent import failed: {e}")
        raise
    
    # Test risk tolerance determination
    from app.agents.tradeoff_scoring_agent import _determine_risk_tolerance
    from app.agents.enhanced_scoring import RiskTolerance
    
    # High severity should be conservative
    signal_high = {"severity": 5}
    risk = _determine_risk_tolerance(signal_high, {})
    print(f"✓ High severity (5): {risk.value}")
    assert risk == RiskTolerance.CONSERVATIVE
    
    # Low severity should be aggressive
    signal_low = {"severity": 2}
    risk = _determine_risk_tolerance(signal_low, {})
    print(f"✓ Low severity (2): {risk.value}")
    assert risk == RiskTolerance.AGGRESSIVE
    
    # Critical order should be conservative regardless of severity
    signal_med = {"severity": 3}
    orders = {"ord-1": {"order_id": "ord-1", "priority": "critical"}}
    risk = _determine_risk_tolerance(signal_med, orders)
    print(f"✓ Critical order: {risk.value}")
    assert risk == RiskTolerance.CONSERVATIVE
    
    print("\n✅ All Agent Integration tests passed!")


def test_seed_scenario_generation():
    """Test seed scenario generation from rules."""
    print("\n=== Testing Seed Scenario Generation ===")
    
    from app.agents.scenario_generator_agent import _generate_seed_scenarios
    
    orders = [
        {
            "order_id": "ord-001",
            "priority": "standard",
            "dc": "DC-EAST",
            "promised_ship_time": "2026-03-06T10:00:00Z",
            "cutoff_time": "2026-03-06T08:00:00Z",
            "lines": [{"sku": "SKU-A", "qty": 5}],
        },
        {
            "order_id": "ord-002",
            "priority": "expedite",
            "dc": "DC-EAST",
            "promised_ship_time": "2026-03-05T14:00:00Z",
            "cutoff_time": "2026-03-05T12:00:00Z",
            "lines": [{"sku": "SKU-B", "qty": 3}],
        },
    ]
    disruption = {
        "id": "dis-001",
        "type": "capacity_shortage",
        "severity": 3,
        "details": {"affected_dc": "DC-EAST"},
    }
    constraints = {
        "available_inventory": [],
        "substitution_rules": [],
    }
    
    seeds = _generate_seed_scenarios(orders, disruption, constraints)
    print(f"✓ Generated {len(seeds)} seed scenarios for {len(orders)} orders")
    
    # Should have at least one scenario per order
    assert len(seeds) >= len(orders)
    
    # Verify structure
    for seed in seeds[:3]:
        assert "action_type" in seed
        assert "order_id" in seed
        print(f"  - {seed['order_id']}: {seed['action_type']}")
    
    print("\n✅ Seed scenario generation tests passed!")


def test_enhanced_llm_prompt():
    """Test enhanced prompt building."""
    print("\n=== Testing Enhanced LLM Prompt ===")
    
    from app.agents.scenario_generator_agent import _build_enhanced_llm_prompt
    
    disruption = {
        "id": "dis-001",
        "type": "weather_delay",
        "severity": 4,
        "details": {"location": "Northeast", "duration_hours": 24},
    }
    orders = [
        {
            "order_id": "ord-001",
            "priority": "critical",
            "dc": "DC-EAST",
            "promised_ship_time": "2026-03-06T10:00:00Z",
            "lines": [{"sku": "SKU-A", "qty": 5}],
        },
    ]
    constraints = {
        "available_inventory": [{"sku": "SKU-A", "qty": 100, "dc": "DC-WEST"}],
        "substitution_rules": [],
        "capacity": "normal",
    }
    rag_context = {
        "rag_available": True,
        "similar_disruptions": [
            {"content": "Weather delay in Northeast Dec 2025 - rerouted 80% orders successfully"}
        ],
        "relevant_decisions": [
            {"content": "Approved: Expedite shipping for critical orders during weather delays"}
        ],
        "domain_knowledge": [
            {"content": "Policy: Never exceed 2-day delay for critical priority orders"}
        ],
    }
    seed_scenarios = [
        {"action_type": "reroute", "plan_json": {"summary": "Ship from DC-WEST"}},
        {"action_type": "delay", "plan_json": {"summary": "Wait 24h for weather to clear"}},
    ]
    
    prompt = _build_enhanced_llm_prompt(disruption, orders, constraints, rag_context, seed_scenarios)
    
    print(f"✓ Generated prompt ({len(prompt)} chars)")
    
    # Check key sections are present
    assert "DISRUPTION EVENT" in prompt
    assert "weather_delay" in prompt
    assert "IMPACTED ORDERS" in prompt
    assert "ord-001" in prompt
    assert "HISTORICAL CONTEXT" in prompt
    assert "BASELINE OPTIONS" in prompt
    
    print("✓ All required sections present in prompt")
    print("\n  Prompt preview (first 500 chars):")
    print("  " + prompt[:500].replace("\n", "\n  ") + "...")
    
    print("\n✅ Enhanced prompt tests passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("COMPREHENSIVE TEST SUITE FOR LLM-NATIVE ARCHITECTURE")
    print("=" * 60)
    
    try:
        test_enhanced_scoring()
        test_scenario_validator()
        test_agent_integration()
        test_seed_scenario_generation()
        test_enhanced_llm_prompt()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
