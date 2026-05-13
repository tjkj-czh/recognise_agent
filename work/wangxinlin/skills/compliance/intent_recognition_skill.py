"""语义意图识别 Skill

用于理解用户在对话框中输入的自然语言意图，将非结构化文本解析为结构化的意图与参数。
适用于用地识别智能体的输入对话框，支持规则+关键词匹配，无需 LLM API。

支持识别的意图：
- analyze_compliance   用地合规分析
- compare_base         现状基底校核
- list_parcels         列出图斑（按区域+地类）
- zoom_map             缩放地图到指定区域
- switch_view          切换地图视图模式
- reset_view           回到全景视角
- upload_imagery       上传影像
- switch_module        切换右侧功能模块
- help                 获取帮助
- greeting             问候/闲聊
- unknown              未识别意图

输入：用户原始输入字符串
输出：结构化意图对象（含 intent, params, confidence, raw_input）
"""

import json
import re
from typing import Any


# ── 地类关键词映射 ──
LAND_TYPE_KEYWORDS = {
    "耕地": ["耕地", "农田", "水田", "旱地", "基本农田", "农用地"],
    "建设用地": ["建设用地", "建筑用地", "城建", "城镇", "城市", "工业区", "开发区", "楼盘", "房屋"],
    "水体": ["水体", "水域", "河流", "湖泊", "水库", "池塘", "水塘", "水渠", "河道"],
    "林地": ["林地", "森林", "树林", "山林", "乔木", "灌木", "林业"],
    "草地": ["草地", "草原", "牧场", "草坪", "草甸"],
    "未利用地": ["未利用地", "裸地", "荒地", "荒山", "闲置土地"],
}

# ── 区域关键词映射（常见浙江区域） ──
REGION_KEYWORDS = {
    "浙江省": ["浙江省", "浙江", "全省"],
    "杭州市": ["杭州市", "杭州"],
    "西湖区": ["西湖区"],
    "宁波市": ["宁波市", "宁波"],
    "温州市": ["温州市", "温州"],
    "嘉兴市": ["嘉兴市", "嘉兴"],
    "湖州市": ["湖州市", "湖州"],
    "绍兴市": ["绍兴市", "绍兴"],
    "金华市": ["金华市", "金华"],
    "衢州市": ["衢州市", "衢州"],
    "舟山市": ["舟山市", "舟山"],
    "台州市": ["台州市", "台州"],
    "丽水市": ["丽水市", "丽水"],
}

# ── 视图模式关键词 ──
VIEW_MODE_KEYWORDS = {
    "risk": ["风险", "合规", "提示", "关注", "风险视图"],
    "landtype": ["地类", "分割", "地类视图", "土地利用"],
}

