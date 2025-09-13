import asyncio
from typing import Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from utils.logger import get_logger
from core.request_context import generate_request_id, set_request_id

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """为每个请求生成唯一ID并在响应中返回的中间件"""
    
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # 生成请求ID
        request_id = generate_request_id()
        
        # 设置请求ID到上下文
        set_request_id(request_id)
        
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