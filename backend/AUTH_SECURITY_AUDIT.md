# 认证鉴权系统安全审计报告

## 一、系统架构概述

本系统采用 FastAPI + SQLAlchemy + JWT 构建认证体系，包含 Web 端（用户名密码）与小程序端（微信登录）两种登录方式，基于角色（ADMIN/TEACHER/STUDENT/PARENT）进行访问控制。

---

## 二、完整执行路径分析

### 2.1 Web 端登录流程（`/api/auth/web-login`）

**入口文件**：[auth.py](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L28-L44)

```
客户端请求 → 路由层 web_login()
    ↓
1.  根据 username 查询 User 表（第30行）
    → 无用户 → 返回 401 "账号或密码错误"
    ↓
2.  角色白名单校验：user.role ∈ {ADMIN, TEACHER}（第34行）
    → 不属于 → 返回 403 "该角色不允许网页登录"
    ↓
3.  密码校验：verify_password() 比对 SHA256 哈希（第37行）
    → 不匹配 → 返回 401 "账号或密码错误"
    ↓
4.  账号状态校验：user.is_active == True（第40行）
    → 已禁用 → 返回 403 "账号已被禁用"
    ↓
5.  签发 JWT：create_access_token(user.id, user.role.value)（第43行）
    ↓
6.  返回 access_token + 用户信息
```

### 2.2 小程序端登录流程（`/api/auth/wechat-login`）

**入口文件**：[auth.py](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L47-L84)

```
客户端请求（code + role + student_no） → 路由层 wechat_login()
    ↓
1.  角色规范化：_normalize_mini_role() 映射为 STUDENT/PARENT（第49行）
    → 其他角色 → 返回 422 "角色仅支持 STUDENT 或 PARENT"
    ↓
2.  学号非空校验（第51-53行）
    → 空学号 → 返回 422 "请提供学号用于身份绑定"
    ↓
3.  生成伪 OpenID：fake_wechat_openid(code)（第55行）
    → 实际是 wx_ + SHA256(code)[:24]
    ↓
4.  根据学号查询 StudentProfile（第56行）
    → 无档案 → 返回 404 "未找到对应学生档案"
    ↓
5.  按角色分支查询用户（第60-71行）：
    ├─ STUDENT：查 User 满足 id=student.user_id AND role=STUDENT
    └─ PARENT：查 ParentStudentRelation → 取第一条记录的 parent_id → 查 User 满足 role=PARENT
    → 用户不存在 → 进入下一步统一判断
    ↓
6.  用户有效性校验：user 存在 AND user.is_active == True（第73行）
    → 无效 → 返回 403 "账号不可用"
    ↓
7.  OpenID 冲突处理（第76-79行）：
    → 若 openid 已被其他用户绑定 → 先将旧用户的 wechat_openid 置空
    ↓
8.  绑定当前用户的 wechat_openid，commit 事务（第80-81行）
    ↓
9.  签发 JWT：create_access_token(user.id, role.value)（第83行）⚠️ 注意：role 来自请求参数，非数据库
    ↓
10. 返回 access_token + 用户信息
```

### 2.3 JWT 签发机制

