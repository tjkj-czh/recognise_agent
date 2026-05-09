# Backend for Frontend (BFF)

变化监测智能体的前端专属后端服务，承担请求聚合、鉴权、Skill 调用网关等职责。

## 目录结构

```
backend-for-frontend/
├── src/
│   ├── handlers/            # 路由处理器
│   │   ├── monitoring.ts    # 监测相关接口
│   │   ├── reports.ts       # 报告相关接口
│   │   └── system.ts        # 系统管理接口
│   ├── middleware/          # 中间件
│   │   ├── auth.ts          # JWT 鉴权
│   │   ├── logger.ts        # 请求日志
│   │   └── rate-limit.ts    # 限流
│   ├── skill-gateway/       # Skill 调用网关
│   │   ├── client.ts        # Skill Runtime 客户端
│   │   ├── router.ts        # Skill 路由表
│   │   └── error-handler.ts # Skill 错误转换
│   ├── database/            # 数据访问层
│   │   ├── connection.ts    # 数据库连接
│   │   ├── models/          # ORM 模型
│   │   └── repositories/    # 仓库模式
│   └── index.ts             # 服务入口
├── package.json
└── tsconfig.json
```

## 技术栈

- Node.js 20+
- Fastify（HTTP 框架）
- Prisma 或 Drizzle（ORM）
- Redis（缓存与会话）

## 接口设计原则

1. **面向前端聚合**：一个页面一个接口，减少前端请求次数
2. **错误统一封装**：所有错误返回 `{ code, message, data }` 统一结构
3. **Skill 透传透明**：前端不感知 Skill 调用细节，BFF 负责路由与超时控制

## 快速开始

```bash
npm install
npm run dev
```
