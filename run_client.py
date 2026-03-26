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
        import cadquery
        print("✅ CadQuery 已安装")
    except ImportError:
        print("❌ CadQuery 未安装，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "cadquery", "ezdxf", "numpy"])


def run():
    """主函数"""
    print("🚀 Auto-Bonding 客户端启动中...")
    
    # 检查依赖
    check_dependencies()
    
    # 启动客户端
    print("🎯 启动客户端...")
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from gui.main_window import MainWindow
    
    # 启用高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("Auto-Bonding")
    app.setOrganizationName("Auto-Bonding")
    app.setApplicationVersion("1.0.0")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
