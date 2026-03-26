"""
Auto-Bonding FastAPI 后端
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import tempfile
import os
import shutil
from pathlib import Path
import uuid

from bonding_converter import BondingDiagramConverter, DXFParser, CoordinateExporter
from bonding_converter.drc import DRCChecker

app = FastAPI(
    title="Auto-Bonding API",
    description="键合图转换服务",
    version="0.2.0"
)

# CORS 配置
# 生产环境应改为具体域名
ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",") if origin.strip()]

# 安全配置
ALLOW_CREDENTIALS = os.getenv("ALLOW_CREDENTIALS", "true").lower() == "true"
ALLOWED_METHODS = os.getenv("ALLOWED_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
ALLOWED_HEADERS = os.getenv("ALLOWED_HEADERS", "Content-Type,Authorization").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS and ALLOWED_ORIGINS != ["*"] else ["*"],
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
)

# 临时文件存储目录
TEMP_DIR = Path(os.getenv("TEMP_DIR", tempfile.gettempdir())) / "auto-bonding"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# 文件保留时间（秒）
FILE_RETENTION_SECONDS = int(os.getenv("FILE_RETENTION_SECONDS", "3600"))

# 上传限制
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE", "50"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024


class ConversionConfig(BaseModel):
    """转换配置"""
    loop_height_coefficient: float = 1.5
    default_wire_diameter: float = 0.025
    default_material: str = "gold"
    export_format: str = "STEP"  # STEP, KS, ASM, SHINKAWA, CSV
    
    # IGBT 特定配置
    mode: str = "standard"  # standard, igbt, automotive
    operating_voltage: float = 600.0  # IGBT 工作电压
    expected_current: float = 0.0     # 预期电流 (A)
    wire_type: str = "al_wire"        # al_wire, al_ribbon, cu_wire


class DRCRules(BaseModel):
    """DRC 规则"""
    min_wire_spacing: float = 0.1
    max_loop_height: float = 1.0
    min_pad_size: float = 0.2
    
    # IGBT 特定规则
    mode: str = "standard"  # standard, igbt, automotive
    operating_voltage: float = 600.0
    min_spacing_override: Optional[float] = None


class ConversionResponse(BaseModel):
    """转换响应"""
    success: bool
    message: str
    file_id: Optional[str] = None
    download_url: Optional[str] = None
    drc_report: Optional[dict] = None


class BatchResultItem(BaseModel):
    """批量转换结果项"""
    filename: str
    success: bool
    message: str
    file_id: Optional[str] = None
    download_url: Optional[str] = None


class BatchConversionResponse(BaseModel):
    """批量转换响应"""
    total: int
    success_count: int
    failed_count: int
    results: List[BatchResultItem]


@app.get("/")
def root():
    """API 根路径"""
    return {
        "name": "Auto-Bonding API",
        "version": "0.2.0",
        "status": "running"
    }


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "healthy"}


def _generate_file_id() -> str:
    """生成唯一文件 ID"""
    return str(uuid.uuid4())


def _cleanup_old_files():
    """清理过期文件"""
    import time
    current_time = time.time()
    for file_path in TEMP_DIR.glob("*"):
        if file_path.is_file():
            file_age = current_time - file_path.stat().st_mtime
            if file_age > FILE_RETENTION_SECONDS:
                try:
                    file_path.unlink()
                except Exception:
                    pass


@app.post("/convert", response_model=ConversionResponse)
async def convert_file(
    file: UploadFile = File(...),
    config: ConversionConfig = None
):
    """
    转换单个文件
    
    - **file**: DXF 文件
    - **config**: 转换配置
    """
    if not file.filename.lower().endswith('.dxf'):
        raise HTTPException(status_code=400, detail="仅支持 DXF 文件")
    
    # 检查文件大小
    content = await file.read()
    file_size = len(content)
    if file_size > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小不能超过 {MAX_UPLOAD_SIZE_MB}MB"
        )
    
    config = config or ConversionConfig()
    
    try:
        # 保存上传文件
        input_file_id = _generate_file_id()
        input_path = TEMP_DIR / f"{input_file_id}_input.dxf"
        input_path.write_bytes(content)
        
        # 解析 DXF
        parser = DXFParser()
        elements = parser.parse_file(str(input_path))
        
        if not elements:
            raise HTTPException(status_code=400, detail="未解析到键合图元素")
        
        # 转换为 3D
        converter = BondingDiagramConverter({
            'loop_height_coefficient': config.loop_height_coefficient,
            'default_wire_diameter': config.default_wire_diameter,
            'default_material': config.default_material,
        })
        
        assembly = converter.convert_elements(elements)
        
        # 导出文件
        output_format = config.export_format.lower()
        output_ext = 'step' if output_format == 'step' else output_format
        
        output_file_id = _generate_file_id()
        output_filename = f"{output_file_id}_output.{output_ext}"
        output_path = TEMP_DIR / output_filename
        
        if config.export_format == 'STEP':
            converter.export_step(assembly, str(output_path))
        else:
            exporter = CoordinateExporter()
            exporter.export(assembly, str(output_path), config.export_format)
        
        # 清理输入文件
        try:
            input_path.unlink()
        except Exception:
            pass
        
        # 生成下载 URL
        download_url = f"/download/{output_filename}"
        
        return ConversionResponse(
            success=True,
            message=f"成功转换 {len(elements)} 个元素",
            file_id=output_file_id,
            download_url=download_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"转换失败：{str(e)}")


@app.post("/convert/batch", response_model=BatchConversionResponse)
async def convert_batch(
    files: List[UploadFile] = File(...),
    config: ConversionConfig = None
):
    """批量转换"""
    config = config or ConversionConfig()
    results = []
    success_count = 0
    
    for file in files:
        try:
            # 验证文件
            if not file.filename.lower().endswith('.dxf'):
                results.append(BatchResultItem(
                    filename=file.filename,
                    success=False,
                    message="仅支持 DXF 文件"
                ))
                continue
            
            # 读取文件内容
            content = await file.read()
            
            # 检查文件大小
            if len(content) > MAX_UPLOAD_SIZE_BYTES:
                results.append(BatchResultItem(
                    filename=file.filename,
                    success=False,
                    message=f"文件大小不能超过 {MAX_UPLOAD_SIZE_MB}MB"
                ))
                continue
            
            # 保存临时文件
            input_file_id = _generate_file_id()
            input_path = TEMP_DIR / f"{input_file_id}_input.dxf"
            input_path.write_bytes(content)
            
            # 解析 DXF
            parser = DXFParser()
            elements = parser.parse_file(str(input_path))
            
            if not elements:
                results.append(BatchResultItem(
                    filename=file.filename,
                    success=False,
                    message="未解析到键合图元素"
                ))
                try:
                    input_path.unlink()
                except Exception:
                    pass
                continue
            
            # 转换为 3D
            converter = BondingDiagramConverter({
                'loop_height_coefficient': config.loop_height_coefficient,
                'default_wire_diameter': config.default_wire_diameter,
                'default_material': config.default_material,
            })
            
            assembly = converter.convert_elements(elements)
            
            # 导出文件
            output_format = config.export_format.lower()
            output_ext = 'step' if output_format == 'step' else output_format
            
            output_file_id = _generate_file_id()
            output_filename = f"{output_file_id}_output.{output_ext}"
            output_path = TEMP_DIR / output_filename
            
            if config.export_format == 'STEP':
                converter.export_step(assembly, str(output_path))
            else:
                exporter = CoordinateExporter()
                exporter.export(assembly, str(output_path), config.export_format)
            
            # 清理输入文件
            try:
                input_path.unlink()
            except Exception:
                pass
            
            results.append(BatchResultItem(
                filename=file.filename,
                success=True,
                message=f"成功转换 {len(elements)} 个元素",
                file_id=output_file_id,
                download_url=f"/download/{output_filename}"
            ))
            success_count += 1
            
        except Exception as e:
            results.append(BatchResultItem(
                filename=file.filename,
                success=False,
                message=str(e)
            ))
    
    # 清理过期文件
    _cleanup_old_files()
    
    return BatchConversionResponse(
        total=len(files),
        success_count=success_count,
        failed_count=len(files) - success_count,
        results=results
    )


@app.post("/drc")
async def run_drc(
    file: UploadFile = File(...),
    rules: DRCRules = None
):
    """运行 DRC 检查"""
    rules = rules or DRCRules()
    
    try:
        # 验证文件
        if not file.filename.lower().endswith('.dxf'):
            raise HTTPException(status_code=400, detail="仅支持 DXF 文件")
        
        # 读取并保存文件
        content = await file.read()
        input_file_id = _generate_file_id()
        input_path = TEMP_DIR / f"{input_file_id}_input.dxf"
        input_path.write_bytes(content)
        
        # 解析并转换
        parser = DXFParser()
        elements = parser.parse_file(str(input_path))
        
        converter = BondingDiagramConverter()
        assembly = converter.convert_elements(elements)
        
        # 确定 DRC 模式
        from bonding_converter.drc import DRCMode
        if rules.mode == "igbt":
            drc_mode = DRCMode.IGBT
        elif rules.mode == "automotive":
            drc_mode = DRCMode.AUTOMOTIVE
        else:
            drc_mode = DRCMode.STANDARD
        
        # DRC 检查
        drc_checker = DRCChecker({
            'min_wire_spacing': rules.min_spacing_override or rules.min_wire_spacing,
            'max_loop_height': rules.max_loop_height,
            'min_pad_size': rules.min_pad_size,
            'operating_voltage': rules.operating_voltage,
        }, mode=drc_mode)
        
        report = drc_checker.run_and_report(assembly, elements)
        
        # 清理临时文件
        try:
            input_path.unlink()
        except Exception:
            pass
        
        return {
            "passed": report['passed'],
            "total_violations": report['total_violations'],
            "errors": report['errors'],
            "warnings": report['warnings'],
            "mode": rules.mode,
            "violations": [
                {
                    "type": v.violation_type,
                    "severity": v.severity,
                    "description": v.description,
                    "actual": v.actual_value,
                    "required": v.required_value,
                    "category": v.rule_category,
                }
                for v in report['violations']
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/{filename}")
async def download_file(filename: str):
    """下载转换后的文件"""
    file_path = TEMP_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在或已过期")
    
    # 获取文件扩展名
    suffix = file_path.suffix.lower()
    
    # 设置 MIME 类型
    mime_types = {
        '.step': 'application/step',
        '.stp': 'application/step',
        '.stl': 'application/sla',
        '.obj': 'application/obj',
        '.csv': 'text/csv',
        '.ks': 'text/plain',
        '.asm': 'text/plain',
        '.cmd': 'text/plain',
    }
    
    media_type = mime_types.get(suffix, 'application/octet-stream')
    
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename
    )


@app.get("/formats")
async def get_formats():
    """获取支持的导出格式"""
    return {
        "3d": ["STEP", "STL", "OBJ"],
        "coordinates": ["KS", "ASM", "SHINKAWA", "CSV"]
    }


@app.get("/materials")
async def get_materials():
    """获取支持的材料"""
    return {
        "materials": [
            {"id": "gold", "name": "金线", "coefficient": 1.5, "typical_use": "信号线"},
            {"id": "copper", "name": "铜线", "coefficient": 1.2, "typical_use": "通用"},
            {"id": "aluminum", "name": "铝线", "coefficient": 1.8, "typical_use": "功率器件"},
            {"id": "silver", "name": "银线", "coefficient": 1.4, "typical_use": "高频"},
        ]
    }


@app.get("/igbt/rules")
async def get_igbt_rules():
    """获取 IGBT 键合规则配置"""
    return {
        "modes": [
            {"id": "standard", "name": "标准 IC", "description": "普通集成电路"},
            {"id": "igbt", "name": "IGBT 功率器件", "description": "绝缘栅双极晶体管"},
            {"id": "automotive", "name": "车规级", "description": "AEC-Q100 车规标准"},
        ],
        "voltage_classes": [
            {"class": "low", "name": "低压", "range": "<100V", "min_spacing": 0.5},
            {"class": "medium", "name": "中压", "range": "100-600V", "min_spacing": 1.0},
            {"class": "high", "name": "高压", "range": "600-1200V", "min_spacing": 2.0},
            {"class": "ultra_high", "name": "超高压", "range": ">1200V", "min_spacing": 3.0},
        ],
        "wire_types": [
            {"id": "al_wire", "name": "铝线", "diameters": [0.1, 0.15, 0.2, 0.25, 0.3, 0.375, 0.4, 0.5]},
            {"id": "al_ribbon", "name": "铝带", "sizes": ["500×50μm", "1000×75μm", "1500×100μm", "2000×125μm"]},
            {"id": "cu_wire", "name": "铜线", "diameters": [0.1, 0.15, 0.2, 0.25, 0.3]},
        ],
        "pad_types": [
            {"id": "emitter", "name": "发射极", "min_size": 0.3, "description": "大电流输出"},
            {"id": "collector", "name": "集电极", "min_size": 0.5, "description": "高压输入"},
            {"id": "gate", "name": "栅极", "min_size": 0.2, "description": "控制信号"},
        ],
        "current_density": {
            "al_wire": 300,      # A/mm²
            "al_ribbon": 400,    # A/mm²
            "cu_wire": 500,      # A/mm²
        }
    }


@app.get("/igbt/current-capacity")
async def calculate_current_capacity(
    wire_type: str = "al_wire",
    diameter: float = 0.3,
    ribbon_width: float = None,
    ribbon_thickness: float = None
):
    """
    计算引线电流承载能力
    
    Args:
        wire_type: al_wire, al_ribbon, cu_wire
        diameter: 线径 (mm)
        ribbon_width: 铝带宽度 (mm)
        ribbon_thickness: 铝带厚度 (mm)
    """
    import math
    
    # 电流密度 (A/mm²)
    current_density = {
        'al_wire': 300,
        'al_ribbon': 400,
        'cu_wire': 500,
    }
    
    if wire_type == 'al_ribbon' and ribbon_width and ribbon_thickness:
        # 铝带截面积
        cross_section = ribbon_width * ribbon_thickness
        desc = f"铝带 {ribbon_width}×{ribbon_thickness}mm"
    else:
        # 圆线截面积
        cross_section = math.pi * (diameter / 2) ** 2
        desc = f"线径 Ø{diameter}mm"
    
    density = current_density.get(wire_type, 300)
    max_current = cross_section * density
    
    return {
        "wire_type": wire_type,
        "description": desc,
        "cross_section_mm2": round(cross_section, 4),
        "current_density_A_mm2": density,
        "max_current_A": round(max_current, 2),
        "recommendation": f"建议工作电流 < {round(max_current * 0.8, 2)}A (80% 降额)"
    }


@app.on_event("startup")
async def startup_event():
    """启动时清理过期文件"""
    _cleanup_old_files()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
