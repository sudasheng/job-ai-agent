# AI 智能出题系统

基于 **LangGraph + RAG + DeepSeek** 的 AI 面试出题与评分系统。自动抓取岗位 JD，结合向量检索生成岗位定制化面试题，支持 10 轮答题和智能评分报告。

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户输入                              │
│              （岗位描述 / 招聘链接 / 答题）                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    LangGraph 主图（状态机）                     │
│                                                              │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐    │
│  │  岗位采集    │───▶│  RAG 检索     │───▶│  逐题生成     │    │
│  │  (ReAct)    │    │  + 出题       │    │  (1~10轮)    │    │
│  └──────┬──────┘    └──────────────┘    └──────┬───────┘    │
│         │                                       │            │
│         │ ReAct 循环：                           │ 10题完成    │
│         │ Thought→Action→Observation            ▼            │
│         │ 多轮追问直到获取完整 JD        ┌──────────────┐    │
│         └──────────────────────────────▶│  评分报告     │    │
│                                         └──────────────┘    │
└──────────────────────────────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  DeepSeek    │  │  ChromaDB    │  │  MySQL 8.0   │
│  LLM API     │  │  向量数据库   │  │  业务数据库   │
└──────────────┘  └──────────────┘  └──────────────┘
```

## 核心功能

| 功能 | 说明 |
|------|------|
| **ReAct 岗位采集** | 输入岗位描述或招聘链接，Agent 自动推理调用工具，多轮追问直到获取完整 JD |
| **RAG 智能出题** | 根据岗位 JD 检索面试题库，生成岗位定制化技术面试题 |
| **逐题生成** | 根据考生上一轮回答深度，动态生成下一道题（非批量生成） |
| **智能评分** | 10 轮答题完成后，生成包含总分、每题点评、优势/薄弱点的评分报告 |
| **会话持久化** | LangGraph MemorySaver 实现多轮对话断点恢复 |

## 技术栈

| 分类 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn + Jinja2 |
| AI Agent | LangGraph（主图）+ LangChain Agent（ReAct 子图） |
| LLM | DeepSeek API（推理 t=0.1，出题 t=0.4） |
| 向量数据库 | ChromaDB + 千问 text-embedding-v3（1024维） |
| 混合检索 | BM25（rank_bm25 + jieba）+ 向量检索，RRF 排名融合 |
| 业务数据库 | MySQL 8.0 + SQLAlchemy 异步 ORM |
| 爬虫 | Playwright + BeautifulSoup4 |
| 认证 | JWT（python-jose + passlib/bcrypt） |
| 部署 | Docker Compose + Uvicorn |

## 快速开始

### 1. 环境要求

- Python >= 3.11
- MySQL 8.0
- Node.js（可选，前端开发用）

### 2. 安装依赖

```bash
# 推荐使用 uv（更快）
uv sync

# 或 pip
pip install -e .
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入真实配置：
#   DEEPSEEK_API_KEY=your-deepseek-api-key
#   QWEN_API_KEY=your-qwen-api-key
#   MYSQL_PASSWORD=your-mysql-password
```

### 4. 启动数据库

```bash
docker compose up -d
```

### 5. 初始化数据库

```bash
alembic upgrade head
```

### 6. 启动服务

```bash
# Windows
start.bat

# 或直接运行
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000

## 项目结构

```
job-ai-agent/
├── app/
│   ├── agent/                  # AI Agent 核心
│   │   ├── agent.py            # Agent 门面（LangGraph 封装）
│   │   ├── main_graph.py       # LangGraph 主图（出题/评分流程）
│   │   ├── react_graph.py      # ReAct 采集子图（岗位信息获取）
│   │   ├── state.py            # 统一 InterviewState
│   │   └── skills/             # Agent 工具（爬虫/出题/评分）
│   ├── api/v1/                 # REST API 路由
│   │   ├── auth.py             # 认证接口
│   │   ├── jobs.py             # 岗位接口
│   │   ├── interview.py        # 面试接口
│   │   └── chat.py             # 对话接口
│   ├── core/                   # 基础设施
│   │   ├── config.py           # 配置管理（pydantic-settings）
│   │   ├── database.py         # 数据库连接
│   │   └── security.py         # JWT 认证
│   ├── crawler/                # Boss 直聘爬虫
│   ├── llm/                    # LLM 封装
│   │   ├── deepseek.py         # DeepSeek API
│   │   └── prompts.py          # 提示词模板
│   ├── models/                 # SQLAlchemy 数据模型
│   ├── rag/                    # RAG 检索增强
│   │   ├── document_loader.py  # 文档加载与切割
│   │   ├── embeddings.py       # 千问 Embedding
│   │   ├── vector_store.py     # ChromaDB 向量存储
│   │   ├── retriever.py        # 多路检索器
│   │   └── hybrid_retriever.py # BM25 + 向量混合检索
│   ├── schemas/                # Pydantic Schema
│   ├── services/               # 业务逻辑层
│   ├── templates/              # HTML 模板
│   └── main.py                 # FastAPI 应用入口
├── migrations/                 # Alembic 数据库迁移
├── static/                     # 静态资源
├── tests/                      # 测试
├── docker-compose.yml          # Docker 编排
├── alembic.ini                 # Alembic 配置
├── pyproject.toml              # 项目配置
└── .env.example                # 环境变量模板
```

## API 接口

### 面试流程（LangGraph）

```
POST /api/v1/interview/graph/start    # 开始/继续面试
GET  /api/v1/interview/graph/{id}     # 查询会话状态
POST /api/v1/interview/chat           # Agent 对话
GET  /api/v1/interview/report/{id}    # 获取评分报告
```

### 示例调用

```bash
# 输入岗位描述，开始面试
curl -X POST http://localhost:8000/api/v1/interview/graph/start \
  -H "Content-Type: application/json" \
  -d '{"user_input": "3年Python后端开发，FastAPI、Redis、MySQL"}'

# 返回第1题
# {"type": "question", "round": 1, "question": "...", "session_id": "xxx"}

# 答题，自动生成下一题
curl -X POST http://localhost:8000/api/v1/interview/graph/start \
  -H "Content-Type: application/json" \
  -d '{"user_input": "装饰器是一个接收函数作为参数的高阶函数...", "session_id": "xxx"}'
```

## 面试资料

项目 `interview_materials/` 目录包含向量数据库学习资料和面试准备文档。

## License

MIT
