"""
模型调用日志处理器
用于处理模型调用记录
"""

import asyncio
from typing import List, Dict, Any, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class FeishuModelLogHandler:
    """模型调用日志处理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化模型日志处理器
        
        Args:
            config: 配置信息
        """
        logger.info("Initialized FeishuModelLogHandler (no-op)")
    
    async def save_model_calls(self, request_id: str, model_calls: List[Dict[str, Any]]):
        """
        保存模型调用记录（空实现）
        
        Args:
            request_id: 请求ID
            model_calls: 模型调用记录列表
        """
        logger.info(f"Skipping save model calls for request {request_id} - {len(model_calls)} records")
        return
