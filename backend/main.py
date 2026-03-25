"""
Auto-Bonding FastAPI 后端
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import tempfile
import os
from pathlib import Path

from bonding_converter import BondingDiagramConverter, DXFParser, CoordinateExporter
from bonding_converter.drc import DRCChecker

app = FastAPI(
    title="Auto-Bonding API",
    description="键合图转换服务",
    version="0.1.0"
)

# CORS 配置（允许 Lovable 前端调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境改为 Lovable 的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    file_url: Optional[str] = None
    drc_report: Optional[dict] = None


@app.get("/")
def root():
    """API 根路径"""
    return {
        "name": "Auto-Bonding API",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "healthy"}


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
    
    config = config or ConversionConfig()
    
    try:
        # 保存上传文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.dxf') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # 解析 DXF
        parser = DXFParser()
        elements = parser.parse_file(tmp_path)
        
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
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{output_ext}') as tmp:
            output_path = tmp.name
        
        if config.export_format == 'STEP':
            converter.export_step(assembly, output_path)
        else:
            exporter = CoordinateExporter()
            exporter.export(assembly, output_path, config.export_format)
        
        # 生成下载 URL（实际部署时改为云存储）
        file_url = f"/download/{Path(output_path).name}"
        
        return ConversionResponse(
            success=True,
            message=f"成功转换 {len(elements)} 个元素",
            file_url=file_url
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # 清理临时文件
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/convert/batch")
async def convert_batch(
    files: List[UploadFile] = File(...),
    config: ConversionConfig = None
):
    """批量转换"""
    results = []
    
    for file in files:
        try:
            # 调用单个转换逻辑
            # TODO: 实现批量处理
            results.append({
                "filename": file.filename,
                "success": True,
                "message": "转换成功"
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "message": str(e)
            })
    
    return {
        "total": len(files),
        "success": sum(1 for r in results if r['success']),
        "results": results
    }


@app.post("/drc")
async def run_drc(
    file: UploadFile = File(...),
    rules: DRCRules = None
):
    """运行 DRC 检查"""
    rules = rules or DRCRules()
    
    try:
        # 保存上传文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.dxf') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # 解析并转换
        parser = DXFParser()
        elements = parser.parse_file(tmp_path)
        
        converter = BondingDiagramConverter()
        assembly = converter.convert_elements(elements)
        
        # DRC 检查
        drc_checker = DRCChecker({
            'min_wire_spacing': rules.min_wire_spacing,
            'max_loop_height': rules.max_loop_height,
            'min_pad_size': rules.min_pad_size,
        })
        
        report = drc_checker.run_and_report(assembly)
        
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.get("/download/{filename}")
async def download_file(filename: str):
    """下载转换后的文件"""
    # TODO: 实现文件下载（实际部署时从云存储获取）
    raise HTTPException(status_code=404, detail="文件不存在")


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
