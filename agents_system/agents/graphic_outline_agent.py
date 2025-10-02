import sys
import os
import json
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
from models.model_manager import ModelManager
from config.settings import settings
from utils.logger import get_logger
from utils.cell_filler import CellFiller
from utils.fetch_user_nickname import fetch_user_nickname
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
    direction: str
    requirements: str
    product_name: str
    notice: Optional[str] = None
    picture_number: Optional[str] = None
    ProductHighlights: str
    outline_direction: str
    blogger_link: str
    
    class Config:
        # 确保所有必需字段都经过验证
        schema_extra = {
            "example": {
                "direction": "种草",
                "requirements": "内容生动有趣",
                "product_name": "智能手表",
                "ProductHighlights": "长续航、健康监测",
                "outline_direction": "用户体验",
                "blogger_link": "https://example.com/blogger/123"
            }
        }


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
    
    def __init__(self, model_manager: ModelManager):
        # 使用graphic_outline作为名称，保持与原有路由一致
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
        
        # 模型管理器
        self.model_manager = model_manager
        
        # 加载提示词
        self._load_prompts()
        
        # 添加特定路由，保持与原有路由一致
        self.router.post("/process-request", response_model=ProcessRequestResponse)(self.process_request_api)
        self.router.post("/feishu/sheet", response_model=dict)(self.create_feishu_sheet)
        
    def _load_prompts(self):
        """加载提示词"""
        prompts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'prompts', 'prompts.json')
        try:
            with open(prompts_path, 'r', encoding='utf-8') as f:
                self.prompts = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load prompts from {prompts_path}: {str(e)}")
            self.prompts = {}
    
    async def process(self, input_data: GraphicOutlineRequest) -> GraphicOutlineResponse:
        """
        处理图文大纲生成请求
        
        Args:
            input_data: 图文大纲生成请求数据
            
        Returns:
            图文大纲生成结果
        """
        result = await self.process_request(input_data.dict())
        if result.get("status") == "success":
            return GraphicOutlineResponse(
                outline_data=result.get("processed_data", {}),
                document_id=result.get("spreadsheet", {}).get("sheet_id", ""),
                spreadsheet_token=result.get("spreadsheet", {}).get("spreadsheet_token", ""),
                request_id=result.get("request_id")
            )
        else:
            # 在出错情况下创建一个空的响应
            return GraphicOutlineResponse(
                outline_data={},
                document_id="",
                spreadsheet_token="",
                request_id=result.get("request_id")
            )
    
    async def process_request_api(self, request: ProcessRequestInput) -> ProcessRequestResponse:
        """
        RESTful API接口，用于处理process_request请求
        
        Args:
            request: ProcessRequest输入数据 
            
        Returns:
            ProcessRequest处理结果
        """
        request_id = get_request_id()
        self.logger.info(f"Processing process_request API request with request_id {request_id}: {request}")

        try:
            # 硬编码验证必填字段
            missing_fields = []
            if not request.direction:
                missing_fields.append("direction")
            if not request.requirements:
                missing_fields.append("requirements")
            if not request.product_name:
                missing_fields.append("product_name")
            if not request.ProductHighlights:
                missing_fields.append("ProductHighlights")
            if not request.outline_direction:
                missing_fields.append("outline_direction")
            if not request.blogger_link:
                missing_fields.append("blogger_link")
                
            if missing_fields:
                error_msg = f"Missing required fields: {', '.join(missing_fields)}"
                self.logger.error(f"Validation error in process_request API with request_id {request_id}: {error_msg}")
                return ProcessRequestResponse(
                    status="error",
                    error=error_msg,
                    request_id=request_id
                )

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
                request_id=request_id
            )
            
            self.logger.info(f"Successfully processed process_request API request with request_id {request_id}")
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing process_request API request with request_id {request_id}: {str(e)}")
            return ProcessRequestResponse(
                status="error",
                error=str(e),
                request_id=request_id
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
            direction = processed_data.get("direction", "")
            # 使用正则表达式匹配方向类型
            # 匹配包含"种草"或"vlog"的内容
            if re.search(r'(种|草|vlog)', direction):
                # 调用豆包大模型生成种草图文规划
                planting_content = await self._generate_planting_content(processed_data)
                processed_data["planting_content"] = planting_content
                
                # 生成种草配文
                planting_captions = await self._generate_planting_captions(processed_data, planting_content)
                processed_data["planting_captions"] = planting_captions
                
            
            # 匹配包含"测试"、"拼团"、"选购"或"指南"的内容
            elif re.search(r'(测|评|选购|指南)', direction):
                # 处理图文规划(测试)的工作
                planting_content = await self._generate_planting_content_cp(processed_data)
                processed_data["planting_content"] = planting_content
               
                
                # 生成种草配文
                planting_captions = await self._generate_planting_captions_cp(processed_data, planting_content)
                processed_data["planting_captions"] = planting_captions
                
            else:
                request_id = get_request_id()
                error_msg = f"[{request_id}] Invalid direction value: {direction}. Expected values containing '种草', 'vlog' for first condition, or '测试', '拼团', '选购', '指南' for second condition."
                self.logger.error(error_msg)
                raise ValueError(f"Invalid direction: {direction}")

            
            # 创建飞书电子表格
            blogger_link = request.get("blogger_link", "")
            # 从链接中提取userUuid（最后一部分）
            user_uuid = blogger_link.rstrip('/').split('/')[-1] if blogger_link else "默认主题"
            
            # 如果有user_uuid，则通过API获取用户昵称
            if user_uuid != "默认主题":
                nickname = await fetch_user_nickname(user_uuid)
                if nickname:
                    user_uuid = nickname
            
            spreadsheet_result = await self.create_feishu_sheet({
                "topic": user_uuid,
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
            async with httpx.AsyncClient(timeout=httpx.Timeout(300)) as client:
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
                "B8": outline_data.get("planting_captions", ""),  
                "B9": outline_data.get("sections", {}).get("main_topic", ""),  
                "C2": "",  
                "D6": "",  
                "E2": "",  
                "F6": "",  
            }

            # 测试种草图文规划生成
            # planting_content = await self._generate_planting_content(outline_data)
            # self.logger.info("Generated planting content:")
            # self.logger.info(planting_content[:-1])

            # 解析图文规划内容
            planting_content = outline_data.get("planting_content", "")
            planting_data = []
            
            # 检查是否是JSON格式的输出
            if planting_content:
                # 首先尝试清理可能的代码块标记
                cleaned_content = planting_content.strip()
                if cleaned_content.startswith("```") and cleaned_content.endswith("```"):
                    # 提取代码块中的内容
                    lines = cleaned_content.split('\n')
                    if len(lines) >= 3:
                        # 去掉第一行和最后一行（代码块标记）
                        cleaned_content = '\n'.join(lines[1:-1]).strip()
                
                # 检查是否是JSON格式的输出
                if cleaned_content.startswith('{'):
                    self.logger.info(f"cleaned_content spreadsheet data for outline_data: {cleaned_content}")
                    try:
                        import json
                        planting_json = json.loads(cleaned_content)
                        images = planting_json.get("images", [])
                        for img in images:
                            planting_data.append({
                                "image_type": img.get("image_type", ""),
                                "planning": img.get("planning", ""),
                                "remark": img.get("remark", ""),
                                "caption": ""
                            })
                    except json.JSONDecodeError:
                        # 如果JSON解析失败，回退到原来的解析方法
                        planting_data = parse_planting_content(planting_content)
                else:
                    # 使用原来的解析方法
                    planting_data = parse_planting_content(planting_content)
            else:
                # 内容为空时使用原来的解析方法
                planting_data = parse_planting_content(planting_content)
                
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
            
            # 更新单元格数据
            cell_data.update({
                "B1": "",  
                "B2": "",  
                "B3": "",  
                "B4": "", 
                "B5": "",  
                "B6": "",  
                "B7": "",  
                "B8": outline_data.get("planting_captions", ""),  
                "B9": outline_data.get("sections", {}).get("main_topic", ""),  
                "C2": "",  
                "D6": "",  
                "E2": "",  
                "F6": "",  
            })
            
            # 处理图文规划数据
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
            prompt_template = self.prompts.get("graphic_outline", {}).get("planting_captions", {})
            
            # 构建输入描述
            input_description = prompt_template.get("input_description", "").format(
                notice=notice,
                outline_direction=outline_direction,
                ProductHighlights=ProductHighlights,
                blogger_style=blogger_style,
                planting_content=planting_content,
                requirements=requirements
            )
            
            # 构建技能1描述
            skill_1 = prompt_template.get("skills", {}).get("skill_1", "")
            
            # 构建全局要求
            global_requirements = prompt_template.get("global_requirements", "")
            
            # 构建禁止用语
            forbidden_phrases = prompt_template.get("forbidden_phrases", "")
            
            # 构建输出格式和内容
            output_format_and_content = prompt_template.get("output_format_and_content", "")
            
            # 构建限制
            restrictions = prompt_template.get("restrictions", "")
            
            system_prompt = f"""## 角色
{prompt_template.get("role", "")}

## 输入
{input_description}

## 全局要求
{global_requirements}

## 禁止话术
{forbidden_phrases}

### 技能
## 技能1
{skill_1}
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
- 框架公式：风险/痛点 → 兴趣 → 差异→ 效果
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
{output_format_and_content}

## 限制
{restrictions}
"""
            
            # 使用用户提示词或系统提示词
            prompt = user_prompt if user_prompt else system_prompt
            
            # 调用模型
            captions_content = await self.model_manager.call_model("_generate_planting_captions", prompt)
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
            prompt_template = self.prompts.get("graphic_outline", {}).get("planting_captions_cp", {})
            
            # 构建输入描述
            input_description = prompt_template.get("input_description", "").format(
                outline_direction=outline_direction,
                ProductHighlights=ProductHighlights,
                planting_content=planting_content,
                notice=notice,
                requirements=requirements
            )
            
            # 构建全局要求
            global_requirements = prompt_template.get("global_requirements", "")
            
            # 构建技能描述
            skill_1 = prompt_template.get("skills", {}).get("skill_1", "")
            
            # 构建输出格式
            output_format = prompt_template.get("output_format", "")
            
            # 构建限制
            restrictions = "\n".join(prompt_template.get("restrictions", []))
            
            system_prompt = f"""## 角色
{prompt_template.get("role", "")}

## 输入
{input_description}

## 全局要求
{global_requirements}

## 技能
{skill_1}

## 强制输出格式要求
{output_format}

## 限制
{restrictions}
"""
            
            # 使用用户提示词或系统提示词
            prompt = user_prompt if user_prompt else system_prompt
            
            # 调用模型
            captions_content = await self.model_manager.call_model("_generate_planting_captions_cp", prompt)
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
            prompt_template = self.prompts.get("graphic_outline", {}).get("planting_content", {})
            
            # 构建输入描述
            input_description = prompt_template.get("input_description", "").format(
                outline_direction=outline_direction,
                ProductHighlights=ProductHighlights,
                notice=notice,
                picture_number=picture_number,
                blogger_style=blogger_style,
                requirements=requirements,
                product_name=product_name
            )
            
            # 构建技能描述
            skill_1 = prompt_template.get("skills", {}).get("skill_1", "")
            skill_2 = prompt_template.get("skills", {}).get("skill_2", "")
            skill_3 = prompt_template.get("skills", {}).get("skill_3", "")
            skill_4 = prompt_template.get("skills", {}).get("skill_4", "")
            skill_5 = prompt_template.get("skills", {}).get("skill_5", "")
            
            # 构建输出格式
            output_format = prompt_template.get("output_format", "").format(picture_number=picture_number)
            
            # 构建限制
            restrictions = "\n".join(prompt_template.get("restrictions", []))
            
            system_prompt = f"""## 角色
{prompt_template.get("role", "")}

## 输入
{input_description}

## 产品相关信息
- 产品名称：{product_name}

### 技能
## 技能1：
{skill_1}

## 技能2：
{skill_2}

## 技能3：生成图片规划内容
{skill_3}

## 技能4：生成图片的花字内容
{skill_4}

## 技能5：备注
{skill_5}

## 输出格式要求
{output_format}

## 限制
{restrictions}
"""

            # 使用用户提示词或系统提示词
            prompt = user_prompt if user_prompt else system_prompt
            
            # 调用模型时添加response_format参数，要求JSON格式输出
            planting_content = await self.model_manager.call_model(
                "_generate_planting_content", 
                prompt, 
                response_format={"type": "json_object"}
            )
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
            requirements = processed_data.get("requirements", "")  # 内용方向建议
            notice = processed_data.get("notice", "")  # 注意事项
            picture_number = processed_data.get("picture_number", 6)  # 图片数量，默认为6
            outline_direction = processed_data.get("outline_direction", "")
           
            
            if isinstance(sections, dict):
                
                blogger_style = sections.get("blogger_style", "")
            
            # 构建系统提示词
            prompt_template = self.prompts.get("graphic_outline", {}).get("planting_content_cp", {})
            
            # 构建输入描述
            input_description = prompt_template.get("input_description", "").format(
                notice=notice,
                outline_direction=outline_direction,
                ProductHighlights=ProductHighlights,
                blogger_style=blogger_style,
                product_name=product_name,
                picture_number=picture_number,
                requirements=requirements
            )
            
            # 构建必备技能
            required_skills = prompt_template.get("required_skills", "")
            
            # 构建技能描述
            skill_1 = prompt_template.get("skills", {}).get("skill_1", "")
            skill_2 = prompt_template.get("skills", {}).get("skill_2", "")
            skill_3 = prompt_template.get("skills", {}).get("skill_3", "")
            
            # 构建输出格式
            output_format = prompt_template.get("output_format", "").format(picture_number=picture_number)
            
            # 构建限制
            restrictions = "\n".join(prompt_template.get("restrictions", []))
            
            system_prompt = f"""## 角色
{prompt_template.get("role", "")}

## 输入
{input_description}

## 产品相关信息
【 产品名称】：{product_name}
【卖点信息】：{ProductHighlights}

## 必备技能
{required_skills}

## 技能
### 技能1：
{skill_1}

### 技能2：规划图文结构
{skill_2}

### 技能3：生成图片规划
{skill_3}

## 输出格式要求
{output_format}

## 限制
{restrictions}
"""

            # 使用用户提示词或系统提示词
            prompt = user_prompt if user_prompt else system_prompt
            
            # 调用模型时添加response_format参数，要求JSON格式输出
            planting_content = await self.model_manager.call_model(
                "_generate_planting_content_cp", 
                prompt, 
                response_format={"type": "json_object"}
            )
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
    
    # 使用正则表达式匹配图片信息块
    # 匹配模式：图片类型 + 图文规划 + 备注（可能包含排版建议）
    pattern = r'图片类型：(.*?)\n图文规划：(.*?)\n(备注：.*?)(?=\n\n图片类型：|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    # 如果匹配到内容，处理每个匹配项
    if matches:
        for match in matches:
            image_type = match[0].strip()
            planning = match[1].strip()
            remark_section = match[2].strip()
            
            # 从备注部分提取备注内容
            remark = ""
            remark_match = re.search(r'备注：(.*)', remark_section, re.DOTALL)
            if remark_match:
                remark = remark_match.group(1).strip()
            
            image_info = {
                "image_type": image_type,
                "planning": planning,
                "remark": remark,
                "caption": ""
            }
            result.append(image_info)
    else:
        # 尝试另一种模式匹配（处理包含排版建议的情况）
        pattern2 = r'图片类型：(.*?)\n图文规划：(.*?)\n排版建议：(.*?)\n(备注：.*?)(?=\n\n图片类型：|\Z)'
        matches2 = re.findall(pattern2, content, re.DOTALL)
        
        for match in matches2:
            image_type = match[0].strip()
            # 合并图文规划和排版建议
            planning = match[1].strip() + "\n排版建议：" + match[2].strip()
            remark_section = match[3].strip()
            
            # 从备注部分提取备注内容
            remark = ""
            remark_match = re.search(r'备注：(.*)', remark_section, re.DOTALL)
            if remark_match:
                remark = remark_match.group(1).strip()
            
            image_info = {
                "image_type": image_type,
                "planning": planning,
                "remark": remark,
                "caption": ""
            }
            result.append(image_info)
    
    # 如果仍然没有结果，尝试按"图片类型："分割处理
    if not result:
        # 按"图片类型："分割内容
        sections = re.split(r'(\n图片类型：)', content)
        if len(sections) > 1:
            # 重新组合分割后的内容
            combined_sections = []
            for j in range(0, len(sections), 2):
                section = sections[j] if j < len(sections) else ""
                if j + 1 < len(sections):
                    section += sections[j + 1]
                    if j + 2 < len(sections):
                        section += sections[j + 2]
                combined_sections.append(section)
            
            # 处理每个部分
            for section in combined_sections:
                if '图片类型：' in section:
                    # 提取图片类型
                    type_match = re.search(r'图片类型：(.*?)(?=\n|$)', section)
                    if type_match:
                        image_type = type_match.group(1).strip()
                        
                        # 提取图文规划（可能包含排版建议）
                        planning = ""
                        planning_match = re.search(r'图文规划：(.*?)(?=备注：|\Z)', section, re.DOTALL)
                        if planning_match:
                            planning = planning_match.group(1).strip()
                            # 检查是否还有排版建议
                            layout_match = re.search(r'排版建议：(.*?)(?=备注：|\Z)', section, re.DOTALL)
                            if layout_match:
                                planning += "\n排版建议：" + layout_match.group(1).strip()
                        
                        # 提取备注
                        remark = ""
                        remark_match = re.search(r'备注：(.*?)(?=\n图片类型：|\Z)', section, re.DOTALL)
                        if remark_match:
                            remark = remark_match.group(1).strip()
                        
                        image_info = {
                            "image_type": image_type,
                            "planning": planning,
                            "remark": remark,
                            "caption": ""
                        }
                        result.append(image_info)
    
    return result


def parse_planting_captions(content: str) -> Dict[str, Any]:
    """
    解析种草配文内容，提取标题、正文和标签
    
    Args:
        content: 大模型返回的种草配文文本
        
    Returns:
        包含titles、body和hashtags的字典
    """
    # 初始化返回数据
    captions_data = {
        "titles": [],
        "body": "",
        "hashtags": []
    }
    
    # 如果内容为空，直接返回空数据
    if not content:
        return captions_data
    
    # 解析标题部分
    title_match = re.search(r'- \*\*标题\*\*：(.*?)(?=\n- \*\*正文|\Z)', content, re.DOTALL)
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