# Auto-Bonding Frontend

键合图转换工具的前端界面

## 🚀 快速启动

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

访问：http://localhost:3000

### 构建生产版本

```bash
npm run build
```

### 预览生产版本

```bash
npm run preview
```

## 📁 项目结构

```
src/
├── api/           # API 客户端
├── components/    # React 组件
├── layouts/       # 布局组件
├── pages/         # 页面组件
├── store/         # 状态管理 (Zustand)
├── types/         # TypeScript 类型
├── App.tsx        # 应用根组件
├── main.tsx       # 入口文件
└── index.css      # 全局样式
```

## 🛠️ 技术栈

- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Tailwind CSS** - 样式
- **React Router** - 路由
- **React Query** - 数据获取
- **Zustand** - 状态管理
- **React Three Fiber** - 3D 渲染
- **Three.js** - 3D 图形
- **React Hook Form** - 表单处理
- **Axios** - HTTP 客户端

## 📦 主要功能

- ✅ 文件上传（拖拽支持）
- ✅ 参数配置（弧高/线径/材料/格式）
- ✅ 3D 预览（Three.js）
- ✅ 任务队列管理
- ✅ DRC 检查报告
- ✅ 深色主题

## 🔗 后端 API

默认连接：`http://localhost:8000`

详见：`../backend/API_DOCS.md`

## 📝 开发笔记

### 添加新组件

```bash
# 创建组件文件
src/components/NewComponent.tsx

# 导出
src/components/index.ts
```

### 调用 API

```typescript
import { convertFile } from '@/api/client'

const result = await convertFile(file, config)
```

### 状态管理

```typescript
import { useAppStore } from '@/store'

const { files, addFile } = useAppStore()
addFile(file)
```

---

*最后更新：2026-03-25*
