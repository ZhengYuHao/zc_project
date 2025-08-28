# Agents System

一个基于Python、FastAPI和Pydantic的智能体集合项目。每个子智能体单独处理一类功能，通过统一的注册机制进行管理。

## 项目结构

```
agents_system/
├── agents/              # 各个智能体模块
│   └── text_reviewer.py # 文本审稿智能体示例
├── core/                # 核心模块
│   ├── base_agent.py    # 智能体基类
│   └── registry.py      # 智能体注册机制
├── config/              # 配置模块
│   └── settings.py      # 系统配置
├── models/              # 大模型调用模块
│   └── llm.py           # 大模型接口
├── utils/               # 工具模块
│   └── logger.py        # 统一日志模块
├── main.py              # 应用入口
└── requirements.txt     # 项目依赖
```

## 功能特点

1. **模块化设计**：每个子智能体处理一类功能
2. **统一注册机制**：新增智能体自动注册到系统中
3. **统一日志模块**：包含模块名、行号、时间戳等信息
4. **大模型调用模块**：统一处理大模型调用逻辑
5. **统一配置管理**：系统配置集中管理

## 快速开始

1. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

2. 配置环境变量（可选）：
   创建 `.env` 文件并配置相关参数

3. 运行应用：
   ```
   python main.py
   ```

## API接口

- `GET /` - 根路径，显示系统信息
- `GET /health` - 健康检查
- `GET /agents/text_reviewer/info` - 获取文本审稿智能体信息
- `POST /agents/text_reviewer/review` - 文本审稿

## 智能体开发

要创建新的智能体：

1. 在 `agents/` 目录下创建新的智能体文件
2. 继承 [BaseAgent](file:///D:/python_codes/zc_project/agents_system/core/base_agent.py#L7-L35) 基类
3. 实现 [process()](file:///D:/python_codes/zc_project/agents_system/core/base_agent.py#L24-L35) 方法
4. 在 [main.py](file:///D:/python_codes/zc_project/agents_system/main.py) 中注册智能体

## 配置说明

通过 [settings.py](file:///D:/python_codes/zc_project/agents_system/config/settings.py) 文件或环境变量配置系统：

- `PROJECT_NAME`: 项目名称
- `PROJECT_VERSION`: 项目版本
- `DEBUG`: 调试模式
- `QWEN_API_KEY`: Qwen API密钥
- `QWEN_MODEL_NAME`: Qwen模型名称
- `LOG_LEVEL`: 日志级别
- `LOG_FILE`: 日志文件路径