# ── 意图规则定义 ──
INTENT_RULES = [
    {
        "intent": "greeting",
        "patterns": [
            r"^(你好|您好|嗨|hello|hi|嗨嗨|早上好|下午好|晚上好)",
        ],
        "priority": 10,
    },
    {
        "intent": "help",
        "patterns": [
            r"(帮助|help|怎么用|如何使用|能做什么|功能|说明|提示)",
            r"^(请问|请问你|你能|你可以)",
        ],
        "priority": 9,
    },
    {
        "intent": "list_parcels",
        "patterns": [
            r"(列出|显示|查询|找|搜索|查看|统计|给我|展示).*?(图斑|地块|宗地)",
            r"(图斑|地块|宗地).*?(列出|显示|查询|找|搜索|查看|统计)",
            r"(哪些|哪里|哪个区域).*?(耕地|建设用地|水体|林地|草地)",
            r"(耕地|建设用地|水体|林地|草地).*?(分布|在哪|位置|区域|情况|信息|列表)",
            r"(列出|显示|查询|找|搜索|查看|统计|给我|展示).*?(耕地|建设用地|水体|林地|草地)",
        ],
        "priority": 8,
    },
    {
        "intent": "zoom_map",
        "patterns": [
            r"(放大|缩小|飞到|定位|查看|视角|移动|聚焦).*?(到|至)?.*?(杭州|浙江|宁波|温州|西湖|地图)",
            r"(看|查看|显示).*?(杭州|浙江|宁波|温州|西湖|地图|区域)",
            r"(飞到|跳转|定位到|移动至)",
        ],
        "priority": 7,
    },
    {
        "intent": "switch_view",
        "patterns": [
            r"(切换|转换|换成|改为|打开|关闭).*?(视图|模式|显示)",
            r"(风险|地类).*?(视图|模式)",
            r"(显示|隐藏).*?(风险|地类|图斑|分割)",
        ],
        "priority": 7,
    },
    {
        "intent": "reset_view",
        "patterns": [
            r"(回到|返回|重置|恢复|初始).*?(全景|全屏|全省|浙江|太空|地球|初始|默认)",
            r"(全景|全览|总览|全貌)",
            r"(正北| north|重置视角|恢复视角)",
        ],
        "priority": 7,
    },
    {
        "intent": "upload_imagery",
        "patterns": [
            r"(上传|导入|加载|添加|发).*?(影像|图片|图像|tif|tiff|geotiff|照片|遥感|卫星)",
            r"(影像|图片|图像|tif|tiff).*?(上传|导入|加载|添加)",
        ],
        "priority": 7,
    },
    {
        "intent": "compare_base",
        "patterns": [
            r"(现状|基底|校核|比对|对比|比较|核查|检查|核对).*?(数据|图斑|基底|校核|现状)",
            r"(二调|三调|遥感|影像).*?(对比|比对|校核|核查|检查)",
            r"(校核|核查|检查|核对).*?(二调|三调|遥感|影像|数据)",
            r"(基底校核|现状基底|数据比对|变化|差异)",
        ],
        "priority": 8,
    },
    {
        "intent": "analyze_compliance",
        "patterns": [
            r"(分析|审查|审核|检查|评估|合规|提示|风险|判断|判定|审查).*?(合规|用地|图斑|地块|土地)",
            r"(合规|用地|图斑|地块|土地).*?(分析|审查|审核|检查|评估|提示|风险)",
            r"(这个|该|此).*?(图斑|地块|宗地).*?(如何|怎么样|合规|风险|问题)",
            r"(提交|开始|进行|执行|启动).*?(分析|审查|合规|校核|检查)",
        ],
        "priority": 8,
    },
    {
        "intent": "switch_module",
        "patterns": [
            r"(切换|转到|打开|进入|选择).*?(模块|功能|合规|校核|基底)",
            r"(用地合规|现状基底|合规提示|基底校核)",
        ],
        "priority": 6,
    },
]


def _extract_land_type(text: str) -> str | None:
    """从文本中提取地类关键词。"""
    for land_type, keywords in LAND_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return land_type
    return None


def _extract_region(text: str) -> str | None:
    """从文本中提取区域关键词。
    策略：收集所有匹配，优先返回匹配关键词在文本中最后出现的（更具体的子区域通常在后）。
    """
    best_region = None
    best_pos = -1
    for region, keywords in REGION_KEYWORDS.items():
        for kw in keywords:
            pos = text.find(kw)
            if pos != -1 and pos >= best_pos:
                # 如果位置相同，选择区域名更长的（更具体）
                if pos == best_pos and best_region is not None and len(region) <= len(best_region):
                    continue
                best_pos = pos
                best_region = region
    return best_region


def _extract_view_mode(text: str) -> str | None:
    """提取视图模式。"""
    for mode, keywords in VIEW_MODE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return mode
    return None


def _extract_parcel_id(text: str) -> str | None:
    """提取图斑ID，如 P20240199。"""
    m = re.search(r"[Pp]\d{8}", text)
    if m:
        return m.group(0).upper()
    return None