**文件**：[security.py](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/security.py#L21-L40)

- **算法**：HS256（HMAC-SHA256）
- **载荷**：`sub`(user_id 字符串)、`role`(角色字符串)、`exp`(过期时间，UTC)
- **有效期**：由 `settings.access_token_expire_minutes` 配置
- **解码逻辑**：验证签名 + 过期时间 + 必填字段存在性，失败返回 None

### 2.4 下游接口鉴权流程

**文件**：[dependencies.py](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/dependencies.py#L25-L53)

```
受保护接口 → Depends(get_current_user) / Depends(require_roles(...))
    ↓
1.  HTTPBearer 提取 Authorization: Bearer <token>
    → 无凭证 → 返回 401 "未登录或登录已过期"
    ↓
2.  decode_access_token() 验证 JWT
    → 无效 → 返回 401 "登录令牌无效"
    ↓
3.  从 payload 提取 user_id
    → 缺失 → 返回 401 "登录令牌缺少用户信息"
    ↓
4.  数据库查询 User，校验 user.is_active（第40-42行）
    → 不存在/已禁用 → 返回 401 "当前账号不可用"
    ↓
5.  [若使用 require_roles] 检查 current_user.role 是否在允许列表
    → 越权 → 返回 403 "权限不足"
    ↓
6.  返回 User 对象供接口使用
```

---

## 三、业务规则逐条核对

### 规则一：网页端仅 ADMIN/TEACHER 可登录

**实现位置**：[auth.py](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L34-L35)

| 核对项 | 状态 | 说明 |
|--------|------|------|
| 角色白名单 | ✅ 已实现 | `user.role not in {UserRole.ADMIN, UserRole.TEACHER}` 正确拦截非管理员/教师角色 |
| 返回状态码 | ✅ 正确 | 越权角色返回 403 Forbidden |

**结论**：该规则**基本一致**，但存在校验顺序问题（见安全隐患部分）。

---

### 规则二：小程序端仅 STUDENT/PARENT 且需学号绑定校验

**实现位置**：[auth.py](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L20-L25, L49-L71)

| 核对项 | 状态 | 说明 |
|--------|------|------|
| 角色白名单 | ✅ 已实现 | `_normalize_mini_role()` 仅允许 STUDENT/PARENT，大小写中英文均兼容 |
| 学号必填 | ✅ 已实现 | 学号为空/空字符串返回 422 |
| 学号存在性校验 | ✅ 已实现 | 查 StudentProfile，不存在返回 404 |
| STUDENT 绑定校验 | ✅ 已实现 | 通过 `student.user_id` 关联 User，且要求 role=STUDENT |
| PARENT 绑定校验 | ❌ **严重缺陷** | 仅取 `ParentStudentRelation` 表中按 id 升序的**第一条**家长记录，**完全不验证登录者身份**——任何人只要知道任意学生学号，选择 PARENT 角色即可直接登录为该学生的第一个绑定家长，无需任何家长身份证明 |

**结论**：该规则**部分一致**，家长端身份绑定校验存在**严重越权漏洞**。

---

### 规则三：禁用账号一律拒绝访问

| 检查点 | 位置 | 状态 | 说明 |
|--------|------|------|------|
| Web 登录时检查 | [auth.py:40-41](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L40-L41) | ✅ 已实现 | `if not user.is_active` → 403 |
| 小程序登录时检查 | [auth.py:73-74](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L73-L74) | ✅ 已实现 | `if user is None or not user.is_active` → 403 |
| 每次请求鉴权时检查 | [dependencies.py:41-42](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/dependencies.py#L41-L42) | ✅ 已实现 | 每次请求都从数据库查用户并校验 is_active，可实时封禁 |

**结论**：该规则**完全一致**，且在登录和每次请求两个环节都有检查，实现正确。

---

## 四、安全隐患与修复建议

### 🔴 高危漏洞

#### 漏洞 1：JWT 签发角色来源不可信（越权风险）

**位置**：[auth.py:83](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L83)

```python
token = create_access_token(user.id, role.value)  # role 来自请求参数 _normalize_mini_role()
```

**问题描述**：小程序登录签发 JWT 时，`role` 取自客户端传入的 payload（经 `_normalize_mini_role` 规范化），而非数据库中查询出来的 `user.role`。虽然当前代码中查询用户时已过滤角色，但：
- 若未来修改逻辑（如去除查询中的 role 条件），攻击者可传入任意角色
- 违反"不以客户端输入为信任源"的安全原则
- 与 Web 登录（第43行使用 `user.role.value`）行为不一致

**修复建议**：
```python
# 第83行改为：
token = create_access_token(user.id, user.role.value)
```

---

#### 漏洞 2：小程序家长登录无身份验证（任意家长账户接管）

**位置**：[auth.py:63-71](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L63-L71)

**问题描述**：家长登录时仅需提供学生学号，系统自动取该学生的第一个绑定家长（按 relation id 升序），**没有任何机制验证当前登录者是否是该家长本人**。攻击者只需枚举/猜到任意学生学号，即可：
- 以该学生第一个家长身份登录
- 查看该学生所有成绩、行为记录等隐私数据
- 可能执行家长权限下的操作

**修复建议**（三选一或组合）：
1. **首次绑定后验证**：家长首次通过学号登录时，要求输入预留手机号后四位/验证码进行核验，核验通过后将 wechat_openid 与 parent_id 绑定；后续登录必须验证 openid 与 parent_id 对应关系
2. **基于 OpenID 反查**：如果是再次登录（已有 openid），应先通过 openid 查 User，再验证其是否与该学号有家长关系，而不是直接通过学号取家长
3. **增加家长邀请码机制**：学生/管理员生成唯一邀请码发给家长，家长必须同时提供学号和邀请码才能绑定

---

#### 漏洞 3：OpenID 绑定可被恶意覆盖（账户劫持）

**位置**：[auth.py:76-81](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L76-L81)

**问题描述**：任何人只要知道学号，就能用自己的微信 code（生成自己的 openid）调用 wechat-login，系统会将目标用户（学生或家长）的 wechat_openid **强制替换为攻击者的 openid**，导致原绑定者被踢下线，攻击者持续控制该账户。

**修复建议**：
```python
# 在 wechat_login 中先检查 openid 是否已绑定用户
already_bound = db.query(User).filter(User.wechat_openid == openid).first()
if already_bound and already_bound.id != user.id:
    raise HTTPException(status_code=403, detail="该微信已绑定其他账号，请先解绑")

# 仅当用户从未绑定过 openid（首次登录）时才允许绑定
if user.wechat_openid is None:
    user.wechat_openid = openid
    db.commit()
elif user.wechat_openid != openid:
    raise HTTPException(status_code=403, detail="请使用已绑定的微信登录")
```

---

### 🟡 中危问题

#### 问题 4：Web 登录校验顺序不当（用户/角色枚举风险）

**位置**：[auth.py:30-41](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L30-L41)

当前顺序：①查用户→②查角色→③验密码→④查禁用

**问题描述**：不同错误返回不同状态码/消息：
- 用户名不存在 → 401
- 角色不允许网页登录 → 403（用户名存在，但角色不对）
- 密码错误 → 401
- 账号禁用 → 403

攻击者可通过返回状态码判断：①用户名是否存在；②该用户名是什么角色（如果返回403说明是 STUDENT/PARENT 角色）。

**修复建议**：统一先验证密码（或至少在用户不存在时使用与密码错误相同的错误），将角色和禁用检查放在密码验证之后，且所有失败统一返回模糊错误消息：
```python
user = db.query(User).filter(User.username == payload.username).first()
if user is None or not verify_password(payload.password, user.password_hash):
    raise HTTPException(status_code=401, detail="账号或密码错误")
# 密码验证通过后再检查角色和状态
if user.role not in {UserRole.ADMIN, UserRole.TEACHER}:
    raise HTTPException(status_code=403, detail="该角色不允许网页登录")
if not user.is_active:
    raise HTTPException(status_code=403, detail="账号已被禁用")
```

---

#### 问题 5：密码哈希算法不安全

**位置**：[security.py:12-18](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/security.py#L12-L18)

```python
def hash_password(raw_password: str) -> str:
    payload = f"{raw_password}:{settings.secret_key}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
```

**问题描述**：使用单一固定盐（`settings.secret_key`）+ SHA256 做密码哈希，存在以下问题：
- SHA256 是快速哈希函数，GPU 每秒可尝试数十亿次，抗暴力破解能力极弱
- 所有用户共用同一个盐，一旦数据库泄露，攻击者可使用预计算彩虹表批量破解
- 无工作因子/迭代次数配置

**修复建议**：使用 `bcrypt` 或 `argon2-cffi` 等专用密码哈希库：
```python
# pip install bcrypt
import bcrypt

def hash_password(raw_password: str) -> str:
    return bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

def verify_password(raw_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(raw_password.encode("utf-8"), hashed_password.encode("utf-8"))
```
**注意**：切换算法后需做迁移兼容（可在哈希前加版本前缀，登录时自动升级旧哈希）。

---

#### 问题 6：下游鉴权未校验 JWT 中角色与数据库一致性

**位置**：[dependencies.py:36-44](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/dependencies.py#L36-L44)

**问题描述**：`get_current_user` 从 JWT 取出 `role` 但完全没有使用，而是依赖从数据库查出的 `user.role`。虽然这在权限判断上是安全的（`require_roles` 使用 `current_user.role` 即数据库值），但 JWT 载荷中的过期角色信息可能导致依赖 `payload["role"]` 的潜在逻辑出错，且缺少纵深防御。

**修复建议**：在 `get_current_user` 中增加角色一致性校验：
```python
token_role = payload.get("role")
if token_role != user.role.value:
    raise HTTPException(status_code=401, detail="令牌角色信息异常，请重新登录")
```

---

### 🟢 低危问题 / 优化建议

#### 问题 7：无登录失败限制与账户锁定机制

**问题描述**：Web 登录接口无任何暴力破解防护，攻击者可无限次尝试密码。

**修复建议**：
- 引入 Redis/内存缓存记录 IP/用户名的失败次数
- 连续失败 5 次后锁定账户 15 分钟
- 或集成 CAPTCHA 人机验证

---

#### 问题 8：JWT 无刷新机制

**问题描述**：Access Token 一旦签发在过期前无法撤销（虽然 `get_current_user` 每次查库检查 `is_active` 可封禁用户，但无法阻止已签发的 token 在过期前被用于正常权限的接口访问），且无 Refresh Token 机制，过期后必须重新登录。

**修复建议**：实现双 token 方案（access_token 短有效期 + refresh_token 长有效期），并增加 token 黑名单/版本号机制支持主动注销。

---

#### 问题 9：fake_wechat_openid 为模拟实现

**位置**：[security.py:43-44](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/security.py#L43-L44)

**问题描述**：当前是开发用的模拟 openid 生成逻辑，生产环境必须替换为调用微信官方 `code2session` 接口，否则无法保证 openid 的真实性和唯一性。

**修复建议**：生产环境使用微信 API：
```python
import httpx

async def get_wechat_openid(code: str) -> str:
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": settings.wechat_appid,
        "secret": settings.wechat_secret,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        data = resp.json()
        if "openid" not in data:
            raise HTTPException(status_code=401, detail="微信登录凭证无效")
        return data["openid"]
```

---

#### 问题 10：audit 装饰器为空实现

**位置**：[dependencies.py:56-65](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/dependencies.py#L56-L65)

**问题描述**：审计装饰器仅设置了函数属性，但没有实际记录日志逻辑。需补充审计日志持久化到 `audit_logs` 表的实现。

---

## 五、修复优先级总结

| 优先级 | 漏洞/问题 | 影响 |
|--------|-----------|------|
| P0 立即修复 | 家长登录无身份验证（漏洞2） | 任意家长账户接管，大规模学生隐私泄露 |
| P0 立即修复 | OpenID 可被恶意覆盖（漏洞3） | 账户持续劫持，原用户无法登录 |
| P1 尽快修复 | JWT role 来源不可信（漏洞1） | 潜在越权风险，与安全最佳实践冲突 |
| P1 尽快修复 | 密码哈希算法弱（问题5） | 数据库泄露后密码极易被破解 |
| P2 计划修复 | 登录枚举风险（问题4） | 用户信息泄露 |
| P2 计划修复 | JWT 角色一致性校验（问题6） | 纵深防御缺失 |
| P3 后续优化 | 暴力破解防护、Token刷新机制、微信API对接、审计实现 | 安全加固 |

---

## 六、关键代码引用索引

| 文件 | 功能 |
|------|------|
| [auth.py](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py) | 登录路由：Web登录、微信登录、获取当前用户 |
| [security.py](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/security.py) | 密码哈希、JWT签发/解码、模拟OpenID生成 |
| [dependencies.py](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/dependencies.py) | DB会话、当前用户获取、角色权限装饰器、审计装饰器 |
| [models.py](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/models.py) | User/UserRole/StudentProfile/ParentStudentRelation 数据模型 |
