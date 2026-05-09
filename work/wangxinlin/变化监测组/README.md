# 变化监测智能体

面向自然资源监管领域的 AI 驱动遥感变化监测智能体系统。

## 项目简介

本项目旨在构建一套智能化土地供应与利用变化监测平台，以 AI 智能体为核心操作向导，实现"对话即监测"的零门槛监测体验。系统整合遥感影像分析、变化检测算法、供地数据管理与报告生成能力，服务于自然资源监管部门的日常监测与决策支持。

## 工程架构

采用 Monorepo 统一仓库管理，按职责划分为五大模块：

```
变化监测智能体/
├── 01-specs/          # 工程规范包（需求规格、技术规范、设计规范）
├── 02-skills/         # Skill 文件包（核心技能、智能体编排、工具技能）
├── 03-frontend/       # 前端代码包（含 BFF 后端服务）
├── 04-data/           # 数据资产包（评测数据集、基准测试、模拟数据）
└── 05-deployment/     # 部署配置包（Docker、CI/CD、脚本）
```

### 模块分工

| 模块 | 主负责人 | 协辅人 | 说明 |
|------|---------|--------|------|
| 03-frontend | 前端开发 | Skill 开发 | React + TS 前端 + Node/BFF 后端 |
| 02-skills | Skill 开发 | 前端/规范 | 智能体核心技能与工具链 |
| 01-specs | 工程规范 | Skill 开发 | 业务需求、技术规范、设计规范 |
| 04-data | Skill 开发 | 前端/规范 | 数据集准备与评测体系建设 |
| 05-deployment | 前端开发 | 工程规范 | 容器化与持续交付 |

## 快速开始

### 环境要求
- Node.js >= 20
- Python >= 3.10（AI/算法侧）
- Docker（可选，用于部署）

### 安装依赖
```bash
# 根目录安装 workspace 依赖
npm install

# 安装前端依赖
cd 03-frontend && npm install
```

### 启动开发环境
```bash
# 启动前端开发服务器
npm run dev:frontend

# 启动 BFF 服务
npm run dev:bff
```

## 协作规范

- 所有代码修改必须同步更新对应规格文档（`01-specs/`）
- Skill 开发遵循 `01-specs/technical/skill-standard.md` 规范
- 提交前运行 `npm run lint` 与 `npm run test`
- 重大架构变更需先在 `01-specs/technical/architecture.md` 中更新设计

## 文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| AI 协作指南 | `CLAUDE.md` | 与 AI 助手协作的规范与约定 |
| Agent 工作流 | `AGENTS.md` | 智能体开发流程与验收标准 |
| 产品需求 | `01-specs/requirements/PRD.md` | 业务需求与功能清单 |
| 架构设计 | `01-specs/technical/architecture.md` | 系统架构与技术选型 |
| Skill 规范 | `01-specs/technical/skill-standard.md` | Skill 开发与注册规范 |
| Skill 注册表 | `02-skills/registry.json` | 全量 Skill 清单与元数据 |
