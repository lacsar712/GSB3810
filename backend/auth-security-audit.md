# Web 登录与小程序登录鉴权路径分析及安全审计

## 一、完整执行路径

### 1.1 Web 登录流程（`POST /api/auth/web-login`）

**涉及文件**：[auth.py](backend/app/routers/auth.py) → [security.py](backend/app/security.py) → [dependencies.py](backend/app/dependencies.py)

```
客户端提交 { username, password }
        │
        ▼
① 按 username 查询 User 表
   └─ 未找到 → 401 "账号或密码错误"
        │
        ▼
② 角色白名单校验：user.role ∉ {ADMIN, TEACHER}
   └─ 不在白名单 → 403 "该角色不允许网页登录"
        │
        ▼
③ 密码校验：verify_password(password, user.password_hash)
   └─ 不匹配 → 401 "账号或密码错误"
        │
        ▼
④ 账号状态校验：not user.is_active
   └─ 已禁用 → 403 "账号已被禁用"
        │
        ▼
⑤ 签发 JWT：create_access_token(user.id, user.role.value)
   Payload = { sub: str(user_id), role: role_string, exp: 过期时间 }
   算法 = HS256，密钥 = settings.secret_key
        │
        ▼
⑥ 返回 AuthTokenResponse { access_token, token_type="bearer", user }
```

### 1.2 小程序登录流程（`POST /api/auth/wechat-login`）

**涉及文件**：[auth.py](backend/app/routers/auth.py) → [security.py](backend/app/security.py) → [models.py](backend/app/models.py)

```
客户端提交 { code, role, student_no }
        │
        ▼
① 角色归一化：_normalize_mini_role(payload.role)
   仅接受 STUDENT/PARENT（含中文"学生"/"家长"映射）
   └─ 其他角色 → 422 "角色仅支持 STUDENT 或 PARENT"
        │
        ▼
② 学号必填校验：student_no 为空
   └─ 为空 → 422 "请提供学号用于身份绑定"
        │
        ▼
③ 生成伪 OpenID：fake_wechat_openid(code)
   = "wx_" + SHA256(code)[:24]
        │
        ▼
④ 按 student_no 查询 StudentProfile
   └─ 未找到 → 404 "未找到对应学生档案"
        │
        ▼
⑤ 根据 role 解析关联 User：
   ├─ STUDENT → 查 User(id=student.user_id, role=STUDENT)
   └─ PARENT  → 查 ParentStudentRelation(student_id=student.id)
                取第一条关联 → 查 User(id=relation.parent_id, role=PARENT)
                └─ 无关联 → 404 "该学生暂未绑定家长"
        │
        ▼
⑥ 账号可用性校验：user is None or not user.is_active
   └─ 不可用 → 403 "账号不可用"
        │
        ▼
⑦ OpenID 绑定：
   - 若 openid 已被其他用户持有 → 清除旧绑定
   - 将 openid 写入当前 user.wechat_openid
   - db.commit()
        │
        ▼
⑧ 签发 JWT：create_access_token(user.id, role.value)
   Payload = { sub: str(user_id), role: role_string, exp: 过期时间 }
        │
        ▼
⑨ 返回 AuthTokenResponse { access_token, token_type="bearer", user }
```

### 1.3 下游接口鉴权流程

**涉及文件**：[dependencies.py](backend/app/dependencies.py)

```
请求携带 Authorization: Bearer <token>
        │
        ▼
① HTTPBearer 提取凭证
   └─ 无凭证 → 401 "未登录或登录已过期"
        │
        ▼
② decode_access_token(token)
   JWT 解码 + 签名验证 + 过期检查
   └─ 无效 → 401 "登录令牌无效"
        │
        ▼
③ 提取 payload.user_id
   └─ 缺失 → 401 "登录令牌缺少用户信息"
        │
        ▼
④ 按 user_id 查询 User 表
   └─ 未找到 or not is_active → 401 "当前账号不可用"
        │
        ▼
⑤ 返回 User ORM 对象（供下游使用）
        │
   ┌────┴────┐
   │         │
   ▼         ▼
get_current_user    require_roles(*roles)
（仅认证）           （认证 + 授权）
                    └─ user.role ∉ roles → 403 "权限不足"
```

**各路由的鉴权方式**：

