"""报告生成模块：整合规则引擎结果，生成结构化合规报告。"""

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


def build_report(parcel_data: dict, triggered_rules: list[dict]) -> dict:
    """从规则引擎结果生成完整合规报告。"""
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
    summary_parts = [f"该图斑以{dominant}为主，总面积{total_area}m²。"]
    if auto_judgments:
        summary_parts.append(f"共有{len(auto_judgments)}项常规关注提示。")
    if suspected_prompts:
        summary_parts.append(f"共有{len(suspected_prompts)}项疑似提示，建议进一步核实。")
    if manual_review:
        summary_parts.append(f"共有{len(manual_review)}项需人工复核。")

    return {
        "parcel_id": parcel_data.get("parcel_id", ""),
        "summary": "".join(summary_parts),
        "auto_judgments": auto_judgments,
        "suspected_prompts": suspected_prompts,
        "manual_review_items": manual_review,
        "overall_risk_level": overall_risk,
        "triggered_rules": triggered_rules,
        "generated_at": datetime.now().isoformat(),
    }
