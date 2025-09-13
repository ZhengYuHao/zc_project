# Agents System

一个基于 Python、FastAPI 和 Pydantic 构建的智能体集合框架，用于模块化管理和统一处理多个智能体功能。

## 目录结构

```
agents_system/
├── agents/                    # 智能体实现目录
│   ├── text_reviewer.py       # 文本审稿智能体
│   └── graphic_outline_agent.py  # 图文大纲生成智能体
├── config/                    # 配置文件目录
│   └── settings.py            # 系统配置
├── core/                      # 核心模块目录
│   ├── base_agent.py          # 智能体基类
│   ├── registry.py            # 智能体注册机制
│   ├── feishu_callback.py     # 飞书回调处理
│   ├── request_context.py     # 请求上下文管理
│   ├── request_middleware.py  # 请求中间件
│   └── task_processor.py      # 任务处理器
├── models/                    # 模型实现目录
│   ├── doubao.py              # 豆包大模型调用接口
│   ├── feishu.py              # 飞书API客户端
│   └── llm.py                 # 大模型调用接口
├── utils/                     # 工具类目录
│   ├── ac_automaton.py        # AC自动机实现
│   ├── logger.py              # 日志模块
│   ├── xlsx_parser.py         # Excel解析器
│   ├── cell_filler.py         # 表格单元填充器
│   ├── check_excel.py         # Excel检查工具
│   └── analyze_excel.py       # Excel分析工具
├── prohibited_words_output_v2/ # 违禁词库目录
├── main.py                    # 项目入口文件
└── test/                      # 测试文件目录
```

## 系统架构

本系统采用微服务风格的模块化架构，基于 FastAPI 构建 RESTful API，每个智能体作为独立模块注册并运行。

### 核心组件

1. **智能体系统 (Agents)**：系统的核心功能模块，每个智能体负责特定的业务逻辑
2. **核心模块 (Core)**：提供基础服务，包括智能体注册、请求处理、上下文管理等
3. **模型接口 (Models)**：封装外部服务调用，如大语言模型和飞书API
4. **工具库 (Utils)**：通用工具集合，包括日志、Excel处理、文本分析等
5. **配置管理 (Config)**：统一配置管理，支持环境变量配置

### 设计模式

- **模板方法模式**：通过 [BaseAgent](file:///E:/pyProject/zc_project/agents_system/core/base_agent.py#L12-L45) 基类定义抽象方法，具体智能体实现业务逻辑
- **插件式架构**：通过注册机制实现智能体的动态加载和管理
- **中间件模式**：使用中间件处理请求上下文、CORS等横切关注点

## 智能体介绍

### 1. 文本审稿智能体 (text_reviewer)

用于处理文本中的错别字和语言逻辑问题。

#### 主要功能：
- 文本错别字检测与纠正
- 语言逻辑优化
- 违禁词检测与替换
- 飞书文档处理
- 飞书消息处理

#### API接口：
- `POST /text_reviewer/review` - 文本审稿
- `POST /text_reviewer/feishu/document` - 处理飞书文档
- `POST /text_reviewer/feishu/message` - 处理飞书消息

### 2. 图文大纲生成智能体 (graphic_outline)

用于生成图文内容的大纲并创建飞书电子表格。

#### 主要功能：
- 调用大模型生成图文内容大纲
- 创建飞书电子表格
- 将大纲数据填充到电子表格中

#### API接口：
- `POST /graphic_outline/generate` - 生成图文大纲
- `POST /graphic_outline/feishu/sheet` - 创建飞书电子表格

#### 工作流程：
1. 接收用户请求（主题、要求、风格等）
2. 调用大模型生成详细的大纲数据
3. 创建飞书电子表格
4. 将大纲数据结构化并填充到电子表格中
5. 返回电子表格链接和相关数据

## 环境配置

### 1. 安装依赖：
```bash
pip install -r requirements.txt
```

### 2. 配置环境变量：
创建 `.env` 文件并配置相关参数：
```env
# 项目配置
PROJECT_NAME=Agents System
PROJECT_VERSION=1.0.0
DEBUG=True
HOST=0.0.0.0
PORT=8000

# 豆包大模型配置
DOUBAO_API_KEY=your_doubao_api_key
DOUBAO_MODEL_NAME=your_doubao_model_name

# 飞书配置
FEISHU_APP_ID=your_feishu_app_id
FEISHU_APP_SECRET=your_feishu_app_secret
FEISHU_VERIFY_TOKEN=your_feishu_verify_token
FEISHU_ENCRYPT_KEY=your_feishu_encrypt_key

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/agents_system.log

# 图文大纲智能体配置
GRAPHIC_OUTLINE_DEFAULT_STYLE=标准
GRAPHIC_OUTLINE_LLM_MODEL=doubao
GRAPHIC_OUTLINE_MAX_RETRIES=3
GRAPHIC_OUTLINE_TIMEOUT=30
GRAPHIC_OUTLINE_TEMPLATE_SPREADSHEET_TOKEN=your_template_spreadsheet_token
```

## 部署方式

### 本地运行：
```bash
python main.py
```

### Docker部署：
```bash
# 构建镜像
docker build -t agents_system .

# 运行容器
docker run -d -p 8847:8847 agents_system
```

### Docker Compose部署：
```bash
docker-compose up -d
```

## API文档

系统使用 FastAPI 构建，自带交互式 API 文档：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 技术栈

- **语言**: Python 3.13
- **Web框架**: FastAPI
- **数据验证**: Pydantic
- **异步HTTP客户端**: httpx
- **容器化**: Docker
- **API文档**: Swagger UI / ReDoc
- **日志**: Python内置logging模块
- **配置管理**: pydantic-settings

## 安全性

- 敏感配置信息通过环境变量管理
- 飞书回调验证来源合法性
- 请求ID追踪便于调试和监控
- 日志记录包含异常堆栈信息

## 扩展性

系统采用模块化设计，可以轻松添加新的智能体：

1. 继承 [BaseAgent](file:///E:/pyProject/zc_project/agents_system/core/base_agent.py#L12-L45) 基类
2. 实现抽象方法
3. 在 [main.py](file:///E:/pyProject/zc_project/agents_system/main.py) 中注册智能体
4. 添加对应路由和业务逻辑

## 日志与监控

系统提供完整的日志记录功能，包括：
- 请求追踪ID
- 错误堆栈信息
- 性能指标
- 外部服务调用记录

日志文件默认存储在 `logs/agents_system.log`