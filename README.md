# 高中教务管理系统 (label-3810)

## 🛠 技术栈
- Frontend: Vue 3 + Vite + Element Plus + Pinia + Vue Router + ECharts + Zod
- Backend: FastAPI + SQLAlchemy + Pydantic + JWT
- Database: MySQL 8.0
- Mini Program: WeChat Mini Program (WXML/WXSS/JS)

## 🚀 启动指南 (How to Run)
1. 确保 Docker Desktop 已启动。
2. 在根目录执行：`docker compose up --build`
3. 等待数据库健康检查通过，后端自动建表并写入演示数据。
4. 浏览器访问前端地址完成管理员或教师端登录。
5. 小程序端使用 `miniapp/` 导入微信开发者工具后运行。

## 🔗 服务地址 (Services)
- Frontend(Web): http://localhost:3810
- Backend Swagger: http://localhost:8810/docs
- Backend API Base: http://localhost:8810/api
- Backend Health: http://localhost:8810/api/health
- Database: localhost:13810 (user: school_user / pass: school_pass / db: school_db)
- MiniApp 源码: `miniapp/` (默认 API 基址 `http://127.0.0.1:8810/api`)

## 🧪 测试账号
- Admin(Web): `sys_admin / Admin@123456`
- Teacher(Web): `teacher_zhang / Teacher@123456`
- Student(MiniApp): 授权码任意字符串 + 学号 `S2025001`
- Parent(MiniApp): 授权码任意字符串 + 学号 `S2025001`

## ✅ Verification
1. 登录 `http://localhost:3810`，使用管理员账号进入“教师账号管理”，新增/禁用教师账号后刷新确认生效。
2. 登录教师端，进入“成绩管理发布”，创建考试、录入分数并发布，确认列表出现排名。
3. 进入“成绩分析可视化”，筛选学生后确认折线图、雷达图与班级均分图正常展示，并测试 CSV 导出。
4. 管理员进入“系统配置与备份”，执行“立即备份”并确认备份列表新增记录。
5. 微信开发者工具运行 `miniapp/`，学生或家长角色登录后检查通知、成绩、在校表现页面数据。

## 🐳 Docker 镜像源配置 (Docker Registry Configuration)

### 推荐配置（基于实际项目验证）

#### 1. Docker 镜像源
**使用官方 Docker Hub 镜像**（已验证稳定可用）

```yaml
services:
  db:
    image: mysql:8.0

  backend:
    build: ./backend
    # Dockerfile:
    # - python:3.11-slim

  frontend:
    build: ./frontend
    # Dockerfile:
    # - node:20-alpine (build)
    # - nginx:alpine (runtime)
```

#### 2. npm 依赖源
**使用淘宝镜像**（国内访问快）

已在 `frontend/Dockerfile` 中配置：
```dockerfile
RUN npm config set registry https://registry.npmmirror.com
```

#### 3. Python 依赖源
本项目保持默认 PyPI，若需加速可在构建环境中配置镜像源。
