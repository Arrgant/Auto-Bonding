# Auto-Bonding

🔧 键合图自动转换工具 - 将 DWG/DXF 二维键合图转换为 3D 模型并导出打线坐标

## ✨ 功能特性

- 📄 **DXF/DWG 导入** - 支持键合图标准格式
- 🔄 **2D→3D 转换** - 自动重建引线弧、焊盘等 3D 几何
- 📤 **STEP 导出** - 生成 3D 模型供用户预览
- 📊 **坐标导出** - 支持 K&S/ASM/Shinkawa 等打线机格式
- ⚡ **批量处理** - 一次转换多个图纸
- ✅ **DRC 检查** - 设计规则验证（间距、弧高等）

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| 核心建模 | CadQuery (OpenCASCADE) |
| GUI 框架 | PyQt6 |
| 3D 预览 | VTK |
| DXF 解析 | ezdxf |
| 数据处理 | NumPy, Pandas |
| 打包工具 | PyInstaller |

## 📋 安装

### 开发环境

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/Auto-Bonding.git
cd Auto-Bonding

# 创建虚拟环境
python -m venv venv

# 激活环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 运行

```bash
# 启动 GUI
python main.py

# 命令行批量转换
python cli.py --input ./dwg_files --output ./output --format KS
```

## 📖 使用指南

### 1. 导入键合图

支持格式：
- DXF (推荐)
- DWG (需先用 ODA Converter 转换)

### 2. 配置参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 弧高系数 | 引线弧高计算系数 | 1.5 |
| 线径 | 金线/铜线直径 (mm) | 0.025 |
| 最小间距 | DRC 最小线间距 (mm) | 0.1 |

### 3. 导出

- **STEP**: 3D 模型预览
- **CSV**: 焊点坐标
- **WRF**: K&S 打线机格式
- **ABS**: ASM Pacific 格式
- **CMD**: Shinkawa 格式

## 🏗️ 项目结构

```
Auto-Bonding/
├── main.py                 # 程序入口
├── cli.py                  # 命令行工具
├── requirements.txt        # Python 依赖
├── README.md              # 项目说明
├── LICENSE                # MIT License
├── bonding_converter/     # 核心模块
│   ├── __init__.py
│   ├── converter.py       # 2D→3D 转换逻辑
│   ├── dxf_parser.py      # DXF 文件解析
│   ├── exporter.py        # 坐标导出
│   ├── drc.py             # 设计规则检查
│   └── utils.py           # 工具函数
├── gui/                   # GUI 模块
│   ├── __init__.py
│   ├── main_window.py     # 主窗口
│   ├── viewer3d.py        # VTK 3D 预览
│   ├── dialogs.py         # 配置对话框
│   └── widgets.py         # 自定义控件
├── tests/                 # 单元测试
│   ├── __init__.py
│   ├── test_converter.py
│   ├── test_exporter.py
│   └── test_drc.py
└── examples/              # 示例文件
    ├── sample.dxf
    └── sample_output/
```

## 🧪 测试

```bash
# 运行单元测试
pytest tests/ -v

# 运行集成测试
pytest tests/integration/ -v
```

## 📦 打包

```bash
# Windows
pyinstaller --name "Auto-Bonding" --windowed --icon=icon.ico main.py

# Linux
pyinstaller --name "Auto-Bonding" --windowed main.py
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License - 详见 LICENSE 文件

## 👥 作者

夏季 (YOUR_USERNAME)

## 📮 联系方式

- Email: your.email@example.com
- GitHub: https://github.com/YOUR_USERNAME/Auto-Bonding
