import uuid
import contextvars
from typing import Optional

# 创建上下文变量用于存储请求ID
_request_id_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)


def get_request_id() -> Optional[str]:
    """
    获取当前请求的ID
    
    Returns:
        当前请求ID，如果不在请求上下文中则返回None
    """
    return _request_id_context.get()


def set_request_id(request_id: Optional[str]) -> None:
    """
    设置当前请求ID
    
    Args:
        request_id: 要设置的请求ID
    """
    _request_id_context.set(request_id)


def generate_request_id() -> str:
    """
    生成一个新的请求ID
    
    Returns:
        生成的UUID字符串
    """
    return str(uuid.uuid4())