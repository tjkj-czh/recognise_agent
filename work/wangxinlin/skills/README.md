# Skills 目录说明

本目录集中存放项目所有 Skill 模块，按功能分类管理。

## 目录结构

```
skills/
├── compliance/                      # Agent 核心合规分析技能
│   ├── farmland_skill.py            # 耕地保护检查
│   ├── construction_skill.py        # 建设用地检查
│   ├── water_eco_skill.py           # 水体生态检查
│   ├── review_priority_skill.py     # 人工复核优先级排序
│   ├── summary_skill.py             # 合规报告摘要生成
│   ├── intent_recognition_skill.py  # 自然语言意图识别
│   └── skill_creator_skill.py       # Skill 生命周期管理（创建/验证/打包/评估）
├── tiff-segmentation-pipeline-skill-2/ # TIFF 遥感影像全链路处理
│   ├── SKILL.md                     # 主规范：上传→切片→分割→矢量拉取→联调
│   ├── config.yaml                  # pipeline 参数与 eval 配置
│   ├── scripts/
│   │   ├── imagery_skill.py         # 核心处理：GeoTIFF 解析、Cesium 叠加预览、448×448 瓦片切片
│   │   ├── pipeline_client.py       # 链路 API 客户端（upload / wait / segment / vectors）
│   │   ├── run_pipeline.py          # 一键执行入口
│   │   └── run_skill_eval.py        # 校验 + 触发测评 + 冒烟 统一入口
│   ├── references/
│   │   ├── api-contract.md          # Web 后端接口契约
│   │   ├── troubleshooting.md       # 异常排查指南
│   │   └── evaluation.md            # 测评规范
│   └── evals/                       # 触发测评样本集
├── landuse-chat-router-skill/       # 用地智能对话路由
│   └── chat_skill.py                # 关键词路由 + LLM 问答（上下文检索 / 联网搜索）
└── DazhuangSkill-Creator-main/      # Skill 创建与评测框架
    ├── scripts/                     # init_skill.py / quick_validate.py / package_skill.py / run_eval.py
    └── references/                  # 规范文档与评测模板
```

## Agent 集成清单

用地识别 Agent（`compliance_agent/agent/core.py`）当前集成 **12 个 Tools**：

| # | Tool | 来源 | 功能 |
|---|------|------|------|
| 1 | `farmland_check` | `compliance/farmland_skill.py` | 耕地占比关注、基本农田疑似检查 |
| 2 | `construction_check` | `compliance/construction_skill.py` | 建设用地合规检查 |
| 3 | `water_eco_check` | `compliance/water_eco_skill.py` | 水体生态检查 |
| 4 | `review_priority` | `compliance/review_priority_skill.py` | 人工复核优先级排序 |
| 5 | `generate_summary` | `compliance/summary_skill.py` | 生成结构化合规报告摘要 |
| 6 | `intent_recognition` | `compliance/intent_recognition_skill.py` | 解析用户自然语言意图 |
| 7 | `skill_create` | `compliance/skill_creator_skill.py` | 创建 Skill 脚手架 |
| 8 | `skill_validate` | `compliance/skill_creator_skill.py` | 验证 Skill 结构合规性 |
| 9 | `skill_package` | `compliance/skill_creator_skill.py` | 打包 Skill 为 `.skill` 文件 |
| 10 | `skill_evaluate_trigger` | `compliance/skill_creator_skill.py` | 评估 Skill 触发准确率 |
| 11 | `imagery_check` | `tiff-segmentation-pipeline-skill-2/scripts/imagery_skill.py` | 影像元数据解析、预览生成、瓦片切片 |
| 12 | `landuse_chat` | `landuse-chat-router-skill/chat_skill.py` | 用地政策法规智能问答 |

> 注：`imagery_check` Tool 底层实现为 `tiff-segmentation-pipeline-skill-2/scripts/imagery_skill.py`；完整的 TIFF→切片→分割→矢量→联调链路编排由同 skill 的 `pipeline_client.py` 和 `run_pipeline.py` 提供。

## Web 后端复用

Flask Web 后端（`compliance_agent/web/app.py`）直接复用以下 Skill：
- `compliance/intent_recognition_skill.py` → `/api/intent`
- `compliance/skill_creator_skill.py` → `/api/skill/*`
- `tiff-segmentation-pipeline-skill-2/scripts/imagery_skill.py` → `/api/imagery/upload`、`/api/layers/*/tiles/*`
- `landuse-chat-router-skill/chat_skill.py` → `/api/chat`

> `tiff-segmentation-pipeline-skill-2/scripts/pipeline_client.py` 封装了上述影像相关接口的完整调用链路（upload → poll → segment → vectors），供 Agent 通过脚本确定性执行。

## 框架依赖

`DazhuangSkill-Creator-main/` 为 Skill Creator 提供底层脚本支持，**不可删除**。`skill_creator_skill.py` 通过调用该框架的 `scripts/` 完成 Skill 的初始化、验证、打包与评测。
