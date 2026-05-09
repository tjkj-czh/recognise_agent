# 03-frontend / 前端代码包

本目录包含变化监测智能体的前端界面与 BFF（Backend for Frontend）服务。

## 目录结构

```
03-frontend/
├── src/                         # 前端源码
│   ├── app/                     # 页面路由（按功能模块划分）
│   │   ├── monitoring/          # 监测中心
│   │   ├── reports/             # 报告管理
│   │   ├── data-management/     # 数据管理
│   │   └── system/              # 系统管理
│   ├── components/              # 公共组件
│   │   ├── ui/                  # 基础 UI 组件（Button、Modal 等）
│   │   ├── map/                 # 地图相关组件
│   │   └── charts/              # 图表组件
│   ├── services/                # API 调用层
│   │   ├── api-client.ts        # HTTP 客户端封装
│   │   ├── skill-gateway.ts     # Skill 调用封装
│   │   └── types.ts             # API 类型定义
│   ├── stores/                  # 状态管理（Zustand）
│   │   ├── auth-store.ts
│   │   ├── map-store.ts
│   │   └── monitoring-store.ts
│   └── utils/                   # 工具函数
│       ├── geo-utils.ts         # 地理计算
│       └── formatters.ts        # 格式化
├── backend-for-frontend/        # BFF 服务
│   ├── src/
│   │   ├── handlers/            # 路由处理器
│   │   ├── middleware/          # 中间件（鉴权、日志、限流）
│   │   ├── skill-gateway/       # Skill 调用网关
│   │   └── database/            # ORM / 数据访问层
│   └── package.json
├── package.json
├── vite.config.ts
├── tsconfig.json
└── tailwind.config.ts
```

## 技术栈

- React 19 + TypeScript 5
- Tailwind CSS + shadcn/ui
- Zustand（状态管理）
- Leaflet / MapLibre GL（地图）
- ECharts（可视化）
- tRPC 或 OpenAPI（前后端通信）

## 开发规范

详见 `01-specs/technical/frontend-standard.md` 与 `01-specs/technical/backend-standard.md`。

## 快速开始

```bash
# 安装依赖
npm install

# 启动前端开发服务器
npm run dev

# 启动 BFF 服务
npm run dev:bff

# 代码检查
npm run lint

# 运行测试
npm run test
```

## 模块边界

- **前端**禁止直接调用 Skill 运行时，所有 AI 能力通过 BFF 网关访问
- **BFF**禁止下沉业务逻辑（如变化检测算法），仅做请求转发、聚合与鉴权
