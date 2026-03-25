# Lovable + Auto-Bonding 集成指南

## 🏗️ 架构设计

```
┌─────────────────────────────────────────┐
│   Lovable (React/TypeScript 前端)       │
│   - 文件上传                            │
│   - 参数配置                            │
│   - 3D 预览 (Three.js)                  │
│   - 结果下载                            │
└──────────────┬──────────────────────────┘
│              │ HTTP API
│              ▼
└─────────────────────────────────────────┐
│   FastAPI (Python 后端)                 │
│   - DXF 解析                            │
│   - CadQuery 3D 转换                    │
│   - 坐标导出                            │
│   - DRC 检查                            │
└─────────────────────────────────────────┘
```

## 🚀 快速启动

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
python main.py
```

访问：http://localhost:8000/docs (FastAPI 自动文档)

### 2. 在 Lovable 中创建前端

访问 Lovable 并创建新项目，使用以下提示：

```
创建一个键合图转换工具的 Web 界面，包含：

1. 文件上传区域（支持拖拽 DXF 文件）
2. 参数配置表单：
   - 弧高系数 (滑块 0.1-10.0)
   - 线径 (下拉选择：0.015/0.020/0.025/0.030mm)
   - 材料 (下拉选择：金线/铜线/铝线/银线)
   - 导出格式 (STEP/KS/ASM/SHINKAWA/CSV)

3. 3D 预览窗口（使用 Three.js 显示 STEP 模型）
4. 转换结果列表（文件名、状态、下载按钮）
5. DRC 检查结果显示（通过/失败、错误列表）

风格：现代化、简洁、专业工业软件风格
配色：深蓝/灰色系
```

### 3. 配置 API 调用

在 Lovable 中添加 API 调用：

```typescript
// 转换文件
const convertFile = async (file: File, config: ConversionConfig) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('config', JSON.stringify(config));
  
  const response = await fetch('http://localhost:8000/convert', {
    method: 'POST',
    body: formData,
  });
  
  return await response.json();
};

// DRC 检查
const runDRC = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch('http://localhost:8000/drc', {
    method: 'POST',
    body: formData,
  });
  
  return await response.json();
};
```

## 📡 API 文档

### POST /convert

转换单个文件

**请求**:
- `file`: DXF 文件 (multipart/form-data)
- `config`: 转换配置 (JSON)

**响应**:
```json
{
  "success": true,
  "message": "成功转换 15 个元素",
  "file_url": "/download/output.step"
}
```

### POST /convert/batch

批量转换

**请求**:
- `files`: 多个 DXF 文件
- `config`: 转换配置

**响应**:
```json
{
  "total": 10,
  "success": 8,
  "results": [...]
}
```

### POST /drc

运行 DRC 检查

**请求**:
- `file`: DXF 文件
- `rules`: DRC 规则

**响应**:
```json
{
  "passed": false,
  "total_violations": 3,
  "errors": 2,
  "warnings": 1,
  "violations": [...]
}
```

### GET /formats

获取支持的格式

**响应**:
```json
{
  "3d": ["STEP", "STL", "OBJ"],
  "coordinates": ["KS", "ASM", "SHINKAWA", "CSV"]
}
```

## 🎨 Lovable 界面设计建议

### 页面布局

```
┌─────────────────────────────────────────────┐
│  Auto-Bonding           [上传] [DRC 检查]    │
├─────────────────────────────────────────────┤
│  ┌──────────────┐  ┌─────────────────────┐  │
│  │              │  │  参数配置            │  │
│  │  3D 预览      │  │  - 弧高系数 ━━━○    │  │
│  │  (Three.js)  │  │  - 线径 ▼ 0.025mm   │  │
│  │              │  │  - 材料 ▼ 金线      │  │
│  │              │  │  - 格式 ▼ STEP      │  │
│  │              │  │                     │  │
│  │              │  │  [开始转换]          │  │
│  └──────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────┤
│  转换队列                                    │
│  ┌──────────────────────────────────────┐   │
│  │ sample.dxf    ✅ 完成  [下载] [查看]  │   │
│  │ test.dxf      ⏳ 转换中... (45%)     │   │
│  │ board.dxf     ⏸️ 等待中              │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### 配色方案

```css
:root {
  --primary: #1e40af;      /* 深蓝 */
  --secondary: #64748b;    /* 灰色 */
  --success: #10b981;      /* 绿色 */
  --warning: #f59e0b;      /* 橙色 */
  --error: #ef4444;        /* 红色 */
  --background: #0f172a;   /* 深色背景 */
}
```

## 📦 部署

### 后端部署

```bash
# Docker 部署
docker build -t auto-bonding-api .
docker run -p 8000:8000 auto-bonding-api
```

### 前端部署

Lovable 生成的代码可以直接部署到：
- Vercel
- Netlify
- GitHub Pages

## 🔗 相关链接

- **Lovable**: https://lovable.dev
- **FastAPI**: https://fastapi.tiangolo.com
- **Three.js**: https://threejs.org
- **CadQuery**: https://cadquery.readthedocs.io
