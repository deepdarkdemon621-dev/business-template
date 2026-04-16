# 通用业务系统模板 — 核心平台设计 Spec

- **日期**：2026-04-15
- **范围**：V1 核心平台 + 全局规范体系
- **不含**：表单引擎（独立 spec）、AI 分析（独立 spec）、可视化流程设计器（独立 spec）
- **参考项目**：`C:\Programming\Project\farmingFund`

---

## 1. 目标与非目标

### 1.1 目标

1. 产出一个**可复制、可裁剪的业务后台模板**，覆盖市面上"OA/审批流/业务管理"类系统的通用骨架
2. **将"AI 编程不一致漂移"问题作为头等约束**——以机械约束 + 受限原语 + 分层文档 + 审计代理构成闭环
3. 为后续两块子系统（表单引擎、AI 分析）预留契约接入点，现在不实现
4. 作为"AI 是否能按规范执行"的持续评估载体，产生可量化反馈

### 1.2 非目标（显式排除）

- SSR / SEO / 公网门户
- 多租户隔离（V1 单组织）
- BPMN 可视化流程设计
- 国际化（i18n 预留 hook，不做完整 i18n 机制）
- MFA / SSO / LDAP
- 微服务拆分

---

## 2. 技术栈（已锁定）

### 2.1 后端
| 层面 | 选型 | 备注 |
|---|---|---|
| 语言/运行时 | Python 3.13 | 与 farmingFund 对齐 |
| 框架 | FastAPI | async |
| 包管理 | `uv` + `pyproject.toml` | |
| ORM | SQLAlchemy 2.0 (async) | `mapped_column` 新 API |
| 迁移 | Alembic | 启动容器自动 upgrade |
| 数据库 | PostgreSQL 16 | |
| 缓存/队列 | **Redis 7**（新引入） | refresh denylist / 限流 / 失败计数 / 邮件 token |
| 鉴权 | JWT (argon2 哈希) | 见 §5.6 |
| 文件存储 | S3 兼容（dev: MinIO，prod: 可选 Sakura/AWS） | 预签名 URL |
| 扫毒 | ClamAV | 上传前强制 |
| 邮件 | 异步 SMTP (`aiosmtplib`) | |
| 限流 | `slowapi` + Redis 后端 | |
| 测试 | `pytest` + `pytest-asyncio` + `httpx` | |

### 2.2 前端
| 层面 | 选型 | 备注 |
|---|---|---|
| 元框架 | **Vite + React 18/19** | 非 Next.js，见 §3.3 决策 |
| 路由 | React Router v6 `createBrowserRouter` | |
| UI 原语 | **shadcn/ui**（copy-in, Radix + Tailwind + cva） | 非 MUI |
| 样式 | **Tailwind CSS** + CSS vars | design tokens 单源 |
| 表单 | React Hook Form + **ajv (JSON Schema)** resolver | 非 Zod，见 §5.1 |
| HTTP | axios + 拦截器 | 401 自动刷新 |
| 类型 | TypeScript 严格模式 | API 类型由 `openapi-typescript` 生成 |
| 状态管理 | Context + `useState`/`useReducer`；必要时 Zustand | 不引入 Redux |
| 图表 | （后续按需） | ECharts 或 Recharts |
| 测试 | Vitest + Testing Library + Playwright (e2e) | |

### 2.3 部署
- Docker Compose（dev/prod 两份）
- Nginx 反代 + TLS
- FE 纯静态产物托管于 Nginx
- `migrate` one-shot 容器跑 Alembic

---

## 3. 运行时架构

### 3.1 分层图

