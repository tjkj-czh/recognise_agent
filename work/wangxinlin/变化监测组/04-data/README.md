# 04-data / 数据资产包

本目录存放变化监测智能体所需的数据资产，包括评测数据集、基准测试脚本与开发期模拟数据。

## 目录结构

```
04-data/
├── datasets/                    # 评测数据集
│   ├── remote-sensing/          # 遥感影像样本
│   │   ├── before/              # 变化前影像
│   │   ├── after/               # 变化后影像
│   │   └── ground-truth/        # 人工标注的变化图斑
│   ├── land-supply/             # 供地数据样本
│   │   ├── announcements/       # 供地公告原文
│   │   └── parsed/              # 解析后的结构化数据
│   └── vector-knowledge/        # 向量知识库数据
│       ├── regulations/         # 法规政策文档
│       └── qa-pairs/            # 问答对
├── benchmarks/                  # 基准测试
│   ├── change-detection/        # 变化检测评测脚本
│   ├── report-generation/       # 报告生成评测脚本
│   └── data-query/              # 数据查询评测脚本
└── mock-data/                   # 开发期模拟数据
    ├── mock-plots.json          # 模拟地块数据
    ├── mock-messages.json       # 模拟对话数据
    └── mock-reports.md          # 模拟报告模板
```

## 数据管理规范

1. **原始数据禁止提交 Git**：遥感影像、大文件放入 `.gitignore`，通过网盘或对象存储共享
2. **元数据必须提交**：数据集目录下必须包含 `README.md` 说明数据来源、采集时间、坐标系、字段说明
3. **评测集不可污染**：评测数据集一旦冻结，仅允许追加不可修改，确保结果可比性
4. **敏感数据脱敏**：涉及真实供地信息的数据必须进行脱敏处理（隐匿精确坐标、隐去权利人姓名）

## 数据集注册

| 数据集 | 类型 | 状态 | 说明 |
|--------|------|------|------|
| 余杭区2024供地监测集 | remote-sensing | 待采集 | 覆盖余杭区12宗地块，前后两期 Sentinel-2 影像 |
| 供地公告样本集 | land-supply | 待采集 | 中国土地市场网2024年杭州市公告 |
| 遥感监测问答对 | vector-knowledge | 待构建 | 基于法规与业务知识的问答对 |

## 快速开始

```bash
# 运行变化检测基准测试
cd benchmarks/change-detection
python evaluate.py --dataset ../../datasets/remote-sensing --output report.json

# 生成开发期模拟数据
cd ../mock-data
python generate-mock.py
```
