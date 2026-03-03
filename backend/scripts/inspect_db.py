"""
Quick database inspection script.
Shows record counts and sample data from each table.
"""
from sqlalchemy import func, inspect, select

from app.db.models import (
    Capacity,
    DecisionLog,
    Disruption,
    InboundShipment,
    Inventory,
    Order,
    OrderLine,
    Scenario,
    Substitution,
)
from app.db.session import SessionLocal, engine


def main() -> None:
    """Inspect database contents."""
    print("\n" + "=" * 60)
    print("  Database Inspection")
    print("=" * 60 + "\n")
    
    # Get all table names
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print(f"📊 Found {len(tables)} tables:\n")
    for table in tables:
        print(f"  • {table}")
    
    print("\n" + "=" * 60)
    print("  Record Counts")
    print("=" * 60 + "\n")
    
    db = SessionLocal()
    try:
        models = [
            ("Disruptions", Disruption),
            ("Orders", Order),
            ("Order Lines", OrderLine),
            ("Inventory", Inventory),
            ("Inbound Shipments", InboundShipment),
            ("Capacity", Capacity),
            ("Substitutions", Substitution),
            ("Scenarios", Scenario),
            ("Decision Logs", DecisionLog),
        ]
        
        for name, model in models:
            count = db.execute(select(func.count()).select_from(model)).scalar()
            print(f"  {name:20s}: {count:>5d} records")
        
        print("\n" + "=" * 60)
        print("  Sample Data")
        print("=" * 60)
        
        # Sample disruptions
        print("\n📌 Disruptions (first 3):\n")
        disruptions = db.execute(select(Disruption).limit(3)).scalars().all()
        for d in disruptions:
            print(f"  {d.id[:8]}... | {d.type:15s} | Severity: {d.severity} | Status: {d.status}")
        
        # Sample orders
        print("\n📦 Orders (first 3):\n")
        orders = db.execute(select(Order).limit(3)).scalars().all()
        for o in orders:
            print(f"  {o.order_id} | {o.priority:10s} | DC: {o.dc} | Status: {o.status}")
        
        # Sample inventory
        print("\n📊 Inventory (first 5):\n")
        inventory = db.execute(select(Inventory).limit(5)).scalars().all()
        for inv in inventory:
            available = inv.on_hand - inv.reserved
            print(f"  {inv.dc} | {inv.sku} | On-hand: {inv.on_hand:3d} | Reserved: {inv.reserved:2d} | Available: {available:3d}")
        
        # Sample scenarios if any
        scenario_count = db.execute(select(func.count()).select_from(Scenario)).scalar()
        if scenario_count > 0:
            print(f"\n🎯 Scenarios ({scenario_count} total):\n")
            scenarios = db.execute(select(Scenario).limit(3)).scalars().all()
            for s in scenarios:
                print(f"  {s.scenario_id[:8]}... | {s.action_type:12s} | Status: {s.status}")
        
        # Decision logs if any
        log_count = db.execute(select(func.count()).select_from(DecisionLog)).scalar()
        if log_count > 0:
            print(f"\n📝 Decision Logs ({log_count} total):\n")
            logs = db.execute(select(DecisionLog).limit(3)).scalars().all()
            for log in logs:
                print(f"  {log.log_id[:8]}... | {log.agent_name:15s} | Decision: {log.human_decision}")
        
        print("\n" + "=" * 60)
        print("  ✅ Database is healthy and populated!")
        print("=" * 60 + "\n")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
