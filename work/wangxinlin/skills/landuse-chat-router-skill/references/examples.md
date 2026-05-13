# 例子

## 例子 1：政策类问题（走联网搜索）

**输入：**
```python
{
  "message": "最新耕地保护政策有哪些？",
  "context": {"features": [...]},  // 业务上下文
  "session_id": "u-001"
}
```

**路由判断：**
- 命中政策关键词 "政策" -> 选择 `web+model` 路由，忽略 context。

**模型 prompt 策略：**
- system: "你是专业的政策法规咨询助手。请基于你的知识和网页搜索结果，直接、清晰地回答用户关于政策法规的问题。注意：用户提供的上下文数据是土地利用遥感数据，与政策问题无关，请忽略。回答时请尽量列出具体的政策文件名称、发布机构、核心条款。"

**预期输出特征：**
- `mode` 为 `"web+model"`
- `keyword_hit` 为 `true`
- `web_results` 包含 DuckDuckGo 搜索结果摘要
- `answer` 引用具体政策文件名称和发布机构

---

## 例子 2：耕地数量查询（走上下文检索）

**输入：**
```python
{
  "message": "有多少块耕地？",
  "context": {
    "features": [
      {"properties": {"land_type": "耕地", "area": 1200}},
      {"properties": {"land_type": "建设用地", "area": 800}},
      {"properties": {"land_type": "耕地", "area": 950}}
    ]
  },
  "session_id": "u-002"
}
```

**路由判断：**
- 命中耕地关键词 "耕地" -> 选择 `context` 路由。

**检索过程：**
- 统计 features 中 properties 包含 "耕地" 的数量 -> 2 块。
- 提取相关上下文片段 -> `[{"land_type": "耕地", "area": 1200}, {"land_type": "耕地", "area": 950}]`。

**预期输出特征：**
- `mode` 为 `"context"`
- `keyword_hit` 为 `true`
- `web_results` 为空列表
- `answer` 直接回答数量并引用上下文中的面积数据

---

## 例子 3：通用用地问题（在功能范围内但未命中特定关键词，走联网搜索）

**输入：**
```python
{
  "message": "什么是高标准农田？",
  "context": None,
  "session_id": "u-003"
}
```

**路由判断：**
- 命中功能范围关键词 "高标准农田" -> 在功能范围内。
- 未命中耕地/用地核心关键词或政策关键词 -> 选择 `web+model` 路由。

**预期输出特征：**
- `mode` 为 `"web+model"`
- `keyword_hit` 为 `false`
- `web_results` 包含搜索结果
- `answer` 基于网页信息综合回答

---

## 例子 4：超出功能范围（直接拒绝）

**输入：**
```python
{
  "message": "今天天气怎么样？",
  "context": None,
  "session_id": "u-004"
}
```

**路由判断：**
- 未命中任何功能范围关键词（耕地、用地、政策、法规、遥感、国土等） -> 直接拒绝。

**处理策略：**
- 不调用模型，不执行搜索，直接返回固定拒绝文案。

**预期输出特征：**
- `mode` 为 `"out_of_scope"`
- `keyword_hit` 为 `false`
- `web_results` 为空列表
- `answer` 为委婉拒绝文本，提示用户可咨询耕地保护、建设用地、图斑分析、用地政策法规等相关问题
