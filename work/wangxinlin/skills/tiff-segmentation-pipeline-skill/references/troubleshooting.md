# 异常排查手册

## A. 任务成功但 `vectors.geojson` 为空
1. 先核对 `/api/tasks/{task_id}` 的 `feature_count`。
2. 若 `feature_count > 0` 但 `features=[]`，优先判定为后端融合或写回阶段问题。
3. 检查后端日志是否出现 `global_draw`、`merge`、`shapely` 相关错误。
4. 先切到保守融合策略，再复跑同一影像验证。

## B. `vectors.geojson` 非空但地图不显示
1. 前端是否请求了正确 `image_id`。
2. Cesium 图层是否被覆盖或被过滤器清空。
3. 是否存在“任务 success 早于矢量落盘”的时序问题（应有短重试）。
4. 控制台是否有渲染错误或未声明变量异常。

## C. 边界错乱或跨区域粘连
1. 检查融合策略是否过于激进（如 `polygonize` 重建导致误拼接）。
2. 降低吸附/闭运算阈值，优先使用保守并集。
3. 限制按类别融合，避免不同语义对象互相连接。
4. 做面积阈值过滤，清理异常小碎片。

## D. 服务不可用
1. 确认 `work/wangxinlin/compliance_agent/web/app.py` 服务已启动。
2. 检查 `base_url` 是否正确。
3. 优先验证 `GET /api/land-segments` 或 `GET /api/chat/history` 可达性。
