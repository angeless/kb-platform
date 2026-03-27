#!/bin/bash
# replace-ui-spec-path.sh — UI 规范路径占位符自动替换脚本
# 用法: bash scripts/replace-ui-spec-path.sh <UI规范文件路径>
# 示例: bash scripts/replace-ui-spec-path.sh docs/ui-design-spec.html

set -euo pipefail

UI_SPEC_PATH="${1:-}"

if [ -z "$UI_SPEC_PATH" ]; then
  echo "❌ 用法: bash scripts/replace-ui-spec-path.sh <UI规范文件路径>"
  echo "   示例: bash scripts/replace-ui-spec-path.sh docs/ui-design-spec.html"
  exit 1
fi

if [ ! -f "$UI_SPEC_PATH" ]; then
  echo "❌ 文件不存在: $UI_SPEC_PATH"
  exit 1
fi

echo "🔍 搜索 docs/tech-specs/ 中的 {{UI规范文件路径}} 占位符..."

# Count before
BEFORE=$(grep -rc '{{UI规范文件路径}}' docs/tech-specs/dev-governance*.md 2>/dev/null | awk -F: '{s+=$2} END {print s+0}')
echo "   找到 $BEFORE 处占位符"

if [ "$BEFORE" -eq 0 ]; then
  echo "✅ 未发现占位符，无需替换"
  exit 0
fi

# Replace
for f in docs/tech-specs/dev-governance*.md; do
  if grep -q '{{UI规范文件路径}}' "$f" 2>/dev/null; then
    sed -i '' "s|{{UI规范文件路径}}|$UI_SPEC_PATH|g" "$f"
    echo "   ✅ 已替换: $f"
  fi
done

# Verify
AFTER=$(grep -rc '{{UI规范文件路径}}' docs/tech-specs/dev-governance*.md 2>/dev/null | awk -F: '{s+=$2} END {print s+0}')
if [ "$AFTER" -eq 0 ]; then
  echo ""
  echo "✅ 替换完成: $BEFORE 处 → 0 处残留"
  echo "   UI 规范路径: $UI_SPEC_PATH"
else
  echo ""
  echo "⚠️ 仍有 $AFTER 处残留，请手动检查:"
  grep -rn '{{UI规范文件路径}}' docs/tech-specs/dev-governance*.md
  exit 1
fi
