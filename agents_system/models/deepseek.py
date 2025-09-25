import httpx
import json
import asyncio
import time
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
            from config.settings import settings
            config = {
                "api_key": settings.DEEPSEEK_API_KEY,
                "model": settings.DEEPSEEK_MODEL
            }
        
        super().__init__(config)
        
        from config.settings import settings
        self.api_key = config.get("api_key") or settings.DEEPSEEK_API_KEY
        self.model = config.get("model") or settings.DEEPSEEK_MODEL
        self.api_url = "https://api.deepseek.com/chat/completions"
        self.client = httpx.AsyncClient()
        self.timeout = httpx.Timeout(30.0)
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY未设置")
            
        logger.info(f"Initialized DeepSeekModel with model: {self.model}")
    
    async def call(self, prompt: str, **kwargs) -> str:
        """调用DeepSeek模型"""
        logger.info(f"Calling DeepSeek model: {self.model}")
        
        # 添加更详细的日志信息
        logger.debug(f"API URL: {self.api_url}")
        logger.debug(f"Request headers: {self.headers}")
        
        # 构建请求参数
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        # 添加更多请求参数（如果有的话）
        for key, value in kwargs.items():
            payload[key] = value
        
        logger.debug(f"Request payload: {payload}")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Sending request to DeepSeek API (attempt {attempt + 1}/{max_retries})")
                response = await self.client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                logger.info(f"Received response from DeepSeek API with status code: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                
                response.raise_for_status()
                result = response.json()
                logger.debug(f"Response JSON: {result}")
                
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    logger.info(f"Successfully extracted content from response, length: {len(content)}")
                    return content
                else:
                    logger.error(f"Unexpected response format: {result}")
                    raise Exception(f"Unexpected response format from DeepSeek API: {result}")
                    
            except httpx.TimeoutException as e:
                logger.warning(f"Timeout on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"Max retries reached. Last error: {str(e)}")
                    raise Exception(f"请求DeepSeekAPI超时，已重试{max_retries}次: {str(e)}")
                # 使用同步sleep避免asyncio问题
                time.sleep(2 ** attempt)
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
                raise Exception(f"DeepSeekAPI返回HTTP错误 {e.response.status_code}: {e.response.text}")
                
            except Exception as e:
                logger.error(f"Error calling DeepSeek API: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                # 使用同步sleep避免asyncio问题
                time.sleep(2 ** attempt)
        
        raise Exception("Failed to call DeepSeek API after all retries")

    async def generate_text(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """
        调用DeepSeek模型生成文本
        
        Args:
            prompt: 输入提示词
            max_tokens: 最大生成token数
            
        Returns:
            生成的文本
        """
        logger.info(f"Generating text with DeepSeek model: {self.model}")
        logger.debug(f"Prompt: {prompt}")
        
        # 准备额外参数
        kwargs = {}
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
            
        result = await self.call(prompt, **kwargs)
        
        logger.info(f"Successfully generated text with DeepSeek model, length: {len(result)}")
        logger.debug(f"Generated text: {result}")
        return result.strip()

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
                    self.api_url,
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
                                        delta = result["choices"][0]["delta"]
                                        if "content" in delta:
                                            content = delta["content"]
                                            if content:
                                                yield content
                                except Exception as e:
                                    logger.warning(f"Error parsing stream data: {e}")
                                    continue
            logger.info("Successfully streamed text with DeepSeek model")
        except Exception as e:
            logger.error(f"Error calling DeepSeek model stream: {str(e)}")
            raise


    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.client.aclose()

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