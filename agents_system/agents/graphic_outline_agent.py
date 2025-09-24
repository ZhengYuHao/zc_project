import sys
import os
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import httpx
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from core.request_context import get_request_id

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base_agent import BaseAgent
from models.feishu import get_feishu_client, DocumentVersionError
from models.doubao import call_doubao
from config.settings import settings
from utils.logger import get_logger
from utils.cell_filler import CellFiller
from agents_system.core.task_processor import task_processor
from core.request_context import get_request_id


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
    request_id: Optional[str] = None


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


class ProcessRequestInput(BaseModel):
    """ProcessRequest输入模型
    用于图文大纲生成的输入参数模型，包含以下字段：
    
    字段说明：
    - direction: 方向，内容创作的方向指导
    - requirements: 要求，对内容的具体要求
    - product_name: 产品名称，需要推广的产品名称
    - notice: 备注，额外的注意事项或说明
    - picture_number: 图片数量，要求的图片数量
    - ProductHighlights: 产品亮点，产品的核心卖点
    - outline_direction: 大纲方向，大纲制定的具体方向
    - blogger_link: 博主链接，参考的博主主页链接
    """
    direction: Optional[str] = None
    requirements: Optional[str] = None
    product_name: Optional[str] = None
    notice: Optional[str] = None
    picture_number: Optional[str] = None
    ProductHighlights: Optional[str] = None
    outline_direction: Optional[str] = None
    blogger_link: Optional[str] = None


