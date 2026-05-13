"""用地识别智能体核心编排逻辑。"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入外部 skills（项目根目录下的 skills/）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _PROJECT_ROOT)
_IMAGERY_SKILL_DIR = os.path.join(_PROJECT_ROOT, "skills", "tiff-segmentation-pipeline-skill-2", "scripts")
sys.path.insert(0, _IMAGERY_SKILL_DIR)
from imagery_skill import process_uploaded_imagery

_LANDUSE_CHAT_DIR = os.path.join(_PROJECT_ROOT, "skills", "landuse-chat-router-skill")
sys.path.insert(0, _LANDUSE_CHAT_DIR)
from chat_skill import LanduseChatRouterSkill

from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

import config as cfg
from agent.prompts import AGENT_SYSTEM_PROMPT
from skills.compliance.intent_recognition_skill import recognize_intent
from skills.compliance.farmland_skill import farmland_check
from skills.compliance.construction_skill import construction_check
from skills.compliance.water_eco_skill import water_eco_check
from skills.compliance.review_priority_skill import review_priority
from skills.compliance.summary_skill import generate_summary
from skills.compliance.skill_creator_skill import skill_create, skill_validate, skill_package, skill_evaluate_trigger


@tool
def imagery_check(file_path: str) -> str:
    """解析用户上传的 GeoTIFF 影像，提取元数据（坐标系、WGS84范围、行列数、波段数）并生成 Cesium 叠加预览图和 448×448 瓦片。
    输入为影像文件的绝对路径。
    返回 JSON 字符串，包含影像元数据、overlay 路径和瓦片摘要信息。
    """
    import json
    try:
        result = process_uploaded_imagery(file_path, generate_tiles=True)
        return json.dumps({
            "skill": "影像解析",
            "crs": result.get("crs"),
            "bbox_wgs84": result.get("bbox_wgs84"),
            "rows": result.get("rows"),
            "cols": result.get("cols"),
            "bands": result.get("bands"),
            "overlay_path": result.get("overlay_path"),
            "tiles_summary": {
                "tile_size": result["tiles_meta"]["tile_size"],
                "num_tiles_x": result["tiles_meta"]["num_tiles_x"],
                "num_tiles_y": result["tiles_meta"]["num_tiles_y"],
                "total_tiles": result["tiles_meta"]["total_tiles"],
            } if "tiles_meta" in result else None,
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"skill": "影像解析", "error": str(e)}, ensure_ascii=False)


@tool
def intent_recognition(user_input: str) -> str:
    """识别用户自然语言输入的意图，返回结构化的意图类型、参数和置信度。
    当用户输入为非 JSON 的自然语言指令（如"列出杭州市的耕地图斑"、"分析这块地的合规性"）时，调用此工具解析其真实意图。
    Args:
        user_input: 用户原始输入文本
    Returns:
        JSON 字符串，包含 intent（意图类型）、params（提取参数）、confidence（置信度 0-1）、reply_hint（建议回复）
    """
    import json
    result = recognize_intent(user_input)
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def landuse_chat(user_input: str, context_json: str = "{}") -> str:
    """用地智能对话工具：根据用户输入判断关键词命中情况，选择上下文检索或联网搜索，并调用 LLM 生成专业回答。
    当用户提出与用地识别、耕地保护、图斑查询、政策法规等相关问题时，调用此工具生成回答。
    Args:
        user_input: 用户原始问题文本
        context_json: 可选的上下文 JSON 字符串（如图斑 parcels 数据），默认为空对象
    Returns:
        JSON 字符串，包含 answer（回答内容）、mode（路由模式：context/web+model）、web_results（网页搜索结果）
    """
    import json
    try:
        context = json.loads(context_json) if context_json.strip() else {}
    except Exception:
        context = {}
    skill = LanduseChatRouterSkill()
    result = skill.handle_dialog(user_input, context=context)
    return json.dumps(result, ensure_ascii=False, default=str)


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
    """构建用地识别智能体（基于LangGraph react agent）。"""
    llm = _get_llm()

    tools = [
        farmland_check,
        construction_check,
        water_eco_check,
        review_priority,
        generate_summary,
        imagery_check,
        intent_recognition,
        landuse_chat,
        skill_create,
        skill_validate,
        skill_package,
        skill_evaluate_trigger,
    ]

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=AGENT_SYSTEM_PROMPT,
    )

    return agent


def run_agent(parcel_data: dict, imagery_path: str = "") -> dict:
    """运行Agent，输入图斑数据与可选影像路径，返回合规报告。"""
    agent = build_agent()

    user_message = "请分析以下图斑识别结果，给出合规提示和复核建议。\n\n"
    if imagery_path:
        user_message += (
            f"用户提供了遥感影像文件：{imagery_path}\n"
            f"请先调用影像解析工具处理该影像，获取元数据、叠加预览和瓦片信息。\n\n"
        )
    user_message += (
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
