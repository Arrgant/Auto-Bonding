# Auto-Bonding

🔧 键合图自动转换工具 - 将 DXF 二维键合图转换为 3D 模型并导出打线坐标

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 20+](https://img.shields.io/badge/node-20+-green.svg)](https://nodejs.org/)

## ✨ 功能特性

- 📄 **DXF 导入** - 支持键合图标准格式
- 🔄 **2D→3D 转换** - 自动重建引线弧、焊盘等 3D 几何
- 📤 **STEP 导出** - 生成 3D 模型供用户预览
- 📊 **坐标导出** - 支持 K&S/ASM/Shinkawa 等打线机格式
- ⚡ **批量处理** - 一次转换多个图纸
- ✅ **DRC 检查** - 设计规则验证（间距、弧高等）
- 🌐 **Web 界面** - 现代化的 React 前端
- 🐳 **Docker 部署** - 一键容器化部署

## 🎯 快速开始

### 使用 Docker (推荐)

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/Auto-Bonding.git
cd Auto-Bonding

# 启动服务
docker-compose up -d

# 访问 http://localhost:8080
```

### 开发环境

```bash
# 后端
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload

# 前端
cd frontend
npm install
npm run dev
```

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| **后端** | FastAPI, Python 3.11+ |
| **前端** | React 18, TypeScript, Vite |
| **3D 建模** | CadQuery (OpenCASCADE) |
| **3D 预览** | Three.js, React Three Fiber |
| **DXF 解析** | ezdxf |
| **数据处理** | NumPy, Pandas |
| **部署** | Docker, Docker Compose |

## 📖 使用指南

### 1. 导入键合图

支持格式：
- **DXF** (推荐)
- DWG (需先用 ODA Converter 转换为 DXF)

### 2. 配置参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 弧高系数 | 引线弧高计算系数 | 1.5 |
| 线径 | 金线/铜线直径 (mm) | 0.025 |
| 材料 | 引线材料 | 金线 |
| 导出格式 | STEP/KS/ASM/CSV 等 | STEP |

### 3. 导出格式

**3D 模型:**
- STEP - 3D 模型预览
- STL - 3D 打印格式
- OBJ - 通用 3D 格式

**打线坐标:**
- CSV - 通用坐标格式
- KS - K&S 打线机格式
- ASM - ASM Pacific 格式
- CMD - Shinkawa 格式

## 📁 项目结构

```
Auto-Bonding/
├── backend/                # FastAPI 后端
│   ├── main.py            # API 入口
│   ├── requirements.txt   # Python 依赖
│   └── .env.example       # 配置模板
├── frontend/              # React 前端
│   ├── src/
│   │   ├── Index.tsx     # 主入口
│   │   ├── components/   # 组件
│   │   ├── api/          # API 客户端
│   │   └── types/        # TypeScript 类型
│   ├── package.json
│   └── .env.example
├── bonding_converter/     # 核心转换模块
│   ├── converter.py       # 2D→3D 转换
│   ├── dxf_parser.py      # DXF 解析
│   ├── exporter.py        # 坐标导出
│   └── drc.py             # DRC 检查
├── tests/                 # 测试
│   ├── test_converter.py
│   ├── test_exporter.py
│   ├── test_drc.py
│   └── integration/       # 集成测试
├── examples/              # 示例文件
│   ├── sample.dxf
│   └── README.md
├── docker-compose.yml     # Docker 编排
├── Dockerfile.backend     # 后端镜像
├── Dockerfile.frontend    # 前端镜像
├── run_tests.sh          # 测试脚本
├── README.md             # 本文件
├── DEPLOYMENT.md         # 部署指南
├── API.md                # API 文档
└── CONTRIBUTING.md       # 贡献指南
```

## 🧪 测试

```bash
# 运行所有测试
./run_tests.sh

# 单元测试
pytest tests/ -v

# 集成测试
pytest tests/integration/ -v

# 带覆盖率
pytest --cov=bonding_converter
```

## 📚 文档

- **[API 文档](API.md)** - RESTful API 接口说明
- **[部署指南](DEPLOYMENT.md)** - 生产环境部署
- **[贡献指南](CONTRIBUTING.md)** - 如何贡献代码

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

详见 [CONTRIBUTING.md](CONTRIBUTING.md)

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 👥 作者

**夏季**

- GitHub: [@YOUR_USERNAME](https://github.com/YOUR_USERNAME)
- Email: your.email@example.com

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者！

---

**版本**: v0.2.0  
**更新时间**: 2026-03-25
