import os

# === 大模型配置 ===
# 支持: "zhipu" | "openai"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "zhipu")

# 智谱GLM配置
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_MODEL = os.getenv("ZHIPU_MODEL", "glm-4-flash")

# OpenAI配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")

# === 合规规则阈值 ===
# 耕地保护
FARMLAND_RATIO_THRESHOLD = 0.5       # 耕地占比超过50%触发关注
FARMLAND_AREA_THRESHOLD = 6667       # 耕地面积超过6667m²(约10亩)触发基本农田疑似

# 建设用地
CONSTRUCTION_RATIO_THRESHOLD = 0.3   # 建设用地占比超过30%触发关注

# 水体/生态
WATER_EXIST_THRESHOLD = 0.0          # 水体面积存在即触发生态关注

# 置信度
LOW_CONFIDENCE_THRESHOLD = 0.7       # 置信度低于0.7建议人工复核

# 风险等级
RISK_LEVELS = ["一般关注", "重点关注", "建议复核"]
