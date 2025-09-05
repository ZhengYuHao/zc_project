import sys
import os
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import httpx

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base_agent import BaseAgent
from models.feishu import get_feishu_client, DocumentVersionError
from models.doubao import call_doubao
from config.settings import settings
from utils.logger import get_logger


class GraphicOutlineRequest(BaseModel):
    """图文大纲生成请求模型"""
    topic: str  # 主题
    requirements: Optional[str] = None  # 要求
    style: Optional[str] = None  # 风格


class GraphicOutlineResponse(BaseModel):
    """图文大纲生成响应模型"""
    outline_data: Dict[str, Any]
    document_id: str
    spreadsheet_token: str


class ExternalAPIResponse(BaseModel):
    """外部API响应模型"""
    data: Dict[str, Any]
    status: str


class SectionData(BaseModel):
    """章节数据模型"""
    title: str
    content: str
    images: List[str]
    word_count: int


class OutlineData(BaseModel):
    """大纲数据模型"""
    topic: str
    sections: List[SectionData]
    total_words: int
    estimated_time: str


class GraphicOutlineAgent(BaseAgent):
    """图文大纲生成智能体，用于生成图文内容的大纲并创建飞书电子表格"""
    
    def __init__(self):
        super().__init__("graphic_outline")
        self.feishu_client = get_feishu_client()
        self.logger = get_logger("agent.graphic_outline")
        # 从配置文件中读取配置
        self.default_style = settings.GRAPHIC_OUTLINE_DEFAULT_STYLE
        self.llm_model = settings.GRAPHIC_OUTLINE_LLM_MODEL
        self.max_retries = settings.GRAPHIC_OUTLINE_MAX_RETRIES
        self.timeout = settings.GRAPHIC_OUTLINE_TIMEOUT
        self.template_spreadsheet_token = settings.GRAPHIC_OUTLINE_TEMPLATE_SPREADSHEET_TOKEN
        self.template_folder_token = settings.GRAPHIC_OUTLINE_TEMPLATE_FOLDER_TOKEN
        
        # 添加特定路由
        self.router.post("/generate", response_model=GraphicOutlineResponse)(self.generate_outline)
        self.router.post("/feishu/sheet", response_model=dict)(self.create_feishu_sheet)
        
    async def process(self, input_data: GraphicOutlineRequest) -> GraphicOutlineResponse:
        """
        处理图文大纲生成请求
        
        Args:
            input_data: 图文大纲生成请求数据
            
        Returns:
            图文大纲生成结果
        """
        return await self.generate_outline(input_data)
    
    async def generate_outline(self, request: GraphicOutlineRequest) -> GraphicOutlineResponse:
        """
        生成图文大纲
        
        Args:
            request: 图文大纲生成请求
            
        Returns:
            图文大纲生成结果
        """
        self.logger.info(f"Generating outline for topic: {request.topic}")
        
        try:
            # 调用外部API获取大纲数据
            outline_data = await self._generate_outline_with_llm(
                request.topic, 
                request.requirements, 
                request.style or self.default_style  # 使用配置的默认风格
            )
            
            # 基于模板创建飞书电子表格
            spreadsheet_token = await self._create_spreadsheet_from_template(request.topic)
            
            # 填充数据到电子表格
            await self._populate_spreadsheet_data(spreadsheet_token, outline_data)
            
            # 构造响应
            response = GraphicOutlineResponse(
                outline_data=outline_data,
                document_id=spreadsheet_token,  # 电子表格使用spreadsheet_token作为标识
                spreadsheet_token=spreadsheet_token
            )
            
            self.logger.info(f"Successfully generated outline for topic: {request.topic}")
            return response
            
        except Exception as e:
            self.logger.error(f"Error generating outline for topic {request.topic}: {str(e)}")
            raise
    
    async def _generate_outline_with_llm(self, topic: str, requirements: Optional[str] = None, style: str = "标准") -> Dict[str, Any]:
        """
        使用大模型生成大纲数据
        
        Args:
            topic: 主题
            requirements: 要求
            style: 风格
            
        Returns:
            生成的大纲数据
        """
        self.logger.info(f"Generating outline with LLM for topic: {topic}")
        
        # 构建提示词
        prompt = f"""
        请为以下主题生成一个详细的图文内容大纲：

        主题：{topic}
        风格：{style}
        {f"特殊要求：{requirements}" if requirements else ""}

        要求：
        1. 包含3-5个章节
        2. 每个章节包含标题、简要内容描述、建议图片数量和字数估算
        3. 提供总字数和预计阅读时间
        4. 以JSON格式返回结果，结构如下：
        {{
            "topic": "主题",
            "sections": [
                {{
                    "title": "章节标题",
                    "content": "章节内容简述",
                    "images": ["图片建议1", "图片建议2"],
                    "word_count": 200
                }}
            ],
            "total_words": 1000,
            "estimated_time": "5分钟"
        }}

        只返回JSON，不要包含其他内容。
        """
        
        # 带重试机制的调用
        for attempt in range(self.max_retries):
            try:
                # 调用大模型生成大纲
                result_text = await call_doubao(prompt)
                
                # 解析JSON结果
                import json
                outline_data = json.loads(result_text)
                
                self.logger.info(f"Successfully generated outline with LLM for topic: {topic}")
                return outline_data
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse LLM response as JSON (attempt {attempt+1}/{self.max_retries}): {str(e)}")
                if attempt == self.max_retries - 1:  # 最后一次尝试
                    # 返回默认大纲数据
                    default_outline = {
                        "topic": topic,
                        "sections": [
                            {
                                "title": "引言",
                                "content": "简要介绍主题背景和重要性",
                                "images": ["intro_image.jpg"],
                                "word_count": 100
                            },
                            {
                                "title": "主要内容",
                                "content": "详细阐述主题的核心内容",
                                "images": ["main_image1.jpg", "main_image2.jpg"],
                                "word_count": 300
                            },
                            {
                                "title": "总结",
                                "content": "总结要点并提出展望",
                                "images": [],
                                "word_count": 50
                            }
                        ],
                        "total_words": 450,
                        "estimated_time": "3分钟"
                    }
                    return default_outline
                await asyncio.sleep(1)  # 等待1秒后重试
            except Exception as e:
                self.logger.error(f"Error generating outline with LLM (attempt {attempt+1}/{self.max_retries}): {str(e)}")
                if attempt == self.max_retries - 1:  # 最后一次尝试
                    raise
                await asyncio.sleep(1)  # 等待1秒后重试
    
    async def _create_spreadsheet_from_template(self, title: str) -> str:
        """
        基于模板创建飞书电子表格
        
        Args:
            title: 电子表格标题
            
        Returns:
            电子表格token
        """
        self.logger.info(f"Creating Feishu spreadsheet from template with title: {title}")
        
        try:
            # 获取飞书访问令牌
            token = await self.feishu_client.get_tenant_access_token()
            
            # 飞书复制文件的API endpoint (使用正确的API端点)
            url = f"https://open.feishu.cn/open-apis/drive/v1/files/{self.template_spreadsheet_token}/copy"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            # 请求体 - 根据飞书API文档，正确的参数是name和type
            payload = {
                "name": f"{title} - 图文大纲"
            }
            
            # 如果配置了文件夹token，则添加type和folder_token参数
            # 根据错误信息，type应该是'sheet'而不是'explorer'
            if self.template_folder_token:
                payload["type"] = "sheet"
                payload["folder_token"] = self.template_folder_token
            
            self.logger.info(f"Copy file request URL: {url}")
            self.logger.info(f"Copy file request headers: {headers}")
            self.logger.info(f"Copy file request payload: {payload}")
            
            # 发送请求创建电子表格
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=self.timeout)
                self.logger.info(f"Copy file response status code: {response.status_code}")
                self.logger.info(f"Copy file response headers: {dict(response.headers)}")
                self.logger.info(f"Copy file response text: {response.text}")
                
                response.raise_for_status()
                
                result = response.json()
                self.logger.info(f"Feishu API response: {result}")
                
                if result.get("code") != 0:
                    raise Exception(f"Failed to create spreadsheet from template: {result}")
                
                # 获取电子表格token
                if "data" in result and "file" in result["data"]:
                    spreadsheet_token = result["data"]["file"]["token"]
                else:
                    raise Exception(f"Unexpected API response structure: {result}")
                
                self.logger.info(f"Created Feishu spreadsheet from template with token: {spreadsheet_token}")
                return spreadsheet_token
                
        except Exception as e:
            self.logger.error(f"Error creating Feishu spreadsheet from template: {str(e)}")
            raise
    
    async def _populate_spreadsheet_data(self, spreadsheet_token: str, outline_data: Dict[str, Any]) -> bool:
        """
        填充数据到飞书电子表格
        
        Args:
            spreadsheet_token: 电子表格token
            outline_data: 大纲数据
            
        Returns:
            是否填充成功
        """
        self.logger.info(f"Populating spreadsheet data for spreadsheet: {spreadsheet_token}")
        
        try:
            # 获取飞书访问令牌
            tenant_token = await self.feishu_client.get_tenant_access_token()
            
            # 飞书电子表格操作API endpoint
            # 先获取电子表格元数据，确定工作表
            meta_url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/metainfo"
            headers = {
                "Authorization": f"Bearer {tenant_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            async with httpx.AsyncClient() as client:
                # 获取电子表格元数据
                meta_response = await client.get(meta_url, headers=headers, timeout=self.timeout)
                meta_response.raise_for_status()
                meta_result = meta_response.json()
                
                self.logger.info(f"Feishu metainfo API response: {meta_result}")
                
                if meta_result.get("code") != 0:
                    raise Exception(f"Failed to get spreadsheet metadata: {meta_result}")
                
                # 获取第一个工作表的sheet_id (根据实际响应结构调整)
                if "data" in meta_result and "sheets" in meta_result["data"] and len(meta_result["data"]["sheets"]) > 0:
                    first_sheet = meta_result["data"]["sheets"][0]
                    # 检查是否存在sheet_id字段，如果不存在则使用其他可能的字段
                    if "sheetId" in first_sheet:
                        sheet_id = first_sheet["sheetId"]
                    elif "sheet_id" in first_sheet:
                        sheet_id = first_sheet["sheet_id"]
                    else:
                        sheet_id = first_sheet["sheetId"]  # 默认使用sheetId
                else:
                    raise Exception(f"Unexpected metainfo API response structure: {meta_result}")
                
                self.logger.info(f"Using sheet_id: {sheet_id}")
                
                # 准备要写入的数据
                values = [
                    [outline_data.get("topic", "")],  # 主题行
                    [""],  # 空行
                ]
                
                # 添加章节数据
                sections = outline_data.get("sections", [])
                for section in sections:
                    values.append([
                        section.get("title", ""),
                        section.get("content", ""),
                        ", ".join(section.get("images", [])),
                        str(section.get("word_count", 0))
                    ])
                
                # 添加总计行
                values.append(["", "", "总计", str(outline_data.get("total_words", 0))])
                values.append(["", "", "预计时间", outline_data.get("estimated_time", "")])
                
                # 计算数据范围
                row_count = len(values)
                col_count = max(len(row) for row in values) if values else 1
                
                # 写入数据到电子表格 (使用正确的API端点和范围格式)
                write_url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values"
                write_payload = {
                    "valueRange": {
                        "range": f"{sheet_id}!A3:{chr(64 + col_count)}{2 + row_count}",
                        "values": values
                    }
                }
                
                self.logger.info(f"Writing data to spreadsheet with payload: {write_payload}")
                
                # 使用PUT方法
                write_response = await client.put(write_url, headers=headers, json=write_payload, timeout=self.timeout)
                self.logger.info(f"Write API response status code: {write_response.status_code}")
                self.logger.info(f"Write API response headers: {dict(write_response.headers)}")
                self.logger.info(f"Write API response text: {write_response.text}")
                
                write_response.raise_for_status()
                write_result = write_response.json()
                
                self.logger.info(f"Write response: {write_result}")
                
                # 检查API返回的code，如果不为0则抛出异常
                if write_result.get("code") != 0:
                    error_msg = f"Failed to write data to spreadsheet. API returned code: {write_result.get('code')}, message: {write_result.get('msg')}"
                    self.logger.error(error_msg)
                    # 根据错误码提供更具体的错误信息
                    if write_result.get('code') == 99991666:
                        self.logger.error("Possible permission issue: check if your Feishu app has the required permissions to write to spreadsheets")
                    elif write_result.get('code') == 90202:
                        self.logger.error("Range format error: check if the range format is correct")
                    raise Exception(error_msg)
                
                self.logger.info(f"Successfully populated spreadsheet data for spreadsheet: {spreadsheet_token}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error populating spreadsheet data for spreadsheet {spreadsheet_token}: {str(e)}")
            raise
    
    async def create_feishu_sheet(self, request: Dict[str, Any]) -> dict:
        """
        创建飞书电子表格
        
        Args:
            request: 创建请求数据
            
        Returns:
            处理结果
        """
        self.logger.info("Creating Feishu sheet")
        
        try:
            # 从请求中提取数据
            topic = request.get("topic", "默认主题")
            outline_data = request.get("outline_data", {})
            
            # 基于模板创建飞书电子表格
            spreadsheet_token = await self._create_spreadsheet_from_template(topic)
            
            # 填充数据到电子表格
            await self._populate_spreadsheet_data(spreadsheet_token, outline_data)
            
            result = {
                "status": "success",
                "spreadsheet_token": spreadsheet_token,
                "message": "Successfully created Feishu sheet"
            }
            
            self.logger.info(f"Successfully created Feishu sheet: {spreadsheet_token}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error creating Feishu sheet: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }