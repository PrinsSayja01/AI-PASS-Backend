#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

# require ACCESS + DEVICE from environment
if [[ -z "${ACCESS:-}" || -z "${DEVICE:-}" ]]; then
  echo "❌ Missing ACCESS/DEVICE env. Run: source scripts/auth_env.sh"
  exit 1
fi

echo "✅ Running battle tests..."
BASE_URL="$BASE_URL" ACCESS="$ACCESS" DEVICE="$DEVICE" python3 tests/battle/run_battle.py
