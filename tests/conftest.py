"""
pytest 配置
"""

import pytest
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def pytest_configure(config):
    """pytest 配置"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


@pytest.fixture(scope="session")
def test_config():
    """测试配置"""
    return {
        "min_wire_spacing": 0.1,
        "max_loop_height": 1.0,
        "min_pad_size": 0.2,
        "loop_height_coefficient": 1.5,
        "default_wire_diameter": 0.025,
    }
