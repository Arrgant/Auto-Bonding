#!/usr/bin/env python3
"""
Auto-Bonding 客户端启动脚本
一键启动独立客户端
"""

import subprocess
import sys
import os


def check_dependencies():
    """检查依赖是否安装"""
    try:
        import PyQt6
        import PyQt6.QtWebEngineWidgets
        print("✅ PyQt6 已安装")
    except ImportError:
        print("❌ PyQt6 未安装，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyQt6", "PyQt6-WebEngine"])
    
    try:
        import fastapi
        print("✅ FastAPI 已安装")
    except ImportError:
        print("❌ FastAPI 未安装，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "python-multipart"])


def check_frontend():
    """检查前端是否已构建"""
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend", "dist")
    index_html = os.path.join(frontend_dir, "index.html")
    
    if not os.path.exists(index_html):
        print("⚠️  前端未构建，正在构建...")
        frontend_root = os.path.join(os.path.dirname(__file__), "frontend")
        
        try:
            subprocess.check_call(["npm", "install"], cwd=frontend_root)
            subprocess.check_call(["npm", "run", "build"], cwd=frontend_root)
            print("✅ 前端构建完成")
        except subprocess.CalledProcessError as e:
            print(f"❌ 前端构建失败：{e}")
            print("请手动运行：cd frontend && npm install && npm run build")
            return False
    
    return True


def main():
    """主函数"""
    print("🚀 Auto-Bonding 客户端启动中...")
    
    # 检查依赖
    check_dependencies()
    
    # 检查前端
    if not check_frontend():
        sys.exit(1)
    
    # 启动客户端
    print("🎯 启动客户端...")
    from gui.main_window import main
    main()


if __name__ == "__main__":
    main()