```
┌───────────────────────────────────────────────────────────┐
│  Browser (SPA)                                            │
│   Vite+React · shadcn/ui · Tailwind · RHF+ajv · axios     │
└────────────────────────┬──────────────────────────────────┘
                         │ HTTPS / JSON / Problem Details
                         ▼
┌───────────────────────────────────────────────────────────┐
│  Nginx：静态托管 + 反代 /api + TLS                         │
└────────────────────────┬──────────────────────────────────┘
                         ▼
┌───────────────────────────────────────────────────────────┐
│  FastAPI (async, uvicorn)                                 │
│   core/: config auth permissions guards form_rules        │
│          pagination errors audit storage antivirus        │
│          redis email workflow                             │
│   modules/*/: models schemas service router crud          │
│   OpenAPI → openapi-typescript (FE codegen)               │
└──────┬────────────┬──────────────┬────────────────────────┘
       ▼            ▼              ▼              ▼
  ┌─────────┐ ┌──────────┐  ┌────────────┐  ┌───────────┐
  │Postgres │ │  Redis   │  │ S3 存储    │  │ SMTP /    │
  │  16     │ │  7       │  │ MinIO(dev) │  │ LLM 供应  │
  │         │ │ denylist │  │ Sakura(prod│  │ 商(V2)    │
  │         │ │ 计数器   │  │ /AWS)      │  │           │
  │         │ │ 限流     │  │            │  │           │
  └─────────┘ └──────────┘  └─────┬──────┘  └───────────┘
                                   │（上传前扫毒）
                              ┌────▼────┐
                              │ ClamAV  │
                              └─────────┘
```

### 3.2 部署拓扑

- **dev**：`docker-compose.yml` 启动 db / redis / clamav / minio / backend(hot-reload) / frontend(vite dev server) / nginx
- **prod**：`docker-compose.prod.yml` 启动 db / redis / clamav / migrate(one-shot) / backend / nginx(托管 FE 产物 + 反代 /api) —— 生产不暴露内部服务端口

### 3.3 元框架决策记录（ADR 迷你版）

> **为何 Vite+React 而非 Next.js？**
>
> 本系统是登录后的管理后台。Next.js 的核心价值（SSR/SEO/edge/server components）对本场景收益为零；而其 client/server 边界、`"use client"` 标记、双运行时部署、hydration 复杂度正好撞在"AI 编程漂移"这一核心约束上。Vite+React 的 SPA 模式简化 AI 心智模型，产物纯静态便于部署，dev HMR 更快。开源后台管理项目（refine、react-admin、antd-pro 等）几乎统一选 Vite 路线。除非未来新增公网门户需求，不切回 Next.js。

---

## 4. 子系统地图

### 4.1 子系统清单与 V1/V2 划分

| 模块 | V1 | V2/后续 |
|---|---|---|
| `auth` | 登录/登出/刷新/密码重置/会话列表/Captcha hook | MFA |
| `user` | CRUD / 启停 / 改密 / 头像 | 批量导入 / LDAP / SSO |
| `department` | 树形 CRUD / materialized path | 跨部门协作矩阵 |
| `role` | Role CRUD | 权限模板/克隆 |
| `permission` | Permission 常量同步 / RolePermission+scope 分配 / `/me/permissions` | 权限继承 |
| `attachment` | 上传（扫毒）/ 下载（预签名）/ feature+category 路径 | 图片/视频处理 |
| `audit_log` | 所有 mutation 自动审计 / 查询 | 导出 / 归档 |
| `workflow`（库） | 声明式状态机 DSL + 示例模块 | 可视化设计器（独立 spec） |
| `notification` | 站内消息 + 邮件（事件驱动）| WS 推送 |
| `export` | CSV 流式导出通道 | Excel / PDF |
| `search` | 列表过滤 + `?q=` 关键词 | 全文检索 (ES/Meili) |
| `form_engine` | ❌ | **独立 spec** |
| `ai_analysis` | ❌ | **独立 spec** |

### 4.2 跨子系统契约

1. **attachment 是中立服务**：user / workflow / form / ai_analysis 一律调它，不各造上传。调用方声明 `feature` + `category_code`，服务返回 `attachment_id`。
2. **JSON Schema 是表单/校验的传输格式**：静态（Pydantic）与动态（表单引擎，V2）均生成 JSON Schema；前端 `FormRenderer` 对两种来源使用**同一** ajv 实例 + 同一组件树。
3. **workflow 是库不是模块**：`core/workflow.py` 提供状态机 DSL；业务模块声明自己的工作流。与 permission/scope/notification/audit 自动联动。
4. **所有 mutation 自动 audit**：通过 service 基类 hook，业务模块不显式调用。
5. **ai_analysis 输入只收 `attachment_id`**：复用统一扫毒、存储、权限链路，不接受直传文件。

---

## 5. 规范体系（防 AI 漂移核心）

### 5.0 指导原则

> 规范不能只靠文档写"请保持一致"，必须靠**机械约束**让 AI 无法写出不一致的代码。

防漂移三层：

