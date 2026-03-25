"""
坐标导出模块 - 支持多种打线机格式
"""

import cadquery as cq
from typing import List, Dict, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BondPoint:
    """焊点坐标"""
    x: float
    y: float
    z: float
    wire_type: int = 1  # 1=第一焊点，2=第二焊点


class CoordinateExporter:
    """坐标导出器"""
    
    def __init__(self):
        """初始化导出器"""
        self.format_handlers = {
            'KS': self._export_ks,
            'K&S': self._export_ks,
            'KULICKE': self._export_ks,
            'ASM': self._export_asm,
            'ASM_PACIFIC': self._export_asm,
            'SHINKAWA': self._export_shinkawa,
            'CMD': self._export_shinkawa,
            'CSV': self._export_csv,
        }
    
    def extract_bond_points(self, assembly: cq.Assembly) -> List[BondPoint]:
        """
        从 3D 模型提取焊点坐标
        
        Args:
            assembly: 3D 装配体
            
        Returns:
            焊点坐标列表
        """
        points = []
        
        # TODO: 实现焊点提取逻辑
        # 目前返回示例数据
        points.append(BondPoint(0.0, 0.0, 0.0, wire_type=1))
        points.append(BondPoint(5.0, 0.0, 0.5, wire_type=2))
        
        return points
    
    def export(self, assembly: cq.Assembly, output_path: str, 
               machine_type: str = 'KS') -> bool:
        """
        导出坐标文件
        
        Args:
            assembly: 3D 装配体
            output_path: 输出路径
            machine_type: 打线机类型 (KS/ASM/SHINKAWA/CSV)
            
        Returns:
            是否成功
        """
        handler = self.format_handlers.get(machine_type.upper())
        if not handler:
            print(f"不支持的格式：{machine_type}")
            return False
        
        points = self.extract_bond_points(assembly)
        return handler(points, output_path)
    
    def _export_ks(self, points: List[BondPoint], output_path: str) -> bool:
        """
        导出 K&S (Kulicke & Soffa) 格式
        
        格式示例:
        *WRF_FILE
        X1,Y1,Z1,X2,Y2,Z2,WIRE_TYPE
        """
        try:
            with open(output_path, 'w') as f:
                f.write("*WRF_FILE\n")
                f.write("; Auto-Bonding Generated\n")
                f.write("; X,Y,Z,WIRE_TYPE\n")
                
                for i, pt in enumerate(points):
                    f.write(f"{pt.x:.4f},{pt.y:.4f},{pt.z:.4f},{pt.wire_type}\n")
            
            return True
        except Exception as e:
            print(f"导出 K&S 格式失败：{e}")
            return False
    
    def _export_asm(self, points: List[BondPoint], output_path: str) -> bool:
        """
        导出 ASM Pacific 格式
        
        格式示例:
        ABS_FILE
        X=0.0000 Y=0.0000 Z=0.0000 T=1
        """
        try:
            with open(output_path, 'w') as f:
                f.write("ABS_FILE\n")
                f.write("; Auto-Bonding Generated\n")
                
                for pt in points:
                    f.write(f"X={pt.x:.4f} Y={pt.y:.4f} Z={pt.z:.4f} T={pt.wire_type}\n")
            
            return True
        except Exception as e:
            print(f"导出 ASM 格式失败：{e}")
            return False
    
    def _export_shinkawa(self, points: List[BondPoint], output_path: str) -> bool:
        """
        导出 Shinkawa 格式
        
        格式示例:
        CMD_FILE
        GOTO X0.0000 Y0.0000 Z0.0000
        """
        try:
            with open(output_path, 'w') as f:
                f.write("CMD_FILE\n")
                f.write("; Auto-Bonding Generated\n")
                
                for pt in points:
                    f.write(f"GOTO X{pt.x:.4f} Y{pt.y:.4f} Z{pt.z:.4f}\n")
            
            return True
        except Exception as e:
            print(f"导出 Shinkawa 格式失败：{e}")
            return False
    
    def _export_csv(self, points: List[BondPoint], output_path: str) -> bool:
        """
        导出 CSV 格式
        
        格式示例:
        X,Y,Z,WIRE_TYPE
        0.0000,0.0000,0.0000,1
        """
        try:
            import csv
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['X', 'Y', 'Z', 'WIRE_TYPE'])
                
                for pt in points:
                    writer.writerow([f"{pt.x:.4f}", f"{pt.y:.4f}", 
                                   f"{pt.z:.4f}", pt.wire_type])
            
            return True
        except Exception as e:
            print(f"导出 CSV 格式失败：{e}")
            return False
    
    def export_batch(self, assemblies: Dict[str, cq.Assembly], 
                     output_dir: str, machine_type: str = 'KS') -> Dict[str, bool]:
        """
        批量导出
        
        Args:
            assemblies: {文件名：装配体} 字典
            output_dir: 输出目录
            machine_type: 打线机类型
            
        Returns:
            {文件名：是否成功} 字典
        """
        results = {}
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for name, assembly in assemblies.items():
            safe_name = Path(name).stem
            output_file = output_path / f"{safe_name}.{machine_type.lower()}"
            results[name] = self.export(assembly, str(output_file), machine_type)
        
        return results
