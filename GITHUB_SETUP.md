# GitHub 推送指南

## 📤 推送到 GitHub

### 方法 1: 使用 HTTPS（推荐新手）

```bash
# 1. 在 GitHub 创建新仓库
# 访问 https://github.com/new
# 仓库名：Auto-Bonding
# 选择：Public 或 Private
# 不要勾选 "Initialize with README"（我们已经有了）

# 2. 设置远程仓库
git remote add origin https://github.com/YOUR_USERNAME/Auto-Bonding.git

# 3. 推送
git push -u origin main

# 4. 后续推送
git push
```

### 方法 2: 使用 SSH（推荐）

```bash
# 1. 生成 SSH key（如果没有）
ssh-keygen -t ed25519 -C "your.email@example.com"

# 2. 添加 SSH key 到 GitHub
# 访问 https://github.com/settings/keys
# 复制 ~/.ssh/id_ed25519.pub 内容

# 3. 设置远程仓库
git remote add origin git@github.com:YOUR_USERNAME/Auto-Bonding.git

# 4. 推送
git push -u origin main
```

---

## 🔧 常用 Git 命令

```bash
# 查看状态
git status

# 查看修改
git diff

# 添加文件
git add .

# 提交
git commit -m "描述"

# 推送
git push

# 拉取
git pull

# 查看历史
git log --oneline
```

---

## 📝 提交规范

```bash
# 功能开发
git commit -m "feat: 添加批量转换功能"

# Bug 修复
git commit -m "fix: 修复 DXF 解析错误"

# 文档更新
git commit -m "docs: 更新 README 安装说明"

# 重构
git commit -m "refactor: 优化转换器架构"

# 测试
git commit -m "test: 添加导出器单元测试"
```

---

## 🎯 下一步

1. **在 GitHub 创建仓库**
   - 访问 https://github.com/new
   - 仓库名：`Auto-Bonding`
   - 可见性：Public（开源）或 Private（私有）

2. **推送代码**
   ```bash
   cd /home/admin/.openclaw/workspace-default/Auto-Bonding
   git remote add origin https://github.com/夏季/Auto-Bonding.git
   git push -u origin main
   ```

3. **配置 GitHub Pages（可选）**
   - Settings → Pages
   - Source: main branch
   - 自动生成文档站点

4. **添加 Issue 模板**
   - 创建 `.github/ISSUE_TEMPLATE/`
   - Bug 报告、功能请求等模板

---

## 📦 后续开发

```bash
# 创建开发分支
git checkout -b feature/dxf-parser

# 开发完成后合并
git checkout main
git merge feature/dxf-parser

# 推送分支
git push origin feature/dxf-parser
```

---

## 🤝 协作

1. **Fork & Pull Request** (开源协作)
2. **Branch Protection** (保护 main 分支)
3. **Code Review** (代码审查)

---

**夏季**，创建好 GitHub 仓库后，运行上面的推送命令即可！🚀
