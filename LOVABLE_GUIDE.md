# Lovable UI 开发指南

## 🎯 当前状态

- **分支**: `frontend/lovable`
- **后端分支**: `main`
- **状态**: UI 开发中

## 📋 UI 组件开发顺序

### ✅ 已完成

- [ ] 1. 项目初始化
- [ ] 2. 导航和布局
- [ ] 3. 文件上传组件
- [ ] 4. 参数配置面板
- [ ] 5. 3D 预览组件
- [ ] 6. 转换队列
- [ ] 7. DRC 检查报告

### 🔄 进行中

无

### ⏳ 待开始

所有组件

---

## 🚀 开始开发

### 1. 访问 Lovable

打开：https://lovable.dev

### 2. 连接 GitHub

1. Sign in with GitHub
2. Connect to repository: `Arrgant/Auto-Bonding`
3. 选择分支：`frontend/lovable`

### 3. 按顺序发送 Prompt

**第一个 Prompt - 项目初始化：**

```markdown
创建一个工业软件 Web 应用，名为 Auto-Bonding

【项目定位】
键合图自动转换工具 - 将 DXF 二维图纸转换为 3D 模型并导出打线机坐标

【技术栈】
- React 18 + TypeScript
- Tailwind CSS
- Three.js (用于 3D 预览)
- Axios (HTTP 请求)
- React Query (数据获取)

【设计风格】
- 深色主题（工业软件风格）
- 主色调：深蓝 (#1e40af) + 灰色 (#64748b)
- 字体：Inter / System UI
- 圆角：适中 (6-8px)
- 阴影：轻微，用于层级区分

【布局结构】
- 顶部导航栏（Logo + 菜单）
- 左侧边栏（文件列表/任务队列）
- 主内容区（3D 预览 + 参数配置）
- 底部状态栏（进度/日志）

【核心功能模块】
1. 文件上传（拖拽 DXF 文件）
2. 参数配置（弧高/线径/材料/格式）
3. 3D 预览（Three.js 查看器）
4. 转换队列（批量任务管理）
5. DRC 检查结果

【API 端点】
后端运行在 http://localhost:8000
- POST /convert - 单文件转换
- POST /convert/batch - 批量转换
- POST /drc - DRC 检查
- GET /formats - 获取支持格式
- GET /materials - 获取材料列表

【特殊要求】
- 响应式设计（支持 1920x1080 及以上分辨率）
- 加载状态动画
- 错误提示 Toast
- 文件上传进度条
- 支持中文界面

请生成完整的项目结构，包括：
- 路由配置
- 全局样式
- API 客户端封装
- 类型定义
- 主布局组件
```

### 4. 生成后

1. **预览效果** - 在 Lovable 中查看
2. **复制代码** - 点击 "View Code" 或 "Export"
3. **发送给 arrgant** - 让他审查和优化
4. **同步到 GitHub** - 等待他推送

---

## 📁 项目结构预期

```
frontend/
├── public/
├── src/
│   ├── components/
│   │   ├── FileUploadZone.tsx
│   │   ├── ConversionConfig.tsx
│   │   ├── ModelViewer3D.tsx
│   │   ├── ConversionQueue.tsx
│   │   ├── DRCReport.tsx
│   │   └── ...
│   ├── layouts/
│   │   ├── TopNav.tsx
│   │   ├── Sidebar.tsx
│   │   └── MainLayout.tsx
│   ├── api/
│   │   └── client.ts
│   ├── types/
│   │   └── index.ts
│   ├── hooks/
│   ├── utils/
│   ├── App.tsx
│   └── main.tsx
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── vite.config.ts
```

---

## 🔗 相关链接

- **Lovable**: https://lovable.dev
- **GitHub**: https://github.com/Arrgant/Auto-Bonding
- **后端 API 文档**: http://localhost:8000/docs

---

## 📝 开发日志

| 日期 | 组件 | 状态 | 备注 |
|------|------|------|------|
| 2026-03-25 | 项目初始化 | ⏳ 待开始 | |

---

*最后更新：2026-03-25*
