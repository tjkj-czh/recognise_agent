"""Landuse Chat Router Skill.

对接方式：外部系统将对话框输入 message（可选 context）传入 handle_dialog。
- 命中耕地/用地识别关键词：上下文检索 + 模型回答
- 未命中：网页检索 + 模型回答
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import requests
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


KEYWORD_PATTERNS = [
    r"耕地",
    r"用地识别",
    r"多少块耕地",
    r"有多少块耕地",
    r"耕地数量",
    r"图斑",
    r"基本农田",
]

# 政策/法规类关键词：命中后优先走联网搜索而非上下文检索
POLICY_PATTERNS = [
    r"政策",
    r"法规",
    r"规定",
    r"法律",
    r"条例",
    r"通知",
    r"文件",
    r"制度",
    r"标准",
    r"规范",
    r"管理办法",
    r"实施细则",
]

# 功能范围扩展关键词：与用地识别强相关但未在上述两类中覆盖的术语
_SCOPE_EXTRA = [
    r"土地利用", r"土地资源", r"土地规划", r"土地管理", r"土地整治", r"土地复垦",
    r"建设用地", r"宅基地", r"集体建设用地", r"农用地", r"未利用地", r"耕地红线",
    r"永久基本农田", r"高标准农田", r"耕地保护",
    r"遥感", r"遥感影像", r"卫星影像", r"影像解译", r"影像识别",
    r"地块", r"宗地", r"图斑核查", r"图斑分析", r"违法图斑", r"卫片执法",
    r"国土调查", r"三调", r"变更调查", r"自然资源", r"国土空间", r"空间规划",
    r"生态修复", r"矿山修复", r"绿色矿山", r"不动产登记", r"确权登记",
    r"增减挂钩", r"非农化", r"非粮化", r"抛荒", r"闲置土地", r"低效用地",
    r"违建", r"违法用地", r"违规占地", r"耕地占用", r"耕地损毁",
    r"地理信息", r"测绘", r"地籍", r"勘测定界", r"用地审批", r"规划许可", r"选址",
    r"DOM", r"DEM", r"DSM", r"倾斜摄影", r"激光雷达", r"LiDAR", r"点云",
    r"多光谱", r"高光谱", r"SAR", r"InSAR", r"植被指数", r"NDVI",
    r"变化检测", r"目标检测", r"语义分割", r"深度学习", r"人工智能",
    r"WebGIS", r"Cesium", r"OpenLayers", r"GIS", r"叠加分析",
    r"耕地质量", r"土壤普查", r"土地估价", r"基准地价",
    r"承包地", r"经营权", r"林权", r"草权", r"湿地保护", r"水源保护",
    r"生态红线", r"城镇开发边界", r"三条控制线", r"主体功能区",
    r"乡村振兴", r"粮食安全", r"生态文明", r"碳汇", r"双碳",
]

# 完整功能范围关键词：命中任意一个即视为在用地识别agent的功能范围内
SCOPE_PATTERNS = KEYWORD_PATTERNS + POLICY_PATTERNS + _SCOPE_EXTRA


class LanduseChatRouterSkill:
    def __init__(self):
        self.model = self._build_model()

    @staticmethod
    def _build_model() -> ChatOpenAI:
        deepseek_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if deepseek_key:
            return ChatOpenAI(
                api_key=deepseek_key,
                base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").strip(),
                model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro").strip(),
                temperature=float(os.getenv("CHAT_TEMPERATURE", "0.2")),
                timeout=int(os.getenv("CHAT_TIMEOUT_SEC", "60")),
            )

        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not openai_key:
            raise RuntimeError("未配置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY")

        kwargs: dict[str, Any] = {
            "api_key": openai_key,
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
            "temperature": float(os.getenv("CHAT_TEMPERATURE", "0.2")),
            "timeout": int(os.getenv("CHAT_TIMEOUT_SEC", "60")),
        }
        base_url = os.getenv("OPENAI_BASE_URL", "").strip()
        if base_url:
            kwargs["base_url"] = base_url
        return ChatOpenAI(**kwargs)

    @staticmethod
    def _keyword_hit(message: str) -> bool:
        text = (message or "").strip()
        return any(re.search(p, text, flags=re.IGNORECASE) for p in KEYWORD_PATTERNS)

    @staticmethod
    def _is_policy_query(message: str) -> bool:
        """检测是否为政策/法规类问题，此类问题应走联网搜索。"""
        text = (message or "").strip()
        return any(re.search(p, text, flags=re.IGNORECASE) for p in POLICY_PATTERNS)

    @staticmethod
    def _is_in_scope(message: str) -> bool:
        """检测用户问题是否在用地识别agent的功能范围内。"""
        text = (message or "").strip()
        return any(re.search(p, text, flags=re.IGNORECASE) for p in SCOPE_PATTERNS)

    @staticmethod
    def _safe_json_dumps(data: Any, max_len: int = 4000) -> str:
        s = json.dumps(data, ensure_ascii=False, default=str)
        return s[:max_len] + ("...(截断)" if len(s) > max_len else "")

    @staticmethod
    def _count_farmland_features(context: dict[str, Any] | None) -> int | None:
        if not isinstance(context, dict):
            return None

        features = context.get("features")
        if not isinstance(features, list):
            return None

        count = 0
        for f in features:
            if not isinstance(f, dict):
                continue
            props = f.get("properties") if isinstance(f.get("properties"), dict) else {}
            text = json.dumps(props, ensure_ascii=False)
            if "耕地" in text:
                count += 1
        return count

    @staticmethod
    def _search_context_snippets(context: dict[str, Any] | None, query: str, max_items: int = 8) -> list[str]:
        if not isinstance(context, dict):
            return []

        text = LanduseChatRouterSkill._safe_json_dumps(context, max_len=15000)
        keys = ["耕地", "用地", "图斑", "基本农田"]
        q = (query or "").strip()
        if q:
            keys.extend([x for x in re.split(r"\s+", q) if x])

        lines = re.split(r"[\n\r,，。；;]+", text)
        hits: list[str] = []
        for line in lines:
            ls = line.strip()
            if not ls:
                continue
            if any(k and k in ls for k in keys):
                hits.append(ls[:220])
                if len(hits) >= max_items:
                    break
        return hits

    @staticmethod
    def _web_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
        if not query.strip():
            return []

        url = "https://duckduckgo.com/html/"
        try:
            resp = requests.get(
                url,
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            resp.raise_for_status()
            html = resp.text
        except Exception:
            return []

        # 轻量正则抽取标题/链接/摘要
        item_re = re.compile(
            r'<a[^>]*class="result__a"[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>[\s\S]*?'
            r'<a[^>]*class="result__snippet"[^>]*>(?P<snippet>.*?)</a>',
            flags=re.IGNORECASE,
        )

        results: list[dict[str, str]] = []
        for m in item_re.finditer(html):
            title = re.sub(r"<[^>]+>", "", m.group("title")).strip()
            href = m.group("href").strip()
            snippet = re.sub(r"<[^>]+>", "", m.group("snippet")).strip()
            if title and href:
                results.append({"title": title, "url": href, "snippet": snippet})
            if len(results) >= max_results:
                break
        return results

    def _invoke_model(self, message: str, extra_context: dict[str, Any], is_policy: bool = False) -> str:
        if is_policy:
            sys_prompt = (
                "你是专业的政策法规咨询助手。"
                "请基于你的知识和网页搜索结果，直接、清晰地回答用户关于政策法规的问题。"
                "注意：用户提供的上下文数据（如有）是土地利用遥感数据，与政策问题无关，请忽略。"
                "回答时请尽量列出具体的政策文件名称、发布机构、核心条款。"
            )
        else:
            sys_prompt = (
                "你是通用智能助手。"
                "尽量直接、清晰回答问题；当有上下文或网页信息时，优先利用这些证据。"
            )

        ctx_json = self._safe_json_dumps(extra_context, max_len=12000)
        user_prompt = f"用户问题：{message}\n\n可用信息：{ctx_json}"

        result = self.model.invoke([
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt),
        ])
        answer = (result.content or "").strip() if hasattr(result, "content") else str(result)
        return answer or "（模型未返回有效内容）"

    def handle_dialog(self, message: str, context: dict[str, Any] | None = None, session_id: str = "default") -> dict[str, Any]:
        _ = session_id  # 当前版本接口保留 session_id

        text = (message or "").strip()
        if not text:
            raise ValueError("message 不能为空")

        # 功能范围检查：超出用地识别agent范围的问题直接委婉拒绝
        if not self._is_in_scope(text):
            return {
                "answer": (
                    "抱歉，您的问题超出了用地识别智能体的服务范围。"
                    "我可以帮您解答与耕地保护、建设用地、图斑分析、用地政策法规、遥感影像解译等相关的问题，"
                    "请问有什么可以帮您的吗？"
                ),
                "mode": "out_of_scope",
                "keyword_hit": False,
                "web_results": [],
            }

        hit = self._keyword_hit(text)
        is_policy = self._is_policy_query(text)

        # 政策/法规类问题优先走联网搜索，不注入图斑上下文
        if is_policy:
            web_results = self._web_search(text)
            payload = {
                "route": "web+model",
                "keyword_hit": True,
                "is_policy_query": True,
                "web_results": web_results,
            }
            answer = self._invoke_model(text, payload, is_policy=True)
            return {
                "answer": answer,
                "mode": "web+model",
                "keyword_hit": True,
                "web_results": web_results,
            }

        if hit:
            farmland_count = self._count_farmland_features(context)
            snippets = self._search_context_snippets(context, text)
            payload = {
                "route": "context",
                "keyword_hit": True,
                "farmland_feature_count": farmland_count,
                "context_snippets": snippets,
                "raw_context": context or {},
            }
            answer = self._invoke_model(text, payload)
            return {
                "answer": answer,
                "mode": "context",
                "keyword_hit": True,
                "web_results": [],
            }

        web_results = self._web_search(text)
        payload = {
            "route": "web+model",
            "keyword_hit": False,
            "web_results": web_results,
            "raw_context": context or {},
        }
        answer = self._invoke_model(text, payload)
        return {
            "answer": answer,
            "mode": "web+model",
            "keyword_hit": False,
            "web_results": web_results,
        }


__all__ = ["LanduseChatRouterSkill"]
