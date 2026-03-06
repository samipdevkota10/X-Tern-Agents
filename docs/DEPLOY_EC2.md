# Deploy Backend on EC2

Step-by-step guide to run the X-Tern Agents backend on an Amazon EC2 instance.

---

## 1. Launch EC2 Instance

1. **AWS Console** → EC2 → Launch Instance
2. **Name:** `xtern-backend` (or your choice)
3. **AMI:** Ubuntu 22.04 LTS or Amazon Linux 2023
4. **Instance type:** `t3.medium` (2 vCPU, 4 GB RAM) — minimum for ChromaDB + embeddings
5. **Key pair:** Create or select an existing key for SSH
6. **Storage:** 20–30 GB
7. **Security group:** Allow inbound:
   - 22 (SSH)
   - 8000 (API)

---

## 2. SSH into the Instance

```bash
ssh -i your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

---

## 3. Install Prerequisites (One-Time)

```bash
sudo apt update && sudo apt upgrade -y
# Ubuntu 22.04: use python3.11 (or python3.10 works)
sudo apt install -y python3.11 python3.11-venv python3-pip git curl
# If python3.11 not found, try: sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt update
# Or use system Python: sudo apt install -y python3 python3-venv python3-pip git curl
```

---

## 4. Clone the Repository

```bash
cd ~
git clone https://github.com/samipdevkota10/X-Tern-Agents.git
cd X-Tern-Agents
```

---

## 5. Run the Deployment Script

```bash
chmod +x infra/ec2/deploy_backend.sh
./infra/ec2/deploy_backend.sh
```

**Optional:** set your EC2 public IP to auto-configure CORS for the frontend:

```bash
EC2_PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
export EC2_PUBLIC_IP
./infra/ec2/deploy_backend.sh
```

---

## 6. Configure Environment (If Needed)

Edit `backend/.env` for production:

```bash
nano ~/X-Tern-Agents/backend/.env
```

Important variables:

| Variable | Example | Notes |
|----------|---------|-------|
| `JWT_SECRET` | Strong random string (32+ chars) | Required for auth |
| `DATABASE_URL` | `sqlite:///./warehouse.db` | Or RDS Postgres URL |
| `USE_MCP_SERVER` | `0` | Recommended on EC2 (simpler) |
| `USE_AWS` | `0` or `1` | `1` for Bedrock/DynamoDB/S3 |
| `CORS_ORIGINS_EXTRA` | `http://YOUR_IP:3000,https://your-domain.com` | Frontend origins |

After editing:

```bash
sudo systemctl restart xtern-backend
```

---

## 7. Verify

- **Health:** `curl http://localhost:8000/health`
- **API docs:** `http://YOUR_EC2_PUBLIC_IP:8000/api/docs`
- **Login:** `manager_01` / `password` (from seed)

---

## 8. Useful Commands

```bash
# Restart backend
sudo systemctl restart xtern-backend

# View logs
sudo journalctl -u xtern-backend -f

# Stop backend
sudo systemctl stop xtern-backend

# Manual run (for debugging)
cd ~/X-Tern-Agents/backend && source .venv/bin/activate && PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 9. Re-deploy After Code Changes

```bash
cd ~/X-Tern-Agents
git pull
./infra/ec2/deploy_backend.sh
```

---

## 10. Optional: PostgreSQL (RDS)

For production, use RDS instead of SQLite:

1. Create an RDS PostgreSQL instance
2. Ensure the EC2 security group can reach RDS
3. Set in `.env`:
   ```bash
   DATABASE_URL=postgresql://user:password@your-rds-endpoint:5432/warehouse
   ```
4. Restart: `sudo systemctl restart xtern-backend`
5. Seed: `cd backend && PYTHONPATH=. python scripts/seed_data.py`
