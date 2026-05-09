Imagery Cesium Overlay Skill

简介
- 将“影像上传 → 元数据解析 → 叠加预览（SingleTile PNG）→ 分割任务 → 结果矢量层”封装为可被其他智能体直接调用的统一接口。
- 本 Skill 作为轻量 HTTP 客户端，复用现有 Flask Web 后端的 REST 接口。

环境要求
- 已启动本项目的 Flask Web 服务（默认 http://127.0.0.1:5000）。
- Python 3.9+，第三方依赖：requests。

安装依赖
- 在项目根目录执行（若未安装）：
  pip install requests

快速开始

  from skills.imagery-cesium-overlay.imagery_skill import ImageryOverlayClient
  client = ImageryOverlayClient(base_url="http://127.0.0.1:5000")
  meta = client.upload_imagery("/abs/path/to/your.tif")
  overlay = client.get_overlay_meta(meta["image_id"])  # {bbox, overlay_url}
  # 可选：
  task = client.start_segmentation(meta["image_id"])  # 创建分割任务
  final = client.poll_task(task["task_id"])            # 等待完成
  seg = client.get_segment_geojson(meta["image_id"])   # 获取分割结果

接口一览
- upload_imagery(file_path: str) -> dict
- get_overlay_meta(image_id: str) -> dict
- start_segmentation(image_id: str, model: str = "falcon", tile_size: int = 1024, overlap: int = 128) -> dict
- poll_task(task_id: str, max_retries: int = 20, interval_ms: int = 1500) -> dict
- get_segment_geojson(image_id: str) -> dict

与前端 Cesium 的衔接
- 前端可直接将 overlay.overlay_url 作为 Cesium.SingleTileImageryProvider 的 URL，并使用返回的 bbox 构造 Cesium.Rectangle.fromDegrees(minx, miny, maxx, maxy)。

注意事项
- 上传文件需为 GeoTIFF，且服务端会校验地理参考与 WGS84 可达性。
- 若服务端更换端口或部署到远端，请相应调整 base_url。
