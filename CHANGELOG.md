# 更新日志

## [0.2.0] - 2025-03-25

### ✨ 新增

#### 全新现代化 UI 界面
- 采用 shadcn/ui 风格的设计系统
- 深色主题配色方案
- 流畅的动画和过渡效果

#### 组件重构
- **Navbar**: 顶部导航栏，包含 Logo、DRC 检查和转换按钮
- **AppSidebar**: 侧边栏，包含文件上传和任务队列
- **StatusBar**: 底部状态栏，显示系统日志和任务进度
- **ThreeViewer**: 3D 焊点预览组件（基于 Three.js）
- **ConversionConfigPanel**: 参数配置面板
- **DRCPanel**: DRC 设计规则检查面板

#### 基础 UI 组件
- Card、CardHeader、CardContent、CardFooter
- Badge（支持多种状态）
- Navbar、Sidebar、StatusBar

### 🎨 设计改进

- 统一的设计令牌（基于 HSL）
- 现代化的色彩系统
- 改进的视觉层次和间距
- 响应式布局

### 🔧 技术更新

- 修复 TypeScript 类型错误
- 更新 Vite 配置支持 Node.js 模块
- 添加 @types/node 开发依赖
- 优化构建配置

### 📁 文件结构

```
frontend/src/
├── Index.tsx                    # 主入口组件（新）
├── components/
│   ├── layout/                  # 布局组件
│   │   ├── Navbar.tsx
│   │   ├── AppSidebar.tsx
│   │   └── StatusBar.tsx
│   ├── viewer/                  # 查看器组件
│   │   └── ThreeViewer.tsx
│   ├── panels/                  # 面板组件
│   │   ├── ConversionConfigPanel.tsx
│   │   └── DRCPanel.tsx
│   └── ui/                      # 基础 UI 组件
│       ├── Navbar.tsx
│       ├── Sidebar.tsx
│       ├── StatusBar.tsx
│       ├── Card.tsx
│       └── Badge.tsx
├── types/
│   └── index.ts                 # 新增类型定义
└── index.css                    # 更新设计令牌
```

### 📝 说明

- 原有路由结构已简化为单页面应用
- 演示数据为模拟数据，需连接真实后端 API
- 3D 查看器需要 WebGL 支持

### 🚀 使用

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000

---

## [0.1.0] - 2025-03-25

### 初始版本
- 基础前端框架
- 文件上传功能
- 转换任务管理
- DRC 检查功能
- API 客户端
