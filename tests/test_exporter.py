"""
导出器单元测试
"""

import pytest
import tempfile
import os
from pathlib import Path

from bonding_converter.exporter import CoordinateExporter, BondPoint


class TestCoordinateExporter:
    """导出器测试"""
    
    def test_init(self):
        """测试初始化"""
        exporter = CoordinateExporter()
        assert 'KS' in exporter.format_handlers
        assert 'ASM' in exporter.format_handlers
        assert 'SHINKAWA' in exporter.format_handlers
        assert 'CSV' in exporter.format_handlers
    
    def test_export_ks(self):
        """测试 K&S 格式导出"""
        exporter = CoordinateExporter()
        
        points = [
            BondPoint(0.0, 0.0, 0.0, wire_type=1),
            BondPoint(5.0, 0.0, 0.5, wire_type=2),
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.wrf', delete=False) as f:
            temp_path = f.name
        
        try:
            result = exporter._export_ks(points, temp_path)
            assert result is True
            
            # 验证文件内容
            with open(temp_path, 'r') as f:
                content = f.read()
                assert '*WRF_FILE' in content
                assert '0.0000,0.0000,0.0000,1' in content
                assert '5.0000,0.0000,0.5000,2' in content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_export_asm(self):
        """测试 ASM 格式导出"""
        exporter = CoordinateExporter()
        
        points = [
            BondPoint(1.0, 2.0, 3.0, wire_type=1),
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.abs', delete=False) as f:
            temp_path = f.name
        
        try:
            result = exporter._export_asm(points, temp_path)
            assert result is True
            
            with open(temp_path, 'r') as f:
                content = f.read()
                assert 'ABS_FILE' in content
                assert 'X=1.0000 Y=2.0000 Z=3.0000 T=1' in content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_export_shinkawa(self):
        """测试 Shinkawa 格式导出"""
        exporter = CoordinateExporter()
        
        points = [
            BondPoint(10.0, 20.0, 30.0, wire_type=1),
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cmd', delete=False) as f:
            temp_path = f.name
        
        try:
            result = exporter._export_shinkawa(points, temp_path)
            assert result is True
            
            with open(temp_path, 'r') as f:
                content = f.read()
                assert 'CMD_FILE' in content
                assert 'GOTO X10.0000 Y20.0000 Z30.0000' in content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_export_csv(self):
        """测试 CSV 格式导出"""
        exporter = CoordinateExporter()
        
        points = [
            BondPoint(1.5, 2.5, 3.5, wire_type=1),
            BondPoint(4.5, 5.5, 6.5, wire_type=2),
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_path = f.name
        
        try:
            result = exporter._export_csv(points, temp_path)
            assert result is True
            
            with open(temp_path, 'r') as f:
                content = f.read()
                assert 'X,Y,Z,WIRE_TYPE' in content
                assert '1.5000,2.5000,3.5000,1' in content
                assert '4.5000,5.5000,6.5000,2' in content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_export_unsupported_format(self):
        """测试不支持的格式"""
        exporter = CoordinateExporter()
        
        points = [BondPoint(0, 0, 0)]
        
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            temp_path = f.name
        
        try:
            result = exporter.export_file(points, temp_path, 'UNSUPPORTED')
            assert result is False
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
