"""图斑判读摘要Skill：整合所有提示结果，生成结构化合规报告。"""

import json
from datetime import datetime
from langchain_core.tools import tool


@tool
def generate_summary(analysis_result_str: str) -> str:
    """整合所有合规提示和复核清单，生成最终的图斑判读摘要报告。
    输入为JSON格式，包含parcel_data、all_prompts、review_items。"""
    analysis = json.loads(analysis_result_str)
    parcel_data = analysis.get("parcel_data", {})
    all_prompts = analysis.get("all_prompts", [])
    review_items = analysis.get("review_items", [])

    # 区分三类输出
    auto_judgments = [p["content"] for p in all_prompts if p.get("prompt_type") == "关注"]
    suspected_prompts = [p["content"] for p in all_prompts if p.get("prompt_type") == "疑似"]
    manual_review = [
        {"item": r["item"], "priority": r["priority"], "reason": r["reason"]}
        for r in review_items
    ]

    # 确定总体风险等级
    if any(p.get("risk_level") == "建议复核" for p in all_prompts):
        overall_risk = "建议复核"
    elif any(p.get("risk_level") == "重点关注" for p in all_prompts):
        overall_risk = "重点关注"
    elif all_prompts:
        overall_risk = "一般关注"
    else:
        overall_risk = "无特殊关注"

    # 生成摘要文本
    dominant = parcel_data.get("dominant_type", "未知")
    total_area = parcel_data.get("total_area_m2", 0)
    summary_parts = [f"该图斑以{dominant}为主，总面积{total_area}m²。"]
    if auto_judgments:
        summary_parts.append(f"共有{len(auto_judgments)}项常规关注提示。")
    if suspected_prompts:
        summary_parts.append(f"共有{len(suspected_prompts)}项疑似提示，建议进一步核实。")
    if manual_review:
        summary_parts.append(f"共有{len(manual_review)}项需人工复核。")

    report = {
        "parcel_id": parcel_data.get("parcel_id", ""),
        "summary": "".join(summary_parts),
        "auto_judgments": auto_judgments,
        "suspected_prompts": suspected_prompts,
        "manual_review_items": manual_review,
        "overall_risk_level": overall_risk,
        "generated_at": datetime.now().isoformat(),
    }

    return json.dumps(report, ensure_ascii=False, indent=2)
