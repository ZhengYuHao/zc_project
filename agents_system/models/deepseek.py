import httpx
import json
import os
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class DeepSeekModel:
    """DeepSeek大模型调用类"""
    
    def __init__(self):
        """初始化DeepSeek模型"""
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1"
        self.model = "deepseek-chat"
        
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


# 全局实例
_deepseek_model: Optional[DeepSeekModel] = None


def get_deepseek_model() -> DeepSeekModel:
    """
    获取DeepSeek模型单例实例
    
    Returns:
        DeepSeekModel实例
    """
    global _deepseek_model
    if _deepseek_model is None:
        _deepseek_model = DeepSeekModel()
    return _deepseek_model