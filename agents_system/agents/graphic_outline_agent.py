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
from utils.cell_filler import CellFiller
from task_processor import task_processor


class GraphicOutlineRequest(BaseModel):
    """图文大纲生成请求模型"""
    topic: str  # 主题
    style: Optional[str] = None  # 风格
    
    requirements: Optional[str] = None  # 要求
    product_highlights: Optional[str] = None  # 产品亮点
    note_style: Optional[str] = None  # 笔记风格
    product_name: Optional[str] = None  # 产品名称
    direction: Optional[str] = None  # 方向
    blogger_link: Optional[str] = None  # 博主链接


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
        self.cell_filler = CellFiller()  # 添加单元格填充工具
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
            spreadsheet_token, sheet_id = await self._create_spreadsheet_from_template(request.topic)
            
            # 填充数据到电子表格
            await self._populate_spreadsheet_data(spreadsheet_token, sheet_id, outline_data)
            
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
    
    async def _create_spreadsheet_from_template(self, title: str) -> tuple:
        """
        基于模板创建飞书电子表格
        
        Args:
            title: 电子表格标题
            
        Returns:
            电子表格token和sheet_id的元组
        """
        self.logger.info(f"Creating Feishu spreadsheet from template with title: {title}")
        
        try:
            # 获取飞书访问令牌
            token = await self.feishu_client.get_tenant_access_token()
            
            # 飞书复制文件的API endpoint
            url = f"https://open.feishu.cn/open-apis/drive/v1/files/{self.template_spreadsheet_token}/copy"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            # 请求体
            payload = {
                "name": f"{title} - 图文大纲",
                "type": "sheet"
            }
            
            if self.template_folder_token:
                payload["folder_token"] = self.template_folder_token
            
            self.logger.info(f"Copy file request URL: {url}")
            self.logger.info(f"Copy file request headers: {headers}")
            self.logger.info(f"Copy file request payload: {payload}")
            
            # 发送请求创建电子表格
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
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
                    spreadsheet_url = result["data"]["file"]["url"]
                else:
                    raise Exception(f"Unexpected API response structure: {result}")
                
                self.logger.info(f"Created spreadsheet with token: {spreadsheet_token}")
                self.logger.info(f"Spreadsheet URL: {spreadsheet_url}")
                
                # 获取sheet_id
                meta_url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/metainfo"
                meta_response = await client.get(meta_url, headers=headers, timeout=self.timeout)
                meta_response.raise_for_status()
                meta_result = meta_response.json()
                
                if meta_result.get("code") != 0:
                    raise Exception(f"Failed to get spreadsheet metadata: {meta_result}")
                
                if "data" in meta_result and "sheets" in meta_result["data"] and len(meta_result["data"]["sheets"]) > 0:
                    first_sheet = meta_result["data"]["sheets"][0]
                    sheet_id = first_sheet.get("sheetId", first_sheet.get("sheet_id", first_sheet.get("index", "0")))
                else:
                    raise Exception(f"Unexpected metainfo API response structure: {meta_result}")
                
                self.logger.info(f"Created Feishu spreadsheet from template with token: {spreadsheet_token} and sheet_id: {sheet_id}")
                return spreadsheet_token, sheet_id
                
        except httpx.ConnectError as e:
            self.logger.error(f"Connection error when creating Feishu spreadsheet from template: {str(e)}")
            raise Exception(f"无法连接到飞书服务器，请检查网络连接: {str(e)}")
        except httpx.TimeoutException as e:
            self.logger.error(f"Timeout error when creating Feishu spreadsheet from template: {str(e)}")
            raise Exception(f"请求飞书服务器超时，请检查网络连接: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error creating Feishu spreadsheet from template: {str(e)}")
            raise
    
    async def _populate_spreadsheet_data(self, spreadsheet_token: str, sheet_id: str, outline_data: Dict[str, Any]) -> bool:
        """
        填充数据到飞书电子表格
        
        Args:
            spreadsheet_token: 电子表格token
            sheet_id: 工作表ID
            outline_data: 大纲数据
            
        Returns:
            是否填充成功
        """
        self.logger.info(f"Populating spreadsheet data for spreadsheet: {spreadsheet_token}")
        
        try:
            # 获取飞书访问令牌
            tenant_token = await self.feishu_client.get_tenant_access_token()
            
            # 准备要写入的数据（只写入特定单元格数据）
            cell_data = {
                "B1": "你好",  # 在B1单元格插入"你好"
                "B2": "你好",  # 在B2单元格插入"你好"
                "B3": "你好",  # 在B3单元格插入"你好"
                "B4": "你好",  # 在B4单元格插入"你好"
                "B5": "你好",  # 在B5单元格插入"你好"
                "B6": "你好",  # 在B6单元格插入"你好"
                "B7": "你好",  # 在B7单元格插入"你好"
                "B8": "你好",  # 在B8单元格插入"你好"
                "B9": "你好",  # 在B9单元格插入"你好"
                "C2": "你好",  # 在C2单元格插入"你好"
                "D6": "你好",  # 在D6单元格插入"你好"
                "E2": "你好",  # 在E2单元格插入"你好"
                "F6": "你好",  # 在F6单元格插入"你好"
            }
            
            # 统一设置单元格格式，确保字体一致
            await self._set_cell_format(spreadsheet_token, sheet_id, tenant_token, ["B1", "B2"])
            
            # 使用fill_cells_in_sheet方法填充数据
            result = await self.fill_cells_in_sheet(spreadsheet_token, sheet_id, cell_data)
            
            if result.get("status") != "success":
                raise Exception(f"Failed to fill cells: {result.get('error')}")
            
            self.logger.info(f"Successfully populated spreadsheet data for spreadsheet: {spreadsheet_token}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error populating spreadsheet data for spreadsheet {spreadsheet_token}: {str(e)}")
            raise
    
    async def _set_cell_format(self, spreadsheet_token: str, sheet_id: str, tenant_token: str, cell_refs: List[str]) -> bool:
        """
        设置单元格格式，确保字体一致性
        
        Args:
            spreadsheet_token: 电子表格token
            sheet_id: 工作表ID
            tenant_token: 访问令牌
            cell_refs: 单元格引用列表，如 ["A1", "B2"]
            
        Returns:
            是否设置成功
        """
        try:
            headers = {
                "Authorization": f"Bearer {tenant_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            # 为每个单元格分别设置格式
            for cell_ref in cell_refs:
                format_payload = {
                    "appendStyle": {
                        "range": f"{sheet_id}!{cell_ref}:{cell_ref}",
                        "style": {
                            "font": {
                                "bold": False,
                                "italic": False,
                                "fontSize": 12,
                                "color": "#000000"  # 黑色字体
                            },
                            "horizontalAlignment": "CENTER"  # 居中对齐
                        }
                    }
                }
                
                # 发送格式设置请求
                format_url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/style"
                
                self.logger.info(f"Setting cell format for {cell_ref}")
                self.logger.info(f"Format URL: {format_url}")
                self.logger.info(f"Format payload: {format_payload}")
                
                async with httpx.AsyncClient() as client:
                    format_response = await client.put(format_url, headers=headers, json=format_payload, timeout=self.timeout)
                    self.logger.info(f"Format response status: {format_response.status_code}")
                    self.logger.info(f"Format response headers: {dict(format_response.headers)}")
                    
                    # 尝试解析响应内容
                    try:
                        response_text = format_response.text
                        self.logger.info(f"Format response text: {response_text}")
                        
                        format_result = format_response.json()
                        self.logger.info(f"Format response JSON: {format_result}")
                        
                        if format_result.get("code") != 0:
                            self.logger.warning(f"API returned non-zero code for {cell_ref}: {format_result.get('code')}")
                            self.logger.warning(f"API message: {format_result.get('msg', 'No message')}")
                    except Exception as parse_error:
                        self.logger.error(f"Error parsing response for {cell_ref}: {str(parse_error)}")
                        self.logger.info(f"Raw response content: {response_text}")
                    
                    # 检查状态码
                    if format_response.status_code != 200:
                        self.logger.warning(f"Non-200 status code for {cell_ref}: {format_response.status_code}")
                        return False
                    
                    # 检查响应内容
                    try:
                        format_result = format_response.json()
                        if format_result.get("code") != 0:
                            self.logger.warning(f"Failed to set cell format for {cell_ref}: {format_result.get('msg')}")
                            return False
                    except:
                        self.logger.warning(f"Failed to parse JSON response for {cell_ref}")
                        return False
            
            self.logger.info(f"Successfully set format for cells: {cell_refs}")
            return True
            
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error setting cell format: {str(e)}")
            self.logger.error(f"Request info: {e.request}")
            if e.response:
                self.logger.error(f"Response info: {e.response}")
                self.logger.error(f"Response text: {e.response.text}")
            return False
        except Exception as e:
            self.logger.warning(f"Error setting cell format: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            # 即使格式设置失败，也不中断数据填充流程
            return False
    
    def _cell_ref_to_row_index(self, cell_ref: str) -> int:
        """
        将单元格引用（如A1）转换为行索引（从0开始）
        
        Args:
            cell_ref: 单元格引用，如"A1"
            
        Returns:
            行索引
        """
        # 提取行号部分（数字）
        row_part = ''.join(filter(str.isdigit, cell_ref))
        return int(row_part) - 1  # 转换为0基索引
    
    def _cell_ref_to_col_index(self, cell_ref: str) -> int:
        """
        将单元格引用（如A1）转换为列索引（从0开始）
        
        Args:
            cell_ref: 单元格引用，如"A1"
            
        Returns:
            列索引
        """
        # 提取列号部分（字母）
        col_part = ''.join(filter(str.isalpha, cell_ref.upper()))
        
        # 转换列为数字索引
        col_index = 0
        for char in col_part:
            col_index = col_index * 26 + (ord(char) - ord('A'))
        return col_index
    
    async def _fill_custom_data(self, spreadsheet_token: str, sheet_id: str, custom_fill_data: Dict[str, Any]) -> bool:
        """
        填充自定义数据到电子表格
        
        Args:
            spreadsheet_token: 电子表格token
            sheet_id: 工作表ID
            custom_fill_data: 自定义填充数据，格式：
                {
                    "cells": {           # 指定单元格填充
                        "A1": "A1值",
                        "B2": "B2值"
                    }
                }
                
        Returns:
            是否填充成功
        """
        self.logger.info(f"Filling custom data to spreadsheet: {spreadsheet_token}")
        
        try:
            # 获取飞书访问令牌
            tenant_token = await self.feishu_client.get_tenant_access_token()
            
            headers = {
                "Authorization": f"Bearer {tenant_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            # 飞书电子表格操作API endpoint
            write_url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values"
            
            # 按单元格填充
            value_ranges = []
            for cell_ref, value in custom_fill_data["cells"].items():
                value_ranges.append({
                    "range": f"{sheet_id}!{cell_ref}:{cell_ref}",
                    "values": [[value]]
                })
            
            write_payload = {
                "valueRanges": value_ranges
            }
            
            # 发送请求
            async with httpx.AsyncClient() as client:
                response = await client.put(write_url, headers=headers, json=write_payload, timeout=self.timeout)
                response.raise_for_status()
                result = response.json()
                
                if result.get("code") != 0:
                    raise Exception(f"Failed to write custom data to spreadsheet: {result}")
            
            self.logger.info(f"Successfully filled custom data to spreadsheet: {spreadsheet_token}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error filling custom data to spreadsheet {spreadsheet_token}: {str(e)}")
            return False

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
            # 提取自定义填充数据（如果有的话）
            custom_fill_data = request.get("custom_fill_data", None)
            # 是否填充大纲数据的标志
            fill_outline_data = request.get("fill_outline_data", True)
            
            # 基于模板创建飞书电子表格
            spreadsheet_token, sheet_id = await self._create_spreadsheet_from_template(topic)
            
            # 填充数据到电子表格（仅当fill_outline_data为True时）
            if fill_outline_data and outline_data:
                await self._populate_spreadsheet_data(spreadsheet_token, sheet_id, outline_data)
            
            # 如果有自定义填充数据，则进行填充
            if custom_fill_data and "cells" in custom_fill_data:
                self.logger.info("Filling custom data to spreadsheet")
                tenant_token = await self.feishu_client.get_tenant_access_token()
                await self.cell_filler.fill_cells(
                    spreadsheet_token, 
                    sheet_id, 
                    tenant_token, 
                    custom_fill_data["cells"]
                )
            
            result = {
                "status": "success",
                "spreadsheet_token": spreadsheet_token,
                "sheet_id": sheet_id,
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
    
    async def fill_cells_in_sheet(self, spreadsheet_token: str, sheet_id: str, cell_data: Dict[str, Any]) -> dict:
        """
        在指定的电子表格中按单元格引用填充数据（提供给外部调用的简单接口）
        
        Args:
            spreadsheet_token: 电子表格token
            sheet_id: 工作表ID
            cell_data: 单元格数据，格式 {"A1": "值1", "B2": "值2"}
            
        Returns:
            处理结果，包含状态和消息的字典
        """
        self.logger.info(f"Filling cells in sheet: {spreadsheet_token}")
        
        try:
            # 获取飞书访问令牌
            tenant_token = await self.feishu_client.get_tenant_access_token()
            
            # 使用单元格填充工具填充数据
            await self.cell_filler.fill_cells(spreadsheet_token, sheet_id, tenant_token, cell_data)
            
            result = {
                "status": "success",
                "message": "Successfully filled cells"
            }
            
            self.logger.info(f"Successfully filled cells in sheet: {spreadsheet_token}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error filling cells in sheet {spreadsheet_token}: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理图文大纲生成请求
        
        Args:
            request: 请求数据
            
        Returns:
            处理结果
        """
        self.logger.info("Processing graphic outline request")
        
        try:
            # 并发执行七个任务
            task_results = await task_processor.execute_tasks(request)
            
            # 汇总任务结果并进行下一步处理
            processed_data = await self._aggregate_and_process(task_results, request)
            
            # 创建飞书电子表格
            spreadsheet_result = await self.create_feishu_sheet({
                "topic": request.get("topic", "默认主题"),
                "outline_data": processed_data
            })
            
            result = {
                "status": "success",
                "task_results": task_results,
                "processed_data": processed_data,
                "spreadsheet": spreadsheet_result
            }
            
            self.logger.info("Successfully processed graphic outline request")
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing graphic outline request: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _aggregate_and_process(self, task_results: Dict[str, Any], request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        汇总任务结果并进行下一步处理
        
        Args:
            task_results: 各任务的执行结果
            request_data: 原始请求数据
            
        Returns:
            处理后的数据
        """
        self.logger.info("Aggregating and processing task results")
        
        # 汇总所有任务的成功结果
        aggregated_data = {}
        
        for task_name, result in task_results.items():
            if result.get("status") == "success":
                aggregated_data[task_name] = result.get("data", {})
            else:
                self.logger.warning(f"Task {task_name} failed: {result.get('error')}")
        
        # 进一步处理汇总的数据
        processed_outline = {
            "topic": request_data.get("topic", ""),
            "product_name": request_data.get("product_name", ""),
            "product_highlights": request_data.get("product_highlights", ""),
            "note_style": request_data.get("note_style", ""),
            "requirements": request_data.get("requirements", ""),
            "direction": request_data.get("direction", ""),
            "blogger_link": request_data.get("blogger_link", ""),
            "sections": [],  # 可以根据处理结果生成具体章节
            "total_words": 0,
            "estimated_time": "5分钟"
        }
        
        # 根据任务结果生成大纲章节
        sections = []
        
        # 添加目标人群分析章节
        if "target_audience_extractor" in aggregated_data:
            audience_data = aggregated_data["target_audience_extractor"]
            sections.append({
                "title": "目标人群分析",
                "content": audience_data.get("target_audience", ""),
                "word_count": len(audience_data.get("target_audience", ""))
            })
        
        # 添加必提内容章节
        if "required_content_extractor" in aggregated_data:
            content_data = aggregated_data["required_content_extractor"]
            sections.append({
                "title": "必提内容",
                "content": content_data.get("required_content", ""),
                "word_count": len(content_data.get("required_content", ""))
            })
        
        # 添加达人风格理解章节
        if "blogger_style_extractor" in aggregated_data:
            style_data = aggregated_data["blogger_style_extractor"]
            sections.append({
                "title": "达人风格理解",
                "content": style_data.get("blogger_style", ""),
                "word_count": len(style_data.get("blogger_style", ""))
            })
        
        # 添加产品品类章节
        if "product_category_extractor" in aggregated_data:
            category_data = aggregated_data["product_category_extractor"]
            sections.append({
                "title": "产品品类分析",
                "content": category_data.get("product_category", ""),
                "word_count": len(category_data.get("product_category", ""))
            })
        
        # 添加卖点章节
        if "selling_points_extractor" in aggregated_data:
            selling_points_data = aggregated_data["selling_points_extractor"]
            sections.append({
                "title": "核心卖点",
                "content": selling_points_data.get("selling_points", ""),
                "word_count": len(selling_points_data.get("selling_points", ""))
            })
        
        # 添加产品背书章节
        if "product_endorsement_extractor" in aggregated_data:
            endorsement_data = aggregated_data["product_endorsement_extractor"]
            sections.append({
                "title": "产品背书",
                "content": f"背书类型: {endorsement_data.get('endorsement_type', '')}",
                "word_count": len(endorsement_data.get("endorsement_type", ""))
            })
        
        # 添加话题章节
        if "topic_extractor" in aggregated_data:
            topic_data = aggregated_data["topic_extractor"]
            sections.append({
                "title": "话题分析",
                "content": f"主话题: {topic_data.get('main_topic', '')}",
                "word_count": len(topic_data.get("main_topic", ""))
            })
        
        # 添加其他章节
        sections.append({
            "title": "内容大纲",
            "content": "根据分析结果生成的详细内容大纲",
            "word_count": 100
        })
        
        sections.append({
            "title": "创作建议",
            "content": "针对该主题和产品的创作建议",
            "word_count": 80
        })
        
        processed_outline["sections"] = sections
        processed_outline["total_words"] = sum(section["word_count"] for section in sections)
        
        self.logger.info("Successfully aggregated and processed task results")
        return processed_outline
