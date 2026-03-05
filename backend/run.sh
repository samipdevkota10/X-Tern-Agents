#!/usr/bin/env bash
cd "$(dirname "$0")"
PYTHONPATH=$(pwd) uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
