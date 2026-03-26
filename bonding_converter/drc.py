"""
设计规则检查 (DRC) 模块

支持通用 IC 和 IGBT 功率器件的键合规则检查。
"""

import cadquery as cq
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class DRCMode(Enum):
    """DRC 检查模式"""
    STANDARD = "standard"  # 标准 IC
    IGBT = "igbt"          # IGBT 功率器件
    AUTOMOTIVE = "automotive"  # 车规级


@dataclass
class DRCViolation:
    """DRC 违规记录"""
    violation_type: str  # 'spacing', 'height', 'width', 'current', 'voltage'
    severity: str  # 'error', 'warning'
    description: str
    actual_value: float
    required_value: float
    location: Optional[Dict[str, float]] = None
    rule_category: str = "general"  # 'general', 'igbt', 'electrical', 'mechanical'


class DRCChecker:
    """设计规则检查器"""
    
    # IGBT 特定规则
    IGBT_RULES = {
        # 电压相关间距
        'min_spacing_low_voltage': 0.5,      # <100V
        'min_spacing_medium_voltage': 1.0,   # 100-600V
        'min_spacing_high_voltage': 2.0,     # 600-1200V
        'min_spacing_ultra_high_voltage': 3.0,  # >1200V
        
        # 弧高限制
        'max_loop_height_wire': 3.0,
        'max_loop_height_ribbon': 2.0,
        'min_loop_height': 0.5,
        
        # 焊盘尺寸
        'min_pad_size_emitter': 0.3,
        'min_pad_size_collector': 0.5,
        'min_pad_size_gate': 0.2,
        
        # 电流密度 (A/mm²)
        'current_density_al_wire': 300.0,
        'current_density_al_ribbon': 400.0,
        
        # 最大跨度
        'max_wire_span': 8.0,
        'max_ribbon_span': 5.0,
    }
    
    def __init__(self, rules: Optional[Dict] = None, mode: DRCMode = DRCMode.STANDARD):
        """
        初始化检查器
        
        Args:
            rules: DRC 规则配置
            mode: 检查模式（standard/igbt/automotive）
        """
        self.mode = mode
        self.is_igbt = mode in [DRCMode.IGBT, DRCMode.AUTOMOTIVE]
        
        if self.is_igbt:
            # IGBT 模式使用更严格的规则
            self.rules = {**self.IGBT_RULES, **(rules or {})}
        else:
            # 标准 IC 模式
            self.rules = {
                'min_wire_spacing': 0.1,
                'max_loop_height': 1.0,
                'min_pad_size': 0.2,
                **(rules or {})
            }
    
    def check_all(self, assembly: cq.Assembly, elements: Optional[List] = None) -> List[DRCViolation]:
        """
        运行所有 DRC 检查
        
        Args:
            assembly: 3D 装配体
            elements: 原始键合图元素（用于 IGBT 特定检查）
            
        Returns:
            违规列表
        """
        violations = []
        
        # 检查线间距
        spacing_violations = self.check_wire_spacing(assembly)
        violations.extend(spacing_violations)
        
        # 检查弧高
        height_violations = self.check_loop_height(assembly)
        violations.extend(height_violations)
        
        # 检查焊盘尺寸
        pad_violations = self.check_pad_size(assembly)
        violations.extend(pad_violations)
        
        # IGBT 特定检查
        if self.is_igbt:
            # 检查跨度
            span_violations = self.check_wire_span(assembly, elements)
            violations.extend(span_violations)
            
            # 检查电流承载能力
            current_violations = self.check_current_capacity(elements)
            violations.extend(current_violations)
            
            # 检查电压间距
            if elements:
                voltage_violations = self.check_voltage_spacing(elements)
                violations.extend(voltage_violations)
        
        return violations
    
    def check_wire_spacing(self, assembly: cq.Assembly) -> List[DRCViolation]:
        """
        检查引线间距
        
        Args:
            assembly: 3D 装配体
            
        Returns:
            违规列表
        """
        violations = []
        
        # 获取所有实体
        solids = assembly.solids().vals()
        
        for i, solid1 in enumerate(solids):
            for j, solid2 in enumerate(solids[i+1:], i+1):
                try:
                    # 计算最小距离
                    distance = solid1.distToShape(solid2)[0]
                    
                    if distance < self.rules['min_wire_spacing']:
                        violations.append(DRCViolation(
                            violation_type='spacing',
                            severity='error',
                            description=f"引线 {i} 和 {j} 间距过小",
                            actual_value=distance,
                            required_value=self.rules['min_wire_spacing'],
                            location=None
                        ))
                except Exception:
                    # 实体可能相交
                    violations.append(DRCViolation(
                        violation_type='spacing',
                        severity='error',
                        description=f"引线 {i} 和 {j} 相交",
                        actual_value=0.0,
                        required_value=self.rules['min_wire_spacing'],
                        location=None
                    ))
        
        return violations
    
    def check_loop_height(self, assembly: cq.Assembly) -> List[DRCViolation]:
        """
        检查引线弧高
        
        Args:
            assembly: 3D 装配体
            
        Returns:
            违规列表
        """
        violations = []
        
        solids = assembly.solids().vals()
        
        for i, solid in enumerate(solids):
            bbox = solid.BoundingBox()
            height = bbox.zlen
            
            if height > self.rules['max_loop_height']:
                violations.append(DRCViolation(
                    violation_type='height',
                    severity='warning',
                    description=f"引线 {i} 弧高超出限制",
                    actual_value=height,
                    required_value=self.rules['max_loop_height'],
                    location={'z_max': bbox.zmax}
                ))
        
        return violations
    
    def check_pad_size(self, assembly: cq.Assembly) -> List[DRCViolation]:
        """
        检查焊盘尺寸
        
        Args:
            assembly: 3D 装配体
            
        Returns:
            违规列表
        """
        violations = []
        
        if self.is_igbt:
            # IGBT 模式检查不同焊盘类型
            solids = assembly.solids().vals()
            for i, solid in enumerate(solids):
                bbox = solid.BoundingBox()
                min_dim = min(bbox.xlen, bbox.ylen)
                
                # 根据焊盘类型检查
                pad_type = getattr(solid, 'pad_type', 'emitter')
                if pad_type == 'emitter' and min_dim < self.rules.get('min_pad_size_emitter', 0.3):
                    violations.append(DRCViolation(
                        violation_type='pad_size',
                        severity='error',
                        description=f"发射极焊盘 {i} 尺寸过小",
                        actual_value=min_dim,
                        required_value=self.rules['min_pad_size_emitter'],
                        rule_category='igbt'
                    ))
                elif pad_type == 'collector' and min_dim < self.rules.get('min_pad_size_collector', 0.5):
                    violations.append(DRCViolation(
                        violation_type='pad_size',
                        severity='error',
                        description=f"集电极焊盘 {i} 尺寸过小",
                        actual_value=min_dim,
                        required_value=self.rules['min_pad_size_collector'],
                        rule_category='igbt'
                    ))
                elif pad_type == 'gate' and min_dim < self.rules.get('min_pad_size_gate', 0.2):
                    violations.append(DRCViolation(
                        violation_type='pad_size',
                        severity='warning',
                        description=f"栅极焊盘 {i} 尺寸过小",
                        actual_value=min_dim,
                        required_value=self.rules['min_pad_size_gate'],
                        rule_category='igbt'
                    ))
        else:
            # 标准模式
            solids = assembly.solids().vals()
            for i, solid in enumerate(solids):
                bbox = solid.BoundingBox()
                min_dim = min(bbox.xlen, bbox.ylen)
                if min_dim < self.rules.get('min_pad_size', 0.2):
                    violations.append(DRCViolation(
                        violation_type='pad_size',
                        severity='error',
                        description=f"焊盘 {i} 尺寸过小",
                        actual_value=min_dim,
                        required_value=self.rules['min_pad_size'],
                    ))
        
        return violations
    
    def check_wire_span(self, assembly: cq.Assembly, elements: Optional[List] = None) -> List[DRCViolation]:
        """
        检查引线跨度（IGBT 特定）
        
        跨度过大需要中间支撑或改用铝带
        
        Args:
            assembly: 3D 装配体
            elements: 键合图元素
            
        Returns:
            违规列表
        """
        violations = []
        
        if not elements:
            return violations
        
        for elem in elements:
            if elem.element_type == 'wire':
                p1 = elem.geometry.get('p1', [0, 0, 0])
                p2 = elem.geometry.get('p2', [0, 0, 0])
                
                # 计算跨度
                span = ((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2) ** 0.5
                
                wire_type = elem.properties.get('wire_type', 'al_wire')
                max_span = self.rules.get(
                    'max_ribbon_span' if wire_type == 'al_ribbon' else 'max_wire_span',
                    8.0
                )
                
                if span > max_span:
                    violations.append(DRCViolation(
                        violation_type='span',
                        severity='error',
                        description=f"引线跨度过大 ({span:.2f}mm)，需要中间支撑或改用铝带",
                        actual_value=span,
                        required_value=max_span,
                        rule_category='igbt'
                    ))
        
        return violations
    
    def check_current_capacity(self, elements: Optional[List] = None) -> List[DRCViolation]:
        """
        检查电流承载能力（IGBT 特定）
        
        Args:
            elements: 键合图元素
            
        Returns:
            违规列表
        """
        violations = []
        
        if not elements:
            return violations
        
        for elem in elements:
            if elem.element_type == 'wire':
                wire_diameter = elem.properties.get('wire_diameter', 0.3)
                wire_type = elem.properties.get('wire_type', 'al_wire')
                expected_current = elem.properties.get('expected_current', 0)
                
                # 计算截面积
                if wire_type == 'al_ribbon':
                    # 铝带：宽×厚
                    width = elem.properties.get('ribbon_width', 1.0)
                    thickness = elem.properties.get('ribbon_thickness', 0.1)
                    cross_section = width * thickness
                    density = self.rules.get('current_density_al_ribbon', 400.0)
                else:
                    # 圆线
                    cross_section = 3.14159 * (wire_diameter / 2) ** 2
                    density = self.rules.get('current_density_al_wire', 300.0)
                
                max_current = cross_section * density
                
                if expected_current > 0 and expected_current > max_current:
                    violations.append(DRCViolation(
                        violation_type='current',
                        severity='error',
                        description=f"电流承载能力不足：预期{expected_current:.1f}A > 最大{max_current:.1f}A",
                        actual_value=expected_current,
                        required_value=max_current,
                        rule_category='electrical'
                    ))
        
        return violations
    
    def check_voltage_spacing(self, elements: Optional[List] = None) -> List[DRCViolation]:
        """
        检查电压相关间距（IGBT 特定）
        
        根据工作电压确定最小电气间距
        
        Args:
            elements: 键合图元素
            
        Returns:
            违规列表
        """
        violations = []
        
        if not elements:
            return violations
        
        # 获取工作电压
        operating_voltage = max(
            [elem.properties.get('operating_voltage', 0) for elem in elements],
            default=600
        )
        
        # 确定最小间距要求
        if operating_voltage <= 100:
            min_spacing = self.rules.get('min_spacing_low_voltage', 0.5)
        elif operating_voltage <= 600:
            min_spacing = self.rules.get('min_spacing_medium_voltage', 1.0)
        elif operating_voltage <= 1200:
            min_spacing = self.rules.get('min_spacing_high_voltage', 2.0)
        else:
            min_spacing = self.rules.get('min_spacing_ultra_high_voltage', 3.0)
        
        # 检查实际间距
        for i, elem1 in enumerate(elements):
            for j, elem2 in enumerate(elements[i+1:], i+1):
                if elem1.element_type == 'wire' and elem2.element_type == 'wire':
                    p1 = elem1.geometry.get('p1', [0, 0, 0])
                    p2 = elem2.geometry.get('p1', [0, 0, 0])
                    
                    distance = ((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2) ** 0.5
                    
                    if distance < min_spacing:
                        violations.append(DRCViolation(
                            violation_type='voltage_spacing',
                            severity='error',
                            description=f"电压间距不足 ({operating_voltage}V): 实际{distance:.2f}mm < 要求{min_spacing:.2f}mm",
                            actual_value=distance,
                            required_value=min_spacing,
                            rule_category='electrical'
                        ))
        
        return violations
    
    def run_and_report(self, assembly: cq.Assembly) -> Dict[str, Any]:
        """
        运行 DRC 并生成报告
        
        Args:
            assembly: 3D 装配体
            
        Returns:
            检查报告
        """
        violations = self.check_all(assembly)
        
        errors = [v for v in violations if v.severity == 'error']
        warnings = [v for v in violations if v.severity == 'warning']
        
        report = {
            'passed': len(violations) == 0,
            'total_violations': len(violations),
            'errors': len(errors),
            'warnings': len(warnings),
            'violations': violations,
        }
        
        return report
    
    def print_report(self, report: Dict[str, Any]):
        """打印 DRC 报告"""
        if report['passed']:
            print("✅ DRC 检查通过!")
        else:
            print(f"❌ DRC 检查失败：{report['errors']} 个错误，{report['warnings']} 个警告")
            
            if report['errors'] > 0:
                print("\n错误:")
                for v in [vi for vi in report['violations'] if vi.severity == 'error']:
                    print(f"  - {v.description} (实际：{v.actual_value:.4f}, 要求：{v.required_value:.4f})")
            
            if report['warnings'] > 0:
                print("\n警告:")
                for v in [vi for vi in report['violations'] if vi.severity == 'warning']:
                    print(f"  - {v.description} (实际：{v.actual_value:.4f}, 要求：{v.required_value:.4f})")