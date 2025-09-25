import json
import httpx
import sys
import os
from typing import Optional, Dict, Any, AsyncGenerator

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from utils.logger import get_logger
from .base_model import BaseModel

logger = get_logger(__name__)


class QwenModel(BaseModel):
    """Qwen大模型调用接口"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # 如果没有提供配置，则使用默认配置
        if config is None:
            config = {
                "api_key": settings.QWEN_API_KEY,
                "model_name": settings.QWEN_MODEL_NAME,
                "api_base": settings.QWEN_API_BASE
            }
        
        super().__init__(config)
        
        self.api_key = config.get("api_key") or settings.QWEN_API_KEY
        self.model_name = config.get("model_name") or settings.QWEN_MODEL_NAME
        self.api_base = config.get("api_base") or settings.QWEN_API_BASE
        self.client = httpx.AsyncClient()
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        logger.info(f"Initialized QwenModel with model: {self.model_name}")
    
    async def _call_api(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        调用Qwen API的核心方法，包含重试机制
        
        Args:
            prompt: 输入提示
            **kwargs: 其他参数
            
        Returns:
            API响应结果
            
        Raises:
            Exception: 当API调用失败时抛出异常
        """
        url = f"{self.api_base}/services/aigc/text-generation/generation"
        logger.info(f"Calling Qwen model: {self.model_name}")
        logger.debug(f"API URL: {url}")
        logger.debug(f"Request headers: {self.headers}")
        
        # 构建请求参数 - 使用messages格式而不是prompt
        payload = {
            "model": self.model_name,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            },
            "parameters": {
                "max_tokens": kwargs.get("max_tokens", 8000),
                "temperature": kwargs.get("temperature", 0.8),
                **{k: v for k, v in kwargs.items() if k not in ['max_tokens', 'temperature']}
            }
        }
        
        logger.debug(f"Request payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Sending request to Qwen API (attempt {attempt + 1}/{max_retries})")
                response = await self.client.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=httpx.Timeout(30.0)
                )
                
                logger.info(f"Received response from Qwen API with status code: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                
                response.raise_for_status()
                result = response.json()
                logger.debug(f"Response JSON: {json.dumps(result, ensure_ascii=False, indent=2)}")
                
                return result
                
            except httpx.TimeoutException as e:
                logger.warning(f"Timeout on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"Max retries reached. Last error: {str(e)}")
                    raise Exception(f"请求通义千问API超时，已重试{max_retries}次: {str(e)}")
                await asyncio.sleep(2 ** attempt)  # 指数退避
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
                if attempt == max_retries - 1:
                    raise Exception(f"通义千问API返回HTTP错误 {e.response.status_code}: {e.response.text}")
                await asyncio.sleep(2 ** attempt)  # 指数退避
                
            except Exception as e:
                logger.error(f"Error calling Qwen API: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # 指数退避
        
        raise Exception("Failed to call Qwen API after all retries")

    async def generate_text(self, prompt: str, **kwargs) -> str:
        """
        生成文本
        
        Args:
            prompt: 输入提示
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        logger.info(f"Generating text with Qwen model: {self.model_name}")
        logger.debug(f"Prompt: {prompt}")
        
        try:
            result = await self._call_api(prompt, **kwargs)
            
            if "output" in result and "text" in result["output"]:
                content = result["output"]["text"]
                logger.info(f"Successfully generated text with Qwen model, length: {len(content)}")
                logger.debug(f"Generated text: {content}")
                return content
            else:
                logger.error(f"Unexpected response format: {result}")
                raise Exception(f"Unexpected response format from Qwen API: {result}")
                
        except Exception as e:
            logger.error(f"Error generating text with Qwen model: {str(e)}")
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
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            },
            "parameters": {
                "max_tokens": kwargs.get("max_tokens", 8000),
                "temperature": kwargs.get("temperature", 0.8),
                "stream": True,
                **{k: v for k, v in kwargs.items() if k not in ['max_tokens', 'temperature']}
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
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.client.aclose()


# 全局模型实例
qwen_model: Optional[QwenModel] = None


def get_qwen_model(config: Optional[Dict[str, Any]] = None) -> QwenModel:
    """获取Qwen模型实例"""
    global qwen_model
    if qwen_model is None:
        qwen_model = QwenModel(config)
    return qwen_model