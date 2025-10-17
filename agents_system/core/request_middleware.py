import asyncio
from typing import Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from utils.logger import get_logger
from core.request_context import generate_request_id, set_request_id, get_request_id
from models.model_call_logger import ModelCallLogger
from core.feishu_model_log_handler import FeishuModelLogHandler
from config.model_config import load_model_config

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """为每个请求生成唯一ID并在响应中返回的中间件"""
    
    def __init__(self, app):
        super().__init__(app)
        # 加载配置
        config = load_model_config()
        logging_config = config.get("model_call_logging", {})
        self.feishu_config = logging_config.get("feishu_bitable", {})
        self.model_log_handler = FeishuModelLogHandler(self.feishu_config)
    
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # 生成请求ID
        request_id = generate_request_id()
        
        # 设置请求ID到上下文
        set_request_id(request_id)
        
        # 清空当前请求的模型调用记录
        ModelCallLogger.clear_current_calls()
        
        # 记录请求开始
        logger.info(f"开始处理请求 {request_id}: {request.method} {request.url}")
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 在响应头中添加请求ID
            response.headers["X-Request-ID"] = request_id
            
            return response
        except Exception as e:
            # 记录异常
            logger.error(f"请求 {request_id} 处理过程中发生异常: {str(e)}")
            raise
        finally:
            # 记录请求结束
            logger.info(f"请求 {request_id} 处理完成")
            
            # 统一处理模型调用记录
            await self._handle_model_calls(request_id)
    
    async def _handle_model_calls(self, request_id: str):
        """
        统一处理模型调用记录
        
        Args:
            request_id: 请求ID
        """
        try:
            # 获取当前请求的模型调用记录
            model_calls = ModelCallLogger.get_current_calls()
            
            if model_calls:
                logger.info(f"处理 {len(model_calls)} 条模型调用记录")
                # 将模型调用记录写入飞书多维表格
                await self.model_log_handler.save_model_calls(request_id, model_calls)
            else:
                logger.info("没有模型调用记录需要处理")
                
            # 清空当前请求的模型调用记录
            ModelCallLogger.clear_current_calls()
        except Exception as e:
            logger.error(f"处理模型调用记录时发生异常: {str(e)}")