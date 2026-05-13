"""报告生成模块：整合规则引擎结果，生成结构化合规报告。"""

import time
from datetime import datetime

RISK_ORDER = {"建议复核": 0, "重点关注": 1, "一般关注": 2}


def _build_review_items(triggered_rules: list[dict]) -> list[dict]:
    items = []
    for rule in triggered_rules:
        if rule.get("require_manual_review") or rule.get("prompt_type") in ("疑似", "建议复核"):
            priority = "高" if rule.get("risk_level") in ("建议复核", "重点关注") else "中"
            items.append({
                "item": rule.get("prompt_content", ""),
                "rule_id": rule.get("rule_id", ""),
                "priority": priority,
                "prompt_type": rule.get("prompt_type", ""),
                "reason": f"规则{rule.get('rule_id', '')}触发，风险等级：{rule.get('risk_level', '')}",
            })
    items.sort(key=lambda x: RISK_ORDER.get(x.get("prompt_type", "一般关注"), 2))
    return items


def _build_land_type_details(parcel_data: dict) -> list[dict]:
    """构建地类构成明细。"""
    details = []
    land_types = parcel_data.get("land_types", [])
    for lt in land_types:
        details.append({
            "type": lt.get("type", "未知"),
            "area_m2": lt.get("area_m2", 0),
            "ratio": lt.get("ratio", 0),
            "confidence": lt.get("confidence", 0),
        })
    return details


def _build_rule_details(triggered_rules: list[dict]) -> list[dict]:
    """构建触发规则详情。"""
    details = []
    for rule in triggered_rules:
        details.append({
            "rule_id": rule.get("rule_id", ""),
            "rule_name": rule.get("rule_name", ""),
            "prompt_type": rule.get("prompt_type", ""),
            "risk_level": rule.get("risk_level", ""),
            "prompt_content": rule.get("prompt_content", ""),
            "require_manual_review": rule.get("require_manual_review", False),
        })
    return details


def build_report(parcel_data: dict, triggered_rules: list[dict]) -> dict:
    """从规则引擎结果生成完整合规报告。"""
    start_time = time.time()

    auto_judgments = [r["prompt_content"] for r in triggered_rules if r.get("prompt_type") == "关注"]
    suspected_prompts = [r["prompt_content"] for r in triggered_rules if r.get("prompt_type") == "疑似"]
    review_items = _build_review_items(triggered_rules)
    manual_review = [{"item": r["item"], "priority": r["priority"], "reason": r["reason"]} for r in review_items]

    if any(r.get("risk_level") == "建议复核" for r in triggered_rules):
        overall_risk = "建议复核"
    elif any(r.get("risk_level") == "重点关注" for r in triggered_rules):
        overall_risk = "重点关注"
    elif triggered_rules:
        overall_risk = "一般关注"
    else:
        overall_risk = "无特殊关注"

    dominant = parcel_data.get("dominant_type", "未知")
    total_area = parcel_data.get("total_area_m2", 0)
    location = parcel_data.get("location", "未知")
    is_mixed = parcel_data.get("is_mixed", False)
    low_confidence_areas = parcel_data.get("low_confidence_areas", [])

    summary_parts = [f"该图斑以{dominant}为主，总面积{total_area}m²。"]
    if auto_judgments:
        summary_parts.append(f"共有{len(auto_judgments)}项常规关注提示。")
    if suspected_prompts:
        summary_parts.append(f"共有{len(suspected_prompts)}项疑似提示，建议进一步核实。")
    if manual_review:
        summary_parts.append(f"共有{len(manual_review)}项需人工复核。")

    land_type_details = _build_land_type_details(parcel_data)
    rule_details = _build_rule_details(triggered_rules)

    # 统计信息
    triggered_count = len(triggered_rules)
    manual_review_count = len(manual_review)
    high_risk_count = sum(1 for r in triggered_rules if r.get("risk_level") == "建议复核")
    medium_risk_count = sum(1 for r in triggered_rules if r.get("risk_level") == "重点关注")
    low_risk_count = sum(1 for r in triggered_rules if r.get("risk_level") == "一般关注")

    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "parcel_id": parcel_data.get("parcel_id", ""),
        "location": location,
        "dominant_type": dominant,
        "total_area_m2": total_area,
        "is_mixed": is_mixed,
        "low_confidence_areas": low_confidence_areas,
        "summary": "".join(summary_parts),
        "auto_judgments": auto_judgments,
        "suspected_prompts": suspected_prompts,
        "manual_review_items": manual_review,
        "overall_risk_level": overall_risk,
        "triggered_rules": triggered_rules,
        "generated_at": datetime.now().isoformat(),
        # 丰富输出字段
        "land_type_details": land_type_details,
        "rule_details": rule_details,
        "statistics": {
            "triggered_count": triggered_count,
            "manual_review_count": manual_review_count,
            "high_risk_count": high_risk_count,
            "medium_risk_count": medium_risk_count,
            "low_risk_count": low_risk_count,
        },
        "processing_info": {
            "elapsed_ms": elapsed_ms,
            "version": "1.1.0",
            "engine": "compliance-rule-engine",
        },
    }
