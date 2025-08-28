import sys
import os
from pydantic import BaseModel
from typing import Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base_agent import BaseAgent
from models.llm import get_qwen_model


class TextReviewRequest(BaseModel):
    """文本审稿请求模型"""
    text: str
    language: str = "zh"
    style: Optional[str] = None


class TextReviewResponse(BaseModel):
    """文本审稿响应模型"""
    original_text: str
    corrected_text: str
    errors: Optional[list] = None
    suggestions: Optional[list] = None


class TextReviewerAgent(BaseAgent):
    """文本审稿智能体，用于处理文本中的错别字和语言逻辑问题"""
    
    def __init__(self):
        super().__init__("text_reviewer")
        self.llm = get_qwen_model()
        # 添加特定路由
        self.router.post("/review", response_model=TextReviewResponse)(self.review_text)
    
    async def process(self, input_data: TextReviewRequest) -> TextReviewResponse:
        """
        处理文本审稿请求
        
        Args:
            input_data: 文本审稿请求数据
            
        Returns:
            文本审稿结果
        """
        return await self.review_text(input_data)
    
    async def review_text(self, request: TextReviewRequest) -> TextReviewResponse:
        """
        审核文本中的错别字和语言逻辑问题
        
        Args:
            request: 文本审稿请求
            
        Returns:
            文本审稿结果
        """
        self.logger.info(f"Reviewing text: {request.text[:50]}...")
        
        # 构建提示词
        prompt = f"""
        请审核以下文本中的错别字和语言逻辑问题：

        文本内容：{request.text}

        要求：
        1. 指出并纠正文本中的错别字
        2. 优化语言逻辑和表达方式
        3. 保持原意不变
        4. 用{request.language}语言回答
        
        请直接返回纠正后的文本，不需要额外说明。
        """
        
        if request.style:
            prompt += f"\n5. 文本风格要求：{request.style}"
        
        # 调用大模型
        corrected_text = await self.llm.generate_text(prompt)
        
        # 构造响应
        response = TextReviewResponse(
            original_text=request.text,
            corrected_text=corrected_text,
            errors=[],  # 在实际应用中可以详细列出错误
            suggestions=[]  # 在实际应用中可以提供改进建议
        )
        
        self.logger.info("Text review completed")
        return response