# TIFF 链路接口契约（recognise_agent）

## 1. 上传影像
- **接口**: `POST /api/imagery/upload`
- **入参**: `multipart/form-data`，字段 `file`，仅支持 `.tif/.tiff`
- **成功关键字段**:
  - `image_id`
  - `status`（通常为 `tiling`）
  - `tile_size` / `expected_tile_count`
  - `bbox` / `source_bbox`

## 2. 查询影像状态
- **接口**: `GET /api/imagery/{image_id}`
- **成功判据**:
  - `status` 变为 `ready`
  - `tiles` 数组非空，或 `tile_count > 0`

## 3. 创建分割任务
- **接口**: `POST /api/tasks/segment`
- **入参**:
  - `image_id`
  - `model`（固定 `falcon`）
  - `tile_size`、`overlap`（服务端可能按影像参数覆盖）
- **成功关键字段**:
  - `task_id`
  - `status`（`pending`）
  - `result_layer_id`

## 4. 查询任务进度
- **接口**: `GET /api/tasks/{task_id}`
- **终态**:
  - `status=success` 或 `status=failed`
- **重点字段**:
  - `feature_count`
  - `completed_tiles`
  - `success_tiles`
  - `falcon_runs`

## 5. 获取矢量结果
- **接口**: `GET /api/layers/{image_id}/vectors.geojson`
- **成功判据**:
  - 返回 `FeatureCollection`
  - `features` 数组长度可用于绘制验收

## 6. 最小验收标准
- `task.status == success`
- `vectors.geojson` 可访问
- `features` 数量与任务 `feature_count` 不明显矛盾（允许轻微差异）