| 路由前缀 | 鉴权依赖 | 角色限制 |
|-----------|----------|----------|
| `/api/auth/me` | `get_current_user` | 无角色限制（任何已认证用户） |
| `/api/admin/*` | `require_roles(ADMIN)` | 仅 ADMIN |
| `/api/teacher/*` | `require_roles(TEACHER, ADMIN)` + 细粒度权限 | TEACHER（需权限）+ ADMIN（免权限） |
| `/api/mini/*` | `get_current_user` + 业务层 `_resolve_student_for_mini` | 仅 STUDENT/PARENT（由业务逻辑保证） |

---

## 二、三条业务规则逐条核对

### 规则一：网页端仅 ADMIN/TEACHER 可登录

| 检查点 | 位置 | 实现 | 结论 |
|--------|------|------|------|
| 登录时角色白名单 | auth.py:34 | `user.role not in {UserRole.ADMIN, UserRole.TEACHER}` → 403 | ✅ 一致 |
| 下游 teacher 路由 | teacher.py:56 | `require_roles(UserRole.TEACHER, UserRole.ADMIN)` | ✅ 一致 |
| 下游 admin 路由 | admin.py:44 等 | `require_roles(UserRole.ADMIN)` | ✅ 一致 |
| **跨通道防护** | — | **JWT 未编码登录通道，无跨通道拦截** | ⚠️ 缺失 |

**结论**：登录入口的角色白名单正确，下游路由的角色守卫也正确。但 JWT 中未携带"登录通道"字段，理论上一个通过 `wechat-login` 获得的 STUDENT/PARENT token 可以被用于调用任何仅依赖 `get_current_user` 的接口；反之，ADMIN/TEACHER 的 token 也可访问 `/api/mini/*` 端点。当前 mini 路由靠 `_resolve_student_for_mini` 的业务逻辑做了软拦截（非 STUDENT/PARENT 会触发 403），但这是业务层兜底而非架构层硬隔离。

---

### 规则二：小程序端仅 STUDENT/PARENT 且需学号绑定校验

| 检查点 | 位置 | 实现 | 结论 |
|--------|------|------|------|
| 角色归一化仅允许 STUDENT/PARENT | auth.py:20-25 | `_normalize_mini_role` → ROLE_MAP 仅含两角色 | ✅ 一致 |
| 学号必填 | auth.py:51-53 | `student_no` 为空 → 422 | ✅ 一致 |
| 学号对应学生档案存在 | auth.py:56-58 | 查 StudentProfile → 404 | ✅ 一致 |
| STUDENT 绑定校验 | auth.py:60-61 | 查 User(id=student.user_id, role=STUDENT) | ✅ 一致 |
| PARENT 绑定校验 | auth.py:63-71 | 查 ParentStudentRelation → 查 User(role=PARENT) | ✅ 一致 |
| **schema 层 student_no 可选** | schemas.py:23 | `student_no: str \| None = Field(default=None)` | ⚠️ 不一致 |
| **mini 路由无角色守卫** | miniapp.py:47 等 | 仅用 `get_current_user`，无 `require_roles` | ⚠️ 缺失 |

**结论**：登录入口的学号绑定校验逻辑完整。但存在两个不一致：① `WechatLoginRequest` 的 `student_no` 在 schema 中声明为可选（`default=None`），与业务逻辑中的必填要求矛盾，应改为必填字段；② `/api/mini/*` 路由未使用 `require_roles(STUDENT, PARENT)` 做架构级角色守卫，仅靠 `_resolve_student_for_mini` 在业务层拦截，新增端点时容易遗漏。

---

### 规则三：禁用账号一律拒绝访问

| 检查点 | 位置 | 实现 | 结论 |
|--------|------|------|------|
| Web 登录时检查 | auth.py:40-41 | `not user.is_active` → 403 | ✅ 一致 |
| 微信登录时检查 | auth.py:73-74 | `user is None or not user.is_active` → 403 | ✅ 一致 |
| 下游每次请求检查 | dependencies.py:41 | `user is None or not user.is_active` → 401 | ✅ 一致 |
| **HTTP 状态码语义** | dependencies.py:41 | 禁用账号返回 401 而非 403 | ⚠️ 不准确 |

**结论**：禁用账号在登录入口和下游鉴权中均有检查，且下游是每次请求实时查库，不存在"禁用后旧 token 仍可用"的窗口。但下游 `get_current_user` 对禁用账号返回 401（Unauthorized），语义上应为 403（Forbidden）——用户身份已验证，只是账号被禁用，不属于"未认证"。

---

## 三、潜在越权与安全隐患

### 隐患 1：JWT 缺少登录通道标识，存在跨通道越权风险

**严重程度**：🔴 高

**现状**：JWT payload 仅含 `{sub, role, exp}`，不区分 token 来源（web-login 还是 wechat-login）。

