"""
VTK 3D 预览模块
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal

try:
    from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
    import vtkmodules.vtkRenderingOpenGL2 as vtk
    VTK_AVAILABLE = True
except ImportError:
    VTK_AVAILABLE = False


class VTKViewer(QWidget):
    """VTK 3D 查看器"""
    
    def __init__(self):
        super().__init__()
        
        if VTK_AVAILABLE:
            self._setup_vtk()
        else:
            self._setup_fallback()
    
    def _setup_vtk(self):
        """设置 VTK"""
        layout = QVBoxLayout(self)
        
        # VTK 渲染窗口
        self.vtk_widget = QVTKRenderWindowInteractor()
        layout.addWidget(self.vtk_widget)
        
        # VTK 渲染器
        self.renderer = vtk.vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        
        # 设置背景色
        self.renderer.SetBackground(0.1, 0.1, 0.15)
        
        # 添加光源
        light = vtk.vtkLight()
        light.SetPosition(10, 10, 10)
        self.renderer.AddLight(light)
        
        # 初始化
        self.vtk_widget.Initialize()
        self.vtk_widget.Start()
    
    def _setup_fallback(self):
        """VTK 不可用时的备用界面"""
        from PyQt6.QtWidgets import QLabel
        from PyQt6.QtCore import Qt
        
        label = QLabel("VTK 未安装\n请运行：pip install vtk")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #888; font-size: 14px;")
        
        layout = QVBoxLayout(self)
        layout.addWidget(label)
    
    def display_model(self, model):
        """
        显示 3D 模型
        
        Args:
            model: CadQuery 模型
        """
        if not VTK_AVAILABLE:
            return
        
        # TODO: 实现 CadQuery → VTK 转换
        # 目前显示一个示例立方体
        cube_source = vtk.vtkCubeSource()
        cube_source.SetXLength(1.0)
        cube_source.SetYLength(1.0)
        cube_source.SetZLength(1.0)
        
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(cube_source.GetOutputPort())
        
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.2, 0.6, 0.8)
        
        self.renderer.AddActor(actor)
        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()
    
    def clear(self):
        """清空场景"""
        if VTK_AVAILABLE:
            self.renderer.RemoveAllViewProps()
            self.vtk_widget.GetRenderWindow().Render()
    
    def zoom_fit(self):
        """适应窗口"""
        if VTK_AVAILABLE:
            self.renderer.ResetCamera()
            self.vtk_widget.GetRenderWindow().Render()
    
    def reset_view(self):
        """重置视角"""
        if VTK_AVAILABLE:
            camera = self.renderer.GetActiveCamera()
            camera.SetPosition(10, 10, 10)
            camera.SetFocalPoint(0, 0, 0)
            camera.SetViewUp(0, 0, 1)
            self.vtk_widget.GetRenderWindow().Render()
