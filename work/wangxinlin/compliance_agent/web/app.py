"""用地合规提示Agent Web Demo - Flask应用。"""

import json
import os
import sys

# 确保项目根目录在sys.path中，使import config和rules可用
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, render_template, request, jsonify

from rules.compliance_rules import evaluate_rules
from web.report_builder import build_report

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


<<<<<<< HEAD
def _load_land_segments() -> dict:
    path = os.path.join(DATA_DIR, "land_segments.geojson")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


=======
>>>>>>> f79a1051622dbcf7b6c5f4aad027596008fea322
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

<<<<<<< HEAD
    @app.route("/api/land-segments")
    def get_land_segments():
        """返回浙江省地类分割GeoJSON。"""
        return jsonify(_load_land_segments())

=======
>>>>>>> f79a1051622dbcf7b6c5f4aad027596008fea322
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

<<<<<<< HEAD
=======
    @app.route("/results")
    def results_page():
        """合规分析结果页面。"""
        return render_template("results.html")

>>>>>>> f79a1051622dbcf7b6c5f4aad027596008fea322
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

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
