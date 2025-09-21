 # 微信对话智能体模块

## 简介

本模块是基于Java WechatReplyService重构的Python版本，实现了轻量级的微信对话处理功能。该模块不依赖数据库和消息队列，所有状态均保存在内存中，便于快速部署和测试。

## 功能特性

1. **双模型支持**：
   - 旧版聊天模型：基于历史对话的简单聊天处理
   - 新版聊天模型：包含流程判断、对话回复和智能问答三种处理方式

2. **用户类型区分**：
   - 新用户：首次询价处理流程
   - 合作用户：二次议价处理流程

3. **内存状态管理**：
   - 用户信息管理
   - 对话历史记录
   - 提示词模板管理

4. **RESTful API接口**：
   - 消息处理接口
   - 对话历史查询接口
   - 对话重置接口

## 核心组件

### WechatConversationAgent
主要的业务逻辑处理类，包含以下方法：

- `process_message()`: 处理微信消息的核心方法
- `_handle_first_inquiry()`: 处理首次询价逻辑
- `_handle_second_bargaining()`: 处理二次议价逻辑
- `_old_chat_model()`: 旧版聊天模型处理
- `_new_chat_model()`: 新版聊天模型处理

### 数据模型

- `WechatMessage`: 微信消息模型
- `UserResource`: 用户资源模型
- `ChatRecord`: 聊天记录模型
- `PromptTemplate`: 提示词模板模型

### 内存存储

`InMemoryStorage` 类提供了内存中的数据存储功能，替代了原Java版本中的数据库和Redis依赖。

## API接口

### 发送消息
```
POST /wechat/message
```

请求体：
```json
{
  "user_id": "test_user_1",
  "message": "你好，想了解一下合作的事情",
  "new_model_reply": true
}
```

响应：
```json
{
  "user_id": "test_user_1",
  "user_message": "你好，想了解一下合作的事情",
  "bot_response": "您好！很高兴为您介绍我们的合作机会...",
  "chat_status": 0
}
```

### 获取对话历史
```
GET /wechat/history/{user_id}
```

### 重置对话
```
POST /wechat/reset/{user_id}
```

## 使用方法

1. 启动服务：
```bash
cd agents_system
python main.py
```

2. 访问前端测试页面：
打开 `frontend/index.html` 文件

3. 或使用API工具（如Postman）直接调用API接口

## 设计理念

1. **轻量级**：无外部依赖，便于快速部署和测试
2. **模块化**：遵循项目现有的智能体架构模式
3. **兼容性**：保留原Java版本的核心业务逻辑
4. **可扩展**：易于添加新功能和改进

## 后续优化建议

1. 添加文件持久化支持
2. 集成Redis作为可选的缓存方案
3. 添加更丰富的提示词配置管理
4. 实现更复杂的用户状态管理