def _match_intent(text: str) -> tuple[str, float]:
    """基于规则匹配意图，返回 (intent, confidence)。"""
    scores: dict[str, float] = {}

    for rule in INTENT_RULES:
        intent = rule["intent"]
        base_score = float(rule["priority"])
        matched = False

        for pat in rule["patterns"]:
            if re.search(pat, text):
                matched = True
                # 模式匹配成功，根据匹配质量给分
                scores[intent] = max(scores.get(intent, 0.0), base_score)

        # 如果没有正则命中，但包含关键词，给较低分数
        if not matched:
            keyword_boost = _keyword_boost(intent, text)
            if keyword_boost > 0:
                scores[intent] = max(scores.get(intent, 0.0), keyword_boost)

    if not scores:
        return "unknown", 0.0

    best_intent = max(scores, key=scores.get)  # type: ignore[arg-type]
    best_score = scores[best_intent]
    # 将 priority 分数归一化为 0-1 的置信度
    confidence = min(best_score / 10.0, 1.0)
    return best_intent, confidence


def _keyword_boost(intent: str, text: str) -> float:
    """基于关键词给予额外的意图匹配分数（0-5 分）。"""
    text = text.lower()
    boosts = {
        "analyze_compliance": ["合规", "分析", "审查", "规则", "提示", "风险"],
        "compare_base": ["校核", "比对", "对比", "基底", "现状", "差异", "变化"],
        "list_parcels": ["列出", "查询", "显示", "统计", "哪些"],
        "zoom_map": ["放大", "定位", "飞到", "查看", "视角"],
        "switch_view": ["视图", "模式", "切换"],
        "reset_view": ["全景", "重置", "回到", "恢复"],
        "upload_imagery": ["上传", "影像", "tif", "图片"],
        "help": ["帮助", "说明", "怎么用"],
        "greeting": ["你好", "您好", "hello"],
        "switch_module": ["模块", "功能", "切换"],
    }
    keywords = boosts.get(intent, [])
    hits = sum(1 for kw in keywords if kw in text)
    return min(hits * 1.5, 5.0)  # 每个关键词1.5分，最多5分


def recognize_intent(raw_input: str) -> dict[str, Any]:
    """识别用户输入的意图并提取参数。

    Args:
        raw_input: 用户原始输入字符串

    Returns:
        结构化意图对象:
        {
            "intent": str,       # 意图类型
            "params": dict,      # 提取的参数
            "confidence": float, # 置信度 0.0-1.0
            "raw_input": str,    # 原始输入
            "reply_hint": str,   # 建议回复提示（可选）
        }
    """
    if not raw_input or not raw_input.strip():
        return {
            "intent": "unknown",
            "params": {},
            "confidence": 0.0,
            "raw_input": raw_input,
            "reply_hint": "请输入您想执行的操作，例如：列出杭州市西湖区的耕地图斑",
        }

    # 尝试 JSON 解析：如果输入是合法 JSON，视为直接数据输入
    try:
        json.loads(raw_input)
        return {
            "intent": "direct_json",
            "params": {"input_type": "json"},
            "confidence": 1.0,
            "raw_input": raw_input,
            "reply_hint": "检测到JSON格式输入，将直接进行数据分析",
        }
    except (json.JSONDecodeError, ValueError):
        pass

    # 预处理：统一空格和标点
    text = raw_input.strip()
    normalized = re.sub(r"\s+", "", text)

    # 意图匹配
    intent, confidence = _match_intent(normalized)

    # 参数提取
    params: dict[str, Any] = {}
    params["land_type"] = _extract_land_type(normalized)
    params["region"] = _extract_region(normalized)
    params["view_mode"] = _extract_view_mode(normalized)
    params["parcel_id"] = _extract_parcel_id(normalized)

    # 意图特化参数处理
    if intent == "list_parcels":
        if not params.get("land_type") and not params.get("region"):
            confidence *= 0.7  # 缺少关键参数，降低置信度
    elif intent == "zoom_map":
        if not params.get("region"):
            # 尝试从文本中找任何区域词
            for region, keywords in REGION_KEYWORDS.items():
                for kw in keywords:
                    if kw in normalized:
                        params["region"] = region
                        break
                if params.get("region"):
                    break
    elif intent == "switch_module":
        if "合规" in normalized or "提示" in normalized:
            params["target_module"] = "compliance"
        elif "校核" in normalized or "基底" in normalized or "现状" in normalized:
            params["target_module"] = "comparison"
    elif intent == "switch_view":
        if not params.get("view_mode"):
            if "风险" in normalized or "合规" in normalized:
                params["view_mode"] = "risk"
            elif "地类" in normalized or "分割" in normalized:
                params["view_mode"] = "landtype"

    # 兜底：如果地类和区域都很明确，但没有命中 list_parcels，尝试提升为 list_parcels
    if intent == "unknown" and params.get("land_type") and params.get("region"):
        intent = "list_parcels"
        confidence = 0.6

    # 兜底：如果包含明确分析/校核动词且无其他强意图，推断为 analyze_compliance 或 compare_base
    if intent == "unknown":
        if any(kw in normalized for kw in ["分析", "审查", "检查", "评估", "合规"]):
            intent = "analyze_compliance"
            confidence = 0.5
        elif any(kw in normalized for kw in ["校核", "比对", "对比", "核查"]):
            intent = "compare_base"
            confidence = 0.5

    # 建议回复提示
    reply_hint = _build_reply_hint(intent, params)

    return {
        "intent": intent,
        "params": params,
        "confidence": confidence,
        "raw_input": raw_input,
        "reply_hint": reply_hint,
    }


