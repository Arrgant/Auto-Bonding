#!/bin/bash
# 运行所有测试

set -e

echo "🧪 运行 Auto-Bonding 测试..."
echo ""

# 运行单元测试
echo "📋 运行单元测试..."
pytest tests/ -v --ignore=tests/integration/ --cov=bonding_converter --cov-report=term-missing

# 运行集成测试（可选）
echo ""
echo "🔗 运行集成测试..."
pytest tests/integration/ -v -m integration || echo "⚠️  集成测试跳过（需要完整环境）"

echo ""
echo "✅ 测试完成！"