**攻击场景**：
- 攻击者通过 `wechat-login` 获取 STUDENT token → 用该 token 调用 `/api/auth/me` 或未来新增的仅依赖 `get_current_user` 的接口
- 攻击者通过 `web-login` 获取 ADMIN token → 用该 token 调用 `/api/mini/*` 接口，绕过小程序端的学号绑定逻辑

**修复建议**：
```python
# security.py — 在 payload 中增加 channel 字段
def create_access_token(user_id: int, role: str, channel: str = "web") -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "channel": channel,   # "web" | "mini"
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)

# dependencies.py — 增加通道校验函数
def require_channel(channel: str):
    def checker(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    ):
        payload = decode_access_token(credentials.credentials)
        if payload and payload.get("channel") != channel:
            raise HTTPException(status_code=403, detail="不允许跨通道访问")
    return checker
```

---

### 隐患 2：密码哈希使用单轮 SHA-256，抗暴力破解能力极弱

**严重程度**：🔴 高

**现状**：[security.py:12-14](backend/app/security.py) 使用 `SHA256(password + secret_key)` 做密码哈希，仅一轮运算，无盐值分离。

**风险**：
- 相同密码的哈希值相同（无随机盐），易遭彩虹表攻击
- 单轮 SHA-256 在现代 GPU 上可达数十亿次/秒，暴力破解成本极低
- `secret_key` 既用于 JWT 签名又用于密码哈希，一旦泄露则全系统密码可被批量反推

**修复建议**：
```python
# 使用 passlib + bcrypt（需 pip install passlib[bcrypt]）
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(raw_password: str) -> str:
    return pwd_context.hash(raw_password)

def verify_password(raw_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(raw_password, hashed_password)
```

---

### 隐患 3：伪微信 OpenID 可被客户端预测和伪造

**严重程度**：🔴 高

**现状**：[security.py:43-44](backend/app/security.py) 的 `fake_wechat_openid` 是 `SHA256(code)[:24]` 的确定性映射，客户端可自行计算任意 code 对应的 openid。

**风险**：
- 攻击者可枚举 code 值，预先计算 openid，绕过微信身份验证
- 生产环境必须调用微信服务端 API（`jscode2session`）换取真实 openid

**修复建议**：
```python
import httpx

async def get_wechat_openid(code: str) -> str:
    url = (
        f"https://api.weixin.qq.com/sns/jscode2session"
        f"?appid={settings.wechat_appid}"
        f"&secret={settings.wechat_secret}"
        f"&js_code={code}"
        f"&grant_type=authorization_code"
    )
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        data = resp.json()
    if "openid" not in data:
        raise HTTPException(status_code=400, detail="微信登录失败")
    return data["openid"]
```

---

### 隐患 4：小程序路由缺少架构级角色守卫

**严重程度**：🟡 中

**现状**：`/api/mini/*` 所有端点仅依赖 `get_current_user`，角色限制完全由 `_resolve_student_for_mini` 在业务层实现。

**风险**：
- 新增端点时若忘记调用 `_resolve_student_for_mini`，则任何已认证用户（含 ADMIN/TEACHER）均可访问
- 架构上缺少"默认拒绝"的安全基线

**修复建议**：
```python
# dependencies.py — 增加小程序专用守卫
def require_mini_roles() -> Callable[[User], User]:
    return require_roles(UserRole.STUDENT, UserRole.PARENT)

# miniapp.py — 每个端点增加依赖
@router.get("/profile", response_model=MiniProfile)
def get_profile(
    student_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_mini_roles()),  # 架构级守卫
) -> MiniProfile:
    ...
```

---

### 隐患 5：`WechatLoginRequest.student_no` 在 schema 中为可选字段

**严重程度**：🟡 中

**现状**：[schemas.py:23](backend/app/schemas.py) 声明 `student_no: str | None = Field(default=None)`，但 [auth.py:51-53](backend/app/routers/auth.py) 在逻辑中强制要求非空。

**风险**：
- API 文档（OpenAPI/Swagger）会显示 `student_no` 为可选，误导前端开发者
- Pydantic 校验层不拦截空值，依赖手写逻辑兜底

**修复建议**：
```python
class WechatLoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=20)
    student_no: str = Field(min_length=1, max_length=30)  # 改为必填
```

---

### 隐患 6：登录错误消息泄露用户存在性与角色信息

**严重程度**：🟡 中

**现状**：
- Web 登录：角色不符返回"该角色不允许网页登录"（确认用户存在且角色非 ADMIN/TEACHER）
- 微信登录：学号不存在返回"未找到对应学生档案"（确认学号无效），无家长绑定返回"该学生暂未绑定家长"（确认学生存在）

