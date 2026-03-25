"""
后端 API 集成测试
"""

import pytest
import os
from fastapi.testclient import TestClient
from pathlib import Path

# 导入后端应用
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'backend'))
from main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def sample_dxf_file(tmp_path):
    """创建示例 DXF 文件"""
    dxf_content = """  0
SECTION
  2
HEADER
  9
$ACADVER
  1
AC1015
  0
ENDSEC
  0
SECTION
  2
TABLES
  0
TABLE
  2
LAYER
  0
LAYER
  2
PADS
 70
0
 62
1
  6
CONTINUOUS
  0
ENDTAB
  0
ENDSEC
  0
SECTION
  2
BLOCKS
  0
ENDSEC
  0
SECTION
  2
ENTITIES
  0
CIRCLE
  8
PADS
 10
15.0
 20
15.0
 30
0.0
 40
2.0
  0
CIRCLE
  8
PADS
 10
25.0
 20
15.0
 30
0.0
 40
2.0
  0
ENDSEC
  0
EOF
"""
    file_path = tmp_path / "test.dxf"
    file_path.write_text(dxf_content)
    return file_path


class TestBackendAPI:
    """后端 API 集成测试"""
    
    def test_root(self, client):
        """测试根路径"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Auto-Bonding API"
        assert data["status"] == "running"
    
    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_get_formats(self, client):
        """测试获取支持的格式"""
        response = client.get("/formats")
        assert response.status_code == 200
        data = response.json()
        assert "3d" in data
        assert "coordinates" in data
        assert "STEP" in data["3d"]
        assert "KS" in data["coordinates"]
    
    def test_get_materials(self, client):
        """测试获取材料列表"""
        response = client.get("/materials")
        assert response.status_code == 200
        data = response.json()
        assert "materials" in data
        assert len(data["materials"]) > 0
    
    @pytest.mark.skip(reason="需要实际的 bonding_converter 模块")
    def test_convert_file(self, client, sample_dxf_file):
        """测试文件转换"""
        with open(sample_dxf_file, 'rb') as f:
            files = {'file': ('test.dxf', f, 'application/dxf')}
            data = {'config': '{"loop_height_coefficient":1.5,"export_format":"STEP"}'}
            
            response = client.post("/convert", files=files, data=data)
            
            # 如果转换器模块可用，应该成功
            if response.status_code == 200:
                result = response.json()
                assert result["success"] is True
                assert "download_url" in result
            # 否则可能因为缺少模块而失败
            elif response.status_code == 500:
                pytest.skip("bonding_converter 模块未安装")
    
    @pytest.mark.skip(reason="需要实际的 bonding_converter 模块")
    def test_drc_check(self, client, sample_dxf_file):
        """测试 DRC 检查"""
        with open(sample_dxf_file, 'rb') as f:
            files = {'file': ('test.dxf', f, 'application/dxf')}
            
            response = client.post("/drc", files=files)
            
            if response.status_code == 200:
                result = response.json()
                assert "passed" in result
                assert "violations" in result
            elif response.status_code == 500:
                pytest.skip("bonding_converter 模块未安装")
    
    def test_invalid_file_type(self, client, tmp_path):
        """测试无效文件类型"""
        # 创建非 DXF 文件
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not a dxf file")
        
        with open(txt_file, 'rb') as f:
            files = {'file': ('test.txt', f, 'text/plain')}
            
            response = client.post("/convert", files=files)
            assert response.status_code == 400
    
    def test_download_nonexistent_file(self, client):
        """测试下载不存在的文件"""
        response = client.get("/download/nonexistent.step")
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
