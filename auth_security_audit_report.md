# 身份认证与权限控制安全审计报告

## 一、执行路径全景梳理

### 1.1 Web 登录执行路径

Web 登录入口位于 [auth.py](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py) 的 `/api/auth/web-login` 端点，完整执行链路如下：

```
客户端 POST /api/auth/web-login
    ↓
[auth.py L28-L44] web_login() 函数
    ├─ 按 username 查询 User 表
    ├─ 校验角色必须为 ADMIN/TEACHER
    ├─ 调用 verify_password() 校验密码
    ├─ 校验 is_active 状态
    └─ 调用 create_access_token() 签发 JWT
            ↓
[security.py L21-L28] create_access_token()
    ├─ 构造 payload: {sub: user_id, role: role, exp: expire}
    └─ 使用 HS256 + secret_key 签发 Token
            ↓
返回 AuthTokenResponse (access_token + user 信息)
```

### 1.2 小程序登录执行路径

小程序登录入口位于 [auth.py](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py) 的 `/api/auth/wechat-login` 端点，完整执行链路如下：

```
客户端 POST /api/auth/wechat-login
    ↓
[auth.py L47-L84] wechat_login() 函数
    ├─ _normalize_mini_role() 规范化角色 (STUDENT/PARENT)
    ├─ 校验 student_no 非空
    ├─ fake_wechat_openid() 生成 openid (仅开发模拟)
    ├─ 按 student_no 查询 StudentProfile
    ├─ 根据角色查找用户:
    │   ├─ STUDENT: 通过 student.user_id 查找 User
    │   └─ PARENT: 通过 ParentStudentRelation 查找家长 User
    ├─ 校验用户存在且 is_active=True
    ├─ 处理 openid 绑定 (自动解绑其他账号)
    ├─ 更新 user.wechat_openid 并 commit
    └─ 调用 create_access_token() 签发 JWT
```

### 1.3 下游接口鉴权执行路径

下游接口通过 FastAPI 依赖注入实现鉴权，核心依赖位于 [dependencies.py](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/dependencies.py)：

```
请求受保护接口
    ↓
[依赖注入] get_current_user() 或 require_roles()
    ↓
[dependencies.py L25-L44] get_current_user()
    ├─ 从 Authorization Header 提取 Bearer Token
    ├─ 调用 decode_access_token() 解析 JWT
    ├─ 提取 user_id 和 role
    ├─ 按 user_id 查询数据库获取 User 对象
    └─ 校验 user.is_active == True
            ↓
[dependencies.py L47-L53] require_roles(*roles)
    └─ 校验 current_user.role in roles
            ↓
执行业务逻辑
```

**各模块接口使用的鉴权方式：**

| 模块 | 路由前缀 | 鉴权方式 | 允许角色 |
|------|---------|---------|---------|
| 认证模块 | `/api/auth` | 登录接口无鉴权，`/me` 用 `get_current_user` | 登录后所有有效用户 |
| 管理员模块 | `/api/admin` | `require_roles(UserRole.ADMIN)` | 仅 ADMIN |
| 教师模块 | `/api/teacher` | `require_teacher_permissions()` | ADMIN + 具备权限的 TEACHER |
| 小程序模块 | `/api/mini` | `get_current_user` + `_resolve_student_for_mini` | STUDENT + PARENT |

---

## 二、三条业务规则逐条核对

### 规则一：网页端仅 ADMIN/TEACHER 可登录

**规则描述：** 网页端（Web）登录接口仅允许 ADMIN 和 TEACHER 角色的用户登录。

**实现位置：** [auth.py L34-L35](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L34-L35)

```python
if user.role not in {UserRole.ADMIN, UserRole.TEACHER}:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该角色不允许网页登录")
```

**核对结论：✅ 基本一致，但存在隐患**

- ✅ 登录阶段确实校验了角色必须为 ADMIN 或 TEACHER
- ✅ 下游管理接口（`/api/admin`）使用 `require_roles(UserRole.ADMIN)` 限制
- ✅ 教师接口（`/api/teacher`）使用 `require_teacher_permissions()`，底层调用 `require_roles(UserRole.TEACHER, UserRole.ADMIN)`
- ⚠️ **隐患**：小程序接口（`/api/mini`）仅使用 `get_current_user` + 业务层角色判断，理论上 ADMIN/TEACHER 拿到的 Token 也能调用小程序接口（虽然会被 `_resolve_student_for_mini` 拒绝，但 Token 本身是有效的）
- ⚠️ **隐患**：`/api/auth/me` 接口所有登录用户都能访问，未区分登录渠道

---

### 规则二：小程序端仅 STUDENT/PARENT 且需学号绑定校验