**风险**：攻击者可通过不同错误消息枚举有效用户名/学号，为后续攻击提供信息。

**修复建议**：
```python
# Web 登录 — 统一错误消息
def web_login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    if user.role not in {UserRole.ADMIN, UserRole.TEACHER} or not user.is_active:
        raise HTTPException(status_code=401, detail="账号或密码错误")
    ...

# 微信登录 — 合并错误消息
    if student is None:
        raise HTTPException(status_code=401, detail="学号或角色信息无效")
```

---

### 隐患 7：禁用账号在下游鉴权中返回 401 而非 403

**严重程度**：🟢 低

**现状**：[dependencies.py:41-42](backend/app/dependencies.py) 对 `not user.is_active` 返回 `401 UNAUTHORIZED`。

**风险**：语义不准确，可能导致前端错误处理逻辑混淆（401 通常触发重新登录，但禁用账号重新登录也不会成功）。

**修复建议**：
```python
if user is None:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="当前账号不可用")
if not user.is_active:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
```

---

### 隐患 8：JWT 中 role 字段与数据库不同步

**严重程度**：🟢 低

**现状**：JWT 签发时将 `user.role.value` 写入 payload，但下游 `get_current_user` 完全忽略 JWT 中的 role，始终从数据库读取。当前 `require_roles` 检查的是 DB 中的 role，因此不存在实际越权。

**风险**：JWT 中的 role 字段成为冗余数据，可能误导开发者认为"role 从 token 读取"，未来若有人直接使用 `decode_access_token` 返回的 role 做授权判断，将引入越权漏洞。

**修复建议**：要么从 JWT payload 中移除 role 字段（减少攻击面），要么在 `get_current_user` 中增加 JWT role 与 DB role 的一致性校验（检测 token 伪造或角色变更）。

---

### 隐患 9：OpenID 绑定覆盖逻辑可能导致账号劫持

**严重程度**：🟡 中

**现状**：[auth.py:76-78](backend/app/routers/auth.py) 当新用户的 openid 与已有用户冲突时，直接清除旧用户的 openid 绑定。

**风险**：
- 攻击者若能获取某用户的 code（或伪造 code），可将其 openid 强制绑定到自己的账号，导致原用户下次登录时 openid 匹配失败
- 在伪微信模式下，攻击者可构造任意 code 来计算 openid，实施针对性劫持

**修复建议**：
```python
existing = db.query(User).filter(User.wechat_openid == openid, User.id != user.id).first()
if existing:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="该微信已绑定其他账号，请先解绑"
    )
```

---

### 隐患 10：默认密钥硬编码且 Token 有效期过长

**严重程度**：🟡 中

**现状**：
- [config.py:9](backend/app/config.py) 默认 `secret_key = "replace-this-secret-key"`
- [config.py:10](backend/app/config.py) 默认 `access_token_expire_minutes = 720`（12 小时）

**风险**：
- 若部署时未修改 `.env` 中的 `secret_key`，则 JWT 签名密钥为公开已知值，任何人可伪造 token
- 12 小时的 token 有效期在账号被入侵后留有较大的攻击窗口

**修复建议**：
- 在应用启动时检测 `secret_key` 是否为默认值，若是则拒绝启动
- 将 token 有效期缩短至 2-4 小时，并实现 refresh token 机制
- 强制要求 `.env` 中配置随机生成的密钥

---

## 四、总结

| 业务规则 | 登录入口 | 下游鉴权 | 一致性 | 关键缺陷 |
|----------|----------|----------|--------|----------|
| 网页端仅 ADMIN/TEACHER | ✅ 角色白名单 | ✅ require_roles | ⚠️ 部分 | JWT 无通道标识，跨通道可越权 |
| 小程序仅 STUDENT/PARENT + 学号绑定 | ✅ 角色归一化 + 学号校验 | ⚠️ 仅业务层拦截 | ⚠️ 部分 | schema 可选、路由无架构级守卫 |
| 禁用账号一律拒绝 | ✅ 登录时检查 | ✅ 每次请求查库 | ✅ 基本一致 | 状态码语义不准确（401 vs 403） |

**最高优先级修复项**：
1. 引入 bcrypt/argon2 替换 SHA-256 密码哈希
2. JWT 增加 channel 字段并在下游校验
3. 生产环境接入微信 jscode2session API
4. 小程序路由增加 `require_roles(STUDENT, PARENT)` 架构级守卫
5. 启动时校验 secret_key 非默认值
