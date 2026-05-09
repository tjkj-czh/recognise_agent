# 02-skills / Skill 文件包

本目录存放变化监测智能体的全部 AI 能力与工具封装，是系统的"智能引擎"。

## 目录结构

```
02-skills/
├── core/                    # 核心能力 Skill（业务主链路）
│   ├── remote-sensing-change-detection/   # 遥感变化检测
│   ├── land-supply-data-query/            # 供地数据查询
│   └── report-generation/                 # 监测报告生成
├── agents/                  # 智能体编排 Skill（工作流组合）
│   ├── monitoring-orchestrator/           # 监测任务编排
│   └── report-orchestrator/               # 报告生成编排
├── tools/                   # 工具 Skill（基础设施能力）
│   ├── geocoding/                         # 地理编码
│   ├── image-tile-fetcher/                # 影像瓦片获取
│   └── vector-db-query/                   # 向量数据库查询
├── prompts/                 # 复用提示词模板
│   ├── system-prompts/                    # 系统提示词
│   └── few-shots/                         # 少样本示例
├── skill-creator/           # Skill 开发工具（DazhuangSkill-Creator）
│   ├── SKILL.md                           # Skill 定义
│   ├── scripts/                           # 脚手架、校验、评测、打包脚本
│   ├── references/                        # 架构说明与评测流程
│   ├── assets/                            # 模板与可复用资源
│   └── config.yaml                        # 默认配置
├── registry.json            # Skill 注册表（全量清单）
└── requirements.txt         # 公共 Python 依赖
```

## 开发规范

详见 `01-specs/technical/skill-standard.md`。

## 快速开始

```bash
# 进入 Skill 目录
cd 02-skills

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行测试
python -m pytest

# 注册新 Skill
# 1. 在对应子目录下创建 Skill 目录
# 2. 填写 skill.json 与 README.md
# 3. 在 registry.json 中登记

# 使用 skill-creator 创建新 Skill（推荐）
cd skill-creator
python scripts/init_skill.py my-new-skill --path ../core --memory-mode auto --intent "低风险、低变异、可确定性执行"
python scripts/quick_validate.py ../core/my-new-skill
```

## 核心 Skill 列表

| Skill | 类型 | 状态 | 说明 |
|-------|------|------|------|
| remote-sensing-change-detection | core | 规划中 | 基于遥感影像的 AI 变化检测 |
| land-supply-data-query | core | 规划中 | 供地公告数据查询与解析 |
| report-generation | core | 规划中 | 监测报告自动生成 |
| monitoring-orchestrator | agent | 规划中 | 监测任务全流程编排 |
| report-orchestrator | agent | 规划中 | 报告生成流程编排 |
| geocoding | tool | 规划中 | 地址转坐标、坐标转地址 |
| image-tile-fetcher | tool | 规划中 | 遥感影像瓦片下载与缓存 |
| vector-db-query | tool | 规划中 | 语义检索与知识库查询 |
| skill-creator | dev | 已激活 | Skill 脚手架创建、重构、评估、打包与优化工具 |
