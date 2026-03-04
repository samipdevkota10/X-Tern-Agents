#!/usr/bin/env python
"""
MCP Smoke Test - Verify MCP server tools work correctly.

This script tests each MCP tool via the tool_router to ensure
both local and MCP modes work correctly.

Usage:
    # Test local mode
    PYTHONPATH=$(pwd) python scripts/test_mcp_smoke.py
    
    # Test MCP mode (requires MCP server running)
    USE_MCP_SERVER=1 PYTHONPATH=$(pwd) python scripts/test_mcp_smoke.py
"""
import json
import os
import sys
from datetime import datetime, timezone

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_read_open_orders():
    """Test read_open_orders tool."""
    from app.mcp.tool_router import read_open_orders
    
    print("\n[TEST] read_open_orders...")
    result = read_open_orders()
    
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    print(f"  ✓ Returned {len(result)} orders")
    
    if result:
        order = result[0]
        assert "order_id" in order, "Missing order_id"
        assert "status" in order, "Missing status"
        print(f"  ✓ First order: {order.get('order_id')}")
    
    return True


def test_read_disruption():
    """Test read_disruption tool."""
    from app.mcp.tool_router import read_disruption
    
    print("\n[TEST] read_disruption...")
    
    # Test with non-existent ID
    result = read_disruption("nonexistent-id")
    assert "error" in result or result.get("id") is not None
    print(f"  ✓ Non-existent ID handled correctly")
    
    # Try to find an existing disruption
    try:
        from app.db.session import SessionLocal
        from app.db.models import Disruption
        
        db = SessionLocal()
        disruption = db.query(Disruption).first()
        db.close()
        
        if disruption:
            result = read_disruption(disruption.id)
            assert result.get("id") == disruption.id
            print(f"  ✓ Found disruption: {disruption.id}")
    except Exception as e:
        print(f"  ⚠ Could not query DB: {e}")
    
    return True


def test_read_inventory():
    """Test read_inventory tool."""
    from app.mcp.tool_router import read_inventory
    
    print("\n[TEST] read_inventory...")
    
    result = read_inventory("DC1", "SKU001")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "dc" in result or "error" in result
    print(f"  ✓ Result: {json.dumps(result)[:100]}")
    
    return True


def test_read_capacity():
    """Test read_capacity tool."""
    from app.mcp.tool_router import read_capacity
    
    print("\n[TEST] read_capacity...")
    
    result = read_capacity("picking")
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    print(f"  ✓ Returned {len(result)} capacity records")
    
    return True


def test_read_substitutions():
    """Test read_substitutions tool."""
    from app.mcp.tool_router import read_substitutions
    
    print("\n[TEST] read_substitutions...")
    
    result = read_substitutions(["SKU001", "SKU002"])
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    print(f"  ✓ Returned {len(result)} substitution records")
    
    return True


def test_write_decision_log():
    """Test write_decision_log tool."""
    from app.mcp.tool_router import write_decision_log
    
    print("\n[TEST] write_decision_log...")
    
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_run_id": "test-pipeline-run-id",
        "agent_name": "TestAgent",
        "input_summary": "Test input",
        "output_summary": "Test output",
        "confidence_score": 0.9,
        "rationale": "Testing MCP smoke test",
        "human_decision": "pending",
    }
    
    result = write_decision_log(entry)
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    
    if result.get("ok"):
        print(f"  ✓ Created log: {result.get('log_id')}")
    else:
        print(f"  ⚠ Write failed: {result.get('error')}")
    
    return True


def main():
    """Run all smoke tests."""
    mode = "MCP" if os.getenv("USE_MCP_SERVER") == "1" else "LOCAL"
    print(f"=" * 60)
    print(f"MCP Smoke Test - Mode: {mode}")
    print(f"=" * 60)
    
    tests = [
        test_read_open_orders,
        test_read_disruption,
        test_read_inventory,
        test_read_capacity,
        test_read_substitutions,
        test_write_decision_log,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1
    
    print(f"\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print(f"=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
