# Job AI Agent - 部署文档

## 环境要求

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| Windows | Windows 10/11 64-bit | 或 Windows Server 2019+ |
| Python | >= 3.11 | [下载](https://www.python.org/downloads/) |
| Docker Desktop | 最新版 | [下载](https://www.docker.com/products/docker-desktop/) |
| Git | 任意版本 | 可选，用于版本管理 |

此外需要以下 API Key（在 [.env](file:///c:/Users/32964/Documents/trae_projects/job-ai-agent/.env.example) 中配置）：

| 服务 | 获取地址 |
|------|----------|
| DeepSeek API Key | [platform.deepseek.com](https://platform.deepseek.com/) |
| 千问 (DashScope) API Key | [dashscope.aliyun.com](https://dashscope.aliyun.com/) |

---

## 快速部署（Windows）

### 方式一：一键部署（推荐）

在项目根目录下打开 **命令提示符（cmd）** 或双击脚本，执行：

```cmd
:: 首次部署
deploy.bat

:: 开发模式（启用热重载 + dev 依赖）
deploy.bat dev

:: 跳过 Docker（使用已有 MySQL）
deploy.bat skip
```

脚本会自动完成：
1. 检查 Python 3.11+ 和 Docker 环境
2. 创建 `.venv` 虚拟环境
3. 安装项目依赖 + Playwright Chromium 浏览器
4. 从 `.env.example` 创建 `.env` 配置文件
5. 启动 Docker MySQL 8.0 容器（含自动建库）
6. 初始化数据库表
7. 启动 FastAPI 应用

### 方式二：手动部署

```cmd
:: 1. 创建虚拟环境
python -m venv .venv
call .venv\Scripts\activate.bat

:: 2. 安装依赖
pip install -e .
playwright install chromium

:: 3. 配置环境变量
copy .env.example .env
:: 编辑 .env 填入 DEEPSEEK_API_KEY 和 QWEN_API_KEY

:: 4. 启动 MySQL
docker compose up -d mysql

:: 5. 初始化数据库
python -c "import asyncio; from app.core.database import init_db; asyncio.run(init_db())"

:: 6. 启动应用
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 日常使用

### 启动

```cmd
:: 正常启动
start.bat

:: 开发模式（热重载）
start.bat dev
```

### 停止

```cmd
:: 停止 MySQL 容器（保留数据）
stop.bat

:: 停止并清除所有数据
stop.bat clean
```

应用本身通过 `Ctrl+C` 停止。

---

## 访问地址

| 服务 | 地址 |
|------|------|
| 前端页面 | http://localhost:8000 |
| 岗位搜索 | http://localhost:8000/job-search |
| 面试练习 | http://localhost:8000/interview |
| AI 聊天 | http://localhost:8000/chat |
| 登录注册 | http://localhost:8000/login |
| Swagger API 文档 | http://localhost:8000/api/docs |
| ReDoc API 文档 | http://localhost:8000/api/redoc |
| OpenAPI JSON | http://localhost:8000/api/openapi.json |

---

## 目录结构

```
job-ai-agent/
├── deploy.bat               # 一键部署脚本
├── start.bat                # 启动脚本
├── stop.bat                 # 停止脚本
├── docker-compose.yml      # MySQL 容器编排
├── pyproject.toml           # 项目依赖定义
├── .env.example             # 环境变量模板
├── .env                     # 实际环境变量（需自行创建）
├── .venv/                   # Python 虚拟环境（自动创建）
├── migrations/init.sql      # 数据库初始化 SQL
├── data/                    # 运行时数据（自动创建）
│   ├── chroma/              # ChromaDB 向量数据
│   ├── cookies/             # Playwright Cookie
│   └── logs/                # 应用日志
├── app/                     # 应用源码
├── static/                  # 静态资源
└── tests/                   # 测试
```

---

## 配置说明

编辑 `.env` 文件，关键配置项：

```ini
# ---------- 必填 ----------
DEEPSEEK_API_KEY=sk-xxxxxxxx          # DeepSeek API Key
QWEN_API_KEY=sk-xxxxxxxx              # 千问 API Key

# ---------- 数据库 ----------
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root123456
MYSQL_DATABASE=job_ai_agent

# ---------- 可选 ----------
APP_DEBUG=true                         # 开发模式
APP_PORT=8000                          # 应用端口
CHROMA_PERSIST_DIR=./data/chroma       # 向量库存储路径
PLAYWRIGHT_HEADLESS=false              # 浏览器是否无头模式
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60     # Token 过期时间
```

---

## Docker 容器管理

```cmd
:: 查看 MySQL 容器状态
docker ps --filter "name=job-ai-agent-mysql"

:: 查看 MySQL 日志
docker logs job-ai-agent-mysql

:: 进入 MySQL 命令行
docker exec -it job-ai-agent-mysql mysql -uroot -proot123456 job_ai_agent

:: 重启 MySQL
docker restart job-ai-agent-mysql

:: 完全清除（含数据）
docker compose down -v
```

---

## 常见问题

### 1. 中文乱码

如果 cmd 窗口中文显示乱码，执行一次 `chcp 65001` 切换为 UTF-8 编码。三个脚本已内置此命令。

### 2. Docker 未运行

确保 Docker Desktop 已启动（系统托盘应有 Docker 图标）。如果使用 WSL2 后端，确保 WSL2 已安装。

### 3. MySQL 端口冲突

如果本地已有 MySQL 占用 3306 端口，修改 `.env` 中的 `MYSQL_PORT` 为其他端口（如 3307），同时修改 `docker-compose.yml` 的端口映射。

### 4. Playwright 浏览器安装失败

```cmd
:: 手动安装
call .venv\Scripts\activate.bat
playwright install chromium
```

### 5. 数据库连接失败

- 检查 Docker MySQL 是否正常运行：`docker ps`
- 等待 MySQL 完全启动（首次启动约需 30 秒）
- 确认 `.env` 中数据库配置与 Docker 容器配置一致

---

## 生产环境注意事项

1. 将 `APP_DEBUG` 设为 `false`
2. 更换 `APP_SECRET_KEY` 和 `JWT_SECRET_KEY` 为强随机字符串
3. 配置 `CORS_ORIGINS` 为实际前端域名
4. 使用 Nginx 反向代理，配置 HTTPS
5. 配置 MySQL 数据备份策略
6. 使用 `uvicorn` + `gunicorn` 多 worker 模式
7. 考虑使用 Redis 缓存 Session 和频繁查询
8. 配置日志收集（ELK / Loki）