| 层级 | 强度 | 手段 |
|---|---|---|
| **L1 机械约束** | 最硬 | 类型生成、schema codegen、lint 规则、CI 扫描、不存在的 API 让 AI 没法偷懒 |
| **L2 原语约束** | 较硬 | 受限组件库、受限 Tailwind token、封装层强制 |
| **L3 文档约束** | 最软 | 分层 CLAUDE.md、`docs/conventions/` |
| **L∞ 审计闭环** | 持续 | convention-auditor 子代理（§7）|

所有规范的详细版本放在 `docs/conventions/NN-*.md`；CLAUDE.md 短小，引用具体规约文件。

### 5.1 校验契约（`docs/conventions/01-schema-validation.md`）

**方案 A2（JSON Schema 为运输格式，Pydantic 为编写格式）**

- **作者形式（人写什么）**：开发者只写 Pydantic；管理员（V2）在表单引擎 UI 点配置；**无人手写 JSON Schema**
- **运输格式**：Pydantic 导出 `.model_json_schema()`；动态表单引擎编译为 JSON Schema
- **消费者**：前端 `ajv` 校验 + `FormRenderer` 渲染；后端 Pydantic 校验（动态场景用 `create_model`）
- **TS 类型**：通过 `openapi-typescript` 从 OpenAPI 派生到 `src/api/generated/`（禁止手改）

**字段级规则**：Pydantic 原生能力（`max_length` / `ge` / `le` / `pattern` / `EmailStr` / `Literal`）自动进 JSON Schema，ajv 原生消费。

**跨字段规则 — FormRuleRegistry 词汇表（双端各实现一次，签名对齐）**：

```
dateOrder(start, end)            # end > start
mustMatch(a, b)                  # 两字段必须一致
conditionalRequired(when, then)  # 选 A 则 B 必填
mutuallyExclusive([...])         # 几选一
uniqueInList(path, key)          # 列表内某键不重复
```

通过 Pydantic `json_schema_extra = {"x-rules": [...]}` 挂载；Pydantic 侧由同一份规则注册表生成对应 `@model_validator`。**业务代码只能从词汇表选用；超出词汇表须评审后补进词汇表（双端同步实现）；禁止自由 Python lambda 做跨字段校验。**

### 5.2 Service Guards（`docs/conventions/02-service-guards.md`）

**业务不变量**（如"有员工的部门不能删"）不走 JSON Schema，走后端 service 层。

**ServiceGuardRegistry 词汇表（开小不开大）**：

```
# 删除类
NoDependents(table, fk_col)
NoActiveChildren(relation)

# 状态类
StateAllows(field, allowed=[...])
ImmutableAfter(field, frozen_from=...)

# 作用域类
SameDepartment()
```

**声明式挂载**：

```python
class Department(Base):
    __guards__ = {
        "delete": [
            NoDependents("users", "department_id"),
            NoDependents("roles", "default_department_id"),
        ],
    }
```

**协议**：
- DB 层外键 `ON DELETE RESTRICT`（兜底）
- service 层执行前跑 guard → 不通过抛 `GuardViolationError(code, ctx)`
- 前端可预查询 `GET /resource/:id/deletable` → `{can, reason_code, details}`
- **禁止**在 endpoint 里手写 `if exists(...): raise`；违反 guard 必须走注册表

### 5.3 UI 原语（`docs/conventions/03-ui-primitives.md`）

**shadcn/ui + Tailwind + cva**。

- **单一 token 源**：`src/lib/design-tokens.ts` 定义颜色/间距/字号/圆角，`tailwind.config.ts` 从它派生
- **封装层**：所有 shadcn/ui 组件在 `src/components/ui/` 内通过 cva 限定变体；**业务代码只能 import `components/ui/` 和 `components/form/` `components/table/` `components/layout/`**，禁止跨过封装直接 import Radix / 原始 shadcn 组件
- **Tailwind 使用范围**：布局 / 间距 / 排版 utility；**禁止**用 Tailwind 改组件内部样式（颜色、圆角、阴影走 token）
- **间距刻度**：Tailwind `spacing` 基 4px（标准），所有间距值走 token

### 5.4 表单（`docs/conventions/04-forms.md`）

**全系统表单只有一种写法**：

```
JSON Schema (来自 API/引擎) → RHF useForm + ajv resolver → <FormRenderer> 按 schema 渲染 → submit
```

