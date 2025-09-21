#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信对话API接口
提供FastAPI路由供前端调用
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio

from agents_system.agents.wechat_conversation import wechat_agent, WechatMessage

router = APIRouter(prefix="/wechat", tags=["wechat"])

class WechatMessageRequest(BaseModel):
    """微信消息请求模型"""
    user_id: str
    message: str
    zhong_can_wechat: Optional[str] = None
    new_model_reply: bool = False

class WechatMessageResponse(BaseModel):
    """微信消息响应模型"""
    user_id: str
    user_message: str
    bot_response: str
    chat_status: int
    error: Optional[str] = None

class ChatHistoryResponse(BaseModel):
    """聊天历史响应模型"""
    user_id: str
    history: List[Dict[str, str]]

class ResetResponse(BaseModel):
    """重置响应模型"""
    status: str
    message: str

@router.post("/message", response_model=WechatMessageResponse)
async def process_wechat_message(request: WechatMessageRequest):
    """
    处理微信消息
    """
    try:
        message = WechatMessage(
            user_id=request.user_id,
            message=request.message,
            zhong_can_wechat=request.zhong_can_wechat,
            new_model_reply=request.new_model_reply
        )
        
        result = await wechat_agent.process_message(message)
        return WechatMessageResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{user_id}", response_model=ChatHistoryResponse)
async def get_chat_history(user_id: str):
    """
    获取聊天历史
    """
    try:
        history = wechat_agent.get_chat_history(user_id)
        return ChatHistoryResponse(user_id=user_id, history=history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset/{user_id}", response_model=ResetResponse)
async def reset_chat(user_id: str):
    """
    重置聊天
    """
    try:
        result = await wechat_agent.reset_chat(user_id)
        return ResetResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users")
async def list_test_users():
    """
    列出测试用户
    """
    return {
        "users": [
            {"user_id": "test_user_1", "nickname": "测试达人1", "type": "new"},
            {"user_id": "test_user_2", "nickname": "测试达人2", "type": "cooperative"}
        ]
    }