# tiff-segmentation-pipeline-skill

按 `DazhuangSkill-Creator-main` 标准封装的项目技能，用于 recognise_agent 的 TIFF 上传 → 切片准备 → 分割识别 → 矢量结果核验与绘制联调。

## 目录
- `SKILL.md`：技能主体（规则 + 工作流程）
- `config.yaml`：默认参数
- `references/`：接口契约、排障、测评规范
- `assets/output-format.md`：输出模板
- `scripts/`：执行与测评脚本
- `evals/trigger-eval-set.json`：触发测评集

## 快速使用

### 1) 直接上传 TIFF 并执行全链路
```bash
python scripts/run_pipeline.py --base-url http://127.0.0.1:5000 --tiff "D:/data/demo.tif"
```

### 2) 上传事件触发（推荐）
当上游系统已上传完成并拿到 `image_id`，可直接续跑分割：
```bash
python scripts/run_pipeline.py --base-url http://127.0.0.1:5000 --image-id "<image_id>"
```

### 3) 事件 JSON 触发
支持从事件体中自动提取 `image_id` 或 `tiff_path`：
```bash
python scripts/run_pipeline.py --base-url http://127.0.0.1:5000 --event-file "D:/event/upload_event.json"
```

`--event-file` / `--event-json` / `--event-stdin` 支持以下字段（任一即可）：
- `image_id`
- `tiff_path` / `file_path` / `path`
- 也支持嵌套在 `data` 或 `payload` 下

### 4) 第三方系统推荐入口（封装调用）
当对方系统“上传完成后抛事件”时，推荐直接调用封装入口：
```bash
python scripts/run_on_upload_event.py --base-url http://127.0.0.1:5000 --event-file "D:/event/upload_event.json"
```

也支持从标准输入读取事件：
```bash
type D:\event\upload_event.json | python scripts/run_on_upload_event.py --base-url http://127.0.0.1:5000 --event-stdin
```

> 建议在 Windows/PowerShell 场景优先使用 `--event-file` 或 `--event-stdin`，避免 `--event-json` 受引号转义影响。

Windows 可直接用：
```bat
scripts\run_on_upload_event.bat --base-url http://127.0.0.1:5000 --event-file "D:\event\upload_event.json"
```

## 校验
```bash
python scripts/run_skill_eval.py --mode validate
```

## 说明
- `scripts/run_skill_eval.py` 已自动探测 `py/python/python3`，避免目标机器没有 `py` 时失败。
- 若传入 `image_id` 与 `tiff_path`，优先使用 `image_id`（避免重复上传）。
