import httpx
import json
import os
from typing import Optional, Dict, Any, AsyncGenerator
from utils.logger import get_logger
from .base_model import BaseModel

logger = get_logger(__name__)


class DeepSeekModel(BaseModel):
    """DeepSeek大模型调用类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # 如果没有提供配置，则使用默认配置
        if config is None:
            config = {
                "api_key": os.getenv("DEEPSEEK_API_KEY"),
                "model": "deepseek-chat"
            }
        
        super().__init__(config)
        
        self.api_key = config.get("api_key") or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = config.get("base_url", "https://api.deepseek.com/v1")
        self.model = config.get("model", "deepseek-chat")
        
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY环境变量未设置")
    
    async def generate_text(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """
        调用DeepSeek模型生成文本
        
        Args:
            prompt: 输入提示词
            max_tokens: 最大生成token数
            
        Returns:
            生成的文本
        """
        logger.info(f"Calling DeepSeek model with prompt: {prompt[:100]}...")
        
        # 构建请求载荷
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        
        # 如果指定了max_tokens，则添加到载荷中
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        # 设置请求头
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                # 提取生成的文本
                generated_text = result["choices"][0]["message"]["content"].strip()
                
                logger.info("Successfully generated text with DeepSeek model")
                return generated_text
                
        except Exception as e:
            logger.error(f"Error calling DeepSeek model: {str(e)}")
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
        logger.info(f"Calling DeepSeek model stream with prompt: {prompt[:100]}...")
        
        # 构建请求载荷
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": True,
            **kwargs
        }
        
        # 设置请求头
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                ) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_text():
                        if chunk.startswith("data:"):
                            data = chunk[5:].strip()
                            if data != "[DONE]":
                                try:
                                    result = json.loads(data)
                                    if "choices" in result and len(result["choices"]) > 0:
                                        content = result["choices"][0]["delta"]["content"]
                                        if content:
                                            yield content
                                except Exception as e:
                                    logger.warning(f"Error parsing stream data: {e}")
                                    continue
            logger.info("Successfully streamed text with DeepSeek model")
        except Exception as e:
            logger.error(f"Error calling DeepSeek model stream: {str(e)}")
            raise


# 全局实例
_deepseek_model: Optional[DeepSeekModel] = None


def get_deepseek_model(config: Optional[Dict[str, Any]] = None) -> DeepSeekModel:
    """
    获取DeepSeek模型单例实例
    
    Returns:
        DeepSeekModel实例
    """
    global _deepseek_model
    if _deepseek_model is None:
        _deepseek_model = DeepSeekModel(config)
    return _deepseek_model