# Auto-Bonding API 文档

RESTful API 接口文档

## 📍 基础信息

- **Base URL**: `http://localhost:8000`
- **API 版本**: v0.2.0
- **认证**: 暂无（生产环境建议添加）

## 🔧 通用响应格式

### 成功响应

```json
{
  "success": true,
  "message": "操作成功",
  "data": {}
}
```

### 错误响应

```json
{
  "detail": "错误描述信息"
}
```

---

## 📡 API 端点

### 健康检查

#### `GET /health`

检查服务健康状态。

**响应示例:**

```json
{
  "status": "healthy"
}
```

---

### 获取支持格式

#### `GET /formats`

获取支持的导出格式列表。

**响应示例:**

```json
{
  "3d": ["STEP", "STL", "OBJ"],
  "coordinates": ["KS", "ASM", "SHINKAWA", "CSV"]
}
```

---

### 获取材料列表

#### `GET /materials`

获取支持的引线材料及其参数。

**响应示例:**

```json
{
  "materials": [
    {
      "id": "gold",
      "name": "金线",
      "coefficient": 1.5
    },
    {
      "id": "copper",
      "name": "铜线",
      "coefficient": 1.2
    }
  ]
}
```

---

### 转换单个文件

#### `POST /convert`

转换单个 DXF 文件。

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | ✅ | DXF 文件 (最大 50MB) |
| `config` | JSON | ❌ | 转换配置 |

**Config 配置对象:**

```json
{
  "loop_height_coefficient": 1.5,
  "default_wire_diameter": 0.025,
  "default_material": "gold",
  "export_format": "STEP"
}
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `loop_height_coefficient` | float | 1.5 | 弧高系数 |
| `default_wire_diameter` | float | 0.025 | 线径 (mm) |
| `default_material` | string | "gold" | 材料 (gold/copper/aluminum/silver) |
| `export_format` | string | "STEP" | 导出格式 |

**成功响应:**

```json
{
  "success": true,
  "message": "成功转换 16 个元素",
  "file_id": "uuid-string",
  "download_url": "/download/abc123_output.step"
}
```

**curl 示例:**

```bash
curl -X POST "http://localhost:8000/convert" \
  -F "file=@sample.dxf" \
  -F 'config={"loop_height_coefficient":1.5,"export_format":"KS"}'
```

---

### 批量转换

#### `POST /convert/batch`

批量转换多个 DXF 文件。

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `files` | File[] | ✅ | DXF 文件数组 |
| `config` | JSON | ❌ | 转换配置 |

**成功响应:**

```json
{
  "total": 3,
  "success_count": 2,
  "failed_count": 1,
  "results": [
    {
      "filename": "sample1.dxf",
      "success": true,
      "message": "成功转换 16 个元素",
      "file_id": "uuid-1",
      "download_url": "/download/xxx_output.step"
    },
    {
      "filename": "sample2.dxf",
      "success": false,
      "message": "未解析到键合图元素"
    }
  ]
}
```

**curl 示例:**

```bash
curl -X POST "http://localhost:8000/convert/batch" \
  -F "files=@sample1.dxf" \
  -F "files=@sample2.dxf" \
  -F 'config={"export_format":"CSV"}'
```

---

### DRC 检查

#### `POST /drc`

运行设计规则检查 (Design Rule Check)。

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | ✅ | DXF 文件 |
| `rules` | JSON | ❌ | DRC 规则配置 |

**Rules 配置对象:**

```json
{
  "min_wire_spacing": 0.1,
  "max_loop_height": 1.0,
  "min_pad_size": 0.2
}
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `min_wire_spacing` | float | 0.1 | 最小线间距 (mm) |
| `max_loop_height` | float | 1.0 | 最大弧高 (mm) |
| `min_pad_size` | float | 0.2 | 最小焊盘尺寸 (mm) |

**成功响应:**

```json
{
  "passed": true,
  "total_violations": 0,
  "errors": 0,
  "warnings": 0,
  "violations": []
}
```

**违规响应示例:**

```json
{
  "passed": false,
  "total_violations": 2,
  "errors": 1,
  "warnings": 1,
  "violations": [
    {
      "type": "wire_spacing",
      "severity": "error",
      "description": "线间距过小",
      "actual": 0.05,
      "required": 0.1
    },
    {
      "type": "loop_height",
      "severity": "warning",
      "description": "弧高超出建议范围",
      "actual": 1.2,
      "required": 1.0
    }
  ]
}
```

---

### 下载文件

#### `GET /download/{filename}`

下载转换后的文件。

**路径参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| `filename` | string | 文件名（从转换响应获取） |

**响应:**

- 文件二进制流
- Content-Type 根据文件扩展名自动设置

**curl 示例:**

```bash
curl -O "http://localhost:8000/download/abc123_output.step"
```

**注意:** 临时文件默认 1 小时后自动清理。

---

## ⚠️ 错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求错误（文件格式不支持、参数无效等） |
| 404 | 资源不存在（文件已过期等） |
| 500 | 服务器内部错误 |

---

## 📝 使用建议

### 1. 文件上传

- 确保 DXF 文件格式正确
- 文件大小不超过 50MB
- 建议使用 ASCII DXF 格式（兼容性更好）

### 2. 转换配置

- 金线 (gold): 弧高系数 1.5
- 铜线 (copper): 弧高系数 1.2
- 铝线 (aluminum): 弧高系数 1.8

### 3. 文件下载

- 转换成功后尽快下载（文件 1 小时后过期）
- 生产环境建议配置云存储

---

**更新时间**: 2026-03-25
**API 版本**: v0.2.0
