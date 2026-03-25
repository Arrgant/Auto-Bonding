# Auto-Bonding API 文档

**Base URL**: `http://localhost:8000`

---

## 📤 文件转换

### POST /convert

转换单个 DXF 文件

**请求**:
```http
POST /convert
Content-Type: multipart/form-data

file: <DXF 文件>
config: {
  "loop_height_coefficient": 1.5,
  "default_wire_diameter": 0.025,
  "default_material": "gold",
  "export_format": "STEP"
}
```

**响应**:
```json
{
  "success": true,
  "message": "成功转换 15 个元素",
  "file_url": "/download/output.step",
  "drc_report": null
}
```

**错误响应**:
```json
{
  "detail": "仅支持 DXF 文件"
}
```

---

### POST /convert/batch

批量转换多个文件

**请求**:
```http
POST /convert/batch
Content-Type: multipart/form-data

files: [<文件 1>, <文件 2>, ...]
config: { ... }
```

**响应**:
```json
{
  "total": 10,
  "success": 8,
  "results": [
    {
      "filename": "sample1.dxf",
      "success": true,
      "message": "转换成功"
    },
    {
      "filename": "sample2.dxf",
      "success": false,
      "message": "解析失败：无效的 DXF 格式"
    }
  ]
}
```

---

## 🔍 DRC 检查

### POST /drc

运行设计规则检查

**请求**:
```http
POST /drc
Content-Type: multipart/form-data

file: <DXF 文件>
rules: {
  "min_wire_spacing": 0.1,
  "max_loop_height": 1.0,
  "min_pad_size": 0.2
}
```

**响应**:
```json
{
  "passed": false,
  "total_violations": 3,
  "errors": 2,
  "warnings": 1,
  "violations": [
    {
      "type": "spacing",
      "severity": "error",
      "description": "引线 0 和 1 间距过小",
      "actual": 0.05,
      "required": 0.1
    }
  ]
}
```

---

## 📋 数据获取

### GET /formats

获取支持的导出格式

**请求**:
```http
GET /formats
```

**响应**:
```json
{
  "3d": ["STEP", "STL", "OBJ"],
  "coordinates": ["KS", "ASM", "SHINKAWA", "CSV"]
}
```

---

### GET /materials

获取支持的材料

**请求**:
```http
GET /materials
```

**响应**:
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
    },
    {
      "id": "aluminum",
      "name": "铝线",
      "coefficient": 1.8
    },
    {
      "id": "silver",
      "name": "银线",
      "coefficient": 1.4
    }
  ]
}
```

---

## 🏥 健康检查

### GET /health

检查 API 状态

**请求**:
```http
GET /health
```

**响应**:
```json
{
  "status": "healthy"
}
```

---

### GET /

API 根路径

**请求**:
```http
GET /
```

**响应**:
```json
{
  "name": "Auto-Bonding API",
  "version": "0.1.0",
  "status": "running"
}
```

---

## 🔌 WebSocket（开发中）

### WS /ws/progress

接收转换进度更新

**连接**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/progress');
```

**消息格式**:
```json
{
  "task_id": "xxx",
  "filename": "sample.dxf",
  "progress": 45,
  "status": "processing"
}
```

---

## 📝 使用示例

### TypeScript (Axios)

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
});

// 转换文件
export const convertFile = async (file: File, config: ConversionConfig) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('config', JSON.stringify(config));
  
  const response = await api.post('/convert', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
      console.log(`上传进度：${progress}%`);
    },
  });
  
  return response.data;
};

// 获取材料列表
export const getMaterials = async () => {
  const response = await api.get('/materials');
  return response.data.materials;
};

// DRC 检查
export const runDRC = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post('/drc', formData);
  return response.data;
};
```

### React Hook

```typescript
import { useQuery, useMutation } from '@tanstack/react-query';
import { getMaterials, convertFile } from './api';

// 获取材料列表
export const useMaterials = () => {
  return useQuery({
    queryKey: ['materials'],
    queryFn: getMaterials,
  });
};

// 转换文件
export const useConvertFile = () => {
  return useMutation({
    mutationFn: ({ file, config }: { file: File; config: ConversionConfig }) =>
      convertFile(file, config),
  });
};
```

---

## 🐛 错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求错误（文件格式不支持等） |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

---

*最后更新：2026-03-25*
