"""合规规则引擎：定义用地合规规则映射表和硬规则匹配逻辑。"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass, field
from typing import Optional

import config as cfg


@dataclass
class ComplianceRule:
    rule_id: str
    name: str
    applicable_land_type: str          # 适用的地类
    condition_desc: str                # 触发条件描述
    prompt_type: str                   # 关注 | 疑似 | 建议复核
    prompt_template: str               # 提示内容模板
    require_manual_review: bool        # 是否必须人工复核
    risk_level: str                    # 一般关注 | 重点关注 | 建议复核


# 规则映射表
RULES: list[ComplianceRule] = [
    ComplianceRule(
        rule_id="R001",
        name="耕地占比关注",
        applicable_land_type="耕地",
        condition_desc=f"耕地占比 > {int(cfg.FARMLAND_RATIO_THRESHOLD * 100)}%",
        prompt_type="关注",
        prompt_template="该图斑耕地占比达{ratio:.1%}，建议关注耕地保护相关政策要求。",
        require_manual_review=False,
        risk_level="一般关注",
    ),
    ComplianceRule(
        rule_id="R002",
        name="基本农田疑似",
        applicable_land_type="耕地",
        condition_desc=f"耕地面积 > {cfg.FARMLAND_AREA_THRESHOLD}m²",
        prompt_type="疑似",
        prompt_template="该图斑耕地面积达{area}m²（约{mu:.1f}亩），可能涉及基本农田，建议进一步核实。",
        require_manual_review=True,
        risk_level="重点关注",
    ),
    ComplianceRule(
        rule_id="R003",
        name="建设用地占比关注",
        applicable_land_type="建设用地",
        condition_desc=f"建设用地占比 > {int(cfg.CONSTRUCTION_RATIO_THRESHOLD * 100)}%",
        prompt_type="关注",
        prompt_template="该图斑建设用地占比达{ratio:.1%}，建议关注建设用地审批情况。",
        require_manual_review=False,
        risk_level="一般关注",
    ),
    ComplianceRule(
        rule_id="R004",
        name="生态要素关注",
        applicable_land_type="水体",
        condition_desc="图斑中存在水体",
        prompt_type="关注",
        prompt_template="该图斑存在水体面积约{area}m²，建议关注生态保护及水域管控要求。",
        require_manual_review=False,
        risk_level="一般关注",
    ),
    ComplianceRule(
        rule_id="R005",
        name="低置信度复核",
        applicable_land_type="*",
        condition_desc=f"任一地类置信度 < {cfg.LOW_CONFIDENCE_THRESHOLD}",
        prompt_type="建议复核",
        prompt_template="图斑中{land_type}识别置信度为{confidence:.2f}，低于阈值{threshold}，建议人工复核确认。",
        require_manual_review=True,
        risk_level="建议复核",
    ),
    ComplianceRule(
        rule_id="R006",
        name="混合图斑关注",
        applicable_land_type="*",
        condition_desc="图斑为混合类型(耕地+建设用地)",
        prompt_type="疑似",
        prompt_template="该图斑同时包含耕地与建设用地，存在用地冲突可能，建议关注实际用途与审批情况。",
        require_manual_review=True,
        risk_level="重点关注",
    ),
]


def evaluate_rules(parcel_data: dict) -> list[dict]:
    """对图斑数据逐一评估所有规则，返回触发的提示列表。"""
    triggered = []
    land_types = {lt["type"]: lt for lt in parcel_data.get("land_types", [])}

    for rule in RULES:
        result = _evaluate_single_rule(rule, parcel_data, land_types)
        if result is not None:
            triggered.append(result)

    return triggered


def _evaluate_single_rule(
    rule: ComplianceRule, parcel_data: dict, land_types: dict
) -> Optional[dict]:
    """评估单条规则是否触发。"""
    farmland = land_types.get("耕地")
    construction = land_types.get("建设用地")
    water = land_types.get("水体")

    if rule.rule_id == "R001" and farmland:
        if farmland["ratio"] > cfg.FARMLAND_RATIO_THRESHOLD:
            return _build_result(rule, ratio=farmland["ratio"])

    elif rule.rule_id == "R002" and farmland:
        if farmland["area_m2"] > cfg.FARMLAND_AREA_THRESHOLD:
            return _build_result(
                rule, area=farmland["area_m2"], mu=farmland["area_m2"] / 666.67
            )

    elif rule.rule_id == "R003" and construction:
        if construction["ratio"] > cfg.CONSTRUCTION_RATIO_THRESHOLD:
            return _build_result(rule, ratio=construction["ratio"])

    elif rule.rule_id == "R004" and water:
        if water["area_m2"] > cfg.WATER_EXIST_THRESHOLD:
            return _build_result(rule, area=water["area_m2"])

    elif rule.rule_id == "R005":
        for lt in parcel_data.get("land_types", []):
            if lt["confidence"] < cfg.LOW_CONFIDENCE_THRESHOLD:
                return _build_result(
                    rule,
                    land_type=lt["type"],
                    confidence=lt["confidence"],
                    threshold=cfg.LOW_CONFIDENCE_THRESHOLD,
                )

    elif rule.rule_id == "R006":
        if farmland and construction and parcel_data.get("is_mixed"):
            return _build_result(rule)

    return None


def _build_result(rule: ComplianceRule, **kwargs) -> dict:
    return {
        "rule_id": rule.rule_id,
        "rule_name": rule.name,
        "prompt_type": rule.prompt_type,
        "prompt_content": rule.prompt_template.format(**kwargs),
        "require_manual_review": rule.require_manual_review,
        "risk_level": rule.risk_level,
    }
