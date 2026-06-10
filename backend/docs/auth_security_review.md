# 登录与鉴权链路安全审计报告

本文围绕 [auth.py](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py)、[security.py](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/security.py)、[dependencies.py](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/dependencies.py) 三个文件，先用连贯叙述梳理 Web / 小程序两条登录路径与下游接口鉴权流程，再针对三条核心业务规则逐项核对实现，最后给出潜在越权与安全隐患的修复建议。

---

## 一、整体执行路径

### 1. Web 端登录链路

入口为 `POST /api/auth/web-login`，定义在 [web_login](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L28-L44)。

1. 通过 `LoginRequest` 接收 `username` / `password`，再以 `Session` 依赖（`get_db`）打开数据库会话。
2. 用 `username` 查询 `User`；查不到直接抛 `401 账号或密码错误`。
3. **角色门禁**：`user.role not in {ADMIN, TEACHER}` 抛 `403 该角色不允许网页登录`（在密码校验之前执行）。
4. **密码校验**：调用 [verify_password](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/security.py#L17-L18)，其本质是 `sha256(password:secret_key)` 的字符串相等比较。失败则抛 `401`。
5. **禁用拦截**：`user.is_active` 为假抛 `403 账号已被禁用`。
6. 通过 [create_access_token](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/security.py#L21-L28) 颁发 JWT（HS256，载荷为 `sub=user.id`、`role=user.role.value`、`exp`）。
7. 返回 `AuthTokenResponse(access_token, user)`。

### 2. 小程序端登录链路

入口为 `POST /api/auth/wechat-login`，定义在 [wechat_login](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L47-L84)。

1. 借助 `_normalize_mini_role` 仅接受 `STUDENT` / `PARENT`（含中文别名），其他角色 `422`。
2. 强校验 `student_no` 非空，否则 `422 请提供学号用于身份绑定`。
3. 用 [fake_wechat_openid](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/security.py#L43-L44) 由 `code` 通过 SHA256 派生伪 openid（**未对接真实微信 jscode2session**）。
4. 按学号查 `StudentProfile`，缺失则 `404 未找到对应学生档案`。
5. 角色分支：
   - `STUDENT`：以 `student.user_id + role==STUDENT` 取 `User`。
   - `PARENT`：取该学生 `ParentStudentRelation` 中 `id` 最小（最早绑定）那一条家长。
6. 命中 `User` 为空或被禁用则统一抛 `403 账号不可用`。
7. **openid 抢占绑定**：若有他人占用同一 `openid` 则直接清空对方记录，再把 `openid` 写入当前用户并 `commit`。
8. 颁发 JWT（`role` 用的是请求里归一化后的 `role.value`，与查询时的过滤条件等价）。

### 3. 下游接口鉴权链路

凡依赖 [get_current_user](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/dependencies.py#L25-L44) 的接口：

1. `HTTPBearer(auto_error=False)` 解析 `Authorization: Bearer ...`；缺失抛 `401`。
2. [decode_access_token](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/security.py#L31-L40) 用 `secret_key + HS256` 解码，要求 payload 必含 `sub`、`role`，`InvalidTokenError` / `ValueError` 全部静默返回 `None` → 上层 `401`。
3. 用 `sub` 反查 `User`，**再次**校验 `is_active`，失败 `401`。
4. `require_roles(*roles)` 工厂额外检查 `current_user.role` 是否在白名单内，否则 `403`。
5. `audit(module, action)` 仅是元数据装饰器，不参与权限判定。

---

## 二、三条业务规则一致性核对

### 规则①：网页端仅 ADMIN / TEACHER 可登录

- **实现位置**：[web_login L34-L35](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L34-L35)。
- **结论**：基本符合，但顺序存在问题。

存在的偏差：
- 角色校验排在 `verify_password` **之前**，且使用与"账号或密码错误"不同的 `403` 文案与状态码。攻击者只要知道存在的用户名（任何枚举手段拿到），就能通过响应区分该账号是否为 ADMIN / TEACHER，构成**用户名 + 角色枚举**侧信道。
- `is_active` 检查排在密码校验之后：禁用账号若密码正确才会进入 `403` 分支，因此**禁用账号也能被探测出"密码是否正确"**。

### 规则②：小程序端仅 STUDENT / PARENT 且需学号绑定校验

- **实现位置**：[`_normalize_mini_role`](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L20-L25)、[wechat_login L51-L84](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L51-L84)。
- **结论**：角色范围合规，"绑定校验"形同虚设，存在严重越权风险。

存在的偏差：
- `fake_wechat_openid` 仅是 `"wx_" + sha256(code)[:24]`，**根本不向微信开放平台校验 `code`**。也就是说 `code` 是任意可伪造字符串，调用方只要在请求里同时填写 `role`、任意 `code` 与受害者的 `student_no`，即可以该学生本人或第一位家长身份获得合法 JWT —— 这是**纯凭学号即可登录**的越权问题。
- "绑定校验"没有真正核对 openid 与用户的既有绑定关系：当库里 `user.wechat_openid` 已经存在（属于真正绑定过的微信号）时，本次登录会**直接覆盖**它，相当于攻击者每次登录都重新顶号；同时还会清空"恰好同 openid"的其他用户绑定。
- PARENT 分支永远取 `ParentStudentRelation.id.asc()` 第一条，**多家长场景下另一位家长无法登录**，且第一位家长能借任意学号免认证登录。
- 学生档案存在但 `User` 不存在或被禁用时统一 `403 账号不可用`，与"未绑定"语义混淆，上层难以做差异化处理（虽然不算安全风险，但属一致性问题）。

### 规则③：禁用账号一律拒绝访问

- **实现位置**：
  - [web_login L40-L41](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L40-L41)
  - [wechat_login L73-L74](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L73-L74)
  - [get_current_user L41-L42](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/dependencies.py#L41-L42)
- **结论**：登录与受保护接口都做了 `is_active` 校验，禁用后续请求会即时失效（因为每次请求都回库），**功能上达成**。

仍需注意：
- Web 端禁用校验位于密码校验之后，存在前述探测问题。
- JWT 不带 `jti` / 版本号，理论上颁发后无法主动撤销，仅靠每次回库 `is_active` 拦截；如果将来加入缓存或跳过 DB 校验的链路，禁用规则会失效。
- `decode_access_token` 仅捕获 `InvalidTokenError` 与 `ValueError`，PyJWT 大多数异常都继承 `InvalidTokenError`，目前安全；但若被改造成自行解析时需注意。

---

## 三、潜在越权与安全隐患汇总

| 编号 | 风险点 | 影响 | 严重度 |
| --- | --- | --- | --- |
| R1 | `wechat_login` 未真正校验微信 `code`，仅凭学号即可登录 | 任意学生/家长账号被冒用，全量数据越权 | 严重 |
| R2 | openid 写入采取"覆盖+清空他人"策略 | 攻击者可顶号、解绑他人 | 严重 |
| R3 | PARENT 始终取最早 relation，且未要求二次身份核对 | 多家长场景下身份错配 / 越权 | 高 |
| R4 | Web 登录角色与密码错误返回不同状态码与文案 | 用户名 + 角色枚举侧信道 | 中 |
| R5 | `is_active` 校验在密码校验之后 | 可探测禁用账号密码 | 中 |
| R6 | 密码哈希为 `sha256(password:secret_key)` | 离线彩虹表/暴力破解风险显著高于 bcrypt/argon2 | 高 |
| R7 | JWT 无 `iat` / `jti` / 版本号，密钥泄露后无法撤销 | 主动注销、强制下线无法实现 | 中 |
| R8 | `fake_wechat_openid` 命名虽带 fake，但被生产路径直接调用 | 易被误以为已对接微信 | 中 |
| R9 | `wechat_login` 颁发 token 时 `role` 取自请求体而非 `user.role` | 当前查询条件已限制角色，等价但易在后续改动中引入越权 | 低 |
| R10 | `audit` 装饰器只挂元数据，不写日志 | 审计缺失，无法事后追责 | 中 |

---

## 四、可操作的修复建议

1. **真正接入微信登录**：把 `fake_wechat_openid` 替换为微信 `jscode2session`（通过配置可降级为 mock）。登录时**只用 openid 反查已绑定用户**；学号仅在"首次绑定"流程里出现，并需结合短信/家校已知信息做二次确认。
2. **不再覆盖既有绑定**：当前 `user.wechat_openid` 已有值或目标 openid 已属于他人时，统一拒绝并要求走"换绑"独立流程，留下绑定历史记录。
3. **多家长支持**：把 PARENT 分支改成"按 openid → 用户"反查；首次绑定时让家长在多个候选学生中显式选择，禁止系统隐式选第一条 relation。
4. **登录顺序与文案统一**：[web_login](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L28-L44) 调整为"查用户 → 验密码 → 验角色 → 验 is_active"，且**用户不存在 / 密码错 / 角色不允许 / 禁用**统一返回相同 401 文案（必要时做内部审计区分），杜绝枚举侧信道。
5. **加固密码哈希**：将 [hash_password](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/security.py#L12-L14) 改为 `passlib[bcrypt]` 或 `argon2-cffi`，并保留迁移期内的双算法校验。
6. **JWT 增强**：补充 `iat`、`nbf`、`jti`、`token_version`，下发时把 `token_version` 写入 `User`；`get_current_user` 比对版本号实现"修改密码 / 禁用即下线"。
7. **绑定操作纳入事务与日志**：[wechat_login L76-L81](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L76-L81) 当前"清他人 + 写自己 + commit"路径异常时缺乏回滚与告警，建议包裹 try/except + 写审计日志（同步落地 [audit](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/dependencies.py#L56-L65) 装饰器的真实落库逻辑）。
8. **`role` 取自数据库**：在 `wechat_login` 颁发 token 时改用 `user.role.value`，避免日后查询条件松动导致越权。
9. **HTTPBearer 错误统一**：考虑把 `auto_error=False` 改为 `True` 或在 `get_current_user` 入口统一打日志，便于风控接入。
10. **测试用例补强**：为以下场景补充自动化测试——
    - 用 STUDENT/PARENT 试 `web-login` 必须 403；
    - 用 ADMIN/TEACHER 试 `wechat-login` 必须 422；
    - 禁用账号在两条登录路径与所有受保护接口上必须 401/403；
    - 错误 `code` 必须导致 `wechat-login` 失败（修复 R1 后）；
    - 多家长场景下家长各自能登录、互不影响。

---

## 五、结论

当前实现对"角色范围"和"禁用拦截"两条规则在功能层面是成立的，但 **小程序端"绑定校验"形同虚设**：`fake_wechat_openid` 没有任何外部验证，攻击者拿到学号即可冒充对应学生或第一位家长登录，这是最高优先级缺陷。其次是 Web 端登录顺序导致的用户名/角色枚举与禁用探测，以及密码哈希、JWT 撤销、审计落地等纵深防御问题。建议先按 R1–R3 完成业务越权堵漏，再按 R4–R10 进行通用安全加固。
