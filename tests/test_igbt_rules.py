"""
IGBT 规则测试套件

测试 IGBT 功率器件特定的键合规则。
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from bonding_converter.igbt_rules import (
    IGBTRules,
    IGBTPadType,
    WireType,
    IGBT_RULES_DEFAULT,
    IGBT_RULES_HIGH_VOLTAGE,
    IGBT_RULES_AUTOMOTIVE,
)
from bonding_converter.drc import DRCChecker, DRCMode, DRCViolation


class TestIGBTRules:
    """IGBT 规则基础测试"""
    
    def test_default_rules(self):
        """测试默认规则配置"""
        rules = IGBTRules()
        
        assert rules.min_spacing_low_voltage == 0.5
        assert rules.min_spacing_medium_voltage == 1.0
        assert rules.min_spacing_high_voltage == 2.0
        assert rules.min_spacing_ultra_high_voltage == 3.0
        
    def test_voltage_spacing(self):
        """测试电压相关间距"""
        rules = IGBTRules()
        
        # 低压
        assert rules.get_min_spacing_for_voltage(50) == 0.5
        assert rules.get_min_spacing_for_voltage(100) == 0.5
        
        # 中压
        assert rules.get_min_spacing_for_voltage(300) == 1.0
        assert rules.get_min_spacing_for_voltage(600) == 1.0
        
        # 高压
        assert rules.get_min_spacing_for_voltage(800) == 2.0
        assert rules.get_min_spacing_for_voltage(1200) == 2.0
        
        # 超高压
        assert rules.get_min_spacing_for_voltage(1500) == 3.0
        assert rules.get_min_spacing_for_voltage(3300) == 3.0
    
    def test_current_capacity_al_wire(self):
        """测试铝线电流承载能力"""
        rules = IGBTRules()
        
        # 100μm 铝线
        current_100 = rules.get_current_capacity(0.1, WireType.AL_WIRE)
        assert current_100 > 0
        
        # 300μm 铝线
        current_300 = rules.get_current_capacity(0.3, WireType.AL_WIRE)
        assert current_300 > current_100
        
        # 500μm 铝线
        current_500 = rules.get_current_capacity(0.5, WireType.AL_WIRE)
        assert current_500 > current_300
    
    def test_current_capacity_ribbon(self):
        """测试铝带电流承载能力"""
        rules = IGBTRules()
        
        # 铝带 1000×75μm
        # 截面积 = 1.0 × 0.075 = 0.075 mm²
        # 电流密度 400 A/mm²
        # 预期电流 ≈ 30A
        current = rules.get_current_capacity(0, WireType.AL_RIBBON)
        # 注意：这个方法需要传入直径，铝带应该用专门的计算
    
    def test_loop_height_coefficient(self):
        """测试弧高系数"""
        rules = IGBTRules()
        
        # 铝线系数应该大于金线
        assert rules.loop_height_coefficient_al_wire > 1.5
        assert rules.loop_height_coefficient_al_ribbon > 1.0
    
    def test_pad_size_validation(self):
        """测试焊盘尺寸验证"""
        rules = IGBTRules()
        
        # 发射极焊盘
        violations = rules.validate_pad_type(IGBTPadType.EMITTER, 0.2)
        assert len(violations) > 0  # 0.2 < 0.3，应该违规
        
        violations = rules.validate_pad_type(IGBTPadType.EMITTER, 0.4)
        assert len(violations) == 0  # 0.4 > 0.3，应该通过
        
        # 集电极焊盘
        violations = rules.validate_pad_type(IGBTPadType.COLLECTOR, 0.3)
        assert len(violations) > 0  # 0.3 < 0.5，应该违规
        
        # 栅极焊盘
        violations = rules.validate_pad_type(IGBTPadType.GATE, 0.15)
        assert len(violations) > 0  # 0.15 < 0.2，应该违规


class TestIGBTDRC:
    """IGBT DRC 检查测试"""
    
    def test_drc_mode_standard(self):
        """测试标准模式 DRC"""
        checker = DRCChecker(mode=DRCMode.STANDARD)
        assert not checker.is_igbt
    
    def test_drc_mode_igbt(self):
        """测试 IGBT 模式 DRC"""
        checker = DRCChecker(mode=DRCMode.IGBT)
        assert checker.is_igbt
        assert checker.rules.get('min_pad_size_emitter') == 0.3
        assert checker.rules.get('min_pad_size_collector') == 0.5
    
    def test_drc_mode_automotive(self):
        """测试车规级模式 DRC"""
        checker = DRCChecker(mode=DRCMode.AUTOMOTIVE)
        assert checker.is_igbt
        # 车规级应该有更严格的要求
    
    def test_igbt_rules_loaded(self):
        """测试 IGBT 规则正确加载"""
        checker = DRCChecker(mode=DRCMode.IGBT)
        
        # 检查 IGBT 特定规则
        assert 'min_spacing_low_voltage' in checker.rules
        assert 'min_spacing_high_voltage' in checker.rules
        assert 'max_loop_height_wire' in checker.rules
        assert 'current_density_al_wire' in checker.rules


class TestIGBTPresets:
    """IGBT 预设配置测试"""
    
    def test_high_voltage_preset(self):
        """测试高压预设"""
        rules = IGBT_RULES_HIGH_VOLTAGE
        
        assert rules.min_spacing_high_voltage == 2.5
        assert rules.min_spacing_ultra_high_voltage == 4.0
        assert rules.max_loop_height_wire == 4.0
    
    def test_automotive_preset(self):
        """测试车规级预设"""
        rules = IGBT_RULES_AUTOMOTIVE
        
        assert rules.min_spacing_medium_voltage == 1.2
        assert rules.min_spacing_high_voltage == 2.2
        assert rules.fatigue_factor_al == 1.2  # 更严格
        assert rules.max_temperature_rise == 40.0  # 更保守


class TestIGBTConverter:
    """IGBT 转换器集成测试"""
    
    def test_igbt_converter_init(self):
        """测试 IGBT 转换器初始化"""
        from bonding_converter.converter import BondingDiagramConverter
        
        # IGBT 模式
        converter = BondingDiagramConverter({
            'mode': 'igbt',
            'default_wire_diameter': 0.3,
            'default_material': 'aluminum',
        })
        
        assert converter.is_igbt
        assert converter.mode == 'igbt'
        assert converter.default_wire_diameter == 0.3
        assert converter.default_material == 'aluminum'
        assert converter.wire_type == 'al_wire'
    
    def test_igbt_loop_height_calculation(self):
        """测试 IGBT 弧高计算"""
        from bonding_converter.converter import BondingDiagramConverter
        
        # IGBT 模式
        converter_igbt = BondingDiagramConverter({'mode': 'igbt'})
        
        # 标准模式
        converter_std = BondingDiagramConverter({'mode': 'standard'})
        
        # 相同参数下，IGBT 模式应该有更大的弧高
        span = 5.0
        diameter = 0.3
        
        h_igbt = converter_igbt.calculate_loop_height(span, diameter, 'aluminum')
        h_std = converter_std.calculate_loop_height(span, diameter, 'aluminum')
        
        assert h_igbt > h_std
    
    def test_automotive_thermal_compensation(self):
        """测试车规级热膨胀补偿"""
        from bonding_converter.converter import BondingDiagramConverter
        
        # 车规级模式
        converter_auto = BondingDiagramConverter({'mode': 'automotive'})
        
        # IGBT 模式
        converter_igbt = BondingDiagramConverter({'mode': 'igbt'})
        
        span = 5.0
        diameter = 0.3
        
        h_auto = converter_auto.calculate_loop_height(span, diameter, 'aluminum')
        h_igbt = converter_igbt.calculate_loop_height(span, diameter, 'aluminum')
        
        # 车规级应该有 20% 的热膨胀补偿
        assert h_auto > h_igbt


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