- `components/form/FormRenderer.tsx`：读取 JSON Schema 和 `x-rules`，产出受控组件树
- `components/form/fields/`：每种 JSON Schema 类型对应一个 Field 组件（String/Number/Boolean/Date/Enum/File/Array/Object…），使用 shadcn/ui 原语
- `FieldRegistry`：额外的 "x-widget" 映射扩展（如 `x-widget=rich-text` → 富文本组件）
- ajv 实例注册 FormRuleRegistry 的所有规则实现
- **禁止**手写表单（直接用 `<input>` / `<Input>` 拼表单）；**禁止**在单个表单里用 Zod / Yup 替换 ajv

### 5.5 API 契约（`docs/conventions/05-api-contract.md`）

| 子项 | 规则 |
|---|---|
| **错误格式** | RFC 7807 Problem Details 扩展：`{type, title, status, detail, code, errors[], guard_violation?}` |
| **分页** | offset-based：`?page=1&size=20`；响应 `{items, total, page, size, has_next}` |
| **响应包络** | 无外层包络；成功直接返回资源本体或列表结构；错误走 Problem Details |
| **命名边界** | 后端 snake_case；Pydantic `alias_generator=to_camel` + `populate_by_name=True` → API 边界自动 camelCase |
| **列表查询** | 过滤：字段名作为查询键（白名单）；排序：`?sort=-created_at,name`；搜索：`?q=...` |
| **分页硬封顶** | `size ≤ 100`；服务端无视更大值 |
| **列表端点基类** | `PaginatedEndpoint` 自动注入 `PageQuery`；查询走 `paginate(query, page_query)` 辅助函数 |
| **导出通道** | 独立 `GET /resource/export` 端点流式返回 CSV，不走列表 JSON |
| **版本前缀** | `/api/v1/...` |

### 5.6 鉴权与会话（`docs/conventions/06-auth-session.md`）

**B 方案**：短 JWT（15–30min）+ 刷新 token（7 天，滑动窗口 30min 空闲超时） + 轮换 + Redis denylist。

| 维度 | 细节 |
|---|---|
| 密码哈希 | argon2（passlib 封装） |
| 访问令牌 | JWT，载荷 `{sub, role_ids, dept_id, jti, iat, exp}` |
| 刷新令牌 | httpOnly + Secure + SameSite=Strict cookie，Path=/auth；每次刷新轮换，旧入 denylist |
| 空闲过期 | 滑动 30min（refresh 使用即续） |
| 绝对过期 | 7 天（硬超时，需重登） |
| 登录失败 | 同账号 5 次/15min 锁定；同 IP 20 次/min 限流（Redis 计数） |
| 首次登录 | 强制改密 |
| 密码重置 | 邮件 one-time token（Redis 存储），30min 有效，用后作废 |
| 端点保护 | 全局 `Depends(require_auth)`；公开接口必须 `public=True` 显式标注 |
| 前端 401 | 仅 axios 拦截器统一处理（先 refresh，失败跳 /login）；业务代码禁止处理 401 |
| 会话管理 | `GET /me/sessions` 列出所有 refresh token，可单独吊销 |
| Captcha | 登录/密码重置接口留 hook（placeholder），V2 接 hCaptcha/Turnstile |
| "记住我" | 不做 |

### 5.7 RBAC（`docs/conventions/07-rbac.md`）

**C 方案**：Role + Permission + 数据作用域 Scope。

**数据模型**：

```
departments:       id, name, parent_id, path (materialized path)
permissions:       id, code ("user:create"...), description
roles:             id, code, name, is_system
role_permissions:  role_id, permission_id, scope ENUM('global','dept_tree','dept','own')
user_roles:        user_id, role_id   (多对多)
users:             id, email, department_id, is_superadmin
```

**权限命名规范**：`resource:action`；动作词汇表固定：`create / read / update / delete / list / export / approve / reject / publish / invoke`；超词汇须评审。

**作用域语义**：

| scope | 含义 |
|---|---|
| `global` | 全系统 |
| `dept_tree` | 本部门 + 所有子孙 |
| `dept` | 仅本部门 |
| `own` | 仅自己创建 |

**机械约束**：

