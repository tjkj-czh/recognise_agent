"""水体/生态要素提示Skill：检查水体及生态相关合规提示。"""

import json
from langchain_core.tools import tool

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as cfg


@tool
def water_eco_check(parcel_data_str: str) -> str:
    """检查图斑中水体和生态要素相关的合规提示。
    输入为JSON格式的图斑识别结果字符串。"""
    parcel_data = json.loads(parcel_data_str)
    results = []

    land_types = {lt["type"]: lt for lt in parcel_data.get("land_types", [])}
    water = land_types.get("水体")

    if not water:
        return json.dumps({"skill": "水体/生态要素提示", "prompts": [], "message": "图斑中无水体类型"}, ensure_ascii=False)

    # R004: 生态要素关注
    if water["area_m2"] > cfg.WATER_EXIST_THRESHOLD:
        prompt = {
            "rule_id": "R004",
            "prompt_type": "关注",
            "content": f"该图斑存在水体面积约{water['area_m2']}m²，建议关注生态保护及水域管控要求。",
            "risk_level": "一般关注",
        }
        # 水体置信度偏低时升级为建议复核
        if water["confidence"] < cfg.LOW_CONFIDENCE_THRESHOLD:
            prompt["prompt_type"] = "建议复核"
            prompt["risk_level"] = "建议复核"
            prompt["content"] += f"（水体识别置信度{water['confidence']:.2f}偏低，建议人工确认边界）"
            prompt["require_manual_review"] = True
        results.append(prompt)

    return json.dumps({"skill": "水体/生态要素提示", "prompts": results}, ensure_ascii=False)
