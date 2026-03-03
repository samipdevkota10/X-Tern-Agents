# Quick Start - Milestone 1

## Environment setup (recommended)

From the **repository root** (`X-Tern-Agents/`), create and activate the conda environment so backend and frontend share the same Python/Node setup:

```bash
# From X-Tern-Agents/
conda env create -f environment.yml
conda activate xtern-agents
# Or with mamba: mamba env create -f environment.yml && mamba activate xtern-agents
```

Then `cd backend` and use the commands below. If you prefer a local venv, use the pip option instead.

## 🚀 Get Started in 3 Commands

```bash
# From backend/
# 1. Install dependencies (skip if using conda env from environment.yml)
pip install -r requirements.txt

# 2. Generate seed data
PYTHONPATH=$(pwd) python scripts/seed_data.py

# 3. Run tests
PYTHONPATH=$(pwd) python scripts/quick_tool_test.py
```

## ⚡ One-Command Test

```bash
./run_milestone1.sh --reseed
```

## 📊 Database Stats

After seeding, you'll have:
- **9 tables** with proper relationships
- **1,157 total records** across all tables
- **220 KB** SQLite database file

## 🛠️ Common Tasks

### Check Database Health
```bash
PYTHONPATH=$(pwd) python scripts/inspect_db.py
```

### Re-seed Database (Fresh Start)
```bash
rm warehouse.db
PYTHONPATH=$(pwd) python scripts/seed_data.py
```

### Run Individual Tool Tests
```python
from app.mcp.tools import read_open_orders, read_inventory

# Get open orders
orders = read_open_orders.invoke({})
print(f"Found {len(orders)} orders")

# Check inventory
inv = read_inventory.invoke({"dc": "DC1", "sku": "SKU0001"})
print(f"Available: {inv['available']}")
```

## 🔍 Verify Installation

**Expected output from seed script:**
```
✓ Tables created
✓ Generated 200 SKUs
✓ Created 400 inventory records
✓ Created 120 orders with 572 order lines
✓ Created 40 substitution records
✓ Created 8 inbound shipments
✓ Created 6 capacity records
✓ Created 6 disruptions
✓ Seed data generation complete!
```

**Expected output from test script:**
```
✓ Found 120 open orders
✓ Inventory check for SKU0055 at DC1
✓ Inbound status for T001
✓ Capacity for 'packing' process
✓ Created 2 scenarios
✓ Found 2 pending scenarios
✓ Approval result: True
✓ Rejection result: True
✓ Write decision log result: True
✓ Total decision logs in database: 3
✅ All Tests Complete
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `app/db/models.py` | 9 ORM models |
| `app/db/session.py` | DB session factory |
| `app/mcp/tools.py` | 9 LangChain tools |
| `scripts/seed_data.py` | Data generator |
| `scripts/quick_tool_test.py` | Tool validator |
| `warehouse.db` | SQLite database |

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'app'"
**Solution:** Set PYTHONPATH
```bash
export PYTHONPATH=/path/to/backend
# Or prefix each command:
PYTHONPATH=$(pwd) python scripts/seed_data.py
```

### "No such file or directory: warehouse.db"
**Solution:** Run seed script first
```bash
PYTHONPATH=$(pwd) python scripts/seed_data.py
```

### Import errors with langchain
**Solution:** Install langchain-core
```bash
pip install langchain-core
```

## 💡 Pro Tips

1. **Use the runner script** for convenience:
   ```bash
   ./run_milestone1.sh
   ```

2. **Inspect DB anytime** without breaking anything:
   ```bash
   PYTHONPATH=$(pwd) python scripts/inspect_db.py
   ```

3. **Fresh start** when testing:
   ```bash
   rm warehouse.db && ./run_milestone1.sh
   ```

4. **Check data integrity**:
   ```bash
   sqlite3 warehouse.db "SELECT COUNT(*) FROM orders;"
   # Should return: 120
   ```

## 📚 Learn More

- **Full Documentation:** `MILESTONE_1_README.md`
- **Architecture:** `STRUCTURE.md`
- **Completion Report:** `../MILESTONE_1_COMPLETE.md`

## ✅ Success Checklist

- [ ] Environment ready (conda env from `../environment.yml` **or** `pip install -r requirements.txt`)
- [ ] Seed script runs without errors
- [ ] Test script shows all tools passing
- [ ] `warehouse.db` file exists (~220 KB)
- [ ] Inspect script shows 1,157 total records
- [ ] No deprecation warnings
- [ ] Exit codes are 0 (success)

---

**Status:** ✅ Ready for Development  
**Next:** Build LangGraph agents (Milestone 2)