- 端点声明：`dependencies=[Depends(require_perm("user:delete"))]` + `Depends(load_in_scope(...))`
- 列表查询：必须走 `apply_scope(query, current_user, perm_code, dept_field)`；lint 扫描裸 `select()` 且模型受权限保护时告警
- 前端：`/me/permissions` 返回 `[{code, scope}]`；`usePermissions().can(code)` 仅控制 UX；后端独立校验
- `is_superadmin=True` 绕过一切（仅内置超级管理员角色，不对外暴露创建）

**权限 seed**：`core/permissions.py` 定义常量，启动时同步到 DB（新增自动插入；移除 warning 但不删）；内置角色（superadmin / admin / member）通过 Alembic data migration 初始化。

### 5.8 目录与 CLAUDE.md 分层（`docs/conventions/08-naming-and-layout.md`）

**后端 feature-first**：

```
backend/
├── pyproject.toml
├── CLAUDE.md
├── alembic/versions/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── CLAUDE.md
│   │   ├── config.py  database.py  redis.py  auth.py
│   │   ├── permissions.py  guards.py  form_rules.py
│   │   ├── pagination.py  errors.py  audit.py
│   │   ├── storage.py  antivirus.py  email.py  workflow.py
│   ├── modules/
│   │   ├── _template/       ← 新模块复制起点
│   │   │   ├── models.py  schemas.py  service.py  router.py  crud.py
│   │   ├── auth/  user/  department/  role/  permission/
│   │   ├── attachment/  audit_log/  notification/
│   │   ├── workflow_example/   ← 用 workflow DSL 的示范
│   │   │   └── CLAUDE.md
│   └── api/v1.py               ← 仅聚合路由
└── tests/                      ← 镜像 modules/ 结构
```

**前端 feature-first**：

```
frontend/
├── package.json  vite.config.ts  tailwind.config.ts  tsconfig.json
├── CLAUDE.md
├── index.html
└── src/
    ├── main.tsx  App.tsx  router.tsx
    ├── api/
    │   ├── client.ts           ← axios 实例 + 401 拦截器
    │   └── generated/          ← openapi-typescript 产物，勿手改
    ├── lib/
    │   ├── design-tokens.ts    ← 色/距/字/圆角 SSOT
    │   ├── ajv.ts              ← ajv 实例 + FormRule 注册
    │   ├── auth/               ← AuthProvider / useAuth / usePermissions
    │   └── utils/
    ├── components/
    │   ├── ui/                 ← shadcn/ui 封装
    │   │   └── CLAUDE.md
    │   ├── form/               ← FormRenderer / Field / FieldRegistry
    │   │   └── CLAUDE.md
    │   ├── table/              ← DataTable (仅 server pagination)
    │   └── layout/             ← AppShell / Sidebar / TopBar
    ├── modules/
    │   ├── auth/  user/  department/  role/
    │   ├── workflow_example/
    └── types/
```

**规范文档群 `docs/conventions/`**：

```
docs/
├── conventions/
│   ├── 01-schema-validation.md
│   ├── 02-service-guards.md
│   ├── 03-ui-primitives.md
│   ├── 04-forms.md
│   ├── 05-api-contract.md
│   ├── 06-auth-session.md
│   ├── 07-rbac.md
│   ├── 08-naming-and-layout.md
│   └── 99-anti-laziness.md
├── superpowers/specs/       ← 本文件及后续 spec
└── api-requirements.md      ← 功能清单 / 端点列表
```

**CLAUDE.md 分层**：

| 位置 | 内容 |
|---|---|
| `/CLAUDE.md` | 项目定位 / 技术栈 / 运行命令 / **必读规约索引** / 部署入口 |
| `backend/CLAUDE.md`、`frontend/CLAUDE.md` | 该层硬规约清单 + 引用 `docs/conventions/*` |
| `app/core/CLAUDE.md` 等 | 局部特别约束 |

CLAUDE.md **短小精悍**，规范细节不复制到 CLAUDE.md，只引用；避免内容漂移双份维护。

### 5.9 反 AI 偷懒清单（`docs/conventions/99-anti-laziness.md`）

动态文档，AI 新发现一类偷懒就加一行。当前 V1 清单：

