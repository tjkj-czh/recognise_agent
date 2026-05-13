"""用地识别智能体 Web Demo - Flask应用。"""

import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path

import numpy as np
from PIL import Image
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("landuse-agent")

# 确保项目根目录在sys.path中，使import config和rules可用
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# 技能目录（含连字符需特殊处理）
WORKSPACE_DIR = os.path.dirname(PROJECT_ROOT)
sys.path.insert(0, WORKSPACE_DIR)  # 使 from skills.compliance.xxx 可解析
SKILL_DIR = os.path.join(WORKSPACE_DIR, "skills", "landuse-chat-router-skill")
sys.path.insert(0, SKILL_DIR)

IMAGERY_SKILL_DIR = os.path.join(WORKSPACE_DIR, "skills", "tiff-segmentation-pipeline-skill-2", "scripts")
sys.path.insert(0, IMAGERY_SKILL_DIR)

# 加载 .env 环境变量
load_dotenv(os.path.join(WORKSPACE_DIR, ".env"))

from flask import Flask, render_template, request, jsonify, send_file

from rules.compliance_rules import evaluate_rules
from web.report_builder import build_report
from skills.compliance.intent_recognition_skill import recognize_intent
from skills.compliance.skill_creator_skill import (
    skill_create,
    skill_validate,
    skill_package,
    skill_evaluate_trigger,
    get_dazhuang_info,
)
from imagery_skill import process_uploaded_imagery

WEB_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(WEB_DIR, "data")
EVAL_DIR = os.path.join(PROJECT_ROOT, "eval")


def _load_sample_parcels() -> list[dict]:
    path = os.path.join(DATA_DIR, "sample_parcels.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_parcels_geojson() -> dict:
    path = os.path.join(DATA_DIR, "parcels.geojson")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_land_segments() -> dict:
    path = os.path.join(DATA_DIR, "land_segments.geojson")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)



