# Agents System

一个基于Python、FastAPI和Pydantic的智能体集合项目，用于模块化管理多个子智能体，统一处理功能。

## 项目结构

```
agents_system/
├── agents/                 # 智能体实现目录
│   ├── text_reviewer.py    # 文本审稿智能体
│   └── graphic_outline_agent.py  # 图文大纲生成智能体
├── config/                 # 配置文件目录
│   └── settings.py         # 系统配置
├── core/                   # 核心模块目录
│   ├── base_agent.py       # 智能体基类
│   ├── registry.py         # 智能体注册机制
│   └── feishu_callback.py  # 飞书回调处理
├── models/                 # 模型实现目录
│   ├── doubao.py           # 豆包大模型调用接口
│   ├── feishu.py           # 飞书API客户端
│   └── llm.py              # 大模型调用接口
├── utils/                  # 工具类目录
│   ├── ac_automaton.py     # AC自动机实现
│   ├── logger.py           # 日志模块
│   └── xlsx_parser.py      # Excel解析器
├── main.py                 # 项目入口文件
└── test_graphic_outline.py # 图文大纲生成智能体测试脚本
```

## 智能体介绍

### 1. 文本审稿智能体 (text_reviewer)

用于处理文本中的错别字和语言逻辑问题。

主要功能：
- 文本错别字检测与纠正
- 语言逻辑优化
- 违禁词检测与替换
- 飞书文档处理
- 飞书消息处理

API接口：
- `POST /text_reviewer/review` - 文本审稿
- `POST /text_reviewer/feishu/document` - 处理飞书文档
- `POST /text_reviewer/feishu/message` - 处理飞书消息

### 2. 图文大纲生成智能体 (graphic_outline)

用于生成图文内容的大纲并创建飞书电子表格。

主要功能：
- 调用大模型生成图文内容大纲
- 创建飞书电子表格
- 将大纲数据填充到电子表格中

API接口：
- `POST /graphic_outline/generate` - 生成图文大纲
- `POST /graphic_outline/feishu/sheet` - 创建飞书电子表格

工作流程：
1. 接收用户请求（主题、要求、风格等）
2. 调用大模型生成详细的大纲数据
3. 创建飞书电子表格
4. 将大纲数据结构化并填充到电子表格中
5. 返回电子表格链接和相关数据

## 环境配置

1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

2. 配置环境变量：
   创建 `.env` 文件并配置相关参数：
   ```
   # 项目配置
   PROJECT_NAME=Agents System
   PROJECT_VERSION=1.0.0
   DEBUG=True
   
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
   ```

## 运行项目

```bash
python main.py
```

## 测试智能体

### 测试图文大纲生成智能体

```bash
python test_graphic_outline.py
```

## API文档

项目运行后，可通过以下地址访问API文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 开发新智能体

1. 在 `agents/` 目录下创建新的智能体文件
2. 继承 `BaseAgent` 基类并实现抽象方法
3. 在 `main.py` 中注册新智能体
4. 实现具体业务逻辑