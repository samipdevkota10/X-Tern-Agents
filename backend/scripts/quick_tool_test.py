"""
Quick test script for MCP tools.
Tests all tool functions to ensure they work correctly.
"""
import random
import sys
from datetime import datetime

from sqlalchemy import select

from app.db.models import DecisionLog, InboundShipment, Order
from app.db.session import SessionLocal
from app.mcp.tools import (
    approve_scenario,
    get_pending_scenarios,
    read_capacity,
    read_inbound_status,
    read_inventory,
    read_open_orders,
    reject_scenario,
    write_decision_log,
    write_scenarios,
)


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def main() -> None:
    """Run all MCP tool tests."""
    print("\n🧪 Starting MCP Tools Quick Test\n")
    
    try:
        # Test 1: Read open orders
        print_section("Test 1: Read Open Orders")
        orders = read_open_orders.invoke({})
        print(f"✓ Found {len(orders)} open orders")
        if orders:
            first_order = orders[0]
            print(f"\nFirst order: {first_order['order_id']}")
            print(f"  Priority: {first_order['priority']}")
            print(f"  DC: {first_order['dc']}")
            print(f"  Lines: {len(first_order['lines'])}")
            if first_order['lines']:
                print(f"  First line: {first_order['lines'][0]}")
        
        # Test 2: Read inventory
        print_section("Test 2: Read Inventory")
        # Get a random SKU from the first order
        if orders and orders[0]['lines']:
            test_sku = orders[0]['lines'][0]['sku']
            test_dc = orders[0]['dc']
        else:
            test_sku = "SKU0001"
            test_dc = "DC1"
        
        inventory = read_inventory.invoke({"dc": test_dc, "sku": test_sku})
        print(f"✓ Inventory check for {test_sku} at {test_dc}:")
        print(f"  On hand: {inventory.get('on_hand', 0)}")
        print(f"  Reserved: {inventory.get('reserved', 0)}")
        print(f"  Available: {inventory.get('available', 0)}")
        
        # Test 3: Read inbound status
        print_section("Test 3: Read Inbound Status")
        # Get first truck from DB
        db = SessionLocal()
        first_truck = db.execute(select(InboundShipment)).scalar()
        db.close()
        
        if first_truck:
            truck_status = read_inbound_status.invoke({"truck_id": first_truck.truck_id})
            print(f"✓ Inbound status for {truck_status.get('truck_id')}:")
            print(f"  ETA: {truck_status.get('eta')}")
            print(f"  DC: {truck_status.get('dc')}")
            sku_list = truck_status.get('sku_list', [])
            if isinstance(sku_list, list):
                print(f"  SKUs: {len(sku_list)} items")
                if sku_list:
                    print(f"  First item: {sku_list[0]}")
        
        # Test 4: Read capacity
        print_section("Test 4: Read Capacity")
        capacity = read_capacity.invoke({"process": "packing"})
        print(f"✓ Capacity for 'packing' process:")
        for cap in capacity:
            print(f"  {cap['dc']}: {cap['capacity_per_hour']} units/hour (downtime: {cap['downtime_flag']})")
        
        # Test 5: Write scenarios
        print_section("Test 5: Write Scenarios")
        # Get disruption and order IDs for test scenarios
        db = SessionLocal()
        from app.db.models import Disruption
        disruptions = db.execute(select(Disruption)).scalars().all()
        test_orders = db.execute(select(Order).limit(2)).scalars().all()
        db.close()
        
        if disruptions and test_orders:
            test_scenarios = [
                {
                    "disruption_id": disruptions[0].id,
                    "order_id": test_orders[0].order_id,
                    "action_type": "delay",
                    "plan_json": {
                        "action": "delay_order",
                        "delay_hours": 2,
                        "reason": "Waiting for inbound shipment"
                    },
                    "score_json": {
                        "cost_impact": 50.0,
                        "service_impact": 0.3,
                        "overall_score": 7.5
                    },
                    "status": "pending"
                },
                {
                    "disruption_id": disruptions[1].id if len(disruptions) > 1 else disruptions[0].id,
                    "order_id": test_orders[1].order_id if len(test_orders) > 1 else test_orders[0].order_id,
                    "action_type": "reroute",
                    "plan_json": {
                        "action": "reroute_to_dc",
                        "target_dc": "DC2",
                        "reason": "DC1 capacity constraint"
                    },
                    "score_json": {
                        "cost_impact": 120.0,
                        "service_impact": 0.5,
                        "overall_score": 6.8
                    },
                    "status": "pending"
                }
            ]
            
            result = write_scenarios.invoke({"scenarios": test_scenarios})
            print(f"✓ Created {result.get('created', 0)} scenarios")
        
        # Test 6: Get pending scenarios
        print_section("Test 6: Get Pending Scenarios")
        pending = get_pending_scenarios.invoke({})
        print(f"✓ Found {len(pending)} pending scenarios")
        if pending:
            print(f"\nFirst pending scenario: {pending[0]['scenario_id']}")
            print(f"  Action type: {pending[0]['action_type']}")
            print(f"  Disruption type: {pending[0]['disruption']['type']}")
            print(f"  Order: {pending[0]['order']['order_id']}")
        
        # Test 7: Approve a scenario
        print_section("Test 7: Approve Scenario")
        if pending:
            scenario_to_approve = pending[0]['scenario_id']
            approval_result = approve_scenario.invoke({
                "scenario_id": scenario_to_approve,
                "approver": "test_user_001",
                "note": "Approved during automated testing - looks reasonable"
            })
            print(f"✓ Approval result: {approval_result.get('success', False)}")
            if approval_result.get('success'):
                print(f"  Scenario: {approval_result['scenario_id']}")
                print(f"  Status: {approval_result['status']}")
                print(f"  Log ID: {approval_result['log_id']}")
        
        # Test 8: Reject a scenario
        print_section("Test 8: Reject Scenario")
        if len(pending) > 1:
            scenario_to_reject = pending[1]['scenario_id']
            rejection_result = reject_scenario.invoke({
                "scenario_id": scenario_to_reject,
                "approver": "test_user_002",
                "note": "Rejected during automated testing - cost too high"
            })
            print(f"✓ Rejection result: {rejection_result.get('success', False)}")
            if rejection_result.get('success'):
                print(f"  Scenario: {rejection_result['scenario_id']}")
                print(f"  Status: {rejection_result['status']}")
                print(f"  Log ID: {rejection_result['log_id']}")
        
        # Test 9: Write decision log
        print_section("Test 9: Write Decision Log")
        import uuid
        from datetime import timezone
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pipeline_run_id": str(uuid.uuid4()),
            "agent_name": "TestAgent",
            "input_summary": "Test input for decision logging",
            "output_summary": "Test output from decision logging",
            "confidence_score": 0.85,
            "rationale": "This is a test entry created during tool validation",
            "human_decision": "pending",
            "approver_id": None,
            "approver_note": None,
            "override_value": None
        }
        
        log_result = write_decision_log.invoke({"entry": log_entry})
        print(f"✓ Write decision log result: {log_result.get('ok', False)}")
        if log_result.get('ok'):
            print(f"  Log ID: {log_result['log_id']}")
        
        # Test 10: Query decision logs count
        print_section("Test 10: Decision Logs Count")
        db = SessionLocal()
        decision_log_count = db.execute(select(DecisionLog)).scalars().all()
        db.close()
        print(f"✓ Total decision logs in database: {len(decision_log_count)}")
        
        # Final summary
        print_section("✅ All Tests Complete")
        print("All MCP tools executed successfully!")
        print("\nYou can now:")
        print("  - Use these tools in LangChain agents")
        print("  - Build FastAPI routes that call these tools")
        print("  - Integrate with LangGraph for multi-agent workflows\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
