"""
DXF 文件解析模块
"""

import ezdxf
from typing import List, Dict, Any, Optional
from .converter import BondingElement


class DXFParser:
    """DXF 文件解析器"""
    
    def __init__(self, layer_mapping: Optional[Dict[str, str]] = None):
        """
        初始化解析器
        
        Args:
            layer_mapping: 图层名称到元素类型的映射
        """
        self.layer_mapping = layer_mapping or {
            'DIE': 'die_pad',
            'PAD': 'die_pad',
            'WIRE': 'wire',
            'LEAD': 'lead_frame',
            'LF': 'lead_frame',
            'BOND': 'bond_point',
            'FINGER': 'lead_frame',
        }
    
    def parse_file(self, file_path: str) -> List[BondingElement]:
        """
        解析 DXF 文件
        
        Args:
            file_path: DXF 文件路径
            
        Returns:
            键合图元素列表
        """
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()
        
        elements = []
        
        for entity in msp:
            layer = entity.dxf.layer
            element_type = self.layer_mapping.get(layer.upper(), 'unknown')
            
            if element_type == 'unknown':
                continue
            
            element = self._parse_entity(entity, element_type, layer)
            if element:
                elements.append(element)
        
        return elements
    
    def _parse_entity(self, entity, element_type: str, layer: str) -> Optional[BondingElement]:
        """
        解析单个 DXF 实体
        
        Args:
            entity: DXF 实体
            element_type: 元素类型
            layer: 图层名称
            
        Returns:
            BondingElement 或 None
        """
        if entity.dxftype() == 'LINE':
            return self._parse_line(entity, element_type, layer)
        elif entity.dxftype() == 'CIRCLE':
            return self._parse_circle(entity, element_type, layer)
        elif entity.dxftype() == 'ARC':
            return self._parse_arc(entity, element_type, layer)
        elif entity.dxftype() == 'LWPOLYLINE':
            return self._parse_polyline(entity, element_type, layer)
        elif entity.dxftype() == 'POINT':
            return self._parse_point(entity, element_type, layer)
        
        return None
    
    def _parse_line(self, entity, element_type: str, layer: str) -> BondingElement:
        """解析 LINE 实体"""
        start = entity.dxf.start
        end = entity.dxf.end
        
        geometry = {
            'p1': [start.x, start.y, start.z],
            'p2': [end.x, end.y, end.z],
        }
        
        properties = {
            'layer': layer,
            'color': entity.dxf.color if hasattr(entity.dxf, 'color') else 7,
        }
        
        return BondingElement(
            element_type=element_type,
            layer=layer,
            geometry=geometry,
            properties=properties
        )
    
    def _parse_circle(self, entity, element_type: str, layer: str) -> BondingElement:
        """解析 CIRCLE 实体"""
        center = entity.dxf.center
        radius = entity.dxf.radius
        
        geometry = {
            'center': [center.x, center.y, center.z],
            'radius': radius,
        }
        
        properties = {
            'layer': layer,
            'diameter': radius * 2,
        }
        
        return BondingElement(
            element_type=element_type,
            layer=layer,
            geometry=geometry,
            properties=properties
        )
    
    def _parse_arc(self, entity, element_type: str, layer: str) -> BondingElement:
        """解析 ARC 实体"""
        center = entity.dxf.center
        radius = entity.dxf.radius
        start_angle = entity.dxf.start_angle
        end_angle = entity.dxf.end_angle
        
        geometry = {
            'center': [center.x, center.y, center.z],
            'radius': radius,
            'start_angle': start_angle,
            'end_angle': end_angle,
        }
        
        properties = {
            'layer': layer,
            'arc_length': radius * (end_angle - start_angle),
        }
        
        return BondingElement(
            element_type=element_type,
            layer=layer,
            geometry=geometry,
            properties=properties
        )
    
    def _parse_polyline(self, entity, element_type: str, layer: str) -> BondingElement:
        """解析 LWPOLYLINE 实体"""
        points = [[v.x, v.y, v.z] for v in entity.get_points()]
        
        geometry = {
            'points': points,
            'closed': entity.closed,
        }
        
        properties = {
            'layer': layer,
            'width': entity.dxf.const_width if hasattr(entity.dxf, 'const_width') else 0,
        }
        
        return BondingElement(
            element_type=element_type,
            layer=layer,
            geometry=geometry,
            properties=properties
        )
    
    def _parse_point(self, entity, element_type: str, layer: str) -> BondingElement:
        """解析 POINT 实体"""
        location = entity.dxf.location
        
        geometry = {
            'x': location.x,
            'y': location.y,
            'z': location.z,
        }
        
        properties = {
            'layer': layer,
        }
        
        return BondingElement(
            element_type=element_type,
            layer=layer,
            geometry=geometry,
            properties=properties
        )
