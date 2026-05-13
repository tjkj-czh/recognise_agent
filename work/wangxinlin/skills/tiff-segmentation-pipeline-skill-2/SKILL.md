---
name: tiff-segmentation-pipeline-skill
description: 用于 recognise_agent 项目里的 TIFF 上传、切片准备、分割识别、结果矢量拉取与地图绘制联调。用户提到“tiff切片识别绘制”“上传影像后跑分割并检查 vectors.geojson”“任务成功但地图不显示/边界错乱”时应使用该 skill。
license: Apache-2.0
---

# 规则

- 把当前 `SKILL.md` 所在目录定义为 `<skill-base>`，所有本地资源都基于 `<skill-base>` 解析。
- 把项目 Web 服务目录固定为 `work/wangxinlin/compliance_agent/web`，除非用户明确要求切换。
- 优先复用 `<skill-base>/scripts/pipeline_client.py` 与 `<skill-base>/scripts/run_pipeline.py`（上传事件场景优先 `<skill-base>/scripts/run_on_upload_event.py`），不要在会话里重复手写同类调用逻辑。
- 先验证服务可用，再执行上传与任务链路；禁止在服务不可达时直接判定业务失败。
- 任务完成后必须拉取 `/api/layers/{image_id}/vectors.geojson` 做结果验收，不能只看 `/api/tasks/{task_id}` 的 `success`。
- 调试绘制异常时，按“后端结果是否为空 → 前端是否拿到结果 → 融合后几何是否异常”顺序排查，不得跳步。
- 输出结论时默认给出：关键 ID（`image_id`、`task_id`）、任务状态、`feature_count`、`vectors.geojson` 要素数量、下一步动作。
- 在 Windows 环境优先使用 `py -3` 运行 Python 脚本；若不可用再退回 `python`。

# 工作流程

## Step 1：对齐输入与运行参数

- 收集最小参数：`base_url`、`tile_size`、`overlap`、轮询超时，以及 `tiff_path` 或 `image_id`（二选一）。
- 若用户未提供参数，读取 `<skill-base>/config.yaml` 默认值。
- 若由“上传完成事件”触发，优先使用事件中的 `image_id` 直接进入任务创建与结果核验，无需重复上传。

## Step 2：执行 TIFF → 切片 → 识别 主链路

- 使用 `<skill-base>/scripts/run_pipeline.py` 一次性执行：
  - 上传：`POST /api/imagery/upload`
  - 轮询切片就绪：`GET /api/imagery/{image_id}`
  - 发起分割任务：`POST /api/tasks/segment`
  - 轮询任务结束：`GET /api/tasks/{task_id}`
  - 拉取矢量：`GET /api/layers/{image_id}/vectors.geojson`
- 每一步失败都立即返回结构化错误，不吞异常。

## Step 3：执行结果验收与绘制联调

- 读取并记录：任务 `status`、`feature_count`、GeoJSON `features` 数量。
- 若任务 `success` 但 GeoJSON 为空，按 `<skill-base>/references/troubleshooting.md` 的“空结果”分支排查。
- 若 GeoJSON 非空但前端不显示，输出“前端渲染链路排查清单”并给出最小复现请求。
- 若几何错乱，优先检查后端融合参数与策略，再决定是否切换保守融合。

## Step 4：按标准完成校验与测评

- 结构校验：执行 `py -3 "<creator>/scripts/quick_validate.py" "<skill-base>" --strict`。
- 触发测评：用 `py -3 "<skill-base>/scripts/run_skill_eval.py" --mode trigger` 跑 `evals/trigger-eval-set.json`。
- 链路测评（可选）：给定真实 tiff 时执行 `py -3 "<skill-base>/scripts/run_skill_eval.py" --mode smoke --tiff "<path>"`。
- 输出测评摘要与失败样本。

## Step 5：交付与复用

- 输出技能产物路径、执行命令、测评结果摘要。
- 如需分发，执行 creator 打包脚本生成 `.skill` 文件。

# 索引

- 接口契约：`<skill-base>/references/api-contract.md`
- 异常排查：`<skill-base>/references/troubleshooting.md`
- 测评规范：`<skill-base>/references/evaluation.md`
- 管道客户端：`<skill-base>/scripts/pipeline_client.py`
- 一键执行入口：`<skill-base>/scripts/run_pipeline.py`
- 测评入口：`<skill-base>/scripts/run_skill_eval.py`