class ProcessRequestResponse(BaseModel):
    """ProcessRequest响应模型"""
    status: str
    task_results: Optional[Dict[str, Any]] = None
    processed_data: Optional[Dict[str, Any]] = None
    spreadsheet: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    request_id: Optional[str] = None


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
        self.router.post("/feishu/sheet", response_model=dict)(self.create_feishu_sheet)
        self.router.post("/process-request", response_model=ProcessRequestResponse)(self.process_request_api)
        
    async def process(self, input_data: GraphicOutlineRequest) -> GraphicOutlineResponse:
        """
        处理图文大纲生成请求
        
        Args:
            input_data: 图文大纲生成请求数据
            
        Returns:
            图文大纲生成结果
        """
        return await self.generate_outline(input_data)
    
    async def process_request_api(self, request: ProcessRequestInput) -> ProcessRequestResponse:
        """
        RESTful API接口，用于处理process_request请求
        
        Args:
            request: ProcessRequest输入数据 
            
        Returns:
            ProcessRequest处理结果
        """
        self.logger.info("Processing process_request API request")

        try:
            # 转换请求数据为process_request所需的格式
            request_data = {
                "direction": request.direction,
                "requirements": request.requirements,
                "product_name": request.product_name,
                "notice": request.notice,
                "picture_number": request.picture_number,
                "ProductHighlights": request.ProductHighlights,
                "outline_direction": request.outline_direction,
                "blogger_link": request.blogger_link
            }
            
            # 调用process_request方法
            result = await self.process_request(request_data)
            
            # 构造响应
            response = ProcessRequestResponse(
                status=result.get("status", "unknown"),
                task_results=result.get("task_results"),
                processed_data=result.get("processed_data"),
                spreadsheet=result.get("spreadsheet"),
                error=result.get("error"),
                request_id=result.get("request_id")
            )
            
            self.logger.info("Successfully processed process_request API request")
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing process_request API request: {str(e)}")
            return ProcessRequestResponse(
                status="error",
                error=str(e),
                request_id=None
            )
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理图文大纲生成请求
        
        Args:
            request: 请求数据
            
        Returns:
            处理结果
        """
        self.logger.info("Processing graphic outline request")
        
        # 获取当前请求ID
        request_id = get_request_id()
        
        try:
            # 并发执行七个任务
            task_results = await task_processor.execute_tasks(request)
            self.logger.info(f"task_results graphic outline request{task_results}")
            # 汇总任务结果并进行下一步处理
            processed_data = await self._aggregate_and_process(task_results, request)
            self.logger.info(f"Processing graphic outline request{processed_data}")
            if processed_data.get("note_style") == "种草":
                # 调用豆包大模型生成种草图文规划
                planting_content = await self._generate_planting_content(processed_data)
                processed_data["planting_content"] = planting_content
                
                # 生成种草配文
                planting_captions = await self._generate_planting_captions(processed_data, planting_content)
                processed_data["planting_captions"] = planting_captions
                
            
            else:
                # 处理图文规划(测试)的工作
                planting_content = await self._generate_planting_content_cp(processed_data)
                processed_data["planting_content"] = planting_content
               
                
                # 生成种草配文
                planting_captions = await self._generate_planting_captions_cp(processed_data, planting_content)
                processed_data["planting_captions"] = planting_captions
                

            
            # 创建飞书电子表格
            spreadsheet_result = await self.create_feishu_sheet({
                "topic": request.get("topic", "默认主题"),
                "outline_data": processed_data
            })
            
            result = {
                "status": "success",
                "task_results": task_results,
                "processed_data": processed_data,
                "spreadsheet": spreadsheet_result,
                "request_id": request_id
            }
            
            self.logger.info("Successfully processed graphic outline request")
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing graphic outline request: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "request_id": request_id
            }
    
    
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
        self.logger.info(f"Populating spreadsheet data for outline_data: {outline_data}")
        
        try:
            
            # 测试种草图文规划生成
            # planting_content = await self._generate_planting_content(outline_data)
            # self.logger.info("Generated planting content:")
            # self.logger.info(planting_content[:-1])

            # 解析图文规划内容
            planting_data = parse_planting_content(outline_data.get("planting_content",""))
            self.logger.info(f"Parsed planting data:{planting_data}")
            for i, data in enumerate(planting_data):
                self.logger.info(f"  Image {i+1}:")     
                self.logger.info(f"    Type: {data['image_type']}")
                self.logger.info(f"    Planning: {data['planning'][:100]}...")
                self.logger.info(f"    Caption: {data['caption']}")
                self.logger.info(f"    Remark: {data['remark']}")

            # 测试种草配文生成
            # planting_captions = await self._generate_planting_captions(outline_data, planting_content)
            # self.logger.info("\nGenerated planting captions:")
            # self.logger.info(planting_captions[:-1])

            # 解析配文内容
            captions_data = parse_planting_captions(outline_data.get("planting_captions",""))
            self.logger.info("Parsed captions data:")
            self.logger.info(f"  Titles: {captions_data['titles']}")
            self.logger.info(f"  Body length: {captions_data['body']}")
            self.logger.info(f"  Hashtags: {captions_data['hashtags']}")

            
            # 获取飞书访问令牌
            tenant_token = await self.feishu_client.get_tenant_access_token()
            
            # 准备要写入的数据（只写入特定单元格数据）
            cell_data = {
                "B1": "",  
                "B2": "",  
                "B3": "",  
                "B4": "", 
                "B5": "",  
                "B6": "",  
                "B7": "",  
                "B8": captions_data['body'],  
                "B9": outline_data.get("sections", {}).get("main_topic", ""),  
                "C2": "",  
                "D6": "",  
                "E2": "",  
                "F6": "",  
            }
            
            # 安全地处理planting_data数组，避免数组越界问题
            # 每行处理两个数据项，分别放在左侧三列(A,B,C)和右侧三列(D,E,F)
            if planting_data:
                row = 12  # 起始行
                # 每次处理两个数据项
                for i in range(0, len(planting_data), 2):
                    # 处理第一个数据项（放在左侧A,B,C列）
                    if i < len(planting_data):
                        data_item = planting_data[i]
                        cell_data[f"A{row}"] = data_item.get('image_type', '')
                        cell_data[f"B{row}"] = data_item.get('planning', '')
                        cell_data[f"C{row}"] = data_item.get('remark', '')
                    
                    # 处理第二个数据项（放在右侧D,E,F列）
                    if i + 1 < len(planting_data):
                        data_item = planting_data[i + 1]
                        cell_data[f"D{row}"] = data_item.get('image_type', '')
                        cell_data[f"E{row}"] = data_item.get('planning', '')
                        cell_data[f"F{row}"] = data_item.get('remark', '')
                    
                    row += 1
            
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
                        "A1": "A1값",
                        "B2": "B2값"
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
        
        # 获取当前请求ID
        request_id = get_request_id()
        
        try:
            # 从请求中提取数据
            topic = request.get("topic", "默认主题")
            outline_data = request.get("outline_data", {})
            
            # 基于模板创建飞书电子表格
            spreadsheet_token, sheet_id = await self._create_spreadsheet_from_template(topic)
            
            # 填充数据到电子表格
            await self._populate_spreadsheet_data(spreadsheet_token, sheet_id, outline_data)
            
            
            
            # 设置电子表格权限为任何人可编辑
            self.logger.info("Setting spreadsheet permissions to anyone can edit")
            try:
                await self._set_spreadsheet_public_editable(spreadsheet_token)
                self.logger.info("Successfully set spreadsheet permissions")
            except Exception as e:
                self.logger.error(f"Failed to set spreadsheet permissions: {str(e)}")
            
            result = {
                "status": "success",
                "spreadsheet_token": spreadsheet_token,
                "sheet_id": sheet_id,
                "request_id": request_id
            }
            
            self.logger.info(f"Successfully created Feishu sheet: {spreadsheet_token}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error creating Feishu sheet: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "request_id": request_id
            }
    
    async def _set_spreadsheet_public_editable(self, spreadsheet_token: str) -> bool:
        """
        设置电子表格权限为任何人可编辑
        
        Args:
            spreadsheet_token: 电子表格token
            
        Returns:
            是否设置成功
        """
        self.logger.info(f"Setting spreadsheet {spreadsheet_token} permissions to public editable")
        
        try:
            # 获取飞书访问令牌
            tenant_token = await self.feishu_client.get_tenant_access_token()
            
            # 飞书设置权限的API endpoint
            permission_url = f"https://open.feishu.cn/open-apis/drive/v2/permissions/{spreadsheet_token}/public?type=sheet"
            headers = {
                "Authorization": f"Bearer {tenant_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            # 权限设置参数
            permission_payload = {
                "external_access_entity": "open",
                "security_entity": "anyone_can_edit",
                "comment_entity": "anyone_can_edit",
                "share_entity": "anyone",
                "manage_collaborator_entity": "collaborator_can_edit",
                "link_share_entity": "anyone_editable",
                "copy_entity": "anyone_can_edit"
            }
            
            self.logger.info(f"Permission URL: {permission_url}")
            self.logger.info(f"Permission payload: {permission_payload}")
            
            # 发送请求设置权限
            async with httpx.AsyncClient() as client:
                permission_response = await client.patch(
                    permission_url, 
                    headers=headers, 
                    json=permission_payload, 
                    timeout=self.timeout
                )
                
                self.logger.info(f"Permission response status code: {permission_response.status_code}")
                self.logger.info(f"Permission response text: {permission_response.text}")
                
                if permission_response.status_code == 200:
                    try:
                        permission_result = permission_response.json()
                        if permission_result.get("code") == 0:
                            self.logger.info("Successfully set spreadsheet permissions to anyone can edit")
                            return True
                        else:
                            self.logger.error(f"Failed to set permissions: {permission_result}")
                            return False
                    except Exception as e:
                        self.logger.error(f"Error parsing permission response: {str(e)}")
                        return False
                else:
                    self.logger.error(f"Failed to set permissions, status code: {permission_response.status_code}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error setting spreadsheet permissions: {str(e)}")
            raise
    
    async def fill_cells_in_sheet(self, spreadsheet_token: str, sheet_id: str, cell_data: Dict[str, Any]) -> dict:
        """
        在指定的电子表格中按单元格引用填充数据（提供给外部调用的简单接口）
        
        Args:
            spreadsheet_token: 电子表格token
            sheet_id: 工作表ID
            cell_data: 单元格数据，格式 {"A1": "값1", "B2": "값2"}
            
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
        self.logger.info(f"Request data received: {request_data}")
        
        # 汇总所有任务的成功结果
        aggregated_data = {}
        
        for task_name, result in task_results.items():
            if result.get("status") == "success":
                aggregated_data[task_name] = result.get("data", {})
            else:
                self.logger.warning(f"Task {task_name} failed: {result.get('error')}")
        
        # 进一步处理汇总的数据
        processed_outline = {
            
            "direction": request_data.get("direction", ""),
            "requirements": request_data.get("requirements", ""),
            "product_name": request_data.get("product_name", ""),
            "notice": request_data.get("notice", ""),
            
            "picture_number": request_data.get("picture_number", ""),
            "ProductHighlights": request_data.get("ProductHighlights", ""),
            "outline_direction": request_data.get("outline_direction",""),
            "sections": {},  # 使用字典映射方式存储
            "total_words": 0,
            "estimated_time": "5分钟"
        }
        self.logger.info(f"Aggregating and processing task results: {aggregated_data}")
        self.logger.info(f"Processed outline data: {processed_outline}")
        
        # 根据任务结果生成大纲章节
        sections = {}
        
        # 定义需要处理的提取器映射关系
        extractor_mapping = {
            
            #达人链接得出
            # "image": request_data.get("image", ""),
            # "caption": request_data.get("caption", ""),
            
            #达人风格
            "blogger_style_extractor": "blogger_style",
            #产品背书
            "product_endorsement_extractor": "product_endorsement",
            #话题
            "topic_extractor": "main_topic"
        }
        
        # 统一处理所有提取器数据
        for extractor_key, section_key in extractor_mapping.items():
            if extractor_key in aggregated_data:
                extractor_data = aggregated_data[extractor_key]
                sections[section_key] = extractor_data.get(section_key, "")
        self.logger.info(f"sections{sections}")
        processed_outline["sections"] = sections
        processed_outline["total_words"] = sum(len(str(content)) for content in sections.values())
        
        self.logger.info("Successfully aggregated and processed task results")
        return processed_outline

    async def _generate_planting_captions(self, processed_data: Dict[str, Any], planting_content: str, user_prompt: Optional[str] = None) -> str:
        """
        生成种草图文的配文内容
        
        Args:
            processed_data: 处理后的数据
            planting_content: 已生成的图文规划内容
            user_prompt: 用户自定义提示词（可选）
            
        Returns:
            生成的配文内容
        """
        try:
            # 获取相关信息
            product_name = processed_data.get("product_name", "")
            ProductHighlights = processed_data.get("ProductHighlights", "")  # 使用新的字段名
            # 从sections中提取目标人群和卖点信息
            sections = processed_data.get("sections", {})
            requirements = processed_data.get("requirements", "")  # 内容方向建议
            notice = processed_data.get("notice", "")  # 注意事项
            picture_number = processed_data.get("picture_number", 6)  # 图片数量，默认为6
            outline_direction = processed_data.get("outline_direction", "")
           
            
            if isinstance(sections, dict):
                
                blogger_style = sections.get("blogger_style", "")
            
            # 构建系统提示词
            system_prompt = f"""## 角色
你是一个专业的小红书与抖音笔记的配文创作者。擅长根据图文规划、创作要求、产品卖点、达人风格创作配文。配文：笔记的文案

## 输入
【注意事项】：{notice}
【大纲方向建议】：{outline_direction}
【卖点信息】：{ProductHighlights}
【达人风格】：{blogger_style}
【图片规划】：{planting_content}
【创作建议】：{requirements}

## 全局要求
使用真实自然的第一人称叙述风格，语言生动亲切，体现真实使用感受
1. **引入不生硬**：不说“今天我要推荐XX”，而是“我在做XX时发现了XX”。
2. **种草不夸张**：用“我觉得”“试了下”“居然”等词弱化广告感，重点描述“场景里的体验”（比如“挂在推车上不晃”比“质量好”更具体）。
3. **收尾不强迫**：引导像“顺手分享”，甚至可以不分享，比如“可以试试”，而非“赶紧买”。

## 禁止话术
- 不使用 “家人们”“宝子”“铁子” 等特定称呼

### 技能
## 技能1
1. 根据【大纲方向建议】选择一个合适的结构作为配文创作的框架，再结合【大纲方向建议】、【创作要求】、【注意事项】、【卖点信息】生成创作配文的大纲。（注意事项为最高优先级，大纲严禁违背注意事项的内容）（【大纲方向建议】、【创作要求】都属于创作的方向，但以【大纲方向建议】为第一优先级）
# 爆文笔记结构
1.PREP结构
- 框架公式：观点-理由-案例-观点
- 示例文案：有了厨下净水器，还要买台式净水器吗？当然有必要！（P）→ 我台式净水器多档水温即热，还能制冰，满足四季不同需求，不用来回跑厨房取水。（R）→ 我家同时用了厨下净水器和台式净水器，煮茶、冲奶粉、做料理都很方便，用水都能选到最合适的温度。（E）→ 所以，即便有厨下净水器，台式净水器也能大大提升日常用水体验（P）。
- 适用内容类型：测评避坑、科普背书。
- 适配标题风格：悬念式 / 对比式 / 结论直给式。
2. FAB卖点结构
- 框架公式：功能 → 优势 → 好处
- 示例文案：这款吹风机有负离子护发功能（F）→ 风力大还能快速吹干（A）→ 每天早晨节省15分钟出门时间（B）。
- 适用内容类型：好物推荐、种草笔记。
- 适配标题风格：数字式 / 好处直给式。
3. 场景递进结构
- 框架公式：场景代入→产品展示→卖点解析→体验强化→情感收尾
要求整个图片规划的场景要统一；卖点部分图片规划要有花字注明卖点
4. 反转结构
- 框架公式：常见认知/刻板印象 → 出乎意料的反转点 → 产品价值/解决方案 → 高光收尾
- 示例文案：开头（常见认知）：很多人觉得洗水果只要泡一泡盐水就够干净了。→ 反转点（出乎意料）：但你知道吗？盐水只能去掉一小部分污渍，真正的农残、蜡层根本搞不定！→ 产品价值（解决方案）：我后来入手了 果蔬清洗机，用高频气泡+涡流冲洗，连缝隙里的脏东西都能带走。→ 收尾（高光收尾）：以前要泡半小时还不放心，现在3分钟就能吃得安心！
- 适用内容类型：个人经历分享、踩坑避坑。
- 适配标题风格：反转式 / 悬念式。
5. 盘点清单结构
- 框架公式：引出主题 → 按序号盘点 → 每个条目简评 → 总结推荐
- 示例文案：开学必备好物TOP3：①小米便携榨汁杯，随时喝果汁；②降噪耳机，图书馆神器；③收纳袋，宿舍整洁全靠它。
- 适用内容类型：选购指南、合集推荐。
- 适配标题风格：数字式 / 清单式 / 种草式。
6. 痛点解决结构
- 框架公式：痛点 → 加剧情绪 → 提供解决方案 → 推荐具体产品
- 示例文案：夏日出游暴晒，皮肤晒得红热又刺痛（痛点）→ 抹涂防晒油也闷痒，出汗一擦就感觉辣辣的，超难受（情绪）→ 后来用了冰沙霜，轻薄凉感瞬间舒缓晒后肌肤（方案）→ 因为有XXX成分，真的一抹降温又保湿，晒后肌肤不再灼热，整天都清爽舒服（推荐）。
- 适用内容类型：护肤美妆、健康护理。
- 适配标题风格：痛点式 / 需求直击式。
7. 选购攻略结构
- 框架公式：误区 → 标准 → 推荐清单 → 总结
- 示例文案：很多人买空气炸锅只看容量（误区）→ 其实功率才是关键，
选购空气炸锅主要看这几条：①功率大小（决定加热效率和烹饪速度）②温控精准度（温度可调范围和稳定性）③内锅材质（防粘、易清洗）④安全设计（过热保护、童锁等）（标准）→ 我家用的是美的，用起来特别顺手（推荐清单）→ 功率强、温控精准，内锅防粘易清洗，还有过热保护和童锁设计，用起来既安全又方便，做饭效率也高（总结）。
- 适用内容类型：消费选购、家电/数码。
- 适配标题风格：攻略式 / 教程式。
8. 挑战/实验结构
- 框架公式：设立挑战 → 实际过程 → 结果 → 意外收获
- 示例文案：我挑战坚持用飞利浦电动牙刷30天（挑战）→ 每天早晚都刷两分钟（过程）→ 结果牙渍真的淡了（结果）→ 牙医朋友都说效果比普通牙刷好（意外收获）。
- 适用内容类型：健康习惯、美妆护肤、生活实验。
- 适配标题风格：挑战式 / 故事分享式。
9.对比结构
- 框架公式：错误操作 → 负面结果 → 正确方法 → 正向结果
- 示例文案：很多初跑者或中学生体测直接选碳板跑鞋（错误操作）→ 鞋子过硬，驾驭不住，跑不出成绩，还容易受伤（负面结果）→ 应该选择缓震适中、贴合脚型的入门跑鞋（正确方法）→ 跑步更舒适、步幅自然，既保护关节，又能稳定发挥体测成绩（正向结果）。
- 适用内容类型：护发美妆、生活习惯教学。
- 适配标题风格：对比式 / 避坑式 / 教程式。
10.FIRE结构
- 框架公式：事实 → 解读→ 反应 → 结果
- 示例文案：研究显示70%的人手机没贴膜更容易碎屏（事实）→ 因为市面大部分屏幕硬度不够（解读）→ 我赶紧换了贝尔金钢化膜（反应）→ 半年摔了三次还完好无损（结果）。
- 适用内容类型：科普背书、产品验证。
- 适配标题风格：事实冲击式 / 避坑式。
11.RIDE结构
- 框架公式：风险/痛点 →兴趣 → 差异→ 效果
- 示例文案：秋冬如果不用加湿器（风险）→ 皮肤容易干痒、喉咙刺痛（风险）→ 我买的XX加湿器可以一晚无雾加湿（利益）→ 比普通加湿器更静音还省电（差异）→ 用了一周，房间再也不干燥了（效果）。
- 适用内容类型：家居电器、健康产品。
- 适配标题风格：痛点式 / 对比式 / 种草式。
12.强化IP结构
- 框架公式：痛点 → 用户获得感 → IP信任感 → 解决方案
- 示例文案：很多家长发现，不管宝宝怎么吃，体重总不上去，很担心营养跟不上。（痛点）→ 也经常受到粉丝留言咨询，希望我聊一聊奶粉怎么选（用户获得感）→ 作为育婴师，我长期指导宝宝喂养，熟悉不同阶段的营养需求和消化特点。（IP信任感）→ 建议选择高吸收率、蛋白脂肪比例科学、添加益生元和DHA的配方奶粉，帮助宝宝健康增重，同时促进消化吸收，让家长更安心。（解决方案）。
- 适用内容类型：达人分享、专业背书。
- 适配标题风格：人设式 / 经验分享式 / 权威背书式。

2. 创作配文
根据技能1得到的创作大纲和输入的【达人风格】创作配文。
核心依据：按照图片规划的创作结构创作配文，配文可以适当关联图片的内容
风格适配：配文的语言风格、内容呈现方式、表达逻辑等需与达人的风格相似
卖点融合：配文需自然的融合卖点，严禁搬抄输入的【卖点信息】和生硬堆砌
注意事项落地：配文严禁违背【注意事项】
* 配文结构：标题、正文、收尾。

## 强制输出格式和内容
**一、笔记配文**
- **标题**：生成5个富有创意且吸引力的标题，巧妙融入emoji表情，提升趣味性和点击率，**字数控制在20字以内**。
- **正文**：严格按照指定的创作结构撰写，正文内容需基于真实数据和专业分析，风格自然可信。避免镜头语言和剧本式表述。不含价格信息或门店推荐（除非【注意事项】提及）。巧妙融入少量emoji表情。**全文控制在800字以内**。
- **标签**：输出【卖点信息】中要求的必带话题，同时输出3-4个符合规范的标签，包含主话题、精准话题、流量话题。

## 限制
- 严禁输出笔记配文之外的其它内容
"""
            
            # 使用用户提示词或系统提示词
            prompt = user_prompt if user_prompt else system_prompt
            
            from models.doubao import call_doubao
            captions_content = await call_doubao(prompt)
            return captions_content
            
        except Exception as e:
            self.logger.error(f"Error generating planting captions: {str(e)}")
            return "种草配文生成失败"
    
    async def _generate_planting_captions_cp(self, processed_data: Dict[str, Any], planting_content: str, user_prompt: Optional[str] = None) -> str:
        """
        生成测评类图文的配文内容
        
        Args:
            processed_data: 处理后的数据
            planting_content: 已生成的图文规划内容
            user_prompt: 用户自定义提示词（可选）
            
        Returns:
            生成的测评类配文内容
        """
        try:
            # 获取相关信息
            product_name = processed_data.get("product_name", "")
            ProductHighlights = processed_data.get("ProductHighlights", "")  # 使用新的字段名
            # 从sections中提取目标人群和卖点信息
            sections = processed_data.get("sections", {})
            requirements = processed_data.get("requirements", "")  # 内容方向建议
            notice = processed_data.get("notice", "")  # 注意事项
            picture_number = processed_data.get("picture_number", 6)  # 图片数量，默认为6
            outline_direction = processed_data.get("outline_direction", "")
           
            
            if isinstance(sections, dict):
                
                blogger_style = sections.get("blogger_style", "")
            
            # 构建系统提示词
            system_prompt = f"""## 角色
你是一名真实用户视角的专业测评博主。擅长以第一人称写作，创作自然真实且极具吸引力与公信力的测评笔记，能够用Z世代语言解析产品内核，符合小红书或抖音等平台的内容风格。

## 输入
【大纲方向建议】：{outline_direction}
【卖点信息】：{ProductHighlights}
【图片规划】：{planting_content}
【注意事项】：{notice}
【创作要求】：{requirements}

## 全局要求
- 使用真实自然的第一人称叙述风格，语言生动亲切，体现真实使用感受

## 技能
1. 理解【图片规划】、【注意事项】、【大纲方向建议】，【创作要求】、【卖点信息】，按照图片规划的逻辑和内容生成配文，同时要遵从足以事项，符合内容方向。必须要有产品的介绍，产品在日常使用中的实际体验和效果，卖点（自然的融入到正文中，严禁直接搬抄产品卖点的内容）。（【大纲方向建议】、【创作要求】都属于创作的方向，但以【大纲方向建议】为第一优先级）
配文结构：标题、正文、收尾。
标题：引入部分，要引起共鸣
收尾：关联主题，让更多人使用产品

## 强制输出格式要求
**一、笔记配文**
- **标题**：生成5个富有创意且吸引力的标题，巧妙融入emoji表情，提升趣味性和点击率，**字数控制在20字以内**。
- **正文**：严格按照指定的创作结构撰写，正文内容需基于真实数据和专业分析，风格自然可信。段落简短（3-5句），避免镜头语言和剧本式表述。不含价格信息或门店推荐（除非【注意事项】提及）。**全文控制在800字以内**。
- **标签**：输出【产品信息】中要求的必带话题，同时输出3-4个符合规范的标签，包含主话题、精准话题、流量话题。

## 限制
1. 内容必须围绕产品测评和避坑选购指南，避免偏离主题。
2. 保持竞品对比客观中立，侧重自家优势但不过度贬低其他产品。
3. 文中所有数据来源需保证真实性，提高公信力（引用可在内容中以【】等符号隐晦表示）
"""
            
            # 使用用户提示词或系统提示词
            prompt = user_prompt if user_prompt else system_prompt
            
            from models.doubao import call_doubao
            captions_content = await call_doubao(prompt)
            return captions_content
            
        except Exception as e:
            self.logger.error(f"Error generating planting captions: {str(e)}")
            return "测评配文生成失败"

    async def _generate_planting_content(self, processed_data: Dict[str, Any], user_prompt: Optional[str] = None) -> str:
        """
        生成种草图文规划内容
        
        Args:
            processed_data: 处理后的数据
            user_prompt: 用户自定义提示词（可选）
            
        Returns:
            生成的种草图文规划内容
        """
        try:
            # 获取相关信息
            product_name = processed_data.get("product_name", "")
            ProductHighlights = processed_data.get("ProductHighlights", "")  # 使用新的字段名
            # 从sections中提取目标人群和卖点信息
            sections = processed_data.get("sections", {})
            requirements = processed_data.get("requirements", "")  # 内容方向建议
            notice = processed_data.get("notice", "")  # 注意事项
            picture_number = processed_data.get("picture_number", 6)  # 图片数量，默认为6
            outline_direction = processed_data.get("outline_direction", "")
           
            
            if isinstance(sections, dict):
                
                blogger_style = sections.get("blogger_style", "")
                
            
            # 构建系统提示词
            system_prompt = f"""## 角色
你是一位专业的小红书种草图文规划师，擅长为 产品创作极具吸引力的种草类图文笔记。注意，你的任务规划出高互动率的爆款内容的图文规划，而不是视频分镜脚本。

## 输入
【大纲方向建议】：{outline_direction}
【卖点信息】：{ProductHighlights}
【注意事项】：{notice}
【图片数量】：{picture_number}
【达人风格】：{blogger_style}
【创作要求】：{requirements}
【产品名称】：{product_name}

## 产品相关信息
- 产品名称：{product_name}

### 技能
## 技能1：
根据【产品相关信息】、【达人风格】，确定以下拍摄场景、拍摄中出现的人物。
遵循以下要求：
场景：符合产品使用的主场景（仅一个）。
人物：确定展示产品的人物（一定要符合达人的人设和条件以及适配产品）

## 技能2：
仔细分析【大纲方向建议】、【创作要求】和【注意事项】的内容，提取出与拍摄产品图片有关的信息，作为图文规划的**创作方向**。（【大纲方向建议】、【创作要求】都属于创作的方向，但以【大纲方向建议】为第一优先级）

## 技能3：生成图片规划内容
以展示产品为目的，写出{picture_number}张种草类产品图片的静态拍摄规划。按照以下图片类型及其功能，给出规划内容。同时，所有图片规划需遵循图片规划原则，图文规划**创作方向**->（技能2的结果），
常见图片类型及其特点：
* 封面图：构图吸睛、情绪明确，首图抢眼吸引点击，一般为产品特写、产品使用场景图、产品使用氛围图等等几类
* 人物图：达人出镜，营造亲和信任感
* 场景图：还原真实使用情境，增强生活感
* 特写图：展示材质、功能细节等局部亮点
* 产品图：从各个角度展示产品，让用户快速了解产品
* 效果图：展示智能产品的App效果截图（可选）
# 图片规划原则
* 场景描述要简单，重点在于展示产品（不需要细节到地毯什么颜色，墙什么颜色等等）
* 按照确定好的拍摄场景规划所有图片的场景，避免频繁切换场景。
* 产品与场景要绝对的融合
* 确保图片是可以在一个时间段集中拍摄完，避免前后落差大。
* 不要出现不符合达人风格的人物（如：单身博主出现孩子）
* 所有图片的动作、互动设计必须真实可拍摄，避免过度夸张、不安全或不可控的动作；儿童/宠物仅安排简单自然状态，不要求复杂配合。
* 道具简化
* 保证整体风格连贯性

## 技能4：生成图片的花字内容
### 需要添加花字的情况
1. 展示产品卖点/功能的图片规划
- 核心目标：快速传递产品核心优势，花字可直接标注关键功能，帮助用户在 3 秒内抓取关键信息，适配功能型产品的效果对比展示场景
===情况示例===
美妆类：花字标注 “持妆24 小时效果”；
家居类：花字标注 “小户型扩容神器”、“0 甲醛”
===示例结束===
- 要求：花字直接关联产品核心功能，无额外视觉辅助要求，重点在于 “功能/卖点关键词直达”

2. 展示价格/促销信息的图片规划
- 核心目标：放大限时折扣、满减等促销敏感信息，吸引用户关注。
===情况示例===
 花字标注 “持妆24 小时效果”
 花字标注 “小户型扩容神器”、“0 甲醛” 
 ===示例结束===
- 注意：避免使用 “原价” 等违规词汇，替换为 “券后价”“会员专享” 等合规表述。

3. 展示使用步骤/教程的图片规划
- 核心目标：清晰引导教程类内容的操作流程，降低用户理解成本，通常适配 DIY 手工、护肤流程等教程类种草内容。
===示例===
在图文对应位置叠加花字，如 “Step1：洁面后取适量精华”、“Step2：沿纹理涂抹面霜”
===示例结束===
- 要求：需搭配箭头、数字序号（如 Step1/2/3）等辅助元素，确保步骤顺序可视化，让操作流程更清晰。

4. 通过展示情绪展示产品卖点/功能
- 判断依据：展示产品卖点/功能的另一种方式
- 核心目标：传递博主使用产品后的情绪 / 感受，或营造场景氛围，增强种草内容的情感共鸣。
===示例===
用花字标注 “小小一个很好携带~”、“今天天气真好呀”
===示例结束===
- 注意：无需固定视觉格式，重点在于 “情绪 / 感受关键词传递”。

**仔细分析图片规划的内容，对于以上需要添加花字的情况，生成符合上述要求的花字。其他情况严禁生成花字**
### 禁止加花字情况
- 不符合以上4类的图片

## 技能5：备注
针对每张图片，列出拍摄的注意事项

## 强制输出格式与内容
图片类型：XX（从封面图、场景图、产品图、人物图、特写图、效果图中判断是什么类型）  
图文规划：（图片规划和花字的内容）
XX
备注：XX
**仅输出图片类型、图文规划、备注，严禁输出其它内容**

## 限制
1. 在图片规划中，默认无需涉及任何痛点场景内容，仅家装类产品允许通过“装修前（问题状态）vs 装修后（改善状态）”的对比形式呈现痛点。
2. 不使用 “家人们”“宝子”“铁子” 等特定称呼；谁懂啊！这种语句
3. 图文规划是“静态”的，不涉及动作过程或时间推进。
4. 不能写成“视频分镜脚本”，不要出现“随后”“过一会儿”“开始”“打开”等动态词。
5. 每张图片是一个独立的定格画面，而不是连续的故事。
6. 严禁输出图片类型、图文规划、备注以外的内容
7. 针对出现的人物一般称达人，其他的具体情况具体称呼
8. 仅输出图片类型、图文规划、备注，严禁输出其它内容（拍摄场景、拍摄人物、创作方向）

"""
            
            # 使用用户提示词或系统提示词
            prompt = user_prompt if user_prompt else system_prompt
            
            from models.doubao import call_doubao
            planting_content = await call_doubao(prompt)
            return planting_content
            
        except Exception as e:
            self.logger.error(f"Error generating planting content: {str(e)}")
            return "种草图文规划生成失败"
    async def _generate_planting_content_cp(self, processed_data: Dict[str, Any], user_prompt: Optional[str] = None) -> str:
        """
        生成测评类图文规划内容
        
        Args:
            processed_data: 处理后的数据
            user_prompt: 用户自定义提示词（可选）
            
        Returns:
            生成的测评类图文规划内容
        """
        try:
             # 获取相关信息
            product_name = processed_data.get("product_name", "")
            ProductHighlights = processed_data.get("ProductHighlights", "")  # 使用新的字段名
            # 从sections中提取目标人群和卖点信息
            sections = processed_data.get("sections", {})
            requirements = processed_data.get("requirements", "")  # 内容方向建议
            notice = processed_data.get("notice", "")  # 注意事项
            picture_number = processed_data.get("picture_number", 6)  # 图片数量，默认为6
            outline_direction = processed_data.get("outline_direction", "")
           
            
            if isinstance(sections, dict):
                
                blogger_style = sections.get("blogger_style", "")
            
            # 构建系统提示词
            system_prompt = f"""## 角色
你是小红书图文规划架构师，擅长生成适用于小红书的图文规划大纲，涵盖选购攻略、深度测评、横向对比三种类型内容。你能够将核心信息点合理拆分到图片中，形成相互关联且连贯的图片逻辑，创作纯文字的笔记。

## 输入
【注意事项】：{notice}
【大纲方向建议】：{outline_direction}
【卖点信息】：{ProductHighlights}
【达人风格】：{blogger_style}
【产品名称】：{product_name}
【图片数量】：{picture_number}
【创作要求】：{requirements}

## 产品相关信息
【 产品名称】：{product_name}
【卖点信息】：{ProductHighlights}

## 必备技能
- 信息搜集和筛选能力：精准搜索创作时需要的产品、品牌等信息，并且返回适合创作的信息或数据

## 技能
### 技能1：
 理解【注意事项】、【大纲方向建议】、【创作要求】，将以上两个信息都考虑在内，其中【注意事项】为第一优先级，生成一份整合后的**内容创作方向**。（【大纲方向建议】、【创作要求】都属于创作的方向，但以【大纲方向建议】为第一优先级）

### 技能2：规划图文结构
结合整合后的**内容创作方向**和输入产品相关信息，写出{picture_number}张测评类产品的图片规划 ，规划每张图的类型。  
#### 常见图片类型与特性：
- **大字报图**：突出观点/标题，常用于封面图或引流使用。
- **参数拉表型**：用于展示多品牌产品的硬件参数、功能维度，横向对比为主，表格结构清晰、信息密度高，常用于封面图或第1张图。
- **图文混排图**：用于承载复杂信息，如展示对比逻辑、选购逻辑、评测流程、结论观点，可配图标/图形/产品图，是选购类、测评类的主要输出载体。
- **总结推荐图**：用于综合评估与推荐建议，搭配标签或图标说明推荐理由，常用于最后一张图。
#### 测评/对比类（强调“信任感+真实性”）叙事框架
选择最合适产品、内容创作方向的框架
* 单品深度测评
  - 框架：外观 & 功能 → 使用场景演示 → 数据/效果反馈 → 总结推荐理由
  - 示例：新鞋10KM实战测评
* 硬核测评 / 实验拆解类
  - 框架：亮出产品 → 测评维度  → 实验方法（模拟真实使用场景 or 实验室测试）  → 分维度展示测试结果  → 综合结论（选购建议）  
  - 示例：新鞋全方位硬核测评（高处扔鸡蛋测回弹缓震、湿地测抓地等）
* 横向对比测评
  - 框架：A产品 vs B产品（或多款竞品） → 测评维度  → 同维度实测 → 结果展示 （重复以上直到测评维度介绍完）→ 综合结论（选购建议，推荐本品）
* 同品牌多款测评
  - 框架：品牌背景（先介绍为什么要选购，或者本期内容的背景） → 各系列/型号横向介绍 → 适配的使用场景/人群匹配 → 选购建议 →  行动号召
* 榜单推荐
  - 框架：场景/需求/主题切入（马拉松跑鞋，双十一好价，300档以内XXX） → 榜单产品逐个介绍（ 合作产品重点突出，篇幅长点）→ 综合总结 → 选购建议 
* 选购指南
  - 框架：场景/需求/主题切入 → 常见错误认知 → 错误思路/踩坑案例 → 正确选购标准/选购维度 → 怎么选 → 推荐合适产品

### 技能3：生成图片规划
- 根据内容创作方向（技能1的整合结果）、选择的框架和图片的特性创作，为每张图片设定文字排版内容（标题、正文、图表结构、结论语等(可选)），正文信息要完整，要给出一个可以直接使用的版本，表达要符合达人语言风格并带有场景化体验，内容要适配小红书笔记的图片大小（3:4）。
- 提供对应的排版建议，包括信息布局、强调色块、表格可读性等。

## 备注
针对每张图片，列出注意事项/补充说明。

## 输出内容及格式
图片类型：XX
图文规划：XX
备注：XX
**输出图片类型、图文规划，严禁输出其它内容**

## 限制
- 所有未提供的信息的需要通过搜索后都要写上
- 严格遵守【注意事项】
"""
            
            # 使用用户提示词或系统提示词
            prompt = user_prompt if user_prompt else system_prompt
            
            from models.doubao import call_doubao
            planting_content = await call_doubao(prompt)
            return planting_content
            
        except Exception as e:
            self.logger.error(f"Error generating planting content: {str(e)}")
            return "测评图文规划生成失败"

