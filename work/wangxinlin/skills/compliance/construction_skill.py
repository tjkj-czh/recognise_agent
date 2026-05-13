"""建设用地关注提示Skill：检查建设用地占比异常情况。"""

import json
from langchain_core.tools import tool

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as cfg


@tool
def construction_check(parcel_data_str: str) -> str:
    """检查图斑中建设用地相关的合规提示，包括建设用地占比关注。
    输入为JSON格式的图斑识别结果字符串。"""
    parcel_data = json.loads(parcel_data_str)
    results = []

    land_types = {lt["type"]: lt for lt in parcel_data.get("land_types", [])}
    construction = land_types.get("建设用地")

    if not construction:
        return json.dumps({"skill": "建设用地关注提示", "prompts": [], "message": "图斑中无建设用地类型"}, ensure_ascii=False)

    # R003: 建设用地占比关注
    if construction["ratio"] > cfg.CONSTRUCTION_RATIO_THRESHOLD:
        results.append({
            "rule_id": "R003",
            "prompt_type": "关注",
            "content": f"该图斑建设用地占比达{construction['ratio']:.1%}，建议关注建设用地审批情况。",
            "risk_level": "一般关注",
        })

    # R006: 耕地+建设用地混合图斑
    farmland = land_types.get("耕地")
    if farmland and parcel_data.get("is_mixed"):
        results.append({
            "rule_id": "R006",
            "prompt_type": "疑似",
            "content": "该图斑同时包含耕地与建设用地，存在用地冲突可能，建议关注实际用途与审批情况。",
            "risk_level": "重点关注",
            "require_manual_review": True,
        })

    return json.dumps({"skill": "建设用地关注提示", "prompts": results}, ensure_ascii=False)
