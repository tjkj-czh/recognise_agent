# 01-specs / 工程规范包

本目录存放项目全生命周期所需的规格文档与规范标准，是团队协作的"单一事实来源"。

## 目录结构

```
01-specs/
├── requirements/          # 业务需求规格
│   ├── PRD.md             # 产品需求文档（功能清单、用户故事、验收条件）
│   ├── user-stories.md    # 用户故事集
│   └── api-spec.md        # 前后端接口契约（OpenAPI / tRPC）
├── technical/             # 技术规范
│   ├── architecture.md    # 系统架构设计（模块关系、数据流、部署拓扑）
│   ├── frontend-standard.md   # 前端开发规范（目录结构、命名、状态管理）
│   ├── backend-standard.md    # BFF 开发规范（路由、错误码、日志）
│   ├── skill-standard.md      # Skill 开发规范（注册、Prompt、评测）
│   ├── database-design.md     # 数据库设计（ER 图、表结构、索引）
│   └── memory-system-guide.md # 记忆沉淀流程
├── design/                # 设计规范
│   ├── ui-design-system.md    # UI 设计系统（色彩、字体、间距、圆角）
│   └── interaction-spec.md    # 交互规范（动画时长、手势、反馈）
└── review-checklist.md    # 验收检查单（前端 / Skill / 文档）
```

## 维护责任人

| 文档 | 主负责人 | 更新触发条件 |
|------|---------|-------------|
| PRD.md | 工程规范 | 新增/变更业务功能 |
| api-spec.md | 工程规范 | 接口字段或路由变更 |
| architecture.md | 工程规范 | 技术选型或模块拆分调整 |
| skill-standard.md | 工程规范 | 新增 Skill 类型或开发流程变更 |
| frontend-standard.md | 前端开发 | 前端技术栈或目录结构调整 |
| backend-standard.md | 前端开发 | BFF 接口规范或中间件调整 |
| database-design.md | Skill 开发 | 数据模型或表结构变更 |
| review-checklist.md | 工程规范 | 验收标准调整 |

## 使用原则

1. **先写规格，后写代码**：重大功能开发前，PRD 与接口契约必须先通过评审
2. **修改即同步**：代码实现与规格文档必须保持同步，不一致时以最新提交的规格为准
3. **版本可追溯**：规格文档的变更通过 Git 历史追踪，重大变更需在文档顶部标注版本与日期
