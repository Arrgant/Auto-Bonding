"""
键合图 2D→3D 转换核心逻辑
"""

import cadquery as cq
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import numpy as np


@dataclass
class BondingElement:
    """键合图元素"""
    element_type: str  # 'die_pad', 'lead_frame', 'wire', 'bond_point'
    layer: str
    geometry: Dict[str, Any]
    properties: Dict[str, Any]


@dataclass
class WireLoop:
    """引线弧模型"""
    p1: cq.Vector  # 起点
    p2: cq.Vector  # 终点
    loop_height: float  # 弧高
    wire_diameter: float  # 线径
    material: str  # 材料类型


class BondingDiagramConverter:
    """键合图转换器"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化转换器
        
        Args:
            config: 配置参数
                - loop_height_coefficient: 弧高系数 (默认 1.5)
                - default_wire_diameter: 默认线径 mm (默认 0.025)
                - default_material: 默认材料 (默认 'gold')
        """
        self.config = config or {}
        self.loop_height_coefficient = self.config.get('loop_height_coefficient', 1.5)
        self.default_wire_diameter = self.config.get('default_wire_diameter', 0.025)
        self.default_material = self.config.get('default_material', 'gold')
        
        # 材料系数 (经验值)
        self.material_coefficients = {
            'gold': 1.5,
            'copper': 1.2,
            'aluminum': 1.8,
            'silver': 1.4,
        }
    
    def calculate_loop_height(self, span: float, wire_diameter: float, material: str) -> float:
        """
        计算最佳弧高
        
        基于经验公式: loop_height = k * sqrt(span * wire_diameter)
        
        Args:
            span: 跨度 (mm)
            wire_diameter: 线径 (mm)
            material: 材料类型
            
        Returns:
            弧高 (mm)
        """
        k = self.material_coefficients.get(material, self.loop_height_coefficient)
        loop_height = k * np.sqrt(span * wire_diameter)
        return loop_height
    
    def create_wire_loop(self, wire: WireLoop) -> cq.Workplane:
        """
        创建引线弧 3D 模型
        
        Args:
            wire: 引线弧参数
            
        Returns:
            CadQuery 3D 模型
        """
        # 计算中点
        mid_point = (wire.p1 + wire.p2) / 2
        
        # 计算弧顶位置
        arc_apex = mid_point + cq.Vector(0, 0, wire.loop_height)
        
        # 创建 3D 曲线
        wire_3d = cq.Workplane("XY") \
            .moveTo(wire.p1.x, wire.p1.y) \
            .threePointArc(
                (arc_apex.x, arc_apex.y),
                (wire.p2.x, wire.p2.y)
            )
        
        # 沿曲线扫掠生成实体 (带线径)
        if wire.wire_diameter > 0:
            profile = cq.Workplane("XY").circle(wire.wire_diameter / 2)
            wire_solid = wire_3d.wire().sweep(profile)
            return wire_solid
        else:
            return wire_3d
    
    def create_die_pad(self, x: float, y: float, z: float, 
                       width: float, height: float, thickness: float) -> cq.Workplane:
        """
        创建焊盘 3D 模型
        
        Args:
            x, y, z: 位置坐标
            width: 宽度
            height: 高度
            thickness: 厚度
            
        Returns:
            CadQuery 3D 模型
        """
        pad = cq.Workplane("XY") \
            .center(x, y) \
            .rect(width, height) \
            .extrude(thickness)
        
        return pad
    
    def create_lead_frame(self, points: List[cq.Vector], 
                          width: float, thickness: float) -> cq.Workplane:
        """
        创建引线框架 3D 模型
        
        Args:
            points: 路径点列表
            width: 线宽
            thickness: 厚度
            
        Returns:
            CadQuery 3D 模型
        """
        if len(points) < 2:
            return cq.Workplane("XY")
        
        # 创建路径
        path = cq.Workplane("XY").moveTo(points[0].x, points[0].y)
        for pt in points[1:]:
            path.lineTo(pt.x, pt.y)
        
        # 扫掠生成实体
        profile = cq.Workplane("XY").rect(width, thickness)
        lead_frame = path.wire().sweep(profile)
        
        return lead_frame
    
    def convert_elements(self, elements: List[BondingElement]) -> cq.Assembly:
        """
        转换所有键合图元素为 3D 装配体
        
        Args:
            elements: 键合图元素列表
            
        Returns:
            3D 装配体
        """
        assembly = cq.Assembly()
        
        for elem in elements:
            if elem.element_type == 'wire':
                # 创建引线弧
                wire = WireLoop(
                    p1=cq.Vector(elem.geometry.get('p1', [0, 0, 0])),
                    p2=cq.Vector(elem.geometry.get('p2', [5, 0, 0])),
                    loop_height=elem.properties.get('loop_height', self.calculate_loop_height(
                        5.0, self.default_wire_diameter, self.default_material
                    )),
                    wire_diameter=elem.properties.get('wire_diameter', self.default_wire_diameter),
                    material=elem.properties.get('material', self.default_material)
                )
                wire_model = self.create_wire_loop(wire)
                assembly.add(wire_model, name=f"wire_{len(assembly.objects)}")
                
            elif elem.element_type == 'die_pad':
                # 创建焊盘
                pad_model = self.create_die_pad(
                    x=elem.geometry.get('x', 0),
                    y=elem.geometry.get('y', 0),
                    z=elem.geometry.get('z', 0),
                    width=elem.geometry.get('width', 1),
                    height=elem.geometry.get('height', 1),
                    thickness=elem.properties.get('thickness', 0.1)
                )
                assembly.add(pad_model, name=f"die_pad_{len(assembly.objects)}")
                
            elif elem.element_type == 'lead_frame':
                # 创建引线框架
                points = [cq.Vector(p) for p in elem.geometry.get('points', [])]
                lf_model = self.create_lead_frame(
                    points=points,
                    width=elem.properties.get('width', 0.5),
                    thickness=elem.properties.get('thickness', 0.1)
                )
                assembly.add(lf_model, name=f"lead_frame_{len(assembly.objects)}")
        
        return assembly
    
    def export_step(self, assembly: cq.Assembly, output_path: str) -> bool:
        """
        导出 STEP 文件
        
        Args:
            assembly: 3D 装配体
            output_path: 输出路径
            
        Returns:
            是否成功
        """
        try:
            cq.exporters.export(assembly, output_path)
            return True
        except Exception as e:
            print(f"导出 STEP 失败：{e}")
            return False
    
    def convert_file(self, input_path: str, output_path: str) -> bool:
        """
        转换单个文件
        
        Args:
            input_path: 输入 DXF 路径
            output_path: 输出 STEP 路径
            
        Returns:
            是否成功
        """
        # TODO: 集成 DXF 解析
        print(f"转换文件：{input_path} → {output_path}")
        return True
