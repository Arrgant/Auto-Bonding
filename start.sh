#!/bin/bash
# Auto-Bonding 一键启动脚本

set -e

echo "🚀 Auto-Bonding 启动中..."

# 检查 Python 依赖
if ! python3 -c "import PyQt6" 2>/dev/null; then
    echo "📦 安装 Python 依赖..."
    pip3 install -r requirements.txt
fi

# 检查前端
if [ ! -f "frontend/dist/index.html" ]; then
    echo "📦 构建前端..."
    cd frontend
    npm install
    npm run build
    cd ..
fi

# 启动客户端
echo "🎯 启动客户端..."
python3 run_client.py
