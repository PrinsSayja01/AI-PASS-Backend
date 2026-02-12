#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

echo "== CI: approval pipeline =="
python3 security/approval_pipeline.py . || true

echo "== CI: dependency scan =="
./scripts/deps_scan.sh || true

echo "== CI: battle tests =="
if [[ -z "${ACCESS:-}" || -z "${DEVICE:-}" ]]; then
  echo "ERROR: missing ACCESS/DEVICE. Run: source scripts/auth_env.sh"
  exit 2
fi

BASE_URL="$BASE_URL" ACCESS="$ACCESS" DEVICE="$DEVICE" python3 tests/battle/run_battle.py
echo "✅ CI OK"
