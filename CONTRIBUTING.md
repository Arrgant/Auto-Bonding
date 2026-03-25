# 贡献指南

欢迎为 Auto-Bonding 项目做出贡献！

## 🌟 如何贡献

### 1. 报告问题

发现 Bug 或有功能建议？请创建 Issue：

- **Bug 报告**: 描述问题、复现步骤、预期行为
- **功能建议**: 说明使用场景、期望功能

### 2. 提交代码

#### Fork 仓库

```bash
# 1. Fork 项目
# 在 GitHub 上点击 Fork 按钮

# 2. 克隆到本地
git clone https://github.com/YOUR_USERNAME/Auto-Bonding.git
cd Auto-Bonding

# 3. 添加上游远程仓库
git remote add upstream https://github.com/ORIGINAL_OWNER/Auto-Bonding.git
```

#### 创建分支

```bash
# 保持主分支最新
git checkout main
git pull upstream main

# 创建功能分支
git checkout -b feature/your-feature-name
# 或修复分支
git checkout -b fix/issue-123
```

#### 开发和测试

```bash
# 安装依赖
cd frontend && npm install
cd ../backend && pip install -r requirements.txt

# 运行测试
./run_tests.sh

# 代码格式化
cd frontend && npm run lint
cd ../backend && black . && flake8
```

#### 提交更改

```bash
# 添加更改
git add .

# 提交（遵循约定式提交规范）
git commit -m "feat: 添加新功能"
# 或
git commit -m "fix: 修复某个问题"
```

**提交信息格式:**

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `style:` 代码格式（不影响功能）
- `refactor:` 重构
- `test:` 测试相关
- `chore:` 构建/工具配置

#### 推送并创建 Pull Request

```bash
# 推送到你的 fork
git push origin feature/your-feature-name

# 在 GitHub 上创建 Pull Request
```

## 📋 开发环境设置

### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安装开发依赖
pip install -r requirements.txt

# 运行开发服务器
python -m uvicorn main:app --reload
```

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 🧪 测试要求

所有 PR 必须：

- ✅ 通过现有测试
- ✅ 为新功能添加测试
- ✅ 代码覆盖率不降低

运行测试：

```bash
# 所有测试
./run_tests.sh

# 单元测试
pytest tests/ -v --ignore=tests/integration/

# 集成测试
pytest tests/integration/ -v

# 带覆盖率
pytest --cov=bonding_converter --cov-report=html
```

## 📝 代码风格

### Python

遵循 [PEP 8](https://pep8.org/) 规范：

```python
# 使用 4 个空格缩进
def my_function(param1, param2):
    """文档字符串"""
    return param1 + param2

# 类名使用驼峰式
class MyClass:
    pass

# 常量使用大写
MAX_SIZE = 100
```

使用 Black 格式化：

```bash
black .
```

### TypeScript/React

遵循项目 ESLint 配置：

```typescript
// 使用 TypeScript 类型
interface Props {
  name: string;
  age?: number;
}

// 函数组件
const MyComponent: React.FC<Props> = ({ name, age }) => {
  return <div>{name}</div>;
};
```

运行 Lint：

```bash
npm run lint
```

## 📖 文档

代码变更需要更新相应文档：

- **API 变更**: 更新 `API.md`
- **功能变更**: 更新 `README.md`
- **部署变更**: 更新 `DEPLOYMENT.md`

## 🔍 Code Review

所有 PR 需要经过 Code Review：

1. 代码是否正确、清晰
2. 是否有适当的测试
3. 是否遵循项目规范
4. 是否有性能问题

## 📞 联系方式

- GitHub Issues: 提问和讨论
- Email: your.email@example.com

## 🙏 感谢

感谢所有贡献者！🎉

---

**更新时间**: 2026-03-25
**版本**: v0.2.0
