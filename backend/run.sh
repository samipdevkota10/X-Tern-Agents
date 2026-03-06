#!/usr/bin/env bash
cd "$(dirname "$0")"
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi
PYTHONPATH=$(pwd) uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