| # | 偷懒模式 | 症状 | 机械拦截 |
|---|---|---|---|
| 1 | 前端分页 | `.slice(start,end)` 在 FE | 组件无 client 模式；API 无裸数组形状 |
| 2 | 前端搜索/过滤 | 全量 fetch 后 FE `.filter()` | 同上 + 后端支持 `?q=` / 字段过滤 |
| 3 | N+1 查询 | for 循环里读关联 | 慢查询日志 + 强制 `selectinload`/`joinedload` |
| 4 | 缺索引 | 过滤/排序字段无索引 | Alembic 迁移 review checklist |
| 5 | 吞异常 | `except: pass` | lint 规则 |
| 6 | 硬编码 magic value | 字符串比较代替枚举 | lint + 强制枚举 |
| 7 | 跳过事务 | 多步写无事务 | service 基类强制 |
| 8 | 遗漏鉴权 | 新端点无权限装饰器 | pytest 扫描全 router |
| 9 | mock 数据泄漏 | 硬编码假数据 | `MOCK_*` 前缀 + env 检查 + CI grep |
| 10 | TODO 混入 main | `// TODO: 正式要改` | CI grep TODO/FIXME/XXX |
| 11 | token 明文 localStorage | XSS 风险 | 约束到 sessionStorage 或 httpOnly cookie |
| 12 | API 返回全量对象 | 返回 `password_hash` | 强制走响应 Pydantic schema |

每个条目须有"机械拦截"列；仅有"review 注意"的条目不算规范，写到 `docs/review-checklist.md`。

---

## 6. Workflow DSL

声明式状态机库，`app/core/workflow.py`：

```python
class ApplicationWorkflow(Workflow):
    initial = "draft"
    states = ["draft", "submitted", "reviewing", "approved", "rejected", "fix_requested"]
    transitions = [
        T("submit",      from_="draft",          to="submitted",    guards=[FormComplete()]),
        T("start_review",from_="submitted",      to="reviewing",    permission="application:review"),
        T("approve",     from_="reviewing",      to="approved",     permission="application:approve"),
        T("reject",      from_="reviewing",      to="rejected",     permission="application:approve"),
        T("request_fix", from_="reviewing",      to="fix_requested",permission="application:review"),
        T("resubmit",    from_="fix_requested",  to="submitted"),
    ]
    on_enter("approved").emit("application.approved")
    on_enter("rejected").emit("application.rejected")
```

**能力要点**：
- `T(action, from_, to, guards=[], permission=None, on_success=[], on_failure=[])`
- Guards 通过 ServiceGuardRegistry（§5.2）
- permission 走 `require_perm`（§5.7）
- `on_enter(state).emit(event)` 联动 notification 系统
- 所有 transition 自动记 audit log
- 每次 transition 单事务
- 并发控制：版本号字段 + 乐观锁

**V1 交付一个示范模块** `workflow_example/`：简单请假单，演示 DSL 全链路使用。

---

## 7. Convention Auditor（双层审计）

### 7.1 L1 机械层（CI / pre-commit）

`scripts/audit/` 下的确定性脚本，CI 失败阻断合并：

| 脚本 | 检查 |
|---|---|
| `audit_except.sh` | 禁 `except:\s*pass`、裸 `except:` 无 re-raise |
| `audit_listing.py` | AST 扫描：列表端点必须走 `paginate()`，响应形状必须是 `{items,total,...}` |
| `audit_permissions.py` | AST 扫描：所有 router 函数必须有 `require_perm` 或 `public=True` |
| `audit_imports.ts` | `@mui/material` 不能在 `src/modules/` 出现；shadcn 原件不能绕过 `components/ui/` |
| `audit_pagination_fe.ts` | 禁 `paginationMode="client"` |
| `audit_mock_leak.sh` | grep `MOCK_` 前缀确保不在 prod build 里 |
| `audit_todo.sh` | TODO/FIXME/XXX 新增触发 warning（PR 需显式 ack） |
| `audit_json_schema.sh` | 禁手写 `*.schema.json`（必须 Pydantic 生成） |
| `audit_openapi_diff.py` | OpenAPI 变更须对应 `src/api/generated/` 更新 |

### 7.2 L2 语义层 — convention-auditor 子代理

项目内置 Claude Code subagent：`.claude/agents/convention-auditor.md`

```yaml
---
name: convention-auditor
description: >
  Verifies changed code complies with project conventions in docs/conventions/*.md.
  Must be invoked before marking any feature complete or merging.
tools: Bash, Grep, Glob, Read
model: sonnet
---
```

**输入**：
- `git diff --name-only <base>..HEAD` 的改动清单
- `docs/conventions/*.md` 全集
- 涉及模块的 `CLAUDE.md`

