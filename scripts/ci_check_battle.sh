#!/bin/bash
set -e

python3 tests/battle/run_battle.py

FAILS=$(cat reports/battle_latest.json | grep '"ok": false' | wc -l)

if [ "$FAILS" -gt "0" ]; then
  echo "❌ Governance failed"
  exit 1
fi

echo "✅ Governance OK"
