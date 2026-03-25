"""
主窗口模块
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QMenuBar, QMenu,
    QStatusBar, QToolBar, QSplitter, QProgressBar,
    QMessageBox, QGroupBox, QFormLayout, QLineEdit,
    QDoubleSpinBox, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QIcon

from .viewer3d import VTKViewer
from bonding_converter import BondingDiagramConverter, DXFParser, CoordinateExporter
from bonding_converter.drc import DRCChecker

import sys


class ConversionWorker(QThread):
    """转换工作线程"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, input_files: list, output_dir: str, config: dict):
        super().__init__()
        self.input_files = input_files
        self.output_dir = output_dir
        self.config = config
    
    def run(self):
        """执行转换"""
        try:
            converter = BondingDiagramConverter(self.config)
            success_count = 0
            
            for i, input_file in enumerate(self.input_files):
                self.progress.emit(int((i / len(self.input_files)) * 100))
                
                # TODO: 实现转换逻辑
                success_count += 1
            
            self.finished.emit(True, f"成功转换 {success_count}/{len(self.input_files)} 个文件")
        except Exception as e:
            self.finished.emit(False, str(e))


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        
        self.input_files = []
        self.converter = BondingDiagramConverter()
        
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
    
    def _setup_ui(self):
        """设置 UI"""
        self.setWindowTitle("Auto-Bonding - 键合图转换工具")
        self.setMinimumSize(1200, 800)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：文件列表和参数
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)
        
        # 右侧：3D 预览
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(splitter)
        
        # 底部：进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
    
    def _create_left_panel(self) -> QWidget:
        """创建左侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 文件列表
        file_group = QGroupBox("输入文件")
        file_layout = QVBoxLayout(file_group)
        
        self.file_list_label = QLabel("未选择文件")
        file_layout.addWidget(self.file_list_label)
        
        btn_layout = QHBoxLayout()
        
        self.btn_add_files = QPushButton("添加文件")
        self.btn_add_files.clicked.connect(self._add_files)
        btn_layout.addWidget(self.btn_add_files)
        
        self.btn_clear_files = QPushButton("清空")
        self.btn_clear_files.clicked.connect(self._clear_files)
        btn_layout.addWidget(self.btn_clear_files)
        
        file_layout.addLayout(btn_layout)
        layout.addWidget(file_group)
        
        # 参数配置
        param_group = QGroupBox("转换参数")
        param_layout = QFormLayout(param_group)
        
        self.param_loop_height = QDoubleSpinBox()
        self.param_loop_height.setRange(0.1, 10.0)
        self.param_loop_height.setValue(1.5)
        self.param_loop_height.setSuffix(" (系数)")
        param_layout.addRow("弧高系数:", self.param_loop_height)
        
        self.param_wire_diameter = QDoubleSpinBox()
        self.param_wire_diameter.setRange(0.01, 0.1)
        self.param_wire_diameter.setValue(0.025)
        self.param_wire_diameter.setSuffix(" mm")
        param_layout.addRow("线径:", self.param_wire_diameter)
        
        self.param_material = QComboBox()
        self.param_material.addItems(['gold', 'copper', 'aluminum', 'silver'])
        param_layout.addRow("材料:", self.param_material)
        
        layout.addWidget(param_group)
        
        # 导出格式
        export_group = QGroupBox("导出格式")
        export_layout = QVBoxLayout(export_group)
        
        self.export_format = QComboBox()
        self.export_format.addItems(['STEP', 'KS', 'ASM', 'SHINKAWA', 'CSV'])
        export_layout.addWidget(self.export_format)
        
        self.btn_convert = QPushButton("开始转换")
        self.btn_convert.clicked.connect(self._start_conversion)
        export_layout.addWidget(self.btn_convert)
        
        layout.addWidget(export_group)
        
        layout.addStretch()
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """创建右侧面板 (3D 预览)"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # VTK 3D 查看器
        self.viewer = VTKViewer()
        layout.addWidget(self.viewer)
        
        # 查看器控制
        control_layout = QHBoxLayout()
        
        btn_zoom_fit = QPushButton("适应窗口")
        btn_zoom_fit.clicked.connect(self.viewer.zoom_fit)
        control_layout.addWidget(btn_zoom_fit)
        
        btn_reset = QPushButton("重置视角")
        btn_reset.clicked.connect(self.viewer.reset_view)
        control_layout.addWidget(btn_reset)
        
        layout.addLayout(control_layout)
        
        return panel
    
    def _setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        action_open = QAction("打开文件", self)
        action_open.setShortcut("Ctrl+O")
        action_open.triggered.connect(self._add_files)
        file_menu.addAction(action_open)
        
        file_menu.addSeparator()
        
        action_exit = QAction("退出", self)
        action_exit.setShortcut("Ctrl+Q")
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        action_drc = QAction("DRC 检查", self)
        action_drc.triggered.connect(self._run_drc)
        tools_menu.addAction(action_drc)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        action_about = QAction("关于", self)
        action_about.triggered.connect(self._show_about)
        help_menu.addAction(action_about)
    
    def _setup_toolbar(self):
        """设置工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        action_open = QAction("📂 打开", self)
        action_open.triggered.connect(self._add_files)
        toolbar.addAction(action_open)
        
        toolbar.addSeparator()
        
        action_convert = QAction("▶️ 转换", self)
        action_convert.triggered.connect(self._start_conversion)
        toolbar.addAction(action_convert)
    
    def _setup_statusbar(self):
        """设置状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("就绪")
    
    def _add_files(self):
        """添加文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择 DXF 文件", "", "DXF Files (*.dxf);;All Files (*)"
        )
        
        if files:
            self.input_files.extend(files)
            self.file_list_label.setText(f"已选择 {len(self.input_files)} 个文件")
            self.statusbar.showMessage(f"添加了 {len(files)} 个文件")
    
    def _clear_files(self):
        """清空文件列表"""
        self.input_files = []
        self.file_list_label.setText("未选择文件")
        self.statusbar.showMessage("已清空文件列表")
    
    def _start_conversion(self):
        """开始转换"""
        if not self.input_files:
            QMessageBox.warning(self, "警告", "请先选择输入文件")
            return
        
        # 获取参数
        config = {
            'loop_height_coefficient': self.param_loop_height.value(),
            'default_wire_diameter': self.param_wire_diameter.value(),
            'default_material': self.param_material.currentText(),
        }
        
        # 选择输出目录
        output_dir = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if not output_dir:
            return
        
        # 启动工作线程
        self.worker = ConversionWorker(self.input_files, output_dir, config)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self._conversion_finished)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_convert.setEnabled(False)
        
        self.worker.start()
        self.statusbar.showMessage("转换中...")
    
    def _conversion_finished(self, success: bool, message: str):
        """转换完成"""
        self.progress_bar.setVisible(False)
        self.btn_convert.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "成功", message)
            self.statusbar.showMessage(message)
        else:
            QMessageBox.critical(self, "错误", message)
            self.statusbar.showMessage(f"转换失败：{message}")
    
    def _run_drc(self):
        """运行 DRC 检查"""
        QMessageBox.information(self, "DRC", "DRC 检查功能开发中...")
    
    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self, "关于 Auto-Bonding",
            "<h2>Auto-Bonding</h2>"
            "<p>键合图自动转换工具 v0.1.0</p>"
            "<p>将 DXF/DWG 二维键合图转换为 3D 模型并导出打线坐标</p>"
            "<p>© 2026 Auto-Bonding Contributors</p>"
        )
