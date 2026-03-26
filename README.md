# Auto-Bonding

🔧 键合图自动转换工具 - 将 DXF 二维键合图转换为 3D 模型并导出打线坐标

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## ✨ 功能特性

- 📄 **DXF 导入** - 支持键合图标准格式
- 🔄 **2D→3D 转换** - 自动重建引线弧、焊盘等 3D 几何
- 📤 **STEP 导出** - 生成 3D 模型供用户预览
- 📊 **坐标导出** - 支持 K&S/ASM/Shinkawa 等打线机格式
- ⚡ **批量处理** - 一次转换多个图纸
- ✅ **DRC 检查** - 设计规则验证（间距、弧高等）
- 🖥️ **独立客户端** - 现代化 PyQt6 桌面应用
- 🔌 **IGBT 支持** - 功率器件专用规则（电压等级、电流承载、车规级补偿）

## 🎯 快速开始

### 🖥️ 独立客户端

```bash
# 克隆仓库
git clone https://gitee.com/arrgant/AutoBonding.git
cd Auto-Bonding

# 安装依赖
pip install -r requirements.txt

# 启动客户端
python run_client.py
# 或
./start.sh
```

### 📦 打包成可执行文件

```bash
# Windows
pyinstaller --name="Auto-Bonding" --windowed --onefile main.py

# macOS
pyinstaller --name="Auto-Bonding" --windowed --onefile main.py

# Linux
pyinstaller --name="Auto-Bonding" --windowed --onefile main.py
```

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| **客户端** | PyQt6 + WebEngine |
| **3D 建模** | CadQuery (OpenCASCADE) |
| **DXF 解析** | ezdxf |
| **数据处理** | NumPy |

## 📖 使用指南

### 1. 导入键合图

支持格式：
- **DXF** (推荐)
- DWG (需先用 ODA Converter 转换为 DXF)

### 2. 配置参数

| 参数 | 说明 | 默认值 (标准) | 默认值 (IGBT) |
|------|------|--------|--------|
| 模式 | 标准 IC/IGBT/车规级 | standard | igbt |
| 弧高系数 | 引线弧高计算系数 | 1.5 | 2.0 |
| 线径 | 线径 (mm) | 0.025 (金线) | 0.3 (铝线) |
| 材料 | 引线材料 | 金线 | 铝线 |
| 工作电压 | IGBT 工作电压 (V) | - | 600 |
| 引线类型 | 铝线/铝带/铜线 | - | al_wire |
| 导出格式 | STEP/KS/ASM/CSV 等 | STEP | STEP |

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
├── gui/                   # PyQt6 客户端
│   └── main_window.py     # 主窗口
├── bonding_converter/     # 核心转换模块
│   ├── converter.py       # 2D→3D 转换
│   ├── dxf_parser.py      # DXF 解析
│   ├── exporter.py        # 坐标导出
│   ├── drc.py             # DRC 检查
│   └── igbt_rules.py      # IGBT 规则
├── tests/                 # 测试
│   ├── test_converter.py
│   ├── test_exporter.py
│   ├── test_drc.py
│   └── test_igbt_rules.py
├── examples/              # 示例文件
│   └── sample.dxf
├── main.py                # 程序入口
├── run_client.py          # 客户端启动脚本
├── start.sh               # Linux/Mac 启动脚本
├── requirements.txt       # Python 依赖
└── README.md              # 本文件
```

## 🧪 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_converter.py -v
```

## ⚙️ 配置说明

### 弧高系数

弧高系数决定引线弧度：
- **标准 IC**: 1.5 (金线，小跨度)
- **IGBT**: 2.0 (铝线，大跨度)
- **车规级**: 2.0 + 20% 热补偿

### IGBT 模式

IGBT 功率器件需要更严格的设计规则：

1. **电压等级** 自动确定最小间距：
   - 低压 (≤100V): 0.1mm
   - 中压 (100-600V): 0.5mm
   - 高压 (600-1200V): 1.0mm
   - 超高压 (>1200V): 2.0mm

2. **电流承载** 根据线径和材料计算：
   - 金线 25μm: ~0.1A
   - 铝线 300μm: ~3-5A
   - 铝带: 10A+

3. **车规级 (AEC-Q100)**:
   - 额外 20% 弧高补偿
   - 更严格的间距要求
   - 温度循环补偿

## 🔧 开发

### 添加新功能

1. 在 `bonding_converter/` 添加核心逻辑
2. 在 `gui/` 更新界面
3. 在 `tests/` 添加测试

### 代码规范

```bash
# 格式化
black .

# 检查
flake8 .

# 类型检查
mypy .
```

## 📝 更新日志

详见 [CHANGELOG.md](CHANGELOG.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

*最后更新：2026-03-26*