**规则描述：** 小程序端登录仅允许 STUDENT 和 PARENT 角色，且必须通过学号进行身份绑定校验。

**实现位置：** [auth.py L47-L84](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L47-L84)

**核对结论：⚠️ 部分一致，存在多处风险**

#### 2.1 角色限制 — 基本实现

```python
role = _normalize_mini_role(payload.role)  # 仅允许 STUDENT/PARENT
```

- ✅ 登录时通过 `_normalize_mini_role` 限制角色只能是 STUDENT 或 PARENT
- ✅ 查询用户时分别加上了 `User.role == UserRole.STUDENT` 和 `User.role == UserRole.PARENT` 过滤

#### 2.2 学号绑定校验 — 实现存在缺陷

- ✅ 登录时强制要求 `student_no` 非空
- ✅ 通过 `student_no` 查询 `StudentProfile`，找不到则拒绝
- ✅ STUDENT 角色：通过 `student.user_id` 关联查找 User
- ✅ PARENT 角色：通过 `ParentStudentRelation` 关联查找家长 User

**❌ 严重缺陷：JWT 中角色与用户实际角色可能不一致**

```python
# auth.py L83
token = create_access_token(user.id, role.value)
```

这里传入的 `role` 是**前端请求参数中**的 `role`，而非数据库中 `user.role`。虽然查询时做了角色过滤（`User.role == UserRole.STUDENT`），但存在以下问题：

1. **PARENT 登录时的角色越权风险**：如果前端传入 `role=STUDENT`，但通过学号查到的学生档案关联的用户实际是 PARENT 角色——**这种情况不会发生**，因为 STUDENT 分支查询的是 `User.id == student.user_id AND User.role == UserRole.STUDENT`，角色不匹配会返回 None。

2. **JWT 角色声明与数据库角色脱节**：Token 中携带的 role 完全由登录时的参数决定，而非从数据库读取。如果后续有其他登录渠道或代码变更，可能导致 Token 角色与实际角色不一致。

3. **下游接口依赖 Token 中的 role 还是数据库中的 role？**

   查看 [dependencies.py](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/dependencies.py) 的 `get_current_user`：

   ```python
   # 解析 JWT 得到 user_id 和 role
   payload = decode_access_token(credentials.credentials)
   user_id = payload.get("user_id")
   # 但实际只用了 user_id 查库，返回完整 User 对象
   user = db.query(User).filter(User.id == int(user_id)).first()
   return user
   ```

   下游 `require_roles` 校验的是 `current_user.role`（**数据库中的角色**），而非 JWT 中的 role。这意味着：

   - ✅ **好消息**：鉴权最终以数据库角色为准，JWT 被篡改 role 不影响实际权限
   - ⚠️ **坏消息**：JWT 中的 role 字段形同虚设，增加了困惑和维护成本

#### 2.3 家长账号绑定学生的隐患

```python
# auth.py L63-L68
relation = (
    db.query(ParentStudentRelation)
    .filter(ParentStudentRelation.student_id == student.id)
    .order_by(ParentStudentRelation.id.asc())
    .first()
)
```

- ❌ **取第一个家长，而非验证当前登录的是哪个家长**：如果一个学生有多个家长，系统直接取 `id` 最小的那个家长账号登录，**完全没有验证请求者的身份**。
- ❌ **学号+角色=任意家长登录**：只要知道学号，任何人都可以以"家长"身份登录该学生的**第一个家长账号**，无需任何凭证验证。

---

### 规则三：禁用账号一律拒绝访问

**规则描述：** 被禁用的账号（`is_active=False`）在所有环节都应被拒绝访问。

**核对结论：✅ 基本一致，但存在登录时序和状态不一致问题**

#### 3.1 Web 登录校验

```python
# auth.py L40-L41
if not user.is_active:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
```

- ✅ 密码校验通过后才检查 is_active
- ⚠️ **时序问题**：先检查角色，再验证密码，最后检查 is_active。这意味着可以通过错误响应的差异来枚举用户存在性和角色信息（用户名枚举攻击）。

#### 3.2 小程序登录校验

```python
# auth.py L73-L74
if user is None or not user.is_active:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号不可用")
```

- ✅ 统一判断，用户不存在或禁用都返回相同错误

#### 3.3 Token 鉴权阶段校验

```python
# dependencies.py L41-L42
if user is None or not user.is_active:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="当前账号不可用")
```

- ✅ 每次请求都重新从数据库查询并校验 `is_active`
- ✅ 管理员禁用账号后，已登录的用户在下一次请求时会被拒绝

**小结：** 禁用账号的校验在三个关键节点（Web 登录、小程序登录、Token 鉴权）都有实现，符合业务规则。

---

## 三、潜在越权与安全隐患

