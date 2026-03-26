"""
主窗口模块 - 基于 PyQt6 WebEngine 的现代化客户端
嵌入前端网页 UI，提供独立客户端体验
"""

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, 
    QProgressBar, QLabel, QToolBar, QStatusBar,
    QFileDialog, QMessageBox, QMenu, QMenuBar
)
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtGui import QAction, QIcon, QDesktopServices
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile

import subprocess
import sys
import os
import time
import socket


class MainWindow(QMainWindow):
    """主窗口 - 嵌入前端网页"""
    
    def __init__(self):
        super().__init__()
        
        self.backend_process = None
        self.frontend_url = None
        
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        
        # 启动后端和前端
        self._start_services()
    
    def _setup_ui(self):
        """设置 UI"""
        self.setWindowTitle("Auto-Bonding - 键合图转换工具")
        self.setMinimumSize(1400, 900)
        
        # 创建浏览器组件
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl("about:blank"))
        
        # 设置浏览器配置
        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpUserAgent("Auto-Bonding Client/1.0")
        
        # 设置中央部件
        self.setCentralWidget(self.browser)
        
        # 底部状态栏
        self.loading_label = QLabel("正在启动服务...")
        self.loading_label.setStyleSheet("color: #9CA3AF; padding: 8px;")
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 不确定进度
        self.progress_bar.setMaximumHeight(3)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background: transparent;
            }
            QProgressBar::chunk {
                background: #3B82F6;
            }
        """)
    
    def _setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件 (&F)")
        
        action_open = QAction("📂 打开文件", self)
        action_open.setShortcut("Ctrl+O")
        action_open.triggered.connect(self._open_file)
        file_menu.addAction(action_open)
        
        file_menu.addSeparator()
        
        action_exit = QAction("退出 (&X)", self)
        action_exit.setShortcut("Alt+F4")
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具 (&T)")
        
        action_devtools = QAction("🛠️ 开发者工具", self)
        action_devtools.setShortcut("F12")
        action_devtools.triggered.connect(self._toggle_devtools)
        tools_menu.addAction(action_devtools)
        
        action_refresh = QAction("🔄 刷新页面", self)
        action_refresh.setShortcut("F5")
        action_refresh.triggered.connect(self._refresh_page)
        tools_menu.addAction(action_refresh)
        
        tools_menu.addSeparator()
        
        action_drc = QAction("✅ DRC 检查", self)
        action_drc.triggered.connect(self._run_drc)
        tools_menu.addAction(action_drc)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助 (&H)")
        
        action_docs = QAction("📖 文档", self)
        action_docs.triggered.connect(self._open_docs)
        help_menu.addAction(action_docs)
        
        action_about = QAction("ℹ️ 关于", self)
        action_about.triggered.connect(self._show_about)
        help_menu.addAction(action_about)
    
    def _setup_toolbar(self):
        """设置工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(Qt.ToolButtonStyle(2))
        self.addToolBar(toolbar)
        
        action_open = QAction("📂 打开", self)
        action_open.triggered.connect(self._open_file)
        toolbar.addAction(action_open)
        
        toolbar.addSeparator()
        
        action_refresh = QAction("🔄 刷新", self)
        action_refresh.triggered.connect(self._refresh_page)
        toolbar.addAction(action_refresh)
        
        action_devtools = QAction("🛠️ 调试", self)
        action_devtools.triggered.connect(self._toggle_devtools)
        toolbar.addAction(action_devtools)
    
    def _setup_statusbar(self):
        """设置状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.addWidget(self.loading_label)
    
    def _start_services(self):
        """启动服务"""
        # 创建一个简单的本地 HTML 页面作为占位
        import tempfile
        import http.server
        import threading
        
        # 创建临时目录存放静态文件
        self.static_dir = tempfile.mkdtemp(prefix="autobonding_")
        
        # 生成简单的 HTML 页面
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Auto-Bonding</title>
            <style>
                body { 
                    margin: 0; 
                    background: #1F2937; 
                    color: white;
                    font-family: system-ui, -apple-system, sans-serif;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 40px 20px;
                }
                h1 { font-size: 2.5rem; margin-bottom: 1rem; }
                p { font-size: 1.2rem; color: #9CA3AF; }
                .btn {
                    display: inline-block;
                    padding: 12px 24px;
                    background: #3B82F6;
                    color: white;
                    border-radius: 8px;
                    text-decoration: none;
                    margin-top: 20px;
                }
                .btn:hover { background: #2563EB; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔧 Auto-Bonding</h1>
                <p>键合图自动转换工具</p>
                <p>前端界面开发中...</p>
                <a href="#" class="btn" onclick="alert('请使用文件菜单导入 DXF 文件')">📂 选择文件</a>
            </div>
        </body>
        </html>
        """
        
        html_path = os.path.join(self.static_dir, "index.html")
        with open(html_path, 'w') as f:
            f.write(html_content)
        
        # 启动 HTTP 服务器
        port = self._find_free_port(8080)
        
        def serve():
            os.chdir(self.static_dir)
            server = http.server.HTTPServer(("", port), http.server.SimpleHTTPRequestHandler)
            server.serve_forever()
        
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        
        self.frontend_url = f"http://localhost:{port}"
        print(f"✅ 服务已启动：{self.frontend_url}")
        
        # 加载页面
        QTimer.singleShot(500, self._load_page)
    
    def _find_free_port(self, start_port=3000):
        """查找空闲端口"""
        for port in range(start_port, start_port + 100):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            if result != 0:
                return port
        return 3000
    
    def _load_page(self):
        """加载前端页面"""
        if self.frontend_url:
            self.browser.setUrl(QUrl(self.frontend_url))
            self.loading_label.setText("✅ 就绪")
            self.statusbar.showMessage("Auto-Bonding 已就绪")
            
            # 隐藏进度条
            self.progress_bar.setVisible(False)
    
    def _open_file(self):
        """打开文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择 DXF 文件", "", 
            "DXF Files (*.dxf);;DWG Files (*.dwg);;All Files (*)"
        )
        
        if files:
            # 通过 JavaScript 传递给前端
            js_code = f"""
            if (window.handleExternalFiles) {{
                window.handleExternalFiles({files});
            }}
            """
            self.browser.page().runJavaScript(js_code)
    
    def _refresh_page(self):
        """刷新页面"""
        self.browser.reload()
        self.statusbar.showMessage("页面已刷新")
    
    def _toggle_devtools(self):
        """切换开发者工具"""
        # PyQt6 WebEngine 不直接支持 devtools，需要额外配置
        QMessageBox.information(
            self, "开发者工具",
            "开发者工具需要在创建 QWebEngineView 时启用。\n"
            "如需调试，请在浏览器中访问前端地址。"
        )
    
    def _run_drc(self):
        """运行 DRC 检查"""
        # 通过 JavaScript 调用前端 DRC 功能
        js_code = """
        if (window.runDRC) {
            window.runDRC();
        } else {
            alert('请在主界面中选择文件后使用 DRC 检查功能');
        }
        """
        self.browser.page().runJavaScript(js_code)
    
    def _open_docs(self):
        """打开文档"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        readme_path = os.path.join(base_dir, "README.md")
        
        if os.path.exists(readme_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(readme_path))
        else:
            QMessageBox.information(self, "文档", "文档文件未找到")
    
    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self, "关于 Auto-Bonding",
            "<h2>Auto-Bonding</h2>"
            "<p><strong>键合图自动转换工具 v1.0</strong></p>"
            "<p>将 DXF/DWG 二维键合图转换为 3D 模型并导出打线坐标</p>"
            "<p><strong>技术栈:</strong></p>"
            "<ul>"
            "<li>前端：React + TypeScript + Three.js</li>"
            "<li>后端：FastAPI + Python</li>"
            "<li>客户端：PyQt6 WebEngine</li>"
            "</ul>"
            "<p>© 2026 Auto-Bonding Contributors</p>"
        )
    
    def closeEvent(self, event):
        """关闭事件 - 清理服务"""
        print("正在关闭服务...")
        
        # 关闭后端服务
        if self.backend_process:
            self.backend_process.terminate()
            self.backend_process.wait(timeout=5)
            print("✅ 后端服务已停止")
        
        event.accept()


if __name__ == "__main__":
    # 启用高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("Auto-Bonding")
    app.setOrganizationName("Auto-Bonding")
    app.setApplicationVersion("1.0.0")
    
    # 设置应用样式
    app.setStyleSheet("""
        QMainWindow {
            background: #1F2937;
        }
        QMenuBar {
            background: #111827;
            color: #F9FAFB;
            padding: 4px;
        }
        QMenuBar::item:selected {
            background: #374151;
        }
        QMenu {
            background: #1F2937;
            color: #F9FAFB;
            border: 1px solid #374151;
        }
        QMenu::item:selected {
            background: #3B82F6;
        }
        QToolBar {
            background: #1F2937;
            border: none;
            padding: 4px;
            spacing: 8px;
        }
        QToolButton {
            background: transparent;
            color: #F9FAFB;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }
        QToolButton:hover {
            background: #374151;
        }
        QStatusBar {
            background: #111827;
            color: #9CA3AF;
        }
    """)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())
