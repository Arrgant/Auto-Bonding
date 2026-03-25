"""
设计规则检查 (DRC) 模块
"""

import cadquery as cq
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class DRCViolation:
    """DRC 违规记录"""
    violation_type: str  # 'spacing', 'height', 'width'
    severity: str  # 'error', 'warning'
    description: str
    actual_value: float
    required_value: float
    location: Optional[Dict[str, float]] = None


class DRCChecker:
    """设计规则检查器"""
    
    def __init__(self, rules: Optional[Dict] = None):
        """
        初始化检查器
        
        Args:
            rules: DRC 规则
                - min_wire_spacing: 最小线间距 (mm)
                - max_loop_height: 最大弧高 (mm)
                - min_pad_size: 最小焊盘尺寸 (mm)
        """
        self.rules = rules or {
            'min_wire_spacing': 0.1,
            'max_loop_height': 1.0,
            'min_pad_size': 0.2,
        }
    
    def check_all(self, assembly: cq.Assembly) -> List[DRCViolation]:
        """
        运行所有 DRC 检查
        
        Args:
            assembly: 3D 装配体
            
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
        
        # TODO: 实现焊盘尺寸检查
        
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