def _build_reply_hint(intent: str, params: dict[str, Any]) -> str:
    """根据意图和参数生成建议回复提示。"""
    land_type = params.get("land_type", "")
    region = params.get("region", "")
    parcel_id = params.get("parcel_id", "")

    hints = {
        "greeting": "你好！我是用地识别智能体，可以帮您进行用地合规分析、现状基底校核、图斑查询等操作。请问有什么可以帮您的？",
        "help": "您可以输入以下类型的指令：\n1. 列出某区域的某类图斑，如：列出杭州市西湖区的耕地图斑\n2. 用地合规分析，如：分析图斑P20240199的合规情况\n3. 现状基底校核，如：比对二调数据与遥感影像的差异\n4. 地图操作，如：定位到宁波、切换到地类视图\n5. 也可以直接输入JSON格式数据进行分析",
        "analyze_compliance": f"即将为您进行用地合规分析{'（图斑 ' + parcel_id + '）' if parcel_id else ''}{'（区域：' + region + '）' if region else ''}...",
        "compare_base": f"即将为您进行现状基底校核{'（区域：' + region + '）' if region else ''}...",
        "list_parcels": f"正在为您查询{region or '全部区域'}的{land_type or '图斑'}信息...",
        "zoom_map": f"正在定位到{region or '指定区域'}...",
        "switch_view": f"正在切换视图模式...",
        "reset_view": "正在重置视图...",
        "upload_imagery": "请在上传区域选择要加载的影像文件（支持.tif/.tiff格式）",
        "switch_module": f"正在切换到{'用地合规提示' if params.get('target_module') == 'compliance' else '现状基底校核'}模块...",
        "direct_json": "检测到结构化数据输入，将直接进行分析处理",
        "unknown": "抱歉，我没有理解您的意图。您可以输入\"帮助\"查看支持的指令类型，或直接粘贴JSON格式数据。",
    }
    return hints.get(intent, "正在处理您的请求...")


def batch_recognize(inputs: list[str]) -> list[dict[str, Any]]:
    """批量识别多条输入的意图。"""
    return [recognize_intent(inp) for inp in inputs]


# ── LangChain Tool 兼容层 ──
try:
    from langchain.tools import tool

    @tool
    def intent_recognition_tool(user_input: str) -> str:
        """识别用户输入的自然语言意图，返回结构化JSON结果。

        当用户在对话框中输入非JSON的自然语言时，调用此工具解析其意图。
        Args:
            user_input: 用户原始输入文本
        Returns:
            JSON字符串，包含 intent（意图类型）、params（参数）、confidence（置信度）
        """
        result = recognize_intent(user_input)
        return json.dumps(result, ensure_ascii=False, indent=2)

except ImportError:
    intent_recognition_tool = None  # type: ignore[misc,assignment]
