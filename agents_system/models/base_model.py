from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncGenerator


class BaseModel(ABC):
    """模型基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        pass
    
    @abstractmethod
    async def generate_text_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """流式生成文本"""
        pass
    
    async def close(self):
        """关闭资源"""
        pass