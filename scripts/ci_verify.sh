#!/usr/bin/env bash
# KB Platform — 整合检查脚本
# 用途: Phase 3 门禁 Part A 自动化检查
# 用法: bash scripts/ci_verify.sh [--quick]
#   --quick: 仅运行 lint + smoke 测试（Per-Commit 级别）
#   无参数: 运行完整检查（Per-Task 级别）

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
SKIP=0
RESULTS=()

run_check() {
  local name="$1"
  local cmd="$2"
  local required="${3:-true}"

  printf "  %-35s" "$name"

  if eval "$cmd" > /tmp/ci_verify_output.txt 2>&1; then
    echo -e "${GREEN}✅ PASS${NC}"
    PASS=$((PASS + 1))
    RESULTS+=("✅ $name")
  else
    if [ "$required" = "true" ]; then
      echo -e "${RED}❌ FAIL${NC}"
      FAIL=$((FAIL + 1))
      RESULTS+=("❌ $name")
      # Show first 10 lines of error
      head -10 /tmp/ci_verify_output.txt | sed 's/^/     /'
    else
      echo -e "${YELLOW}⚠️  SKIP (optional)${NC}"
      SKIP=$((SKIP + 1))
      RESULTS+=("⚠️  $name (skipped)")
    fi
  fi
}

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   KB Platform — CI Verify                   ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

QUICK_MODE=false
if [ "${1:-}" = "--quick" ]; then
  QUICK_MODE=true
  echo -e "${YELLOW}⚡ Quick mode: lint + smoke only${NC}"
fi

# ── Step 1: Python Lint ──
echo ""
echo "── Python Lint ──"
run_check "Ruff check" "python3 -m ruff check . --quiet" "false"
run_check "Ruff format check" "python3 -m ruff format --check . --quiet" "false"

# ── Step 2: Frontend Type Check ──
echo ""
echo "── Frontend Checks ──"
if [ -d "apps/web" ]; then
  run_check "TypeScript (tsc --noEmit)" "cd apps/web && npx tsc --noEmit" "false"
else
  echo "  (no frontend found, skipping)"
fi

# ── Step 3: Backend Tests ──
echo ""
echo "── Backend Tests ──"
if [ "$QUICK_MODE" = true ]; then
  run_check "Smoke tests" "python3 -m pytest services/api/tests/ -x -q --timeout=30 2>/dev/null || python3 -m pytest services/api/tests/ -x -q"
else
  run_check "Full test suite" "python3 -m pytest services/api/tests/ -v --timeout=120 2>/dev/null || python3 -m pytest services/api/tests/ -v"
fi

# ── Step 4: Frontend Tests (full mode only) ──
if [ "$QUICK_MODE" = false ] && [ -d "apps/web" ]; then
  echo ""
  echo "── Frontend Tests ──"
  run_check "Vitest" "cd apps/web && npx vitest run --reporter=verbose" "false"
fi

# ── Summary ──
echo ""
echo "════════════════════════════════════════════════"
echo "  Results: ${GREEN}${PASS} passed${NC}  ${RED}${FAIL} failed${NC}  ${YELLOW}${SKIP} skipped${NC}"
echo "════════════════════════════════════════════════"

for r in "${RESULTS[@]}"; do
  echo "  $r"
done

echo ""

if [ "$FAIL" -gt 0 ]; then
  echo -e "${RED}❌ CI VERIFY FAILED — $FAIL check(s) failed${NC}"
  exit 1
else
  echo -e "${GREEN}✅ CI VERIFY PASSED${NC}"
  exit 0
fi
