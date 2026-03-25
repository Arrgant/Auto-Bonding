"""
转换器单元测试
"""

import pytest
import cadquery as cq
from bonding_converter.converter import (
    BondingDiagramConverter,
    BondingElement,
    WireLoop,
)


class TestBondingDiagramConverter:
    """转换器测试"""
    
    def test_init(self):
        """测试初始化"""
        converter = BondingDiagramConverter()
        assert converter.loop_height_coefficient == 1.5
        assert converter.default_wire_diameter == 0.025
        assert converter.default_material == 'gold'
    
    def test_init_with_config(self):
        """测试自定义配置初始化"""
        config = {
            'loop_height_coefficient': 2.0,
            'default_wire_diameter': 0.03,
            'default_material': 'copper',
        }
        converter = BondingDiagramConverter(config)
        assert converter.loop_height_coefficient == 2.0
        assert converter.default_wire_diameter == 0.03
        assert converter.default_material == 'copper'
    
    def test_calculate_loop_height(self):
        """测试弧高计算"""
        converter = BondingDiagramConverter()
        
        # 金线
        height = converter.calculate_loop_height(
            span=5.0,
            wire_diameter=0.025,
            material='gold'
        )
        assert height > 0
        assert height < 2.0  # 合理范围
        
        # 铜线应该比金线低
        height_copper = converter.calculate_loop_height(
            span=5.0,
            wire_diameter=0.025,
            material='copper'
        )
        assert height_copper < height
    
    def test_create_wire_loop(self):
        """测试引线弧创建"""
        converter = BondingDiagramConverter()
        
        wire = WireLoop(
            p1=cq.Vector(0, 0, 0),
            p2=cq.Vector(5, 0, 0),
            loop_height=0.5,
            wire_diameter=0.025,
            material='gold'
        )
        
        model = converter.create_wire_loop(wire)
        
        # 验证模型有效
        assert model is not None
        assert model.val() is not None
        
        # 验证尺寸
        bbox = model.val().BoundingBox()
        assert bbox.xlen > 0
        assert bbox.zlen > 0
    
    def test_create_die_pad(self):
        """测试焊盘创建"""
        converter = BondingDiagramConverter()
        
        pad = converter.create_die_pad(
            x=0, y=0, z=0,
            width=1.0,
            height=1.0,
            thickness=0.1
        )
        
        assert pad is not None
        
        bbox = pad.val().BoundingBox()
        assert abs(bbox.xlen - 1.0) < 0.01
        assert abs(bbox.ylen - 1.0) < 0.01
        assert abs(bbox.zlen - 0.1) < 0.01
    
    def test_convert_elements(self):
        """测试批量元素转换"""
        converter = BondingDiagramConverter()
        
        elements = [
            BondingElement(
                element_type='wire',
                layer='WIRE',
                geometry={
                    'p1': [0, 0, 0],
                    'p2': [5, 0, 0],
                },
                properties={
                    'loop_height': 0.5,
                    'wire_diameter': 0.025,
                    'material': 'gold',
                }
            ),
            BondingElement(
                element_type='die_pad',
                layer='DIE',
                geometry={
                    'x': 0,
                    'y': 0,
                    'z': 0,
                    'width': 1.0,
                    'height': 1.0,
                },
                properties={
                    'thickness': 0.1,
                }
            ),
        ]
        
        assembly = converter.convert_elements(elements)
        
        assert assembly is not None
        assert len(assembly.objects) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