### 隐患一：小程序登录无身份验证，学号即可登录任意账号

**严重程度：🔴 高危**

**位置：** [auth.py L47-L84](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L47-L84)

**问题描述：**
小程序登录仅通过 `code` 和 `student_no` 进行，但 `fake_wechat_openid(code)` 只是对 code 做 SHA256 哈希，**没有真正调用微信接口验证用户身份**。这意味着：

1. 任何人只要知道一个学生的学号，就可以构造任意 code 值登录该学生账号（STUDENT 角色）
2. 任何人只要知道一个学生的学号，就可以登录该学生的第一个家长账号（PARENT 角色）
3. 没有任何密码、短信验证码等第二因素验证

**攻击场景：**
- 攻击者通过学号列表批量登录学生/家长账号
- 攻击者查看任意学生的成绩、行为记录、通知等敏感信息

**修复建议：**
1. 接入真实的微信开放接口，通过 `code` 换取真实 `openid`
2. 首次绑定时需验证身份（如学生身份证号后六位、家长手机号验证码等）
3. 已绑定的账号后续登录通过 `openid` 直接匹配，不再需要学号

---

### 隐患二：密码哈希算法强度不足

**严重程度：🟠 中危**

**位置：** [security.py L12-L18](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/security.py#L12-L18)

**问题描述：**
```python
def hash_password(raw_password: str) -> str:
    payload = f"{raw_password}:{settings.secret_key}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
```

- 使用简单的 SHA256 + 静态盐（secret_key），而非专业的密码哈希算法
- 没有加盐（每个用户独立的盐）
- 没有迭代次数/计算成本控制
- 一旦数据库泄露，攻击者可通过彩虹表或 GPU 快速破解弱密码

**修复建议：**
使用 `bcrypt`、`argon2` 或 `pbkdf2_hmac` 等专业密码哈希算法：

```python
import bcrypt

def hash_password(raw_password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(raw_password.encode("utf-8"), salt).decode("utf-8")

def verify_password(raw_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(raw_password.encode("utf-8"), hashed_password.encode("utf-8"))
```

---

### 隐患三：JWT 签发角色与数据库角色脱节

**严重程度：🟡 低危（当前代码无直接危害，但设计不良）**

**位置：** [auth.py L43, L83](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L43)

**问题描述：**
```python
# Web 登录 - 从数据库读取 user.role
token = create_access_token(user.id, user.role.value)

# 小程序登录 - 使用请求参数中的 role
token = create_access_token(user.id, role.value)
```

虽然当前 `get_current_user` 最终以数据库角色为准，但 JWT 中仍携带 role 字段，且小程序登录时用的是请求参数中的角色而非数据库角色。这种不一致可能导致：

1. 维护者误以为 JWT 中的 role 是可信的，未来引入依赖 JWT role 的逻辑时引入漏洞
2. 代码语义混淆，增加理解成本

**修复建议：**
- 统一从数据库 `user.role` 读取角色后再签发 Token
- 或者移除 JWT 中的 role 字段（因为每次请求都会查库），减少冗余和混淆

---

### 隐患四：Web 登录存在用户名枚举风险

**严重程度：🟡 低危**

**位置：** [auth.py L30-L41](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L30-L41)

**问题描述：**
```python
user = db.query(User).filter(User.username == payload.username).first()
if user is None:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")

if user.role not in {UserRole.ADMIN, UserRole.TEACHER}:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该角色不允许网页登录")

if not verify_password(payload.password, user.password_hash):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")

if not user.is_active:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
```

不同的错误场景返回不同的 HTTP 状态码和错误信息：
- 用户不存在 → 401 "账号或密码错误"
- 角色不允许 → 403 "该角色不允许网页登录"
- 密码错误 → 401 "账号或密码错误"
- 账号禁用 → 403 "账号已被禁用"

攻击者可以通过状态码和错误消息区分：
1. 用户名是否存在
2. 用户角色类型（学生/家长 vs 教师/管理员）
3. 账号是否被禁用

**修复建议：**
统一所有认证失败场景的响应：

```python
# 所有失败都返回 401 和相同的错误信息
if user is None or user.role not in {UserRole.ADMIN, UserRole.TEACHER} or not verify_password(...) or not user.is_active:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")
```

同时建议添加登录失败次数限制和账号锁定机制。

---

### 隐患五：小程序家长登录直接取第一个家长，身份完全不验证

**严重程度：🔴 高危**

**位置：** [auth.py L63-L71](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/auth.py#L63-L71)

**问题描述：**
```python
relation = (
    db.query(ParentStudentRelation)
    .filter(ParentStudentRelation.student_id == student.id)
    .order_by(ParentStudentRelation.id.asc())
    .first()
)
```

当 `role=PARENT` 时，系统不验证请求者是哪位家长，直接取该学生的第一个家长关系。这意味着：

1. 只要知道学号，任何人都能登录该学生的**第一位家长**账号
2. 如果一个学生有多个家长，排在后面的家长永远无法通过小程序登录
3. 没有 openid 匹配逻辑（首次登录时 openid 是被写入的，而非用于验证）

**修复建议：**
1. 首次绑定：需要家长身份验证（手机号验证码、身份证号等）
2. 已绑定用户：通过微信 openid 直接查找对应的 User，无需通过学号
3. 学号仅用于首次绑定场景，且绑定后需记录绑定关系

---

### 隐患六：secret_key 默认值硬编码且强度不足

**严重程度：🟠 中危**

**位置：** [config.py L9](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/config.py#L9)

**问题描述：**
```python
secret_key: str = "replace-this-secret-key"
```

- 默认密钥是硬编码的弱口令
- 如果部署时忘记通过环境变量覆盖，所有 JWT 都可被伪造
- 密钥长度和熵值不足（建议至少 32 字节的随机字符串）

**修复建议：**
1. 增加启动时的密钥强度校验，弱密钥拒绝启动
2. 文档中明确要求使用环境变量设置强密钥
3. 建议使用 `secrets.token_urlsafe(32)` 生成的随机密钥

---

### 隐患七：JWT 缺少吊销机制

**严重程度：🟡 低危**

**问题描述：**
当前 JWT 一旦签发，在过期前始终有效。即使用户修改密码、账号被禁用（虽然 `get_current_user` 会查库校验 is_active，但 JWT 本身仍然有效），或者管理员怀疑 Token 泄露，都无法主动吊销 Token。

当前 `get_current_user` 每次都会查询数据库验证 `is_active`，所以**禁用账号能及时失效**，这一点做得不错。但其他场景（如密码修改后旧 Token 仍有效）仍有风险。

**修复建议：**
1. 对于高敏感操作，增加二次验证
2. 可考虑引入 Token 黑名单（Redis）实现主动吊销
3. 缩短 Token 有效期（当前 720 分钟=12 小时，可考虑更短）

---

### 隐患八：小程序接口缺少角色前置校验

**严重程度：🟡 低危**

**位置：** [miniapp.py](file:///e:/lzg/code/GSB0608/label-3810/GSB3810/backend/app/routers/miniapp.py)

**问题描述：**
小程序接口使用 `get_current_user` 而非 `require_roles`，然后在 `_resolve_student_for_mini` 中做角色判断。虽然功能上能拒绝非 STUDENT/PARENT 用户，但：

1. 每个接口都依赖 `_resolve_student_for_mini` 来间接校验角色，不够直观
2. 如果有新接口忘记调用 `_resolve_student_for_mini`，可能导致越权
3. 错误返回不一致（有的接口 403，有的 404）

**修复建议：**
增加小程序专用的角色校验依赖：

```python
def require_mini_user() -> Callable[[User], User]:
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in {UserRole.STUDENT, UserRole.PARENT}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅支持小程序用户访问")
        return current_user
    return checker
```

---

## 四、修复优先级与行动清单

### 高优先级（立即修复）

| # | 隐患 | 影响 |
|---|------|------|
| 1 | 小程序登录无身份验证，学号即可登录任意账号 | 数据泄露、账号盗用 |
| 2 | 小程序家长登录直接取第一个家长，身份不验证 | 越权访问他人账号 |
| 3 | 密码哈希算法强度不足（SHA256 + 静态盐） | 数据库泄露后密码批量破解 |

### 中优先级（近期修复）

| # | 隐患 | 影响 |
|---|------|------|
| 4 | secret_key 默认值弱且硬编码 | JWT 伪造风险 |
| 5 | JWT 角色与数据库角色脱节，设计不一致 | 维护风险，未来可能引入漏洞 |
| 6 | Web 登录存在用户名枚举风险 | 用户信息泄露 |

### 低优先级（规划优化）

| # | 隐患 | 影响 |
|---|------|------|
| 7 | JWT 缺少主动吊销机制 | Token 泄露后无法及时失效 |
| 8 | 小程序接口缺少统一角色前置校验 | 代码维护性差，新增接口易遗漏 |

---

## 五、总结

本项目的身份认证架构整体清晰，采用了 JWT + 数据库角色校验的模式，禁用账号的实时校验做得比较到位。但**小程序登录模块存在严重的身份验证缺失问题**，仅通过学号即可登录任意学生或家长账号，这是当前最大的安全隐患。

同时，密码哈希使用 SHA256 而非专业算法、默认密钥弱、登录错误信息可枚举等问题也需要关注。建议按照优先级逐步修复，优先解决小程序登录的身份验证问题。
