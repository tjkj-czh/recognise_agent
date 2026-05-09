# 05-deployment / 部署配置包

本目录存放变化监测智能体的部署相关配置与脚本，支持开发环境、测试环境与生产环境的一键部署。

## 目录结构

```
05-deployment/
├── docker/                      # Docker 配置
│   ├── Dockerfile.frontend      # 前端镜像
│   ├── Dockerfile.bff           # BFF 镜像
│   ├── Dockerfile.skill         # Skill Runtime 镜像
│   └── docker-compose.yml       # 开发环境编排
├── ci-cd/                       # 持续集成/交付
│   ├── github-actions/          # GitHub Actions 工作流
│   └── scripts/                 # 部署脚本
└── scripts/                     # 运维脚本
    ├── init-db.sh               # 数据库初始化
    ├── backup.sh                # 数据备份
    └── health-check.sh          # 健康检查
```

## 环境说明

| 环境 | 用途 | 部署方式 |
|------|------|----------|
| dev | 本地开发 | `docker-compose up` |
| test | 集成测试 | Docker + CI 自动部署 |
| prod | 生产环境 | Kubernetes / 云服务器 |

## 快速开始（开发环境）

```bash
cd 05-deployment/docker

# 启动全部服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Nginx | 80 / 443 | 静态资源 + 反向代理 |
| Frontend (dev) | 5173 | Vite 开发服务器 |
| BFF | 3000 | 后端服务 |
| Skill Runtime | 8000 | Python Skill 服务 |
| PostgreSQL | 5432 | 主数据库 |
| Redis | 6379 | 缓存 |
