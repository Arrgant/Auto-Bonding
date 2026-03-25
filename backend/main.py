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
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 临时文件存储目录
TEMP_DIR = Path(tempfile.gettempdir()) / "auto-bonding"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# 文件保留时间（秒）
FILE_RETENTION_SECONDS = int(os.getenv("FILE_RETENTION_SECONDS", "3600"))


class ConversionConfig(BaseModel):
    """转换配置"""
    loop_height_coefficient: float = 1.5
    default_wire_diameter: float = 0.025
    default_material: str = "gold"
    export_format: str = "STEP"  # STEP, KS, ASM, SHINKAWA, CSV


class DRCRules(BaseModel):
    """DRC 规则"""
    min_wire_spacing: float = 0.1
    max_loop_height: float = 1.0
    min_pad_size: float = 0.2


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
    
    # 检查文件大小（最大 50MB）
    file_size = 0
    content = await file.read()
    file_size = len(content)
    if file_size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过 50MB")
    
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
            if len(content) > 50 * 1024 * 1024:
                results.append(BatchResultItem(
                    filename=file.filename,
                    success=False,
                    message="文件大小不能超过 50MB"
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
        
        # DRC 检查
        drc_checker = DRCChecker({
            'min_wire_spacing': rules.min_wire_spacing,
            'max_loop_height': rules.max_loop_height,
            'min_pad_size': rules.min_pad_size,
        })
        
        report = drc_checker.run_and_report(assembly)
        
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
            "violations": [
                {
                    "type": v.violation_type,
                    "severity": v.severity,
                    "description": v.description,
                    "actual": v.actual_value,
                    "required": v.required_value,
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
            {"id": "gold", "name": "金线", "coefficient": 1.5},
            {"id": "copper", "name": "铜线", "coefficient": 1.2},
            {"id": "aluminum", "name": "铝线", "coefficient": 1.8},
            {"id": "silver", "name": "银线", "coefficient": 1.4},
        ]
    }


@app.on_event("startup")
async def startup_event():
    """启动时清理过期文件"""
    _cleanup_old_files()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
