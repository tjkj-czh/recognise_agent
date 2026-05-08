"""用地识别智能体 Web Demo - Flask应用。"""

import json
import os
import sys
import uuid
from pathlib import Path

import numpy as np
from PIL import Image

# 确保项目根目录在sys.path中，使import config和rules可用
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, render_template, request, jsonify, send_file

from rules.compliance_rules import evaluate_rules
from web.report_builder import build_report
from skills.intent_recognition_skill import recognize_intent

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
        parcel_data = request.get_json()
        if not parcel_data:
            return jsonify({"error": "请提供图斑数据"}), 400

        # 基本校验
        for field in ("parcel_id", "total_area_m2", "land_types", "dominant_type"):
            if field not in parcel_data:
                return jsonify({"error": f"缺少必填字段: {field}"}), 400

        triggered = evaluate_rules(parcel_data)
        report = build_report(parcel_data, triggered)
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
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OVERLAY_DIR, exist_ok=True)

    def _process_imagery(src_path: str, image_id: str) -> dict:
        """读取 GeoTIFF，生成 PNG 预览，返回元数据。"""
        import rasterio
        from rasterio.warp import transform_bounds

        with rasterio.open(src_path) as src:
            crs = str(src.crs) if src.crs else "Unknown"
            rows, cols = src.height, src.width
            bands = src.count

            # 转换为 WGS-84 bbox
            bounds = src.bounds
            if src.crs and src.crs.to_epsg() != 4326:
                bounds = transform_bounds(src.crs, "EPSG:4326", *bounds)
            minx, miny, maxx, maxy = bounds

            # 生成 PNG 预览（最大 1024x1024）
            max_size = 1024
            scale = min(1.0, max_size / max(rows, cols))
            out_rows, out_cols = int(rows * scale), int(cols * scale)

            if bands >= 3:
                data = src.read([1, 2, 3], out_shape=(3, out_rows, out_cols))
            else:
                band = src.read(1, out_shape=(out_rows, out_cols))
                data = np.stack([band, band, band], axis=0)

            # 归一化到 0-255
            data = data.astype(np.float32)
            for i in range(3):
                band = data[i]
                valid = band[band > 0]
                if len(valid) > 0:
                    vmin, vmax = np.percentile(valid, [2, 98])
                    if vmax > vmin:
                        band = np.clip((band - vmin) / (vmax - vmin) * 255, 0, 255)
                    else:
                        band = np.clip(band / (band.max() + 1e-6) * 255, 0, 255)
                else:
                    band = np.zeros_like(band)
                data[i] = band

            data = data.astype(np.uint8).transpose(1, 2, 0)
            img = Image.fromarray(data)
            overlay_path = os.path.join(OVERLAY_DIR, f"{image_id}.png")
            img.save(overlay_path, "PNG")

            return {
                "image_id": image_id,
                "filename": os.path.basename(src_path),
                "crs": crs,
                "bbox": [minx, miny, maxx, maxy],
                "rows": rows,
                "cols": cols,
                "bands": bands,
                "overlay_url": f"/api/layers/{image_id}/overlay.png",
            }

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
            meta = _process_imagery(src_path, image_id)
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

    # 任务占位
    tasks_db = {}

    @app.route("/api/tasks/segment", methods=["POST"])
    def start_segmentation():
        body = request.get_json() or {}
        image_id = body.get("image_id")
        if not image_id:
            return jsonify({"error": "缺少 image_id"}), 400
        task_id = f"seg_{uuid.uuid4().hex[:8]}"
        tasks_db[task_id] = {"task_id": task_id, "status": "success", "image_id": image_id, "result_layer_id": image_id}
        return jsonify({"task_id": task_id, "status": "success", "result_layer_id": image_id})

    @app.route("/api/tasks/<task_id>")
    def get_task(task_id):
        task = tasks_db.get(task_id, {"task_id": task_id, "status": "failed", "error_message": "任务不存在"})
        return jsonify(task)

    @app.route("/api/layers/<image_id>/vectors.geojson")
    def get_segment_geojson(image_id):
        return jsonify({"type": "FeatureCollection", "features": []})

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
