"""
模型调用日志记录器
用于记录模型调用的提示词和返回结果，存储在内存中供统一处理
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextvars import ContextVar

from utils.logger import get_logger
from config.model_config import load_model_config

logger = get_logger(__name__)

# 使用ContextVar存储当前请求的模型调用记录，确保线程安全
model_calls: ContextVar[List[Dict[str, Any]]] = ContextVar('model_calls', default=[])


class ModelCallLogger:
    """模型调用日志记录器"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, config: Optional[Dict[str, Any]] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化模型调用日志记录器
        
        Args:
            config: 配置信息
        """
        if not self._initialized:
            # 加载配置
            if config is None:
                full_config = load_model_config()
                config = full_config.get("model_call_logging", {})
            
            self.config = config or {}
            self.enabled = self.config.get("enabled", False)
            
            logger.info(f"Initialized ModelCallLogger with enabled={self.enabled}")
            self._initialized = True
    
    async def log_call(self, task_type: str, prompt: str, response: str, **kwargs):
        """
        记录模型调用信息到内存中
        
        Args:
            task_type: 任务类型
            prompt: 提示词
            response: 模型响应
            **kwargs: 其他参数
        """
        if not self.enabled:
            return
            
        try:
            # 获取当前请求的模型调用记录列表
            calls = model_calls.get()
            
            # 构造记录数据
            call_record = {
                "task_type": task_type,
                "prompt": prompt,
                "response": response,
                "timestamp": datetime.now().isoformat(),
                "kwargs": kwargs
            }
            
            # 添加记录到列表
            calls.append(call_record)
            model_calls.set(calls)
            
            logger.debug(f"Logged model call for task: {task_type}")
        except Exception as e:
            logger.error(f"Failed to log model call: {e}")
            # 不抛出异常，避免影响主流程
    
    @staticmethod
    def get_current_calls() -> List[Dict[str, Any]]:
        """
        获取当前请求的所有模型调用记录
        
        Returns:
            当前请求的模型调用记录列表
        """
        return model_calls.get()
    
    @staticmethod
    def clear_current_calls():
        """清空当前请求的模型调用记录"""
        model_calls.set([])