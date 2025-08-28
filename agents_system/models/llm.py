import json
import httpx
import sys
import os
from typing import Optional, Dict, Any, AsyncGenerator

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class QwenModel:
    """Qwen大模型调用接口"""
    
    def __init__(self):
        self.api_key = settings.QWEN_API_KEY
        self.model_name = settings.QWEN_MODEL_NAME
        self.api_base = settings.QWEN_API_BASE
        self.client = httpx.AsyncClient()
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        logger.info(f"Initialized QwenModel with model: {self.model_name}")
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """
        生成文本
        
        Args:
            prompt: 输入提示
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        url = f"{self.api_base}/services/aigc/text-generation/generation"
        
        payload = {
            "model": self.model_name,
            "input": {
                "prompt": prompt
            },
            "parameters": {
                "max_tokens": kwargs.get("max_tokens", 1024),
                "temperature": kwargs.get("temperature", 0.8),
                **kwargs
            }
        }
        
        try:
            logger.info(f"Calling Qwen model with prompt: {prompt[:50]}...")
            response = await self.client.post(url, headers=self.headers, json=payload, timeout=30.0)
            response.raise_for_status()
            
            result = response.json()
            generated_text = result["output"]["text"]
            logger.info("Successfully generated text with Qwen model")
            
            return generated_text
        except Exception as e:
            logger.error(f"Error calling Qwen model: {str(e)}")
            raise
    
    async def generate_text_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """
        流式生成文本
        
        Args:
            prompt: 输入提示
            **kwargs: 其他参数
            
        Yields:
            生成的文本片段
        """
        url = f"{self.api_base}/services/aigc/text-generation/generation"
        
        payload = {
            "model": self.model_name,
            "input": {
                "prompt": prompt
            },
            "parameters": {
                "max_tokens": kwargs.get("max_tokens", 1024),
                "temperature": kwargs.get("temperature", 0.8),
                "stream": True,
                **kwargs
            }
        }
        
        try:
            logger.info(f"Calling Qwen model stream with prompt: {prompt[:50]}...")
            async with self.client.stream("POST", url, headers=self.headers, json=payload, timeout=30.0) as response:
                response.raise_for_status()
                async for chunk in response.aiter_text():
                    if chunk.startswith("data:"):
                        data = chunk[5:].strip()
                        if data != "[DONE]":
                            try:
                                result = json.loads(data)
                                yield result["output"]["text"]
                            except:
                                continue
            logger.info("Successfully streamed text with Qwen model")
        except Exception as e:
            logger.error(f"Error calling Qwen model stream: {str(e)}")
            raise
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()


# 全局模型实例
qwen_model: Optional[QwenModel] = None


def get_qwen_model() -> QwenModel:
    """获取Qwen模型实例"""
    global qwen_model
    if qwen_model is None:
        qwen_model = QwenModel()
    return qwen_model