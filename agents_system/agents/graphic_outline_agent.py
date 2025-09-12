import sys
import os
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import httpx
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base_agent import BaseAgent
from models.feishu import get_feishu_client, DocumentVersionError
from models.doubao import call_doubao
from config.settings import settings
from utils.logger import get_logger
from utils.cell_filler import CellFiller
from agents.task_processor import task_processor


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


class ProcessRequestInput(BaseModel):
    """ProcessRequest输入模型"""
    topic: str
    product_highlights: Optional[str] = None
    note_style: Optional[str] = None
    product_name: Optional[str] = None
    direction: Optional[str] = None
    blogger_link: Optional[str] = None
    requirements: Optional[str] = None
    style: Optional[str] = None


class ProcessRequestResponse(BaseModel):
    """ProcessRequest响应模型"""
    status: str
    task_results: Optional[Dict[str, Any]] = None
    processed_data: Optional[Dict[str, Any]] = None
    spreadsheet: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


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
        self.router.post("      ", response_model=ProcessRequestResponse)(self.process_request_api)
        
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
                "topic": request.topic,
                "product_highlights": request.product_highlights,
                "note_style": request.note_style,
                "product_name": request.product_name,
                "direction": request.direction,
                "blogger_link": request.blogger_link,
                "requirements": request.requirements,
                "style": request.style
            }
            
            # 调用process_request方法
            result = await self.process_request(request_data)
            
            # 构造响应
            response = ProcessRequestResponse(
                status=result.get("status", "unknown"),
                task_results=result.get("task_results"),
                processed_data=result.get("processed_data"),
                spreadsheet=result.get("spreadsheet"),
                error=result.get("error")
            )
            
            self.logger.info("Successfully processed process_request API request")
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing process_request API request: {str(e)}")
            return ProcessRequestResponse(
                status="error",
                error=str(e)
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
        
        try:
            # 并发执行七个任务
            task_results = await task_processor.execute_tasks(request)
            
            # 汇总任务结果并进行下一步处理
            processed_data = await self._aggregate_and_process(task_results, request)

            if processed_data.get("note_style") == "种草":
                # 调用豆包大模型生成种草图文规划
                planting_content = await self._generate_planting_content(processed_data)
                processed_data["planting_content"] = planting_content
                
                # 生成种草配文
                planting_captions = await self._generate_planting_captions(processed_data, planting_content)
                processed_data["planting_captions"] = planting_captions
                
            
            else:
                # 处理图文规划(测试)的工作
                planting_content = await self._generate_planting_content(processed_data)
                processed_data["planting_content"] = planting_content
               
                
                # 生成种草配文
                planting_captions = await self._generate_planting_captions(processed_data, planting_content)
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
            # agent = GraphicOutlineAgent()
        
            # # 准备测试数据
            # processed_data = {
            #     "topic": "夏季护肤指南",
            #     "product_name": "水润防晒霜",
            #     "product_highlights": "防晒、保湿、温和配方",
            #     "note_style": "种草",
            #     "requirements": "需要包含使用前后对比，适合敏感肌",
            #     "direction": "重点介绍防晒效果和使用感受",
            #     "blogger_link": "https://xiaohongshu.com/user/12345",
            #     "sections": {
            #         "target_audience": "适合户外活动较多的年轻女性",
            #         "required_content": "需要展示防晒效果和使用感受",
            #         "blogger_style": "小红书风格，轻松活泼",
            #         "product_category": "护肤品",
            #         "selling_points": "防晒指数高，温和不刺激，保湿效果好",
            #         "product_endorsement": "专业护肤品牌",
            #         "main_topic": "夏季防晒的重要性"
            #     },
            #     "total_words": 1000,
            #     "estimated_time": "5分钟"
            # }
            
            # 测试种草图文规划生成
            planting_content = await self._generate_planting_content(outline_data)
            self.logger.info("Generated planting content:")
            self.logger.info(planting_content[:-1])

            # 解析图文规划内容
            planting_data = parse_planting_content(planting_content)
            self.logger.info(f"Parsed planting data:{planting_data}")
            for i, data in enumerate(planting_data):
                self.logger.info(f"  Image {i+1}:")     
                self.logger.info(f"    Type: {data['image_type']}")
                self.logger.info(f"    Planning: {data['planning'][:100]}...")
                self.logger.info(f"    Caption: {data['caption']}")
                self.logger.info(f"    Remark: {data['remark']}")

            # 测试种草配文生成
            planting_captions = await self._generate_planting_captions(outline_data, planting_content)
            self.logger.info("\nGenerated planting captions:")
            self.logger.info(planting_captions[:-1])

            # 解析配文内容
            captions_data = parse_planting_captions(planting_captions)
            self.logger.info("Parsed captions data:")
            self.logger.info(f"  Titles: {captions_data['titles']}")
            self.logger.info(f"  Body length: {captions_data['body']}")
            self.logger.info(f"  Hashtags: {captions_data['hashtags']}")

            
            # 获取飞书访问令牌
            tenant_token = await self.feishu_client.get_tenant_access_token()
            
            # 准备要写入的数据（只写入特定单元格数据）
            cell_data = {
                "B1": "",  # 在B1单元格插入"你好"
                "B2": "",  # 在B2单元格插入"你好"
                "B3": "",  # 在B3单元格插入"你好"
                "B4": "",  # 在B4单元格插入"你好"
                "B5": "",  # 在B5单元格插入"你好"
                "B6": "",  # 在B6单元格插入"你好"
                "B7": "",  # 在B7单元格插入"你好"
                "B8": captions_data['body'],  # 在B8单元格插入"你好"
                "B9": outline_data.get("sections", {}).get("main_topic", ""),  # 在B9单元格插入"你好"
                "C2": "",  # 在C2单元格插入"你好"
                "D6": outline_data.get("selling_points"),  # 在D单元格插入"你好"
                "E2": outline_data.get("blogger_style"),  # 在E2单元格插入"你好"
                "F6": outline_data.get("product_endorsement"),  # 在F6单元格插入"你好"
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
            
            # 构造所有单元格数据
            # all_cell_data = {}
            # for i, image_data in enumerate(planting_data):
            #     row_index = 13 + i
            #     all_cell_data.update({
            #         f"A{row_index}": image_data['image_type'],
            #         f"B{row_index}": image_data['planning'],
            #         f"C{row_index}": image_data['caption'],
            #         f"D{row_index}": image_data['remark']
            #     })

# 一次性填充所有数据
# await self.fill_cells_in_sheet(spreadsheet_token, sheet_id, all_cell_data)
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
            
            # 基于模板创建飞书电子表格
            spreadsheet_token, sheet_id = await self._create_spreadsheet_from_template(topic)
            
            # 填充数据到电子表格（仅当fill_outline_data为True时）
            
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
            cell_data: 单元格数据，格式 {"A1": "值1", "B2": "값2"}
            
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
            "sections": {},  # 使用字典映射方式存储
            "total_words": 0,
            "estimated_time": "5分钟"
        }
        
        # 根据任务结果生成大纲章节
        sections = {}
        
        # 添加目标人群分析章节
        if "target_audience_extractor" in aggregated_data:
            audience_data = aggregated_data["target_audience_extractor"]
            sections["target_audience"] = audience_data.get("target_audience", "")
        
        # 添加必提内容章节
        if "required_content_extractor" in aggregated_data:
            content_data = aggregated_data["required_content_extractor"]
            sections["required_content"] = content_data.get("required_content", "")
        
        # 添加达人风格理解章节
        if "blogger_style_extractor" in aggregated_data:
            style_data = aggregated_data["blogger_style_extractor"]
            sections["blogger_style"] = style_data.get("blogger_style", "")
        
        # 添加产品品类章节
        if "product_category_extractor" in aggregated_data:
            category_data = aggregated_data["product_category_extractor"]
            sections["product_category"] = category_data.get("product_category", "")
        
        # 添加卖点章节
        if "selling_points_extractor" in aggregated_data:
            selling_points_data = aggregated_data["selling_points_extractor"]
            sections["selling_points"] = selling_points_data.get("selling_points", "")
        
        # 添加产品背书章节
        if "product_endorsement_extractor" in aggregated_data:
            endorsement_data = aggregated_data["product_endorsement_extractor"]
            sections["product_endorsement"] = endorsement_data.get("endorsement_type", "")
        
        # 添加话题章节
        if "topic_extractor" in aggregated_data:
            topic_data = aggregated_data["topic_extractor"]
            sections["main_topic"] = topic_data.get("main_topic", "")
        
        
        processed_outline["sections"] = sections
        processed_outline["total_words"] = sum(len(str(content)) for content in sections.values())
        
        self.logger.info("Successfully aggregated and processed task results")
        return processed_outline
    
    async def _generate_formatted_output(self, processed_data: Dict[str, Any], planting_content: str, planting_captions: str, user_prompt: Optional[str] = None) -> str:
        """
        生成格式统一的输出内容，包含图文规划和配文
        
        Args:
            processed_data: 处理后的数据
            planting_content: 图文规划内容
            planting_captions: 配文内容
            user_prompt: 用户自定义提示词（可选）
            
        Returns:
            格式统一的输出内容
        """
        try:
            # 获取相关信息
            product_name = processed_data.get("product_name", "")
            product_highlights = processed_data.get("product_highlights", "")
            target_audience = ""
            blogger_style = processed_data.get("note_style", "")
            selling_points = ""
            product_category = ""
            requirements = processed_data.get("requirements", "")
            
            # 从sections中提取目标人群和卖点信息
            sections = processed_data.get("sections", {})
            content_requirement = ""
            endorsement = ""
            output = ""
            
            if isinstance(sections, dict):
                target_audience = sections.get("target_audience", "")
                selling_points = sections.get("selling_points", "")
                product_category = sections.get("product_category", "")
                content_requirement = sections.get("required_content", "")
                endorsement = sections.get("product_endorsement", "")
                main_topic = sections.get("main_topic", "")
            
            # 构建系统提示词
            system_prompt = f"""## 任务
接收配文、图文规划、话题，按照要求格式正确输出

## 强制输出格式和内容（配文{planting_captions}、图文规划[{planting_content}]、话题填写到对应的位置，其它内容以空白形式填写）
**账号名称**

**主页链接**

**发布时间**

**合作形式**

**内容主题方向**            

**图片数量**
供选图（15）张，发布（9）张
**发布配文**

**发布话题**

**🔺拍摄注意事项，需仔细阅读**
1.光线问题：不要逆光拍摄！拍出来素材不可用，补拍风险极高，整体画面需呈现明亮感
2.素材数量：素材尽可能多拍多拍多拍！后期调整起来方便，也避免进行补拍，节省双方时间
3.画面清晰：其中特写镜头产品一定要拍的清晰，近景镜头也要清晰一些，不可以模糊虚焦。


2. 仅“配文”“图文规划”2个字段填写对应内容（`{planting_content}`填图文规划，`{planting_captions}`填配文），图文规划的图片类型、图片规划、备注是3列要填写在对应位置；{main_topic}填发布话题）
3. 其余字段的第二列留空，不填任何信息；
4. 确保表格整洁、易读，符合标准 Markdown 语法。
"""
            
            # 使用用户提示词或系统提示词
            prompt = user_prompt if user_prompt else system_prompt
            
            from models.doubao import call_doubao
            formatted_output = await call_doubao(prompt)
            return formatted_output
            
        except Exception as e:
            self.logger.error(f"Error generating formatted output: {str(e)}")
            return "格式化输出生成失败"

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
            product_highlights = processed_data.get("product_highlights", "")
            target_audience = ""
            blogger_style = processed_data.get("note_style", "")
            selling_points = ""
            product_category = ""
            requirements = processed_data.get("requirements", "")
            
            # 从sections中提取目标人群和卖点信息
            sections = processed_data.get("sections", {})
            content_requirement = ""
            endorsement = ""
            output = ""
            
            if isinstance(sections, dict):
                target_audience = sections.get("target_audience", "")
                selling_points = sections.get("selling_points", "")
                product_category = sections.get("product_category", "")
                content_requirement = sections.get("required_content", "")
                endorsement = sections.get("product_endorsement", "")
                output = planting_content
            
            # 构建系统提示词
            system_prompt = f"""# 角色
你是一个专业的小红书与抖音笔记的配文创作者。擅长根据图文规划、创作要求、产品卖点、达人风格创作配文。
配文：笔记的文案
# 输入
【创作要求】：{requirements}
【内容方向建议】：{content_requirement}
【卖点】：{selling_points}
【达人风格】：{blogger_style}
【图片规划】：{output}

【产品名称】：{product_name}
【产品背书】：{endorsement}
【产品品类】：{product_category}
【图片规划】：{output}

## 全局要求
使用真实自然的第一人称叙述风格，语言生动亲切，体现真实使用感受
1. **引入不生硬**：不说“今天我要推荐XX”，而是“我在做XX时发现了XX”。
2. **种草不夸张**：用“我觉得”“试了下”“居然”等词弱化广告感，重点描述“场景里的体验”（比如“挂在推车上不晃”比“质量好”更具体）。
3. **收尾不强迫**：引导像“顺手分享”，甚至可以不分享，比如“可以试试”，而非“赶紧买”。

## 禁止话术
不使用 “家人们”“宝子”“铁子” 等特定称呼

### 技能
1. 理解图片规划的内容，按照图片规划的创作结构创作配文

2. 创作配文
理解提供的产品创作要求，内容方向建议，达人风格，卖点，必提内容
核心依据：按照图片规划的创作结构创作配文，配文可以适当关联图片的内容
风格适配：配文的语言风格、内容呈现方式、表达逻辑等需与达人的风格相似
卖点融合：配文需自然的融合卖点
创作要求落地：配文要遵守创作要求

* 配文结构：标题、正文、收尾。

## 强制输出格式要求
**一、笔记配文**
- **标题**：生成5个富有创意且吸引力的标题，巧妙融入emoji表情，提升趣味性和点击率，**字数控制在20字以内**。
- **正文**：严格按照指定的创作结构撰写，正文内容需基于真实数据和专业分析，风格自然可信。避免镜头语言和剧本式表述。不含价格信息或门店推荐（除非【创作要求】提及）。巧妙融入少量emoji表情。**全文控制在800字以内**。
- **标签**：输出【产品卖点】中要求的必带话题，同时输出3-4个符合规范的标签，包含主话题、精准话题、流量话题。
"""
            
            # 使用用户提示词或系统提示词
            prompt = user_prompt if user_prompt else system_prompt
            
            from models.doubao import call_doubao
            captions_content = await call_doubao(prompt)
            return captions_content
            
        except Exception as e:
            self.logger.error(f"Error generating planting captions: {str(e)}")
            return "种草配文生成失败"

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
            product_highlights = processed_data.get("product_highlights", "")
            target_audience = ""
            blogger_style = processed_data.get("note_style", "")
            selling_points = ""
            product_category = ""
            requirements = processed_data.get("requirements", "")
            
            # 从sections中提取目标人群和卖点信息
            sections = processed_data.get("sections", {})
            content_requirement = ""
            endorsement = ""
            output = ""
            
            if isinstance(sections, dict):
                target_audience = sections.get("target_audience", "")
                selling_points = sections.get("selling_points", "")
                product_category = sections.get("product_category", "")
                content_requirement = sections.get("required_content", "")
                endorsement = sections.get("product_endorsement", "")
                output = sections.get("output", "")
            
            # 构建系统提示词
            system_prompt = f"""### 角色
你是一位专业的小红书种草图文规划师，擅长为 产品创作极具吸引力的种草类图文笔记。你的任务规划出高互动率的爆款内容的图文规划(必须要有10张图文规划的输出)，而不是视频分镜脚本。

## 图文规划
图文规划 = 针对图文笔记的创作规划。
它包含：
- 静态画面描述（定格的场景、构图、氛围）
- 简短的配图文案（用于图片上的花字或简短口语化表达，≤20字）
- 必要的备注（对光线、人物表情、氛围等补充说明）
- 图片张数要求：必须必须必须10张！！！！!！！！！！

## 产品背景信息
- 产品名称：{product_name}
- 产品品类：{product_category}
- 目标人群：{target_audience}

### 流程
## 流程1： 
需将创作要求的内容{requirements}作为核心约束，再将内容方向建议和必提内容中没有违背核心约束的部分与创作要求整合得到创作方向。

## 流程2：生成图片规划内容
1. 根据提供的产品创作要求，内容方向建议，达人风格，从爆文笔记结构中筛选最合适的1中结构，再结合创作要求，内容方向建议得到一个最完美的创作结构。
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
3. 
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

2. 结合整合后的创作方向、产品背景信息、 卖点、创作的结构，写出15张种草类产品图片的静态拍摄规划。首先，规划图片的类型。
常见图片类型及其特点，包括但不限于：
* 封面图：构图吸睛、情绪明确，首图抢眼吸引点击，一般为产品特写+花字、产品使用场景图、产品使用氛围图等等几类
* 人物图：达人出镜，营造亲和信任感
* 场景图：还原真实使用情境，增强生活感
* 特写图：展示材质、功能细节等局部亮点
*  对比图：同类产品对比，常用于测评或盘点类笔记
*  总结图：以产品特写+花字形式整洁呈现使用结论、推荐理由等

3. 然后，按照创作结构和规划好的图片类型，结合创作方向、产品背景信息、图片类型的特点、必提内容、注意事项，规划图片的内容。同时，要保证遵循拍摄约束、无重复内容。
规划图片内容：
 场景确定：确定拍摄的场景，尽量限定在同一场景/空间，避免频繁切换场景。
 产品植入与场景融合：将种草产品自然融入对应场景中（例如：餐厨场景放厨电 / 餐具；客厅场景放装饰摆件 / 小家电；卧室场景放床品 / 收纳用品；卫浴场景放洗漱好物等），体现产品在真实生活里的使用状态。
功能与优势呈现：针对产品，规划拍摄特写镜头展示核心卖点和功能。
通过从场景细节、拍摄主体（画面核心焦点是？主体是？它的状态、动作、外观、情感？例：保温杯旁放半杯温水 + 一片柠檬；粉底液旁放一支美妆蛋 + 一张浅粉色化妆棉，道具与产品间距 5-8cm，避免杂乱。）、镜头要求（例：用 "俯拍（镜头与桌面呈 45° 角）" 或 "平拍（镜头与产品中部齐平）、画面氛围四个维度文字描述。用具体指令+可视化描述替代模糊表述。
* 拍摄约束：
  时间段统一：确保图片是可以在一个时间段集中拍摄完，避免前后落差大。
  道具简化
  不要出现不符合达人风格的人物（如：单身博主出现孩子）
**以上直接用完整的场景描述来写，不要分点说明**

## 流程3：生成图片的文字内容
1. 一般对于图片规划中体现产品卖点或功能的图片需要有花字注明，其它的图片不是很需要，如果要加，确认好花字的内容。同时，确定好文字排版（大小、位置）。

## 流程4：备注
针对每张图片，列出拍摄的注意事项

## 强制输出格式
图片类型：XX（从封面图、场景图、产品图、对比图、人物图、特写图、总结图中判断是什么类型）
图文规划：
XX（图片规划）
XX（图片的文字内容）
备注：XX

## 限制
1. 在图片规划中，默认无需涉及任何痛点场景内容（如果选择单品种草框架是不要出现痛点内容），仅家装类产品允许通过"装修前（问题状态）vs 装修后（改善状态）"的对比形式呈现痛点。
2. 不使用 "家人们""宝子""铁子" 等特定称呼；谁懂啊！这种语句
3. 图文规划是"静态"的，不涉及动作过程或时间推进。
4. 不能写成"视频分镜脚本"，不要出现"随后""过一会儿""开始""打开"等动态词。
5. 每张图片是一个独立的定格画面，而不是连续的故事。


## 创作要求
- 核心要求：{requirements}
- 产品卖点：{selling_points}
- 内容方向：{content_requirement}
- 产品背书：{endorsement}
- 必提内容：{output}
- 图片张数要求：必须必须必须10张！！！！!！！！！！


"""
            
            # 使用用户提示词或系统提示词
            prompt = user_prompt if user_prompt else system_prompt
            
            from models.doubao import call_doubao
            planting_content = await call_doubao(prompt)
            return planting_content
            
        except Exception as e:
            self.logger.error(f"Error generating planting content: {str(e)}")
            return "种草图文规划生成失败"



def parse_planting_content(content: str) -> List[Dict[str, str]]:
    """
    解析图文规划内容
    
    Args:
        content: 大模型返回的图文规划文本
        
    Returns:
        解析后的图文规划数据列表
    """
    # 使用正则表达式匹配图文规划内容
    pattern = r'图片类型：(.*?)\n图文规划：\n(.*?)\n图片的文字内容：(.*?)\n备注：(.*?)(?=\n\n图片类型：|$)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    result = []
    for match in matches:
        image_info = {
            "image_type": match[0].strip(),
            "planning": match[1].strip(),
            "caption": match[2].strip(),
            "remark": match[3].strip()
        }
        result.append(image_info)
    
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
    
    # 解析标题部分
    title_match = re.search(r'- \*\*标题\*\*：((?:\n\s*- [^\n]+)+)', content)
    if title_match:
        titles_text = title_match.group(1)
        titles = re.findall(r'- ([^\n]+)', titles_text)
        captions_data["titles"] = [title.strip() for title in titles]
    
    # 解析正文部分
    body_match = re.search(r'- \*\*正文\*\*：(.*?)(?=\n- \*\*标签|\Z)', content, re.DOTALL)
    if body_match:
        captions_data["body"] = body_match.group(1).strip()
    
    # 解析标签部分
    hashtag_match = re.search(r'- \*\*标签\*\*：(.*?)(?=\Z)', content, re.DOTALL)
    if hashtag_match:
        hashtags_text = hashtag_match.group(1).strip()
        hashtags = re.findall(r'#\S+', hashtags_text)
        captions_data["hashtags"] = hashtags
    
    return captions_data