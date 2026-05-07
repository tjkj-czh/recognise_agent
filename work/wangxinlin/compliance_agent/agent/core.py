"""用地合规提示Agent核心编排逻辑。"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.prebuilt import create_react_agent

import config as cfg
from agent.prompts import AGENT_SYSTEM_PROMPT
from skills.farmland_skill import farmland_check
from skills.construction_skill import construction_check
from skills.water_eco_skill import water_eco_check
from skills.review_priority_skill import review_priority
from skills.summary_skill import generate_summary


def _get_llm():
    """根据配置获取大模型实例。"""
    if cfg.LLM_PROVIDER == "zhipu":
        from langchain_community.chat_models import ChatZhipuAI
        return ChatZhipuAI(
            model=cfg.ZHIPU_MODEL,
            zhipuai_api_key=cfg.ZHIPU_API_KEY,
        )
    elif cfg.LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        kwargs = {
            "model": cfg.OPENAI_MODEL,
            "api_key": cfg.OPENAI_API_KEY,
        }
        if cfg.OPENAI_BASE_URL:
            kwargs["base_url"] = cfg.OPENAI_BASE_URL
        return ChatOpenAI(**kwargs)
    else:
        raise ValueError(f"不支持的LLM_PROVIDER: {cfg.LLM_PROVIDER}")


def build_agent():
    """构建用地合规提示Agent（基于LangGraph react agent）。"""
    llm = _get_llm()

    tools = [
        farmland_check,
        construction_check,
        water_eco_check,
        review_priority,
        generate_summary,
    ]

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=AGENT_SYSTEM_PROMPT,
    )

    return agent


def run_agent(parcel_data: dict) -> dict:
    """运行Agent，输入图斑数据，返回合规报告。"""
    agent = build_agent()

    user_message = (
        f"请分析以下图斑识别结果，给出合规提示和复核建议。\n\n"
        f"图斑数据：\n{json.dumps(parcel_data, ensure_ascii=False, indent=2)}\n\n"
        f"请按顺序使用工具完成分析：\n"
        f"1. 先用耕地保护、建设用地、水体生态检查工具分别检查\n"
        f"2. 再用人工复核优先级工具对提示排序\n"
        f"3. 最后用摘要工具生成报告"
    )

    result = agent.invoke(
        {"messages": [("user", user_message)]}
    )

    # 提取最终AI回复
    messages = result.get("messages", [])
    final_message = messages[-1].content if messages else ""

    return {"output": final_message, "full_result": result}