import re
from typing import List, Dict, Any


def parse_planting_content(content: str) -> List[Dict[str, str]]:
    """
    解析图文规划内容
    
    Args:
        content: 大模型返回的图文规划文本
        
    Returns:
        解析后的图文规划数据列表
    """
    # 去除内容前后的空白字符
    content = content.strip()
    
    # 如果内容为空，直接返回空列表
    if not content:
        return []
    
    result = []
    
    # 使用正则表达式直接匹配所有图片信息
    # 匹配模式：图片编号 + 图片类型 + 图文规划 + 备注
    pattern = r'图片\s*\d+：\s*\n图片类型：(.*?)\s*\n图文规划：(.*?)\s*\n排版建议：(.*?)\s*\n备注：(.*?)(?=\n\n图片\s*\d+：|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    # 如果匹配到内容，处理每个匹配项
    if matches:
        for match in matches:
            image_type = match[0].strip()
            # 合并图文规划和排版建议
            planning = match[1].strip() + "\n排版建议：" + match[2].strip()
            remark = match[3].strip()
            
            # 清理备注中的干扰信息（如包含下一张图片的编号）
            remark = re.sub(r'图片\s*\d+：.*$', '', remark, flags=re.MULTILINE).strip()
            
            image_info = {
                "image_type": image_type,
                "planning": planning,
                "remark": remark,
                "caption": ""
            }
            result.append(image_info)
    else:
        # 尝试另一种模式，不包含排版建议的单独匹配
        pattern2 = r'图片\s*\d+：\s*\n图片类型：(.*?)\s*\n图文规划：(.*?)\s*\n备注：(.*?)(?=\n\n图片\s*\d+：|\Z)'
        matches2 = re.findall(pattern2, content, re.DOTALL)
        
        for match in matches2:
            image_type = match[0].strip()
            planning = match[1].strip()
            remark = match[2].strip()
            
            # 清理备注中的干扰信息（如包含下一张图片的编号）
            remark = re.sub(r'图片\s*\d+：.*$', '', remark, flags=re.MULTILINE).strip()
            
            image_info = {
                "image_type": image_type,
                "planning": planning,
                "remark": remark,
                "caption": ""
            }
            result.append(image_info)
    
    # 如果仍然没有结果，尝试手动分割处理
    if not result:
        # 按"图片X："分割内容
        sections = re.split(r'(图片\s*\d+：)', content)
        
        # 处理每个部分（跳过第一个空的部分）
        i = 1
        while i < len(sections):
            if sections[i].startswith('图片') and '：' in sections[i]:
                # 构建完整的图片部分
                image_section = sections[i]
                if i + 1 < len(sections):
                    image_section += sections[i + 1]
                
                # 提取图片类型
                type_match = re.search(r'图片类型：(.*?)(?:\n|$)', image_section)
                if type_match:
                    image_type = type_match.group(1).strip()
                    
                    # 提取图文规划（包括排版建议）
                    planning = ""
                    planning_match = re.search(r'图文规划：(.*?)(?=排版建议：|备注：)', image_section, re.DOTALL)
                    layout_match = re.search(r'排版建议：(.*?)(?=备注：)', image_section, re.DOTALL)
                    
                    if planning_match and layout_match:
                        planning = planning_match.group(1).strip() + "\n排版建议：" + layout_match.group(1).strip()
                    elif planning_match:
                        planning = planning_match.group(1).strip()
                    
                    # 提取备注
                    remark_match = re.search(r'备注：(.*?)(?=\n\n图片\s*\d+：|\Z)', image_section, re.DOTALL)
                    remark = remark_match.group(1).strip() if remark_match else ""
                    
                    # 清理备注中的干扰信息
                    remark = re.sub(r'图片\s*\d+：.*$', '', remark, flags=re.MULTILINE).strip()
                    
                    image_info = {
                        "image_type": image_type,
                        "planning": planning,
                        "remark": remark,
                        "caption": ""
                    }
                    result.append(image_info)
            i += 2
    
    return result


