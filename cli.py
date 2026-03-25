#!/usr/bin/env python3
"""
Auto-Bonding 命令行工具

使用示例:
    # 批量转换
    python cli.py --input ./dwg_files --output ./output --format KS
    
    # 单个文件
    python cli.py -i sample.dxf -o output.step --format STEP
    
    # DRC 检查
    python cli.py -i sample.dxf --drc
"""

import argparse
import sys
from pathlib import Path

from bonding_converter import BondingDiagramConverter, DXFParser, CoordinateExporter
from bonding_converter.drc import DRCChecker


def main():
    parser = argparse.ArgumentParser(
        description="Auto-Bonding - 键合图自动转换工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '-i', '--input',
        nargs='+',
        required=True,
        help='输入文件 (DXF/DWG) 或目录'
    )
    
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='输出目录或文件路径'
    )
    
    parser.add_argument(
        '-f', '--format',
        choices=['STEP', 'KS', 'ASM', 'SHINKAWA', 'CSV'],
        default='STEP',
        help='导出格式 (默认：STEP)'
    )
    
    parser.add_argument(
        '--loop-height',
        type=float,
        default=1.5,
        help='弧高系数 (默认：1.5)'
    )
    
    parser.add_argument(
        '--wire-diameter',
        type=float,
        default=0.025,
        help='线径 mm (默认：0.025)'
    )
    
    parser.add_argument(
        '--material',
        choices=['gold', 'copper', 'aluminum', 'silver'],
        default='gold',
        help='材料类型 (默认：gold)'
    )
    
    parser.add_argument(
        '--drc',
        action='store_true',
        help='运行 DRC 检查'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='详细输出'
    )
    
    args = parser.parse_args()
    
    # 配置
    config = {
        'loop_height_coefficient': args.loop_height,
        'default_wire_diameter': args.wire_diameter,
        'default_material': args.material,
    }
    
    # 收集输入文件
    input_files = []
    for input_path in args.input:
        path = Path(input_path)
        if path.is_dir():
            input_files.extend(list(path.glob('*.dxf')))
            input_files.extend(list(path.glob('*.DXF')))
        elif path.is_file():
            input_files.append(path)
        else:
            print(f"警告：{input_path} 不存在")
    
    if not input_files:
        print("错误：未找到输入文件")
        sys.exit(1)
    
    print(f"找到 {len(input_files)} 个输入文件")
    
    # 创建转换器
    converter = BondingDiagramConverter(config)
    exporter = CoordinateExporter()
    
    # 输出目录
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 处理每个文件
    success_count = 0
    for input_file in input_files:
        print(f"\n处理：{input_file.name}")
        
        try:
            # 解析 DXF
            dxf_parser = DXFParser()
            elements = dxf_parser.parse_file(str(input_file))
            print(f"  解析到 {len(elements)} 个元素")
            
            # 转换为 3D
            assembly = converter.convert_elements(elements)
            
            # DRC 检查
            if args.drc:
                drc_checker = DRCChecker()
                report = drc_checker.run_and_report(assembly)
                drc_checker.print_report(report)
                
                if not report['passed']:
                    print("  ⚠️ DRC 检查未通过，继续转换...")
            
            # 导出
            if args.format == 'STEP':
                output_file = output_path / f"{input_file.stem}.step"
                converter.export_step(assembly, str(output_file))
                print(f"  ✅ 导出：{output_file}")
            else:
                output_file = output_path / f"{input_file.stem}.{args.format.lower()}"
                exporter.export(assembly, str(output_file), args.format)
                print(f"  ✅ 导出：{output_file}")
            
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ 失败：{e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
    
    # 总结
    print(f"\n{'='*50}")
    print(f"完成：{success_count}/{len(input_files)} 个文件成功")
    
    if success_count == len(input_files):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
