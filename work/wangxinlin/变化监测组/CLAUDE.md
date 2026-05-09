# CLAUDE.md — 变化监测智能体

## 项目定位

变化监测智能体是面向自然资源监管领域的 AI 驱动遥感监测平台。核心能力包括：遥感影像变化检测、供地数据智能分析、监测报告自动生成、多模态交互（对话 + 地图 + 时序对比）。

## 技术栈

### 前端
- React 19 + TypeScript 5
- Tailwind CSS + shadcn/ui
- Leaflet / MapLibre GL（地图渲染）
- ECharts（数据可视化）
- Zustand（状态管理）

### BFF（Backend for Frontend）
- Node.js + Fastify / Express
- tRPC 或 OpenAPI 契约
- 与 Skill 网关通过 IPC / HTTP 通信

### Skill / AI 层
- Python 3.10+
- 遥感处理：GDAL、Rasterio、OpenCV
- 模型推理：ONNX Runtime / PyTorch（轻量部署版）
- LLM 编排：LangChain / 自研 Agent Runtime
- 向量数据库：Chroma / Qdrant（可选）

## 协作约定

### 代码规范
- TypeScript：`strict` 模式开启，禁止 `any`
- Python：Black + Ruff 格式化，PEP 8 规范
- 文件命名：kebab-case（组件 PascalCase 除外）
- 模块导入：绝对路径优先（`@/components`），禁止相对路径深层引用（`../../../`）

### 文档同步原则
- 修改代码实现时，必须同步更新 `01-specs/` 中的对应规格文档
- 新增 Skill 必须在 `02-skills/registry.json` 中注册，并在 `01-specs/technical/skill-standard.md` 中补充规范说明
- API 接口变更需同步更新 `01-specs/requirements/api-spec.md`

### AI 辅助边界
- AI 可自主完成：代码生成、单元测试、文档补全、数据 mock、CRUD 接口
- AI **必须**人工确认：数据库 schema 变更、生产环境配置、敏感权限操作、核心算法逻辑调整
- AI **禁止**执行：删除生产数据、修改 CI/CD 密钥、直接推送主分支

### 提交规范
```
<type>(<scope>): <subject>

<body>

<footer>
```
- type: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- scope: `frontend`, `bff`, `skill`, `spec`, `data`, `deploy`

## 关键路径

```
用户指令 → 前端界面 → BFF 网关 → Skill 编排器 → 核心 Skill（变化检测 / 数据查询 / 报告生成） → 结果回流 → 前端渲染
```

## 常用命令

```bash
# 根目录
npm run dev:frontend    # 启动前端
npm run dev:bff         # 启动 BFF
npm run lint            # 全量代码检查
npm run test            # 全量测试
npm run build           # 生产构建

# Skill 开发
cd 02-skills && python -m pytest  # 运行 Skill 单元测试
```
