# Skill 开发规范

> 版本：0.1.0 | 日期：2026-05-08

## 1. Skill 定义

Skill 是变化监测智能体的最小能力单元，封装特定的 AI 能力或工具调用。每个 Skill 具备明确的输入契约、输出契约与副作用声明。

## 2. 目录结构

```
02-skills/
├── core/                    # 核心能力 Skill
│   ├── remote-sensing-change-detection/
│   ├── land-supply-data-query/
│   └── report-generation/
├── agents/                  # 智能体编排 Skill
│   ├── monitoring-orchestrator/
│   └── report-orchestrator/
├── tools/                   # 工具 Skill
│   ├── geocoding/
│   ├── image-tile-fetcher/
│   └── vector-db-query/
├── prompts/                 # 复用提示词模板
│   ├── system-prompts/
│   └── few-shots/
└── registry.json            # Skill 注册表
```

## 3. Skill 目录规范

每个 Skill 必须包含：

```
skill-name/
├── README.md            # 能力说明、调用示例、边界条件
├── skill.json           # 元数据（名称、版本、作者、依赖）
├── main.py              # 入口逻辑
├── prompt.md            # 系统提示词（如适用）
├── tests/               # 单元测试
│   ├── test_main.py
│   └── fixtures/
└── requirements.txt     # Python 依赖
```

### skill.json 格式

```json
{
  "name": "remote-sensing-change-detection",
  "version": "0.1.0",
  "type": "core",
  "author": "skill-dev",
  "description": "基于遥感影像的变化检测能力",
  "input_schema": {
    "type": "object",
    "properties": {
      "bbox": { "type": "array", "items": "number" },
      "before_date": { "type": "string", "format": "date" },
      "after_date": { "type": "string", "format": "date" }
    },
    "required": ["bbox", "before_date", "after_date"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "change_polygons": { "type": "array" },
      "confidence": { "type": "number" }
    }
  },
  "dependencies": ["gdal", "rasterio", "onnxruntime"],
  "timeout_seconds": 120
}
```

## 4. 开发原则

### 4.1 单一职责
- 一个 Skill 只做一件事，复杂场景通过 Agent 编排多个 Skill
- 避免"万能 Skill"，保持可测试与可复用

### 4.2 无副作用声明
- Skill 必须在 `README.md` 中明确声明副作用（如：写入数据库、调用外部 API、消耗额度）
- 纯查询类 Skill 禁止产生写操作

### 4.3 失败模式
- 所有 Skill 必须定义明确的异常类型与错误码
- 超时、空结果、依赖不可用等情况需返回结构化错误，禁止抛出未捕获异常

### 4.4 Prompt 工程（LLM Skill）
- 系统提示词与少样本示例分离：系统提示词放在 `prompt.md`，少样本放在 `prompts/few-shots/`
- 必须包含输入校验与注入防护指令
- 输出格式强制要求：如 JSON Schema、Markdown 模板

## 5. Skill 开发工具

项目已集成 `skill-creator`（基于 DazhuangSkill-Creator），用于辅助 Skill 的创建、重构、评估与打包。

### 5.1 创建新 Skill

```bash
cd 02-skills/skill-creator
python scripts/init_skill.py <skill-name> --path ../<type> --memory-mode auto --intent "<任务语义>"
```

常用参数：
- `--path`：输出目录（如 `../core`、`../tools`）
- `--memory-mode`：`off` / `adaptive` / `lessons` / `auto`（默认）
- `--intent`：任务语义描述，供 auto 模式判型
- `--resources`：额外生成 `scripts,references,assets`
- `--sections`：单文件 Skill 可选章节，如 `role,output-format`
- `--examples`：生成 `references/examples.md`

### 5.2 校验 Skill 结构

```bash
python scripts/quick_validate.py <skill-dir>
# 交付前严格校验
python scripts/quick_validate.py <skill-dir> --strict
```

### 5.3 评估与打包

```bash
# 评估前置对齐 → 正式评估计划 → 执行评测
# 详见 skill-creator/references/eval-planning.md

# 打包 Skill
python scripts/package_skill.py <skill-dir> <output-dir>
```

## 6. 注册流程

1. 在 `02-skills/` 下按规范创建 Skill 目录（或使用 `skill-creator` 脚手架）
2. 填写 `skill.json` 与 `README.md`
3. 在 `02-skills/registry.json` 中注册
4. 提交前运行 `python -m pytest` 通过全部测试
5. 在 `01-specs/technical/architecture.md` 中更新数据流（如涉及新接口）

## 7. 评测要求

- 每个核心 Skill 必须配套 `04-data/benchmarks/` 中的评测用例
- 评测指标：准确率、召回率、F1、平均响应时间、成功率
- 评测脚本需可自动化执行，输出标准化 JSON 报告