def create_app():
    app = Flask(__name__,
                template_folder=os.path.join(WEB_DIR, "templates"),
                static_folder=os.path.join(WEB_DIR, "static"))

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/parcels")
    def get_parcels():
        """返回所有图斑GeoJSON，含预计算的合规风险等级。"""
        parcels_data = _load_sample_parcels()
        geojson = _load_parcels_geojson()

        # 为每个图斑计算合规结果，合并到GeoJSON properties
        for feature, parcel in zip(geojson["features"], parcels_data):
            triggered = evaluate_rules(parcel)
            report = build_report(parcel, triggered)
            props = feature["properties"]
            props["overall_risk_level"] = report["overall_risk_level"]
            props["triggered_rules_count"] = len(triggered)
            props["land_types"] = parcel["land_types"]

        return jsonify(geojson)

    @app.route("/api/parcel/<parcel_id>")
    def get_parcel(parcel_id):
        """根据图斑ID返回完整合规报告。"""
        parcels_data = _load_sample_parcels()
        parcel = next((p for p in parcels_data if p["parcel_id"] == parcel_id), None)
        if not parcel:
            return jsonify({"error": f"图斑 {parcel_id} 不存在"}), 404

        triggered = evaluate_rules(parcel)
        report = build_report(parcel, triggered)
        return jsonify(report)

    @app.route("/api/land-segments")
    def get_land_segments():
        """返回浙江省地类分割GeoJSON。"""
        return jsonify(_load_land_segments())


    @app.route("/api/analyze", methods=["POST"])
    def analyze():
        """分析用户输入的图斑数据，返回合规报告。"""
        req_start = time.time()
        parcel_data = request.get_json()
        if not parcel_data:
            logger.warning("[/api/analyze] 请求缺少图斑数据")
            return jsonify({"error": "请提供图斑数据"}), 400

        parcel_id = parcel_data.get("parcel_id", "unknown")
        logger.info("[/api/analyze] 开始分析 parcel_id=%s", parcel_id)
        logger.debug("[/api/analyze] 输入数据: %s", json.dumps(parcel_data, ensure_ascii=False)[:500])

        # 基本校验
        for field in ("parcel_id", "total_area_m2", "land_types", "dominant_type"):
            if field not in parcel_data:
                logger.warning("[/api/analyze] parcel_id=%s 缺少必填字段: %s", parcel_id, field)
                return jsonify({"error": f"缺少必填字段: {field}"}), 400

        # 规则引擎
        rule_start = time.time()
        triggered = evaluate_rules(parcel_data)
        rule_elapsed = round((time.time() - rule_start) * 1000, 2)
        logger.info("[/api/analyze] parcel_id=%s 规则引擎完成，触发 %d 条规则，耗时 %.2f ms",
                    parcel_id, len(triggered), rule_elapsed)
        for r in triggered:
            logger.info("[/api/analyze] 触发规则: [%s] %s - %s", r.get("rule_id"), r.get("rule_name"), r.get("risk_level"))

        # 报告生成
        report_start = time.time()
        report = build_report(parcel_data, triggered)
        report_elapsed = round((time.time() - report_start) * 1000, 2)
        total_elapsed = round((time.time() - req_start) * 1000, 2)

        logger.info("[/api/analyze] parcel_id=%s 报告生成完成，风险等级=%s，耗时 %.2f ms (规则%.2f ms + 报告%.2f ms)",
                    parcel_id, report.get("overall_risk_level"), total_elapsed, rule_elapsed, report_elapsed)
        return jsonify(report)

    @app.route("/api/intent", methods=["POST"])
    def recognize_intent_api():
        """语义意图识别API：解析用户自然语言输入，返回意图和参数。"""
        body = request.get_json() or {}
        user_input = body.get("input", "")
        if not user_input or not user_input.strip():
            return jsonify({"error": "请提供输入文本"}), 400
        result = recognize_intent(user_input)
        return jsonify(result)

    @app.route("/api/chat", methods=["POST"])
    def chat():
        """智能对话API：将用户输入交给 LanduseChatRouterSkill 处理。"""
        body = request.get_json() or {}
        message = body.get("message", "")
        context = body.get("context", None)
        session_id = body.get("session_id", "web-default")

        if not message or not message.strip():
            return jsonify({"error": "message不能为空"}), 400

        # 将 parcels 数据注入 context（若未提供）
        if context is None:
            context = {}
        if isinstance(context, dict) and "parcels" not in context:
            try:
                parcels = _load_sample_parcels()
                context["parcels"] = parcels
            except Exception:
                pass

        try:
            from chat_skill import LanduseChatRouterSkill
            skill = LanduseChatRouterSkill()
            result = skill.handle_dialog(message, context, session_id)
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": f"技能调用失败: {str(e)}"}), 500

    @app.route("/eval")
    def eval_page():
        """评测样本集浏览页面。"""
        return render_template("eval.html")

    @app.route("/api/eval/samples")
    def get_eval_samples():
        """返回所有评测样本列表（含预期但不执行分析）。"""
        path = os.path.join(EVAL_DIR, "eval_samples.json")
        with open(path, "r", encoding="utf-8") as f:
            samples = json.load(f)
        summary = []
        for s in samples:
            summary.append({
                "sample_id": s["sample_id"],
                "category": s["category"],
                "category_label": s["category_label"],
                "description": s["description"],
                "tags": s["tags"],
                "parcel_id": s["input"]["parcel_id"],
                "dominant_type": s["input"]["dominant_type"],
                "expected_rules": s["expected_rules"],
                "expected_risk_level": s["expected_risk_level"],
            })
        return jsonify(summary)

    @app.route("/api/eval/run", methods=["POST"])
    def run_eval():
        """批量运行评测，返回每个样本的实际结果与预期对比。"""
        path = os.path.join(EVAL_DIR, "eval_samples.json")
        with open(path, "r", encoding="utf-8") as f:
            samples = json.load(f)

        body = request.get_json() or {}
        category_filter = body.get("category")

        results = []
        for s in samples:
            if category_filter and s["category"] != category_filter:
                continue
            parcel_data = s["input"]
            triggered = evaluate_rules(parcel_data)
            report = build_report(parcel_data, triggered)
            triggered_ids = sorted([r["rule_id"] for r in triggered])
            expected_ids = sorted(s["expected_rules"])
            rules_match = triggered_ids == expected_ids
            risk_match = report["overall_risk_level"] == s["expected_risk_level"]
            review_match = (len(report["manual_review_items"]) > 0) == s["expected_manual_review"]
            passed = rules_match and risk_match and review_match
            results.append({
                "sample_id": s["sample_id"],
                "category": s["category"],
                "category_label": s["category_label"],
                "description": s["description"],
                "passed": passed,
                "triggered_rules": triggered_ids,
                "expected_rules": expected_ids,
                "rules_match": rules_match,
                "risk_level": report["overall_risk_level"],
                "expected_risk_level": s["expected_risk_level"],
                "risk_match": risk_match,
                "report": report,
                "adversarial_note": s.get("adversarial_note", ""),
            })

        total = len(results)
        passed_count = sum(1 for r in results if r["passed"])
        cat_stats = {}
        for r in results:
            cat = r["category"]
            if cat not in cat_stats:
                cat_stats[cat] = {"total": 0, "passed": 0, "label": r["category_label"]}
            cat_stats[cat]["total"] += 1
            if r["passed"]:
                cat_stats[cat]["passed"] += 1

        return jsonify({
            "total": total,
            "passed": passed_count,
            "pass_rate": round(passed_count / total * 100, 1) if total else 0,
            "category_stats": cat_stats,
            "results": results,
        })

    # === 影像上传 / Cesium 叠加 / 分割任务 ===
    UPLOAD_DIR = os.path.join(WEB_DIR, "uploads")
    OVERLAY_DIR = os.path.join(WEB_DIR, "overlays")
    TILES_DIR = os.path.join(WEB_DIR, "tiles")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OVERLAY_DIR, exist_ok=True)
    os.makedirs(TILES_DIR, exist_ok=True)
    image_meta_cache = {}

    @app.route("/api/imagery/upload", methods=["POST"])
    def upload_imagery():
        if "file" not in request.files:
            return jsonify({"error": "请上传文件"}), 400
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "文件名不能为空"}), 400

        image_id = str(uuid.uuid4())[:12]
        ext = Path(file.filename).suffix.lower()
        if ext not in {".tif", ".tiff"}:
            return jsonify({"error": "仅支持 GeoTIFF 格式 (.tif/.tiff)"}), 400

        src_path = os.path.join(UPLOAD_DIR, f"{image_id}{ext}")
        file.save(src_path)

        try:
            tiles_dir = os.path.join(TILES_DIR, image_id)
            result = process_uploaded_imagery(src_path, generate_tiles=True, tiles_dir=tiles_dir)
            # 将生成的 overlay 复制到 overlays 目录
            import shutil
            generated_overlay = result["overlay_path"]
            dest_overlay = os.path.join(OVERLAY_DIR, f"{image_id}.png")
            if generated_overlay != dest_overlay:
                shutil.copy(generated_overlay, dest_overlay)

            meta = {
                "image_id": image_id,
                "filename": os.path.basename(src_path),
                "crs": result["crs"],
                "bbox": result["bbox_wgs84"] or result["bbox"],
                "rows": result["rows"],
                "cols": result["cols"],
                "bands": result["bands"],
                "overlay_url": f"/api/layers/{image_id}/overlay.png",
                "tiles_url": f"/api/layers/{image_id}/tiles",
            }
            image_meta_cache[image_id] = meta
            return jsonify(meta)
        except Exception as e:
            return jsonify({"error": f"影像处理失败: {str(e)}"}), 500

    @app.route("/api/layers/<image_id>/overlay.png")
    def get_overlay_png(image_id):
        path = os.path.join(OVERLAY_DIR, f"{image_id}.png")
        if not os.path.exists(path):
            return jsonify({"error": "预览图不存在"}), 404
        return send_file(path, mimetype="image/png")

    @app.route("/api/layers/<image_id>/overlay")
    def get_overlay_meta(image_id):
        path = os.path.join(OVERLAY_DIR, f"{image_id}.png")
        if not os.path.exists(path):
            return jsonify({"error": "预览图不存在"}), 404

        # 优先从缓存读取，避免重复解析 GeoTIFF
        meta = image_meta_cache.get(image_id)
        if meta:
            return jsonify({
                "image_id": image_id,
                "bbox": meta["bbox"],
                "overlay_url": meta["overlay_url"],
            })

        # fallback：重新读取源文件
        import glob
        src_files = glob.glob(os.path.join(UPLOAD_DIR, f"{image_id}.*"))
        if not src_files:
            return jsonify({"error": "源文件不存在"}), 404
        import rasterio
        from rasterio.warp import transform_bounds
        with rasterio.open(src_files[0]) as src:
            bounds = src.bounds
            if src.crs and src.crs.to_epsg() != 4326:
                bounds = transform_bounds(src.crs, "EPSG:4326", *bounds)
            minx, miny, maxx, maxy = bounds
        return jsonify({
            "image_id": image_id,
            "bbox": [minx, miny, maxx, maxy],
            "overlay_url": f"/api/layers/{image_id}/overlay.png",
        })

    @app.route("/api/layers/<image_id>/tiles")
    def get_tiles_meta(image_id):
        """返回 448x448 瓦片元数据。"""
        meta_path = os.path.join(TILES_DIR, image_id, "tiles_meta.json")
        if not os.path.exists(meta_path):
            return jsonify({"error": "瓦片元数据不存在"}), 404
        with open(meta_path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))

    @app.route("/api/layers/<image_id>/tiles/0/<int:x>/<int:y>.png")
    def get_tile(image_id, x, y):
        """返回单张 448x448 瓦片（TMS 风格，y 从底部起算）。"""
        tile_path = os.path.join(TILES_DIR, image_id, "0", str(x), f"{y}.png")
        if not os.path.exists(tile_path):
            return jsonify({"error": "瓦片不存在"}), 404
        return send_file(tile_path, mimetype="image/png")

    # === tiff-segmentation-pipeline-skill-2: 分割任务引擎 ===
    import threading
    import rasterio
    from rasterio import features as rio_features
    from rasterio.warp import transform_geom

    tasks_db = {}
    VECTORS_DIR = os.path.join(WEB_DIR, "vectors")
    os.makedirs(VECTORS_DIR, exist_ok=True)

    def _find_source_tiff(image_id):
        """根据 image_id 查找上传的源 TIFF 文件。"""
        for ext in (".tif", ".tiff"):
            p = os.path.join(UPLOAD_DIR, f"{image_id}{ext}")
            if os.path.isfile(p):
                return p
        return None

    def _run_segmentation(image_id, task_id):
        """在后台线程中执行分割：提取有效数据区域的矢量轮廓。"""
        try:
            logger.info("[Segmentation] task=%s image=%s started", task_id, image_id)
            tasks_db[task_id]["status"] = "processing"
            src_path = _find_source_tiff(image_id)
            if not src_path:
                logger.warning("[Segmentation] task=%s source not found", task_id)
                tasks_db[task_id] = {"task_id": task_id, "status": "failed",
                                       "error_message": "源文件不存在"}
                return

            logger.info("[Segmentation] task=%s opening %s", task_id, src_path)
            with rasterio.open(src_path) as ds:
                band = ds.read(1)
                # 二值掩码：非零像素视为有效数据
                mask = (band > 0).astype("uint8")

                # 形态学闭运算：合并相邻小碎片（如果 scipy 可用）
                try:
                    from scipy import ndimage
                    # 闭运算：先膨胀后腐蚀，填充小孔洞、连接相邻区域
                    mask = ndimage.binary_closing(mask, iterations=2).astype("uint8")
                    logger.info("[Segmentation] task=%s applied morphological closing", task_id)
                except Exception:
                    pass

                logger.info("[Segmentation] task=%s band shape=%s extracting shapes...", task_id, band.shape)
                shapes = list(rio_features.shapes(band.astype("float32"), mask=mask,
                                                   transform=ds.transform, connectivity=8))
                src_crs = ds.crs
                # 估算单像素面积（平方米），用于后续过滤
                pixel_area_m2 = abs(ds.transform.a * ds.transform.e)
                width_px = ds.width
                height_px = ds.height
                logger.info("[Segmentation] task=%s extracted %d raw shapes, pixel_area=%.4f m2, size=%dx%d",
                            task_id, len(shapes), pixel_area_m2, width_px, height_px)

            # 检测是否缺少有效地理变换（pixel_area 异常小或 transform 为 identity）
            has_valid_georef = pixel_area_m2 > 1e-6 and not (
                abs(ds.transform.a - 1.0) < 1e-6 and
                abs(ds.transform.e - 1.0) < 1e-6 and
                abs(ds.transform.c) < 1e-6 and
                abs(ds.transform.f) < 1e-6
            )

            # 尝试使用 shapely 计算面积
            try:
                from shapely.geometry import shape as shapely_shape
                HAS_SHAPELY = True
            except Exception:
                HAS_SHAPELY = False

            MIN_AREA_PX = 50       # 最小像素面积（过滤单像素/线状碎片）
            MAX_FEATURES = 2000    # 最多保留要素数

            candidates = []
            for i, (geom, value) in enumerate(shapes):
                if value <= 0:
                    continue
                if geom["type"] != "Polygon":
                    continue
                coords = geom["coordinates"][0]
                if len(coords) < 4:
                    continue

                # 计算像素面积
                if HAS_SHAPELY:
                    try:
                        geo_area = shapely_shape(geom).area
                        area_px = int(geo_area / pixel_area_m2) if pixel_area_m2 > 1e-6 else int(geo_area)
                    except Exception:
                        area_px = len(coords)
                else:
                    area_px = len(coords)

                if area_px < MIN_AREA_PX:
                    continue

                if has_valid_georef:
                    # 有有效地理参考：转换到 WGS84
                    try:
                        geom_out = transform_geom(src_crs, "EPSG:4326", geom)
                    except Exception:
                        geom_out = geom
                else:
                    # 无有效地理参考：保持像素坐标，前端会进行映射
                    geom_out = geom

                candidates.append({
                    "area_px": area_px,
                    "feature": {
                        "type": "Feature",
                        "properties": {
                            "id": i,
                            "value": float(value),
                            "area_px": area_px,
                            "pixel_coords": not has_valid_georef,
                            "image_width": width_px,
                            "image_height": height_px,
                        },
                        "geometry": geom_out,
                    },
                })

            # 按面积从大到小排序，保留前 MAX_FEATURES 个
            candidates.sort(key=lambda x: x["area_px"], reverse=True)
            if len(candidates) > MAX_FEATURES:
                candidates = candidates[:MAX_FEATURES]

            features = [c["feature"] for c in candidates]

            geojson = {"type": "FeatureCollection", "features": features}
            vector_path = os.path.join(VECTORS_DIR, f"{image_id}.geojson")
            with open(vector_path, "w", encoding="utf-8") as f:
                json.dump(geojson, f, ensure_ascii=False)

            logger.info("[Segmentation] task=%s success features=%d (filtered from %d raw)",
                        task_id, len(features), len(shapes))
            tasks_db[task_id] = {"task_id": task_id, "status": "success",
                                  "image_id": image_id, "feature_count": len(features),
                                  "result_layer_id": image_id}
        except Exception as e:
            logger.exception("[Segmentation] task=%s failed", task_id)
            tasks_db[task_id] = {"task_id": task_id, "status": "failed",
                                  "error_message": str(e)}

    @app.route("/api/tasks/segment", methods=["POST"])
    def start_segmentation():
        body = request.get_json() or {}
        image_id = body.get("image_id")
        if not image_id:
            return jsonify({"error": "缺少 image_id"}), 400
        if not _find_source_tiff(image_id):
            return jsonify({"error": f"影像 {image_id} 源文件不存在"}), 404

        task_id = f"seg_{uuid.uuid4().hex[:8]}"
        tasks_db[task_id] = {"task_id": task_id, "status": "pending",
                              "image_id": image_id, "result_layer_id": image_id}
        t = threading.Thread(target=_run_segmentation, args=(image_id, task_id), daemon=True)
        t.start()
        return jsonify({"task_id": task_id, "status": "pending", "image_id": image_id})

    @app.route("/api/tasks/<task_id>")
    def get_task(task_id):
        task = tasks_db.get(task_id)
        if task is None:
            return jsonify({"task_id": task_id, "status": "failed",
                            "error_message": "任务不存在"})
        return jsonify(task)

    @app.route("/api/layers/<image_id>/vectors.geojson")
    def get_segment_geojson(image_id):
        vector_path = os.path.join(VECTORS_DIR, f"{image_id}.geojson")
        if os.path.isfile(vector_path):
            return send_file(vector_path, mimetype="application/geo+json")
        return jsonify({"type": "FeatureCollection", "features": []})

    # === Skill Creator API ===
    @app.route("/api/skill/info")
    def skill_info():
        """返回 DazhuangSkill-Creator 基本信息和可用工具列表。"""
        return jsonify(get_dazhuang_info())

    @app.route("/api/skill/create", methods=["POST"])
    def skill_create_api():
        """创建新 skill 脚手架。"""
        body = request.get_json() or {}
        name = body.get("name", "").strip()
        if not name:
            return jsonify({"error": "缺少 name 参数"}), 400
        result = skill_create.invoke({
            "name": name,
            "output_path": body.get("output_path", ""),
            "intent": body.get("intent", ""),
            "memory_mode": body.get("memory_mode", "auto"),
            "resources": body.get("resources", "scripts,references,assets"),
            "sections": body.get("sections", "role,examples,output-format,index"),
            "with_examples": body.get("with_examples", False),
            "with_config": body.get("with_config", False),
        })
        return jsonify(json.loads(result))

    @app.route("/api/skill/validate", methods=["POST"])
    def skill_validate_api():
        """验证 skill 目录结构。"""
        body = request.get_json() or {}
        skill_path = body.get("skill_path", "").strip()
        if not skill_path:
            return jsonify({"error": "缺少 skill_path 参数"}), 400
        result = skill_validate.invoke({
            "skill_path": skill_path,
            "strict": body.get("strict", False),
        })
        return jsonify(json.loads(result))

    @app.route("/api/skill/package", methods=["POST"])
    def skill_package_api():
        """打包 skill 为 .skill 文件。"""
        body = request.get_json() or {}
        skill_path = body.get("skill_path", "").strip()
        if not skill_path:
            return jsonify({"error": "缺少 skill_path 参数"}), 400
        result = skill_package.invoke({
            "skill_path": skill_path,
            "output_dir": body.get("output_dir", ""),
        })
        return jsonify(json.loads(result))

    @app.route("/api/skill/evaluate", methods=["POST"])
    def skill_evaluate_api():
        """评估 skill 触发准确率。"""
        body = request.get_json() or {}
        skill_path = body.get("skill_path", "").strip()
        if not skill_path:
            return jsonify({"error": "缺少 skill_path 参数"}), 400
        result = skill_evaluate_trigger.invoke({
            "skill_path": skill_path,
            "eval_set_path": body.get("eval_set_path", ""),
            "num_workers": body.get("num_workers", 5),
            "timeout": body.get("timeout", 30),
        })
        return jsonify(json.loads(result))

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, use_reloader=False, threaded=True, port=5000)
