#!/usr/bin/env bash
set -euo pipefail

mkdir -p reports

echo "== Dependency Scan =="

echo
echo "1) Python dependency scan (pip-audit)"
if ! command -v pip-audit >/dev/null 2>&1; then
  echo "pip-audit not found, installing..."
  pip install -q pip-audit
fi

# Always write JSON report (even if vulnerabilities exist)
set +e
pip-audit -f json > reports/deps_pip_audit.json
PIP_AUDIT_EXIT=$?
set -e

echo "✅ Wrote reports/deps_pip_audit.json"
if [ $PIP_AUDIT_EXIT -ne 0 ]; then
  echo "⚠️ pip-audit found vulnerabilities (exit=$PIP_AUDIT_EXIT)"
else
  echo "✅ pip-audit clean"
fi

echo
echo "2) Node dependency scan (npm audit) - optional"
if [ -f "../package.json" ] || [ -f "package.json" ]; then
  if command -v npm >/dev/null 2>&1; then
    set +e
    npm audit --json > reports/deps_npm_audit.json
    NPM_EXIT=$?
    set -e
    echo "✅ Wrote reports/deps_npm_audit.json"
    if [ $NPM_EXIT -ne 0 ]; then
      echo "⚠️ npm audit found vulnerabilities (exit=$NPM_EXIT)"
    else
      echo "✅ npm audit clean"
    fi
  else
    echo "⚠️ npm not found, skipping npm audit"
  fi
else
  echo "ℹ️ No package.json found, skipping npm audit"
fi

echo
echo "== Dependency Scan Done =="
# If you want CI to fail on vulnerabilities:
# export FAIL_ON_VULNS=1
if [ "${FAIL_ON_VULNS:-0}" = "1" ] && [ $PIP_AUDIT_EXIT -ne 0 ]; then
  echo "❌ FAIL_ON_VULNS=1 and pip-audit found issues. Failing CI."
  exit 10
fi