**检查矩阵**：逐条规约 × 本次改动 → 产出表

**输出格式**：

```
## PASS (N)
- [01-schema-validation] modules/user/schemas.py 字段校验合规
- ...

## VIOLATIONS (M)
### [07-rbac] modules/user/router.py:42 list_users
裸 select(User) 未经 apply_scope → 跨部门数据泄漏风险
修正建议: query = apply_scope(select(User), current_user, "user:list", "department_id")

### [99-anti-laziness #5] modules/ai/service.py:89
`except Exception: pass` 吞异常

## VERDICT: BLOCK   ← PASS / BLOCK
```

**触发时机**：
- 每个 feature 实现完成、测试通过、准备标记完成前**必须**调用
- 仓库 `CLAUDE.md` 写明：**verdict=PASS 才算真完成**
- 亦可集成 git pre-push（但 agent 慢，不放 pre-commit）

### 7.3 L3 反馈闭环

```
规约 → AI 写代码 → L1 机械审 → L2 agent 审
                        │            │
                        └── 发现新漂移 ──┐
                                       ▼
                           补进机械脚本 OR anti-laziness 条目
                                       ▼
                                    回写规约
```

本项目本身就是"AI 规范遵循能力"的持续评估载体。

---

## 8. V1 交付清单

### 8.1 文档
- [ ] 仓库 `CLAUDE.md`
- [ ] `backend/CLAUDE.md`、`frontend/CLAUDE.md`
- [ ] `docs/conventions/01-09、99`
- [ ] `docs/api-requirements.md`
- [ ] `.claude/agents/convention-auditor.md`

### 8.2 后端
- [ ] 骨架：`app/{main,core/*,modules/_template,api/v1}`
- [ ] 核心库：auth / permissions / guards / form_rules / pagination / errors / audit / storage / antivirus / redis / email / workflow
- [ ] 模块：auth / user / department / role / permission / attachment / audit_log / notification / workflow_example
- [ ] Alembic 初始迁移 + 内置数据（permission seed / 内置角色 / 超级管理员账号）
- [ ] 测试：每模块 unit + integration，覆盖率目标 70%+

### 8.3 前端
- [ ] 骨架：vite + ts + tailwind + shadcn/ui init
- [ ] `src/lib/{design-tokens,ajv,auth}`
- [ ] `src/components/{ui,form,table,layout}`
- [ ] `src/api/{client,generated}`
- [ ] `src/modules/{auth,user,department,role,workflow_example}`
- [ ] 路由 + AuthProvider + 路由守卫
- [ ] 测试：关键页 component 测试 + e2e 冒烟（登录/CRUD 一轮）

### 8.4 基础设施
- [ ] `docker-compose.yml` / `docker-compose.prod.yml`
- [ ] `nginx/nginx.conf`
- [ ] `deploy.sh` / `deploy.ps1`
- [ ] `scripts/audit/*`（L1 机械审计脚本）
- [ ] GitHub Actions（或等价 CI）配置：lint / test / audit / build

---

## 9. 延后子 spec

| spec | 触发时机 |
|---|---|
| `YYYY-MM-DD-form-engine-design.md` | V1 稳定后立即 |
| `YYYY-MM-DD-ai-analysis-design.md` | 需求明确后（当前"还没想好"）|
| `YYYY-MM-DD-workflow-designer-design.md` | 可选，若 workflow DSL 用户有可视化需求 |

---

## 10. 次要决策（已锁定）

- **文件存储**：dev 用 MinIO（docker-compose 内置），prod 环境变量切换到 S3 兼容云（Sakura/AWS）；抽象层 `core/storage.py` 屏蔽差异
- **React 版本**：React 19（稳定版，新项目默认）
- **邮件模板引擎**：**Jinja2 only**；模板放 `backend/app/templates/emails/{name}.html` + `{name}.txt`；未来真需要精美 HTML 邮件再引入 MJML
- **审计日志保留**：热存 90 天（Postgres），90 天后冷存归档（CSV 压缩到 S3），2 年后清理；V1 实现热存和归档脚本，清理留为 V2
- **CI 平台**：GitHub Actions
- **design tokens 同步**：不接 Figma tokens；手工维护 `src/lib/design-tokens.ts` 为 SSOT
- **workflow 示范模块**：请假单（场景简单、状态少、容易 cover DSL 全部能力，避免抢风头）
