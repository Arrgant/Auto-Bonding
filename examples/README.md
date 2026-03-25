# Auto-Bonding 示例文件

本目录包含用于测试和演示的示例文件。

## 📁 文件说明

### sample.dxf
一个简单的键合图示例，包含：
- **芯片区域 (DIE)**: 80x80mm 的正方形区域
- **焊盘 (PADS)**: 16 个圆形焊盘（直径 4mm）
  - 底部 8 个焊盘，间距 10mm
  - 顶部 8 个焊盘，间距 10mm

## 🚀 快速测试

### 使用 GUI
1. 启动后端：`cd backend && python main.py`
2. 启动前端：`cd frontend && npm run dev`
3. 上传 `sample.dxf` 进行测试

### 使用 CLI
```bash
# 转换单个文件
python cli.py --input ./examples/sample.dxf --output ./examples/sample_output --format KS

# 批量转换
python cli.py --input ./examples --output ./examples/sample_output --format STEP
```

### 使用 API
```bash
# 转换文件
curl -X POST "http://localhost:8000/convert" \
  -F "file=@./examples/sample.dxf" \
  -F 'config={"loop_height_coefficient":1.5,"export_format":"STEP"}'

# DRC 检查
curl -X POST "http://localhost:8000/drc" \
  -F "file=@./examples/sample.dxf"
```

## 📊 预期输出

转换成功后，`sample_output/` 目录将包含：
- `sample.step` - 3D 模型文件
- `sample.csv` - 焊点坐标（CSV 格式）
- `sample.ks` - K&S 打线机格式
- `sample.asm` - ASM Pacific 格式

## 📝 注意事项

- 示例文件单位为毫米 (mm)
- 焊盘坐标相对于芯片左下角
- 可根据实际需求修改焊盘位置和数量

---

**更新时间**: 2026-03-25
**版本**: v0.2.0
