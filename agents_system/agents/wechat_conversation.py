#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信对话智能体模块
实现类似Java WechatReplyService的功能，但采用轻量级设计
"""

import json
import logging
import sys
import os
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 修复导入问题
from models.doubao import DoubaoModel
from config.settings import settings

logger = logging.getLogger(__name__)


class WechatMessage(BaseModel):
    """微信消息模型"""
    user_id: str
    message: str
    zhong_can_wechat: Optional[str] = None
    new_model_reply: bool = False
    message_time: str = ""


class UserResource(BaseModel):
    """用户资源模型"""
    user_id: str
    nickname: str
    project_name: str
    chat_status: int  # 0: 进行中, 1: 已结束
    wechat_add_status: str
    user_type: str  # "new" 或 "cooperative"
    cooperation_time: Optional[str] = None


class ChatRecord(BaseModel):
    """聊天记录模型"""
    id: str
    user_id: str
    message: str
    message_reply: Optional[str] = None
    message_time: str
    message_type: str  # "user" 或 "assistant"


class PromptTemplate(BaseModel):
    """提示词模板模型"""
    prompt_type: str
    step: str
    prompt_word: str
    model: str = "doubao"
    model_params: Dict[str, Any] = {}


class InMemoryStorage:
    """内存存储管理器，替代数据库和Redis"""
    
    def __init__(self):
        self.users: Dict[str, UserResource] = {}
        self.chat_histories: Dict[str, List[ChatRecord]] = {}
        self.prompts: Dict[str, PromptTemplate] = {}
        self._load_default_prompts()
    
    def _load_default_prompts(self):
        """加载默认提示词"""
        default_prompts = [
            PromptTemplate(
                prompt_type="建联微信智能体",
                step="开场语",
                prompt_word="宝子你好～辛苦确认一下这个主页链接是不是你呀～ {user_link} 这边有个小红书广告要跟你合作"
            ),
            PromptTemplate(
                prompt_type="WechatReply",
                step="自动聊天",
                prompt_word="""你是一位专业的小红书合作商务，正在与达人沟通合作事宜。
                
                当前用户: {name}
                合作产品: {product}
                
                历史对话记录:
                {history}
                
                当前用户消息: {input}
                
                请根据历史对话和当前消息，给出合适的回复。回复应专业、友好，推动合作进程。
                如果合作已经完成，请在回复中包含"chatEnd:true"。
                """
            ),
            PromptTemplate(
                prompt_type="WechatReply",
                step="1统筹智能体-提示词（流程优先版）",
                prompt_word="""你是一个流程判断专家，请分析用户输入并判断应该采用哪种处理流程：

                用户输入：{input}
                
                请只回复以下两种结果之一：
                000 - 对话流程
                001 - 问答流程
                """
            ),
            PromptTemplate(
                prompt_type="WechatReply",
                step="2对话回复-提示词",
                prompt_word="""你是一个专业的小红书合作商务，请继续与达人进行对话沟通：

                产品信息: {product}
                达人昵称: {name}
                
                对话历史:
                {outputList}
                
                当前消息: {input}
                
                请继续对话，推进合作进程。
                """
            ),
            PromptTemplate(
                prompt_type="WechatReply",
                step="3智能问答系统规范-提示词",
                prompt_word="""你是一个智能问答系统，请回答达人关于合作的相关问题：

                产品信息: {production}
                
                对话历史:
                {conversation}
                
                当前问题: {input}
                
                请提供准确、专业的回答。
                """
            )
        ]
        
        for prompt in default_prompts:
            key = f"{prompt.prompt_type}:{prompt.step}"
            self.prompts[key] = prompt
    
    def get_user(self, user_id: str) -> Optional[UserResource]:
        """获取用户信息"""
        return self.users.get(user_id)
    
    def save_user(self, user: UserResource):
        """保存用户信息"""
        self.users[user.user_id] = user
    
    def get_prompt(self, prompt_type: str, step: str) -> Optional[PromptTemplate]:
        """获取提示词模板"""
        key = f"{prompt_type}:{step}"
        return self.prompts.get(key)
    
    def save_chat_record(self, record: ChatRecord):
        """保存聊天记录"""
        if record.user_id not in self.chat_histories:
            self.chat_histories[record.user_id] = []
        self.chat_histories[record.user_id].append(record)
    
    def get_chat_history(self, user_id: str, limit: int = 20) -> List[ChatRecord]:
        """获取聊天历史"""
        records = self.chat_histories.get(user_id, [])
        return records[-limit:] if len(records) > limit else records


class WechatConversationAgent:
    """微信对话智能体"""
    
    def __init__(self):
        self.storage = InMemoryStorage()
        self.llm = DoubaoModel()
        self.settings = settings
        
        # 初始化一些测试用户数据
        self._init_test_users()
    
    def _init_test_users(self):
        """初始化测试用户数据"""
        test_users = [
            UserResource(
                user_id="test_user_1",
                nickname="测试达人1",
                project_name="美妆产品A",
                chat_status=0,
                wechat_add_status="success",
                user_type="new"
            ),
            UserResource(
                user_id="test_user_2",
                nickname="测试达人2",
                project_name="数码产品B",
                chat_status=0,
                wechat_add_status="success",
                user_type="cooperative",
                cooperation_time=datetime.now().isoformat()
            )
        ]
        
        for user in test_users:
            self.storage.save_user(user)
    
    async def process_message(self, message: WechatMessage) -> Dict[str, Any]:
        """
        处理微信消息的核心方法
        替代Java中的 saveAndReply2 方法
        """
        logger.info(f"Processing message from user {message.user_id}: {message.message}")
        
        try:
            user = self.storage.get_user(message.user_id)
            if not user:
                logger.warning(f"User {message.user_id} not found")
                return {
                    "user_id": message.user_id,
                    "user_message": message.message,
                    "bot_response": "未找到对应用户信息",
                    "chat_status": 0
                }
            
            # 根据用户类型选择处理逻辑
            if user.user_type == "cooperative":
                response = await self._handle_second_bargaining(message, user)
            else:
                response = await self._handle_first_inquiry(message, user)
            
            # 保存聊天记录
            self._save_conversation(message, response, user)
            
            return {
                "user_id": message.user_id,
                "user_message": message.message,
                "bot_response": response,
                "chat_status": user.chat_status
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return {
                "user_id": message.user_id,
                "user_message": message.message,
                "bot_response": "处理消息时发生错误，请稍后重试",
                "chat_status": 0,
                "error": str(e)
            }
    
    async def _handle_first_inquiry(self, message: WechatMessage, user: UserResource) -> str:
        """
        处理首次询价逻辑
        替代Java中的 getWechatRecord_1 方法
        """
        # 是否重置会话
        if message.message.strip() == "重置":
            self._reset_conversation(user.user_id)
            user.chat_status = 0
            self.storage.save_user(user)
            return self._generate_opening_message(user)
        
        # 如果是问候消息
        if self._is_greeting(message.message):
            return self._generate_opening_message(user)
        
        # 根据模型类型选择处理方式
        if message.new_model_reply:
            return await self._new_chat_model(message, user)
        else:
            return await self._old_chat_model(message, user)
    
    async def _handle_second_bargaining(self, message: WechatMessage, user: UserResource) -> str:
        """
        处理二次议价逻辑
        替代Java中的 getWechatRecord_2 方法
        """
        # 获取合作后的聊天记录
        chat_history = self.storage.get_chat_history(user.user_id)
        
        # 简化处理，实际应根据历史记录生成议价回复
        response = f"亲爱的{user.nickname}，关于之前的合作价格，我们这边可以适当调整。您觉得{user.project_name}的合作预算大概在什么范围呢？"
        
        return response
    
    async def _old_chat_model(self, message: WechatMessage, user: UserResource) -> str:
        """
        旧版聊天模型处理
        替代Java中的 oldChat 方法
        """
        try:
            # 构建聊天历史
            chat_history = self.storage.get_chat_history(user.user_id, 10)
            history_text = "\n".join([
                f"{'用户' if record.message_type == 'user' else '助手'}: {record.message}" 
                for record in chat_history
            ])
            
            # 获取提示词
            prompt_template = self.storage.get_prompt("WechatReply", "自动聊天")
            if not prompt_template:
                return "系统提示词未配置"
            
            # 格式化提示词
            prompt = prompt_template.prompt_word.format(
                name=user.nickname,
                product=user.project_name,
                history=history_text,
                input=message.message
            )
            
            # 调用AI模型
            response = await self.llm.generate_text(prompt)
            
            # 解析响应中的特殊标记
            if "chatEnd:true" in response:
                user.chat_status = 1
                self.storage.save_user(user)
            
            return response
            
        except Exception as e:
            logger.error(f"Old chat model error: {str(e)}", exc_info=True)
            return "抱歉，回复生成失败，请稍后重试"
    
    async def _new_chat_model(self, message: WechatMessage, user: UserResource) -> str:
        """
        新版聊天模型处理
        替代Java中的 newChat 方法
        """
        try:
            # 第一步：流程判断
            process_prompt = self.storage.get_prompt("WechatReply", "1统筹智能体-提示词（流程优先版）")
            if not process_prompt:
                return await self._old_chat_model(message, user)  # 回退到旧模型
            
            process_prompt_text = process_prompt.prompt_word.format(input=message.message)
            process_result = (await self.llm.generate_text(process_prompt_text)).strip()
            
            # 构建对话历史
            chat_history = self.storage.get_chat_history(user.user_id, 20)
            history_json = []
            for record in chat_history:
                if record.message_type == "user":
                    history_json.append(f'{{"role":"user","content":"{record.message}"}}')
                else:
                    history_json.append(f'{{"role":"assistant","content":"{record.message}"}}')
            
            history_text = "".join(history_json)
            
            # 根据流程判断结果选择处理方式
            if process_result == "000":
                # 对话流程
                dialog_prompt = self.storage.get_prompt("WechatReply", "2对话回复-提示词")
                if not dialog_prompt:
                    return await self._old_chat_model(message, user)
                
                dialog_prompt_text = dialog_prompt.prompt_word.format(
                    product=user.project_name,
                    name=user.nickname,
                    outputList=history_text,
                    input=message.message
                )
                
                response = await self.llm.generate_text(dialog_prompt_text)
                return response
                
            elif process_result == "001":
                # 问答流程
                qa_prompt = self.storage.get_prompt("WechatReply", "3智能问答系统规范-提示词")
                if not qa_prompt:
                    return await self._old_chat_model(message, user)
                
                qa_prompt_text = qa_prompt.prompt_word.format(
                    production=user.project_name,
                    conversation=history_text,
                    input=message.message
                )
                
                response = await self.llm.generate_text(qa_prompt_text)
                return response
            else:
                # 未知流程，回退到旧模型
                return await self._old_chat_model(message, user)
                
        except Exception as e:
            logger.error(f"New chat model error: {str(e)}", exc_info=True)
            return await self._old_chat_model(message, user)  # 发生错误时回退到旧模型
    
    def _generate_opening_message(self, user: UserResource) -> str:
        """生成开场白消息"""
        opening_prompt = self.storage.get_prompt("建联微信智能体", "开场语")
        if opening_prompt:
            return opening_prompt.prompt_word.format(
                userName=user.nickname,
                user_link=f"https://xiaohongshu.com/user/{user.user_id}"
            )
        else:
            return f"宝子你好～辛苦确认一下这个主页链接是不是你呀～ https://xiaohongshu.com/user/{user.user_id} 这边有个小红书广告要跟你合作"
    
    def _is_greeting(self, message: str) -> bool:
        """判断是否为问候消息"""
        greetings = [
            "我通过了你的朋友验证请求，现在我们可以开始聊天了",
            "我通过了你的好友验证请求，现在我们可以开始聊天了"
        ]
        
        return any(greeting in message for greeting in greetings)
    
    def _reset_conversation(self, user_id: str):
        """重置对话"""
        # 在简化版本中，我们不实际删除历史记录
        # 实际应用中可能需要更复杂的清理逻辑
        pass
    
    def _save_conversation(self, message: WechatMessage, response: str, user: UserResource):
        """保存对话记录"""
        # 保存用户消息
        user_message_record = ChatRecord(
            id=f"{user.user_id}_{datetime.now().timestamp()}_user",
            user_id=user.user_id,
            message=message.message,
            message_reply=None,
            message_time=datetime.now().isoformat(),
            message_type="user"
        )
        self.storage.save_chat_record(user_message_record)
        
        # 保存助手回复
        assistant_message_record = ChatRecord(
            id=f"{user.user_id}_{datetime.now().timestamp()}_assistant",
            user_id=user.user_id,
            message=response,
            message_reply=None,
            message_time=datetime.now().isoformat(),
            message_type="assistant"
        )
        self.storage.save_chat_record(assistant_message_record)
    
    def get_chat_history(self, user_id: str) -> List[Dict[str, str]]:
        """获取聊天历史"""
        records = self.storage.get_chat_history(user_id, 50)
        return [
            {
                "message": record.message,
                "message_type": record.message_type,
                "timestamp": record.message_time
            }
            for record in records
        ]
    
    async def reset_chat(self, user_id: str) -> Dict[str, str]:
        """重置聊天"""
        try:
            user = self.storage.get_user(user_id)
            if user:
                user.chat_status = 0
                self.storage.save_user(user)
                self._reset_conversation(user_id)
                return {"status": "success", "message": "聊天已重置"}
            else:
                return {"status": "error", "message": "用户不存在"}
        except Exception as e:
            logger.error(f"Error resetting chat: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}


# 实例化智能体
wechat_agent = WechatConversationAgent()


if __name__ == "__main__":
    # 简单测试
    async def main():
        test_message = WechatMessage(
            user_id="test_user_1",
            message="你好，我想了解一下合作的事情",
            new_model_reply=True
        )
        
        result = await wechat_agent.process_message(test_message)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    asyncio.run(main())