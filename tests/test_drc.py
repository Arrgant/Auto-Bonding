"""
DRC (Design Rule Check) 单元测试
"""

import pytest
import cadquery as cq
from bonding_converter.drc import DRCChecker, DRCViolation, ViolationSeverity
from bonding_converter.converter import BondingDiagramConverter, BondingElement


class TestDRCChecker:
    """DRC 检查器测试"""
    
    def test_init(self):
        """测试初始化"""
        checker = DRCChecker()
        assert checker.min_wire_spacing == 0.1
        assert checker.max_loop_height == 1.0
        assert checker.min_pad_size == 0.2
    
    def test_init_with_rules(self):
        """测试自定义规则初始化"""
        rules = {
            'min_wire_spacing': 0.15,
            'max_loop_height': 1.5,
            'min_pad_size': 0.3,
        }
        checker = DRCChecker(rules)
        assert checker.min_wire_spacing == 0.15
        assert checker.max_loop_height == 1.5
        assert checker.min_pad_size == 0.3
    
    def test_check_wire_spacing_pass(self):
        """测试线间距检查 - 通过"""
        checker = DRCChecker({'min_wire_spacing': 0.1})
        
        # 创建两个间距足够的焊点
        assembly = cq.Assembly()
        assembly.add(cq.Workplane().sphere(0.05), loc=cq.Location((0, 0, 0)))
        assembly.add(cq.Workplane().sphere(0.05), loc=cq.Location((0.5, 0, 0)))
        
        violations = checker.check_wire_spacing(assembly)
        assert len(violations) == 0
    
    def test_check_wire_spacing_fail(self):
        """测试线间距检查 - 失败"""
        checker = DRCChecker({'min_wire_spacing': 0.5})
        
        # 创建两个间距不足的焊点
        assembly = cq.Assembly()
        assembly.add(cq.Workplane().sphere(0.05), loc=cq.Location((0, 0, 0)))
        assembly.add(cq.Workplane().sphere(0.05), loc=cq.Location((0.2, 0, 0)))
        
        violations = checker.check_wire_spacing(assembly)
        assert len(violations) > 0
        assert violations[0].violation_type == 'wire_spacing'
    
    def test_check_loop_height_pass(self):
        """测试弧高检查 - 通过"""
        checker = DRCChecker({'max_loop_height': 1.0})
        
        # 创建合理的弧高
        assembly = cq.Assembly()
        assembly.add(cq.Workplane().sphere(0.05), loc=cq.Location((0, 0, 0.5)))
        
        violations = checker.check_loop_height(assembly)
        assert len(violations) == 0
    
    def test_check_loop_height_fail(self):
        """测试弧高检查 - 失败"""
        checker = DRCChecker({'max_loop_height': 0.5})
        
        # 创建过高的弧
        assembly = cq.Assembly()
        assembly.add(cq.Workplane().sphere(0.05), loc=cq.Location((0, 0, 1.0)))
        
        violations = checker.check_loop_height(assembly)
        assert len(violations) > 0
        assert violations[0].violation_type == 'loop_height'
    
    def test_check_pad_size_pass(self):
        """测试焊盘尺寸检查 - 通过"""
        checker = DRCChecker({'min_pad_size': 0.1})
        
        # 创建足够大的焊盘
        assembly = cq.Assembly()
        assembly.add(cq.Workplane().box(0.5, 0.5, 0.1), loc=cq.Location((0, 0, 0)))
        
        violations = checker.check_pad_size(assembly)
        assert len(violations) == 0
    
    def test_check_pad_size_fail(self):
        """测试焊盘尺寸检查 - 失败"""
        checker = DRCChecker({'min_pad_size': 0.5})
        
        # 创建过小的焊盘
        assembly = cq.Assembly()
        assembly.add(cq.Workplane().box(0.2, 0.2, 0.1), loc=cq.Location((0, 0, 0)))
        
        violations = checker.check_pad_size(assembly)
        assert len(violations) > 0
        assert violations[0].violation_type == 'pad_size'
    
    def test_run_and_report(self):
        """测试完整 DRC 检查和报告"""
        checker = DRCChecker({
            'min_wire_spacing': 0.1,
            'max_loop_height': 1.0,
            'min_pad_size': 0.2,
        })
        
        # 创建测试装配
        converter = BondingDiagramConverter()
        elements = [
            BondingElement(
                element_type='die_pad',
                layer='DIE',
                geometry={'x': 0, 'y': 0, 'z': 0, 'width': 1.0, 'height': 1.0},
                properties={'thickness': 0.1}
            ),
        ]
        assembly = converter.convert_elements(elements)
        
        report = checker.run_and_report(assembly)
        
        assert 'passed' in report
        assert 'total_violations' in report
        assert 'errors' in report
        assert 'warnings' in report
        assert 'violations' in report
    
    def test_violation_severity(self):
        """测试违规严重程度"""
        violation = DRCViolation(
            violation_type='wire_spacing',
            severity=ViolationSeverity.ERROR,
            description='线间距过小',
            actual_value=0.05,
            required_value=0.1,
        )
        
        assert violation.severity == ViolationSeverity.ERROR
        assert violation.is_error()
        assert not violation.is_warning()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
