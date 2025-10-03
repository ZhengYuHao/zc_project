import json
import httpx
import sys
import os
import asyncio
from typing import Optional, Dict, Any, AsyncGenerator

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from utils.logger import get_logger
from .base_model import BaseModel

logger = get_logger(__name__)


class DoubaoModel(BaseModel):
    """豆包大模型调用接口"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # 如果没有提供配置，则使用默认配置
        if config is None:
            config = {
                "api_key": settings.DOUBAO_API_KEY,
                "model": settings.DOUBAO_MODEL_NAME or "default-model"
            }
        
        super().__init__(config)
        
        self.api_key = config.get("api_key") or settings.DOUBAO_API_KEY
        # 支持model和model_name两种参数
        self.model_name = config.get("model") or config.get("model_name") or settings.DOUBAO_MODEL_NAME or "default-model"
        self.client = httpx.AsyncClient()
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        logger.info(f"Initialized DoubaoModel with model: {self.model_name}")
    
    async def _call_api(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        调用豆包模型API的核心方法，包含重试机制
        
        Args:
            prompt: 输入提示
            **kwargs: 其他参数
            
        Returns:
            API返回的JSON结果
            
        Raises:
            Exception: 当所有重试都失败后抛出
        """
        url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        messages = [{"role": "user", "content": prompt}]
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            **kwargs
        }
        
        # 添加详细日志
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Request Headers (excluding Authorization): {dict((k, v) for k, v in self.headers.items() if k.lower() != 'authorization')}")
        logger.debug(f"Request Payload: {payload}")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Sending request to Doubao API (attempt {attempt + 1}/{max_retries})")
                response = await self.client.post(
                    url, 
                    headers=self.headers, 
                    json=payload, 
                    timeout=300
                )
                
                logger.info(f"Received response from Doubao API, status code: {response.status_code}")
                logger.debug(f"Response Headers: {dict(response.headers)}")
                
                # 检查HTTP状态码
                response.raise_for_status()
                
                result = response.json()
                logger.debug(f"Response JSON: {json.dumps(result, ensure_ascii=False, indent=2)}")
                
                # 验证响应格式
                if ("choices" not in result or 
                    len(result["choices"]) == 0 or 
                    "message" not in result["choices"][0] or 
                    "content" not in result["choices"][0]["message"]):
                    error_msg = f"Unexpected response format from Doubao API: {result}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                    
                return result
                
            except httpx.TimeoutException as e:
                logger.warning(f"Request timeout on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"Max retries reached for timeout. Final error: {str(e)}")
                    raise Exception(f"请求豆包API超时，已重试{max_retries}次: {str(e)}") from e
                # 指数退避
                await asyncio.sleep(2 ** attempt)
                
            except httpx.HTTPStatusError as e:
                error_detail = f"HTTP {e.response.status_code}: {e.response.text}"
                logger.error(f"HTTP error from Doubao API: {error_detail}")
                # 对于客户端错误（4xx），通常重试无意义，直接抛出
                if 400 <= e.response.status_code < 500:
                    raise Exception(f"豆包API返回客户端错误 {e.response.status_code}: {e.response.text}") from e
                # 对于服务端错误（5xx），可以重试
                if attempt == max_retries - 1:
                    raise Exception(f"豆包API返回服务端错误 {e.response.status_code}: {e.response.text}") from e
                await asyncio.sleep(2 ** attempt)
                
            except httpx.RequestError as e:
                logger.error(f"Request error on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    raise Exception(f"请求豆包API时发生网络错误: {str(e)}") from e
                await asyncio.sleep(2 ** attempt)
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON response: {str(e)}")
                raise Exception(f"无法解析豆包API返回的JSON数据: {str(e)}") from e
                
            except Exception as e:
                logger.error(f"Unexpected error when calling Doubao API: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        
        # 理论上不会执行到这里，因为循环内会抛出异常
        raise Exception("Failed to call Doubao API after all retry attempts")

    async def generate_text(self, prompt: str, **kwargs) -> str:
        """
        生成文本
        
        Args:
            prompt: 输入提示
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        logger.info(f"Starting text generation with Doubao model: {self.model_name}")
        logger.debug(f"Input prompt length: {len(prompt)}, content: {prompt}")
        
        try:
            result = await self._call_api(prompt, **kwargs)
            generated_text = result["choices"][0]["message"]["content"]
            
            logger.info(f"Successfully generated text, length: {len(generated_text)}")
            logger.debug(f"Generated text: {generated_text}")
            
            return generated_text
            
        except Exception as e:
            logger.error(f"Failed to generate text with Doubao model: {str(e)}")
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
        url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        
        messages = [{"role": "user", "content": prompt}]
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            **kwargs
        }
        
        try:
            logger.info(f"Calling Doubao model stream with prompt: {prompt[:50]}...")
            async with self.client.stream("POST", url, headers=self.headers, json=payload, timeout=300) as response:
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
            logger.info("Successfully streamed text with Doubao model")
        except Exception as e:
            logger.error(f"Error calling Doubao model stream: {str(e)}")
            raise
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()

    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()


# 全局模型实例
doubao_model: Optional[DoubaoModel] = None


def get_doubao_model(config: Optional[Dict[str, Any]] = None) -> DoubaoModel:
    """获取豆包模型实例"""
    global doubao_model
    if doubao_model is None:
        doubao_model = DoubaoModel(config)
    return doubao_model


async def call_doubao(prompt: str, **kwargs) -> str:
    """
    调用豆包模型生成文本（便捷函数）
    
    Args:
        prompt: 输入提示
        **kwargs: 其他参数
        
    Returns:
        生成的文本
    """
    model = get_doubao_model()
    return await model.generate_text(prompt, **kwargs)


async def call_doubao_stream(prompt: str, **kwargs) -> AsyncGenerator[str, None]:
    """
    流式调用豆包模型生成文本（便捷函数）
    
    Args:
        prompt: 输入提示
        **kwargs: 其他参数
        
    Yields:
        生成的文本片段
    """
    model = get_doubao_model()
    async for chunk in model.generate_text_stream(prompt, **kwargs):
        yield chunk