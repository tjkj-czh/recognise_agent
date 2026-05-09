"""人工复核优先级Skill：对所有提示按风险等级排序，生成复核清单。"""

import json
from langchain_core.tools import tool


RISK_ORDER = {"建议复核": 0, "重点关注": 1, "一般关注": 2}


@tool
def review_priority(all_prompts_str: str) -> str:
    """对所有合规提示按风险等级排序，生成人工复核优先级清单。
    输入为JSON格式的所有提示结果列表字符串。"""
    all_prompts = json.loads(all_prompts_str)
    review_items = []

    for prompt in all_prompts:
        if prompt.get("require_manual_review") or prompt.get("prompt_type") in ("疑似", "建议复核"):
            priority = "高" if prompt.get("risk_level") in ("建议复核", "重点关注") else "中"
            review_items.append({
                "item": prompt.get("content", ""),
                "rule_id": prompt.get("rule_id", ""),
                "priority": priority,
                "prompt_type": prompt.get("prompt_type", ""),
                "reason": f"规则{prompt.get('rule_id','')}触发，风险等级：{prompt.get('risk_level','')}",
            })

    review_items.sort(key=lambda x: RISK_ORDER.get(x.get("prompt_type", "一般关注"), 2))

    return json.dumps({
        "skill": "人工复核优先级",
        "manual_review_count": len(review_items),
        "review_items": review_items,
    }, ensure_ascii=False)
