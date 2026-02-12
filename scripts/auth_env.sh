#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

ACCESS=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"tenant1@aipass.com","password":"TenantPass123"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

DEVICE=$(curl -s -X POST "$BASE_URL/auth/device/register" \
  -H "Authorization: Bearer '"$ACCESS"'" \
  -H "Content-Type: application/json" \
  -d '{"device_name":"Prins MacBook Air"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["device_token"])')

export ACCESS DEVICE
echo "✅ ACCESS len=${#ACCESS} DEVICE len=${#DEVICE}"
