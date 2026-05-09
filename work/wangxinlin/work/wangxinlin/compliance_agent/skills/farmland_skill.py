"""耕地保护提示Skill：检查耕地占比和基本农田疑似情况。"""

import json
from langchain_core.tools import tool

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as cfg
from rules.compliance_rules import RULES


@tool
def farmland_check(parcel_data_str: str) -> str:
    """检查图斑中耕地相关的合规提示，包括耕地占比关注和基本农田疑似。
    输入为JSON格式的图斑识别结果字符串。"""
    parcel_data = json.loads(parcel_data_str)
    results = []

    land_types = {lt["type"]: lt for lt in parcel_data.get("land_types", [])}
    farmland = land_types.get("耕地")

    if not farmland:
        return json.dumps({"skill": "耕地保护提示", "prompts": [], "message": "图斑中无耕地类型"}, ensure_ascii=False)

    # R001: 耕地占比关注
    if farmland["ratio"] > cfg.FARMLAND_RATIO_THRESHOLD:
        results.append({
            "rule_id": "R001",
            "prompt_type": "关注",
            "content": f"该图斑耕地占比达{farmland['ratio']:.1%}，建议关注耕地保护相关政策要求。",
            "risk_level": "一般关注",
        })

    # R002: 基本农田疑似
    if farmland["area_m2"] > cfg.FARMLAND_AREA_THRESHOLD:
        mu = farmland["area_m2"] / 666.67
        results.append({
            "rule_id": "R002",
            "prompt_type": "疑似",
            "content": f"该图斑耕地面积达{farmland['area_m2']}m²（约{mu:.1f}亩），可能涉及基本农田，建议进一步核实。",
            "risk_level": "重点关注",
            "require_manual_review": True,
        })

    return json.dumps({"skill": "耕地保护提示", "prompts": results}, ensure_ascii=False)
