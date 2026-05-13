# 输出格式

Skill 的 `handle_dialog` 方法返回一个 JSON 对象，字段如下：

```json
{
  "answer": "string",
  "mode": "string",
  "keyword_hit": "boolean",
  "web_results": "list"
}
```

## 字段约束

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| `answer` | string | 回答文本 | 必填，不可为空字符串 |
| `mode` | string | 路由模式 | 枚举值：`"context"`、`"web+model"`、`"out_of_scope"` |
| `keyword_hit` | boolean | 是否命中耕地/用地关键词 | `true` 表示命中，`false` 表示未命中 |
| `web_results` | list | 网页检索摘要 | 仅在 `mode="web+model"` 时填充，否则为空列表 `[]` |

## web_results 子项结构

当 `web_results` 非空时，每项为：

```json
{
  "title": "string",
  "url": "string",
  "snippet": "string"
}
```

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| `title` | string | 网页标题 | 必填，已去除 HTML 标签 |
| `url` | string | 网页链接 | 必填 |
| `snippet` | string | 内容摘要 | 必填，已去除 HTML 标签，长度不超过 500 字符 |

## 错误处理

- 若 `message` 为空或仅包含空白字符，抛出 `ValueError("message 不能为空")`。
- 若未配置 `DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY`，抛出 `RuntimeError`。
