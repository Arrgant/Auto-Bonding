#!/usr/bin/env python3
"""
Auto-Bonding - 键合图自动转换工具
主程序入口
"""

import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("Auto-Bonding")
    app.setOrganizationName("Auto-Bonding")
    app.setApplicationVersion("0.1.0")
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
