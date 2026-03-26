"""
IGBT 功率器件键合规则配置

IGBT（绝缘栅双极晶体管）作为高压大电流功率器件，
键合设计需要满足特殊的电气和机械要求。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class IGBTPadType(Enum):
    """IGBT 焊盘类型"""
    EMITTER = "emitter"      # 发射极（大电流）
    COLLECTOR = "collector"  # 集电极（高压）
    GATE = "gate"            # 栅极（控制信号）
    SENSE = "sense"          # 检测焊盘
    DUMMY = "dummy"          #  dummy 焊盘（应力释放）


class WireType(Enum):
    """引线类型"""
    AL_WIRE = "al_wire"           # 铝线（100-500μm）
    AL_RIBBON = "al_ribbon"       # 铝带（大电流）
    CU_WIRE = "cu_wire"           # 铜线
    AU_WIRE = "au_wire"           # 金线（信号）


@dataclass
class IGBTRules:
    """
    IGBT 键合设计规则
    
    基于行业标准和经验值：
    - IPC-7530: 功率器件键合指南
    - JEDEC JESD22: 可靠性测试标准
    - 厂商设计规范（Infineon, Fuji, Mitsubishi 等）
    """
    
    # ========== 电气规则 ==========
    
    # 最小电气间距（mm）- 根据电压等级
    min_spacing_low_voltage: float = 0.5    # <100V
    min_spacing_medium_voltage: float = 1.0  # 100-600V
    min_spacing_high_voltage: float = 2.0    # 600-1200V
    min_spacing_ultra_high_voltage: float = 3.0  # >1200V
    
    # 电压等级阈值（V）
    voltage_threshold_low: float = 100.0
    voltage_threshold_medium: float = 600.0
    voltage_threshold_high: float = 1200.0
    
    # ========== 机械规则 ==========
    
    # 弧高系数（不同材料）
    loop_height_coefficient_al_wire: float = 2.0      # 铝线
    loop_height_coefficient_al_ribbon: float = 1.5    # 铝带
    loop_height_coefficient_cu_wire: float = 1.8      # 铜线
    
    # 最大弧高限制（mm）
    max_loop_height_wire: float = 3.0
    max_loop_height_ribbon: float = 2.0
    
    # 最小弧高（避免塌丝）
    min_loop_height: float = 0.5
    
    # ========== 焊盘规则 ==========
    
    # 最小焊盘尺寸（mm）
    min_pad_size_emitter: float = 0.3    # 发射极（大电流）
    min_pad_size_collector: float = 0.5  # 集电极（高压）
    min_pad_size_gate: float = 0.2       # 栅极（信号）
    
    # 焊盘间距（mm）
    min_pad_spacing_same_net: float = 0.3
    min_pad_spacing_diff_net: float = 0.8
    
    # ========== 引线规则 ==========
    
    # 标准线径（mm）
    standard_wire_diameters: List[float] = field(default_factory=lambda: [
        0.100,  # 100μm
        0.150,  # 150μm
        0.200,  # 200μm
        0.250,  # 250μm
        0.300,  # 300μm
        0.375,  # 375μm
        0.400,  # 400μm
        0.500,  # 500μm
    ])
    
    # 标准铝带尺寸（宽×厚 mm）
    standard_ribbon_sizes: List[tuple] = field(default_factory=lambda: [
        (0.5, 0.05),   # 500×50μm
        (1.0, 0.075),  # 1000×75μm
        (1.5, 0.10),   # 1500×100μm
        (2.0, 0.125),  # 2000×125μm
        (2.5, 0.15),   # 2500×150μm
        (3.0, 0.20),   # 3000×200μm
    ])
    
    # 最大跨度（mm）- 超过此值需要中间支撑
    max_wire_span: float = 8.0
    max_ribbon_span: float = 5.0
    
    # ========== 电流规则 ==========
    
    # 电流承载能力（A/mm²）- 经验值
    current_density_al_wire: float = 300.0    # 铝线
    current_density_al_ribbon: float = 400.0  # 铝带（散热更好）
    current_density_cu_wire: float = 500.0    # 铜线
    current_density_au_wire: float = 200.0    # 金线
    
    # 温升限制（°C）
    max_temperature_rise: float = 50.0
    
    # ========== 可靠性规则 ==========
    
    # 最小键合强度（gf）
    min_bond_strength_wire: float = 50.0
    min_bond_strength_ribbon: float = 200.0
    
    # 疲劳寿命系数
    fatigue_factor_al: float = 1.0
    fatigue_factor_cu: float = 1.2
    fatigue_factor_au: float = 0.8
    
    # ========== 热膨胀匹配 ==========
    
    # 热膨胀系数（ppm/°C）
    cte_aluminum: float = 23.0
    cte_copper: float = 17.0
    cte_gold: float = 14.0
    cte_silicon: float = 2.6
    cte_al2o3: float = 7.0  # 陶瓷基板
    
    # 最大 CTE 失配容忍度（ppm/°C）
    max_cte_mismatch: float = 15.0
    
    def get_min_spacing_for_voltage(self, voltage: float) -> float:
        """根据工作电压获取最小间距"""
        if voltage <= self.voltage_threshold_low:
            return self.min_spacing_low_voltage
        elif voltage <= self.voltage_threshold_medium:
            return self.min_spacing_medium_voltage
        elif voltage <= self.voltage_threshold_high:
            return self.min_spacing_high_voltage
        else:
            return self.min_spacing_ultra_high_voltage
    
    def get_current_capacity(self, wire_diameter: float, wire_type: WireType) -> float:
        """
        计算引线电流承载能力
        
        Args:
            wire_diameter: 线径（mm）
            wire_type: 引线类型
            
        Returns:
            最大电流（A）
        """
        cross_section = 3.14159 * (wire_diameter / 2) ** 2
        
        if wire_type == WireType.AL_WIRE:
            density = self.current_density_al_wire
        elif wire_type == WireType.AL_RIBBON:
            density = self.current_density_al_ribbon
        elif wire_type == WireType.CU_WIRE:
            density = self.current_density_cu_wire
        else:
            density = self.current_density_au_wire
        
        return cross_section * density
    
    def get_loop_height_coefficient(self, wire_type: WireType) -> float:
        """获取弧高系数"""
        if wire_type == WireType.AL_WIRE:
            return self.loop_height_coefficient_al_wire
        elif wire_type == WireType.AL_RIBBON:
            return self.loop_height_coefficient_al_ribbon
        elif wire_type == WireType.CU_WIRE:
            return self.loop_height_coefficient_cu_wire
        else:
            return 1.5
    
    def validate_pad_type(self, pad_type: IGBTPadType, pad_size: float) -> List[str]:
        """
        验证焊盘尺寸是否符合类型要求
        
        Returns:
            违规列表
        """
        violations = []
        
        if pad_type == IGBTPadType.EMITTER:
            if pad_size < self.min_pad_size_emitter:
                violations.append(
                    f"发射极焊盘尺寸 {pad_size:.3f}mm < 最小 {self.min_pad_size_emitter:.3f}mm"
                )
        elif pad_type == IGBTPadType.COLLECTOR:
            if pad_size < self.min_pad_size_collector:
                violations.append(
                    f"集电极焊盘尺寸 {pad_size:.3f}mm < 最小 {self.min_pad_size_collector:.3f}mm"
                )
        elif pad_type == IGBTPadType.GATE:
            if pad_size < self.min_pad_size_gate:
                violations.append(
                    f"栅极焊盘尺寸 {pad_size:.3f}mm < 最小 {self.min_pad_size_gate:.3f}mm"
                )
        
        return violations


# 预设配置
IGBT_RULES_DEFAULT = IGBTRules()

IGBT_RULES_HIGH_VOLTAGE = IGBTRules(
    min_spacing_high_voltage=2.5,
    min_spacing_ultra_high_voltage=4.0,
    max_loop_height_wire=4.0,
)

IGBT_RULES_AUTOMOTIVE = IGBTRules(
    min_spacing_medium_voltage=1.2,
    min_spacing_high_voltage=2.2,
    fatigue_factor_al=1.2,  # 车规级更严格
    max_temperature_rise=40.0,
)
