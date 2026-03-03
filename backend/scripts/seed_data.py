"""
Synthetic data seed script for disruption response planner.
Generates deterministic test data using a fixed random seed.
"""
import json
import random
import uuid
from datetime import datetime, timedelta, timezone

from app.db.base import Base
from app.db.models import (
    Capacity,
    Disruption,
    InboundShipment,
    Inventory,
    Order,
    OrderLine,
    Substitution,
)
from app.db.session import engine, SessionLocal

# Set deterministic seed for reproducibility
random.seed(42)


def generate_uuid_deterministic() -> str:
    """Generate deterministic UUID based on random state."""
    return str(uuid.UUID(int=random.getrandbits(128)))


def main() -> None:
    """
    Drop and recreate all tables, then populate with synthetic data.
    """
    print("=== Starting Seed Data Generation ===\n")
    
    # Drop and recreate all tables
    print("Dropping and recreating tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created\n")
    
    db = SessionLocal()
    
    try:
        # Generate SKUs
        print("Generating SKUs...")
        skus = [f"SKU{i:04d}" for i in range(1, 201)]
        print(f"✓ Generated {len(skus)} SKUs\n")
        
        # Generate inventory for both DCs
        print("Generating inventory...")
        inventory_records = []
        for sku in skus:
            for dc in ["DC1", "DC2"]:
                on_hand = random.randint(0, 200)
                reserved = random.randint(0, min(50, on_hand))
                inventory_records.append(
                    Inventory(
                        inv_id=generate_uuid_deterministic(),
                        dc=dc,
                        sku=sku,
                        on_hand=on_hand,
                        reserved=reserved,
                    )
                )
        db.add_all(inventory_records)
        print(f"✓ Created {len(inventory_records)} inventory records\n")
        
        # Generate orders with lines
        print("Generating orders...")
        now = datetime.now(timezone.utc)
        orders = []
        order_lines = []
        
        for i in range(120):
            # Generate promised ship time within next 12 hours
            promised_ship_time = now + timedelta(hours=random.uniform(0, 12))
            
            # Determine cutoff time (2pm or 6pm today)
            cutoff_hour = random.choice([14, 18])
            cutoff_time = now.replace(hour=cutoff_hour, minute=0, second=0, microsecond=0)
            
            # Priority distribution
            priority_choice = random.random()
            if priority_choice < 0.7:
                priority = "standard"
            elif priority_choice < 0.9:
                priority = "expedited"
            else:
                priority = "vip"
            
            # DC distribution
            dc = "DC1" if random.random() < 0.8 else "DC2"
            
            order = Order(
                order_id=f"ORD{i+1:04d}",
                priority=priority,
                promised_ship_time=promised_ship_time,
                cutoff_time=cutoff_time,
                dc=dc,
                status="open",
            )
            orders.append(order)
            
            # Generate 2-7 lines per order
            num_lines = random.randint(2, 7)
            for _ in range(num_lines):
                order_lines.append(
                    OrderLine(
                        line_id=generate_uuid_deterministic(),
                        order_id=order.order_id,
                        sku=random.choice(skus),
                        qty=random.randint(1, 5),
                    )
                )
        
        db.add_all(orders)
        db.add_all(order_lines)
        print(f"✓ Created {len(orders)} orders with {len(order_lines)} order lines\n")
        
        # Generate substitutions
        print("Generating substitutions...")
        substitutions = []
        selected_skus = random.sample(skus, 40)
        for sku in selected_skus:
            # Find a different SKU as substitute
            substitute_sku = random.choice([s for s in skus if s != sku])
            substitutions.append(
                Substitution(
                    sub_id=generate_uuid_deterministic(),
                    sku=sku,
                    substitute_sku=substitute_sku,
                    penalty_cost=random.uniform(5.0, 30.0),
                )
            )
        db.add_all(substitutions)
        print(f"✓ Created {len(substitutions)} substitution records\n")
        
        # Generate inbound shipments
        print("Generating inbound shipments...")
        inbound_shipments = []
        for i in range(8):
            truck_id = f"T{i+1:03d}"
            eta = now + timedelta(hours=random.uniform(0, 8))
            dc = random.choice(["DC1", "DC2"])
            
            # Generate SKU list with quantities
            num_skus = random.randint(10, 25)
            sku_list = [
                {"sku": random.choice(skus), "qty": random.randint(10, 100)}
                for _ in range(num_skus)
            ]
            
            inbound_shipments.append(
                InboundShipment(
                    truck_id=truck_id,
                    eta=eta,
                    dc=dc,
                    sku_list_json=json.dumps(sku_list),
                )
            )
        db.add_all(inbound_shipments)
        print(f"✓ Created {len(inbound_shipments)} inbound shipments\n")
        
        # Generate capacity records
        print("Generating capacity...")
        capacity_records = []
        processes = ["picking", "packing", "shipping"]
        for dc in ["DC1", "DC2"]:
            for process in processes:
                capacity_records.append(
                    Capacity(
                        cap_id=generate_uuid_deterministic(),
                        dc=dc,
                        process=process,
                        capacity_per_hour=random.randint(50, 200),
                        downtime_flag=False,
                    )
                )
        db.add_all(capacity_records)
        print(f"✓ Created {len(capacity_records)} capacity records\n")
        
        # Generate disruptions
        print("Generating disruptions...")
        disruptions = []
        
        # 2 late_truck disruptions
        for i in range(2):
            truck_id = inbound_shipments[i].truck_id
            disruptions.append(
                Disruption(
                    id=generate_uuid_deterministic(),
                    type="late_truck",
                    severity=random.randint(2, 4),
                    timestamp=now - timedelta(minutes=random.randint(10, 120)),
                    details_json=json.dumps({
                        "truck_id": truck_id,
                        "delay_minutes": random.randint(60, 240),
                    }),
                    status="open",
                )
            )
        
        # 2 stockout disruptions
        for _ in range(2):
            disruptions.append(
                Disruption(
                    id=generate_uuid_deterministic(),
                    type="stockout",
                    severity=random.randint(3, 5),
                    timestamp=now - timedelta(minutes=random.randint(10, 120)),
                    details_json=json.dumps({
                        "sku": random.choice(skus),
                        "shortage_qty": random.randint(10, 50),
                        "dc": random.choice(["DC1", "DC2"]),
                    }),
                    status="open",
                )
            )
        
        # 2 machine_down disruptions
        for _ in range(2):
            disruptions.append(
                Disruption(
                    id=generate_uuid_deterministic(),
                    type="machine_down",
                    severity=random.randint(2, 5),
                    timestamp=now - timedelta(minutes=random.randint(10, 120)),
                    details_json=json.dumps({
                        "process": random.choice(processes),
                        "dc": random.choice(["DC1", "DC2"]),
                        "expected_recovery_minutes": random.randint(30, 180),
                    }),
                    status="open",
                )
            )
        
        db.add_all(disruptions)
        print(f"✓ Created {len(disruptions)} disruptions\n")
        
        # Commit all changes
        db.commit()
        
        # Print summary
        print("=== Seed Data Summary ===")
        print(f"SKUs: {len(skus)}")
        print(f"Inventory records: {len(inventory_records)}")
        print(f"Orders: {len(orders)}")
        print(f"Order lines: {len(order_lines)}")
        print(f"Substitutions: {len(substitutions)}")
        print(f"Inbound shipments: {len(inbound_shipments)}")
        print(f"Capacity records: {len(capacity_records)}")
        print(f"Disruptions: {len(disruptions)}")
        print("\n✓ Seed data generation complete!")
        
    except Exception as e:
        db.rollback()
        print(f"\n✗ Error during seed data generation: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