def parse_planting_captions(content: str) -> Dict[str, Any]:
    """
    解析配文内容
    
    Args:
        content: 大模型返回的配文文本
        
    Returns:
        解析后的配文数据
    """
    captions_data = {
        "titles": [],
        "body": "",
        "hashtags": []
    }
    
    # 解析标题部分 - 支持多种格式
    # 新格式 (带**标记)
    title_match = re.search(r'- \*\*标题\*\*：((?:\n\s*- [^\n]+)+)', content)
    if title_match:
        titles_text = title_match.group(1)
        titles = re.findall(r'- ([^\n]+)', titles_text)
        captions_data["titles"] = [title.strip() for title in titles]
    else:
        # 旧格式 (不带**标记)
        title_match = re.search(r'标题：((?:\n\s*- [^\n]+)+)', content)
        if title_match:
            titles_text = title_match.group(1)
            titles = re.findall(r'- ([^\n]+)', titles_text)
            captions_data["titles"] = [title.strip() for title in titles]
        else:
            # 单行标题格式
            title_matches = re.findall(r'- \*\*标题\*\*：\s*((?:\n\s*\d+\.\s*[^\n]+)+)', content, re.DOTALL)
            if title_matches:
                titles = re.findall(r'\d+\.\s*([^\n]+)', title_matches[0])
                captions_data["titles"] = [title.strip() for title in titles]
    
    # 解析正文部分
    body_match = re.search(r'- \*\*正文\*\*：(.*?)(?=\n- \*\*标签|\n标签：|\Z)', content, re.DOTALL)
    if body_match:
        captions_data["body"] = body_match.group(1).strip()
    else:
        # 尝试匹配旧格式
        body_match = re.search(r'正文：(.*?)(?=\n标签：|\Z)', content, re.DOTALL)
        if body_match:
            captions_data["body"] = body_match.group(1).strip()
    
    # 解析标签部分
    hashtag_match = re.search(r'- \*\*标签\*\*：(.*?)(?=\Z)', content, re.DOTALL)
    if hashtag_match:
        hashtags_text = hashtag_match.group(1).strip()
        hashtags = re.findall(r'#\S+', hashtags_text)
        captions_data["hashtags"] = hashtags
    else:
        # 尝试匹配旧格式
        hashtag_match = re.search(r'标签：(.*?)(?=\Z)', content, re.DOTALL)
        if hashtag_match:
            hashtags_text = hashtag_match.group(1).strip()
            hashtags = re.findall(r'#\S+', hashtags_text)
            captions_data["hashtags"] = hashtags
    
    return captions_data