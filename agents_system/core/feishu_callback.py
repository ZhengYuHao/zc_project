from fastapi import APIRouter, Request, Header, HTTPException, Response
import sys
import os
import json
import asyncio
from typing import Dict, Any, Optional
from collections import defaultdict

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.feishu import get_feishu_client
from agents.text_reviewer import TextReviewerAgent
from utils.logger import get_logger
from config.settings import settings
from core.request_context import get_request_id

logger = get_logger(__name__)
router = APIRouter(prefix="/feishu")

# 全局实例
feishu_client = get_feishu_client()
text_reviewer_agent = TextReviewerAgent()

# 文档处理队列，用于防止同一文档并发处理
document_queues = defaultdict(asyncio.Queue)


async def process_document_task(document_id: str, event: Dict[Any, Any]):
    """
    处理文档任务
    
    Args:
        document_id: 文档ID
        event: 事件数据
    """
    # 获取当前请求ID
    request_id = get_request_id()
    logger.info(f"Queuing document processing task for {document_id} with request_id {request_id}")
    await document_queues[document_id].put(event)


@router.post("/callback")
async def feishu_callback(
    request: Request,
    request_timestamp: str = Header(None, alias="X-Li-TimeStamp"),
    request_nonce: str = Header(None, alias="X-Li-Nonce"),
    request_signature: str = Header(None, alias="X-Li-Signature")
):
    """
    飞书事件回调处理接口
    
    Args:
        request: HTTP请求对象
        request_timestamp: 请求时间戳
        request_nonce: 请求随机数
        request_signature: 请求签名
        
    Returns:
        回调处理结果
    """
    # 读取请求体
    body = await request.body()
    body_str = body.decode("utf-8")
    
    # 获取当前请求ID
    request_id = get_request_id()
    logger.info(f"Received Feishu callback with request_id {request_id}: {body_str[:100]}...")
    
    # 验证签名
    if settings.FEISHU_ENCRYPT_KEY:
        is_valid = feishu_client.validate_callback(
            request_timestamp, 
            request_nonce, 
            request_signature, 
            body_str
        )
        if not is_valid:
            logger.warning(f"Feishu callback signature validation failed for request_id {request_id}")
            raise HTTPException(status_code=401, detail="Signature validation failed")
    
    # 解析请求体
    try:
        data = json.loads(body_str)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Feishu callback body for request_id {request_id}: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    # 处理不同类型的事件
    event_type = data.get("type", "")
    
    if event_type == "url_verification":
        # 处理首次配置时的URL验证
        challenge = data.get("challenge", "")
        logger.info(f"Processing Feishu URL verification for request_id {request_id}")
        return {"challenge": challenge}
    
    elif event_type == "event_callback":
        # 处理事件回调
        event = data.get("event", {})
        return await _handle_event_callback(event)
    
    else:
        logger.warning(f"Unknown Feishu callback type: {event_type} for request_id {request_id}")
        return {"message": "OK"}


async def _handle_event_callback(event: Dict[Any, Any]) -> Dict[str, str]:
    """
    处理事件回调
    
    Args:
        event: 事件数据
        
    Returns:
        处理结果
    """
    event_type = event.get("type", "")
    # 获取当前请求ID
    request_id = get_request_id()
    logger.info(f"Handling Feishu event callback: {event_type} with request_id {request_id}")
    
    try:
        if event_type == "message":
            # 处理消息事件
            return await _handle_message_event(event)
        elif event_type == "document":
            # 处理文档事件
            return await _handle_document_event(event)
        else:
            logger.info(f"Unsupported Feishu event type: {event_type} for request_id {request_id}")
            return {"message": "OK"}
    except Exception as e:
        logger.error(f"Error handling Feishu event callback for request_id {request_id}: {str(e)}")
        return {"message": "Error"}


async def _handle_message_event(event: Dict[Any, Any]) -> Dict[str, str]:
    """
    处理消息事件
    
    Args:
        event: 消息事件数据
        
    Returns:
        处理结果
    """
    message = event.get("message", {})
    message_id = message.get("message_id", "")
    content = message.get("content", "")
    
    # 获取当前请求ID
    request_id = get_request_id()
    logger.info(f"Handling Feishu message event: {message_id} with request_id {request_id}")
    
    # 这里可以调用文本审稿智能体处理消息内容
    # 示例实现，实际应用中可能需要解析content字段
    # await text_reviewer_agent.process_feishu_message(...)
    
    return {"message": "OK"}


async def _handle_document_event(event: Dict[Any, Any]) -> Dict[str, str]:
    """
    处理文档事件
    
    Args:
        event: 文档事件数据
        
    Returns:
        处理结果
    """
    document_id = event.get("document_id", "")
    # 获取当前请求ID
    request_id = get_request_id()
    logger.info(f"Handling Feishu document event: {document_id} with request_id {request_id}")
    
    # 将文档处理任务加入队列，防止并发处理
    await process_document_task(document_id, event)
    
    return {"message": "OK"}