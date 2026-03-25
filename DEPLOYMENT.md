# Auto-Bonding 部署指南

本文档介绍如何部署 Auto-Bonding 到生产环境。

## 📋 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB RAM
- 10GB 可用磁盘空间

## 🚀 快速部署

### 1. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/Auto-Bonding.git
cd Auto-Bonding
```

### 2. 配置环境变量

```bash
# 后端配置
cp backend/.env.example backend/.env
# 编辑 backend/.env 设置生产环境参数

# 前端配置
cp frontend/.env.example frontend/.env.production
# 编辑 frontend/.env.production 设置 API 地址
```

### 3. 启动服务

```bash
# 使用 Docker Compose 启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 检查服务状态
docker-compose ps
```

访问 http://localhost:8080

## 🔧 手动部署

### 后端部署

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 启动服务
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 前端部署

```bash
cd frontend

# 安装依赖
npm install

# 构建生产版本
npm run build

# 预览构建
npm run preview
```

使用 Nginx 或其他 Web 服务器托管 `dist/` 目录。

## ⚙️ 配置说明

### 后端配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ALLOWED_ORIGINS` | CORS 允许的来源 | `*` |
| `FILE_RETENTION_SECONDS` | 临时文件保留时间 | `3600` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `MAX_UPLOAD_SIZE` | 最大上传大小 (MB) | `50` |

### 前端配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `VITE_API_BASE_URL` | API 基础 URL | `/api` |
| `VITE_MAX_FILE_SIZE` | 最大文件大小 (MB) | `50` |

## 🔒 生产环境安全建议

1. **CORS 配置**: 设置具体的允许来源，不要使用 `*`
2. **HTTPS**: 使用反向代理（如 Nginx）启用 HTTPS
3. **文件上传限制**: 根据实际需求调整大小限制
4. **日志管理**: 配置日志轮转和集中收集
5. **监控**: 添加健康检查和性能监控

### Nginx 反向代理示例

```nginx
server {
    listen 443 ssl;
    server_name auto-bonding.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8080;
    }

    location /api {
        proxy_pass http://localhost:8000;
        client_max_body_size 50M;
    }
}
```

## 📊 监控和维护

### 查看日志

```bash
# 后端日志
docker-compose logs backend

# 前端日志
docker-compose logs frontend

# 实时日志
docker-compose logs -f
```

### 备份临时文件

```bash
# 临时文件卷位置
docker volume inspect auto-bonding_temp_files
```

### 更新服务

```bash
# 拉取最新代码
git pull

# 重新构建并重启
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 🆘 故障排查

### 后端启动失败

```bash
# 检查端口占用
netstat -tlnp | grep 8000

# 检查依赖
docker-compose logs backend | grep ERROR
```

### 前端无法连接后端

1. 检查后端是否正常运行
2. 确认 CORS 配置正确
3. 检查网络连接

### 文件转换失败

1. 检查 DXF 文件格式
2. 查看后端日志获取详细错误
3. 确认临时文件目录有足够空间

## 📈 性能优化

### 增加并发处理

```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

### 使用 Redis 缓存

```yaml
services:
  redis:
    image: redis:alpine
    volumes:
      - redis_data:/data
```

---

**更新时间**: 2026-03-25
**版本**: v0.2.0
