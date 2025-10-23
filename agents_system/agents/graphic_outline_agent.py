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
from fastapi import Request

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base_agent import BaseAgent
from models.feishu import get_feishu_client, DocumentVersionError
from models.model_manager import ModelManager
from config.settings import settings
from utils.logger import get_logger
from utils.cell_filler import CellFiller
from utils.fetch_user_nickname import fetch_user_nickname
from core.task_processor import task_processor
from core.request_context import get_request_id
from core.feishu_bitable_processor import process_feishu_record_cell


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
    - record_link: 记录链接，飞书多维表格的记录链接
    """
    direction: str
    requirements: str
    product_name: str
    notice: Optional[str] = None
    picture_number: Optional[str] = None
    ProductHighlights: str
    outline_direction: str
    blogger_link: str
    record_link: Optional[str] = None
    
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
    
    async def process_request_api(self, request: Request) -> ProcessRequestResponse:
        """
        RESTful API接口，用于处理process_request请求
        
        Args:
            request: FastAPI Request对象 
            
        Returns:
            ProcessRequest处理结果
        """
        request_id = get_request_id()
        self.logger.info(f"Processing process_request API request with request_id {request_id}")

        try:
            # 直接从请求体中获取原始数据
            import json
            body = await request.body()
            request_data = {}  # 初始化request_data变量
            try:
                request_data = json.loads(body.decode('utf-8')) if body else {}
            except json.JSONDecodeError:
                self.logger.error(f"Invalid JSON in request body with request_id {request_id}")
                response = ProcessRequestResponse(
                    status="error",
                    error="Invalid JSON format",
                    request_id=request_id
                )
                
                # 如果提供了record_link，则更新飞书多维表格记录
                record_link = request_data.get("record_link") if request_data else None
                if record_link:
                    try:
                        response_json = response.json()
                        await process_feishu_record_cell(record_link, "图文大纲创作结果", response_json)
                        self.logger.info(f"Successfully updated Feishu bitable record with outline for record_link: {record_link}")
                    except Exception as e:
                        self.logger.error(f"Failed to update Feishu bitable record with outline for record_link {record_link}: {str(e)}")
                    
                return response

            self.logger.info(f"Processing process_request API request with request_id {request_id}: {request_data}")

            # 硬编码验证必填字段
            missing_fields = []
            if not request_data.get("direction"):
                missing_fields.append("创作方向-direction")
            if not request_data.get("requirements"):
                missing_fields.append("创作要求-requirements")
            if not request_data.get("product_name"):
                missing_fields.append("产品名称-product_name")
            if not request_data.get("ProductHighlights"):
                missing_fields.append("卖点信息-ProductHighlights")
            if not request_data.get("outline_direction"):
                missing_fields.append("大纲方向建议-outline_direction")
            if not request_data.get("blogger_link"):
                missing_fields.append("达人主页链接-blogger_link")
                
            if missing_fields:
                error_msg = f"缺少必填参数: {', '.join(missing_fields)}"
                self.logger.error(f"Validation error in process_request API with request_id {request_id}: {error_msg}")
                response = ProcessRequestResponse(
                    status="error",
                    error=error_msg,
                    request_id=request_id
                )
                
                # 如果提供了record_link，则更新飞书多维表格记录
                record_link = request_data.get("record_link")
                if record_link:
                    try:
                        response_json = response.json()
                        await process_feishu_record_cell(record_link, "图文大纲创作结果", response_json)
                        self.logger.info(f"Successfully updated Feishu bitable record with error for record_link: {record_link}")
                    except Exception as e:
                        self.logger.error(f"Failed to update Feishu bitable record with error for record_link {record_link}: {str(e)}")
                    
                return response

            # 如果用户没有提交picture_number字段，默认设置为15张
            if "picture_number" not in request_data:
                request_data["picture_number"] = 15
            else:
                # 验证picture_number必须是非0非负的正整数
                try:
                    picture_number = int(request_data["picture_number"])
                    if picture_number <= 0:
                        error_msg = "picture_number must be a positive integer greater than 0"
                        self.logger.error(f"Validation error in process_request API with request_id {request_id}: {error_msg}")
                        response = ProcessRequestResponse(
                            status="error",
                            error=error_msg,
                            request_id=request_id
                        )
                        
                        # 如果提供了record_link，则更新飞书多维表格记录
                        record_link = request_data.get("record_link")
                        if record_link:
                            try:
                                response_json = response.json()
                                await process_feishu_record_cell(record_link, "图文大纲创作结果", response_json)
                                self.logger.info(f"Successfully updated Feishu bitable record with error for record_link: {record_link}")
                            except Exception as e:
                                self.logger.error(f"Failed to update Feishu bitable record with error for record_link {record_link}: {str(e)}")
                        
                        return response
                    request_data["picture_number"] = picture_number
                except (ValueError, TypeError):
                    error_msg = "picture_number must be a valid positive integer greater than 0"
                    self.logger.error(f"Validation error in process_request API with request_id {request_id}: {error_msg}")
                    response = ProcessRequestResponse(
                        status="error",
                        error=error_msg,
                        request_id=request_id
                    )
                    
                    # 如果提供了record_link，则更新飞书多维表格记录
                    record_link = request_data.get("record_link")
                    if record_link:
                        try:
                            response_json = response.json()
                            await process_feishu_record_cell(record_link, "图文大纲创作结果", response_json)
                            self.logger.info(f"Successfully updated Feishu bitable record with error for record_link: {record_link}")
                        except Exception as e:
                            self.logger.error(f"Failed to update Feishu bitable record with error for record_link {record_link}: {str(e)}")
                    
                    return response
            
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
            
            # 如果提供了record_link，则更新飞书多维表格记录
            record_link = request_data.get("record_link")
            if record_link:
                try:
                    # 获取并记录模型调用日志
                    try:
                        from models.model_call_logger import ModelCallLogger
                        import json
                        model_calls = ModelCallLogger.get_current_calls()
                        if model_calls:
                            model_calls_json = json.dumps(model_calls, ensure_ascii=False, indent=2)
                            await process_feishu_record_cell(record_link, "模型调用日志", model_calls_json)
                            self.logger.info(f"Successfully updated model call logs for record_link: {record_link}")
                    except Exception as e:
                        self.logger.error(f"Failed to update model call logs for record_link {record_link}: {str(e)}")
                        
                    # 只返回电子表格链接
                    spreadsheet_info = result.get("spreadsheet", {})
                    if spreadsheet_info and spreadsheet_info.get("status") == "success":
                        spreadsheet_token = spreadsheet_info.get("spreadsheet_token", "")
                        # 构造完整的电子表格URL
                        spreadsheet_url = f"https://dkke3lyh7o.feishu.cn/sheets/{spreadsheet_token}"
                        await process_feishu_record_cell(record_link, "图文大纲创作结果", spreadsheet_url)
                        self.logger.info(f"Successfully updated Feishu bitable record with spreadsheet URL for record_link: {record_link}")
                    else:
                        # 如果没有成功创建电子表格，则返回完整响应
                        response_json = response.json()
                        await process_feishu_record_cell(record_link, "图文大纲创作结果", response_json)
                        self.logger.info(f"Successfully updated Feishu bitable record with full response for record_link: {record_link}")
                except Exception as e:
                    error_msg = str(e)
                    self.logger.error(f"Failed to update Feishu bitable record for record_link {record_link}: {error_msg}")
                    # 不要中断主流程，继续执行
            
            self.logger.info(f"Successfully processed process_request API request with request_id {request_id}")
            return response
            
        except Exception as e:
            # 获取完整的堆栈跟踪信息
            import traceback
            error_traceback = traceback.format_exc()
            error_msg = str(e)
            self.logger.error(f"Error processing process_request API request with request_id {request_id}: {error_msg}\nFull traceback: {error_traceback}")
            
            error_response = ProcessRequestResponse(
                status="error",
                error=f"{error_msg} (request_id: {request_id})",
                request_id=request_id
            )
            
            # 如果提供了record_link，则尝试更新飞书多维表格记录（即使出错也要记录）
            try:
                record_link = request_data.get("record_link") if request_data else None
                if record_link:
                    # 将错误响应转换为JSON字符串格式
                    error_response_json = error_response.json()
                    # 更新飞书多维表格记录
                    await process_feishu_record_cell(record_link, "图文大纲创作结果", error_response_json)
                    self.logger.info(f"Successfully updated Feishu bitable record with error for record_link: {record_link}")
            except Exception as update_error:
                import traceback
                update_error_traceback = traceback.format_exc()
                self.logger.error(f"Failed to update Feishu bitable record with error for record_link {record_link}: {str(update_error)}\nFull traceback: {update_error_traceback}")
            
            return error_response
    
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
            # 确保任务处理器中注册了达人风格分析任务
            from core.task_processor import task_processor, extract_blogger_style
            if "blogger_style_extractor" not in task_processor.tasks:
                task_processor.register_task("blogger_style_extractor", extract_blogger_style)
            
            # 并发执行七个任务
            task_results = await task_processor.execute_tasks(request)
            self.logger.info(f"task_results graphic outline request{task_results}")
            
            # 提取record_link（如果存在）
            record_link = request.get("record_link", "")
            
            # 汇总任务结果并进行下一步处理
            processed_data = await self._aggregate_and_process(task_results, request)
            self.logger.info(f"Processing graphic outline request{processed_data}")
            
            # 将record_link添加到processed_data中
            if record_link:
                processed_data["record_link"] = record_link
                
            direction = processed_data.get("direction", "")
            # 使用正则表达式匹配方向类型
            # 扩展种草类关键词匹配，保留原有逻辑
            planting_pattern = r'(种|草|vlog|教程|技能攻略|指北|教学|秘籍|技巧|干货|开箱|展示|挑战|好物分享|穿搭|OOTD|清单|合集|推荐|日常|记录|分享|爱用|探店|打卡|方案|改造|规划|沉浸式|神器|送礼|生活方式|赛事|备赛|新手必入|解压|治愈系|Routine|翻包|翻箱|平替|科普|仪式感)'
            
            # 扩展测评类关键词匹配，保留原有逻辑
            review_pattern = r'(测|评|选购|指南|排行|榜单|盘点|选购攻略|单品测评|横向测评|对比|长期测评|深度测评|使用报告|拆解|实验|实验室|检测|硬核测评|数据测评|拉表|实测|真人实测|上脸|上身体验|红黑榜|避坑攻略|排雷|平替测评|真假对比|真伪对比|升级对比|性能测试)'
            
            # 匹配种草类内容（扩展匹配，同时保留原有"种|草|vlog"匹配）
            if re.search(planting_pattern, direction):
                # 调用豆包大模型生成种草图文规划
                planting_content = await self._generate_planting_content(processed_data)
                processed_data["planting_content"] = planting_content
                
                # 生成种草配文
                planting_captions = await self._generate_planting_captions(processed_data, planting_content)
                processed_data["planting_captions"] = planting_captions
                
            
            # 匹配测评类内容（扩展匹配，同时保留原有"测|评|选购|指南"匹配）
            elif re.search(review_pattern, direction):
                # 处理图文规划(测试)的工作
                planting_content = await self._generate_planting_content_cp(processed_data)
                processed_data["planting_content"] = planting_content
               
                
                # 生成种草配文
                planting_captions = await self._generate_planting_captions_cp(processed_data, planting_content)
                processed_data["planting_captions"] = planting_captions
                
            else:
                request_id = get_request_id()
                error_msg = f"[{request_id}] Invalid direction value: {direction}. Expected values containing planting keywords like '种草', '教程', 'vlog' etc. for first condition, or review keywords like '测评', '选购', '指南', '排行' etc. for second condition."
                self.logger.error(error_msg)
                raise ValueError(f"Invalid direction: {direction}")

            
            # 创建飞书电子表格
            blogger_link = request.get("blogger_link", "")
            record_link = request.get("record_link", "")
            
            # 从链接中提取userUuid（最后一部分）
            user_uuid = blogger_link.rstrip('/').split('/')[-1] if blogger_link else "默认主题"
            
            # 如果有user_uuid，则通过API获取用户昵称
            if user_uuid != "默认主题":
                nickname = await fetch_user_nickname(user_uuid)
                if nickname:
                    user_uuid = nickname
            
            spreadsheet_result = await self.create_feishu_sheet({
                "topic": user_uuid,
                "outline_data": processed_data,
                "record_link": record_link
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
                "B8": "",
                "B9": "",
                "C2": "",  
                "D6": "",  
                "E2": "",  
                "F6": "",  
            }


            # 解析图文规划内容
            planting_content = outline_data.get("planting_content", "")
            planting_data = []
            
            # 检查是否是JSON格式的输出
            if planting_content:
                # 首先尝试清理可能的代码块标记
                cleaned_content = planting_content.strip()
                
                # 处理可能存在的多重代码块标记
                # 循环剥离外层的代码块标记，直到无法再剥离为止
                while cleaned_content.startswith("```") and cleaned_content.endswith("```"):
                    # 提取代码块中的内容
                    lines = cleaned_content.split('\n')
                    if len(lines) >= 3:
                        # 去掉第一行和最后一行（代码块标记）
                        cleaned_content = '\n'.join(lines[1:-1]).strip()
                    else:
                        break  # 防止无限循环
                
                # 处理只有开头标记没有结尾标记的情况
                if cleaned_content.startswith("```"):
                    lines = cleaned_content.split('\n')
                    if len(lines) >= 2:
                        cleaned_content = '\n'.join(lines[1:]).strip()
                
                # 处理可能存在的语言标识（如```json）
                if cleaned_content.startswith("json"):
                    lines = cleaned_content.split('\n')
                    if len(lines) >= 2:
                        cleaned_content = '\n'.join(lines[1:]).strip()
                
                # 检查是否是JSON格式的输出
                if cleaned_content.startswith('{') and cleaned_content.endswith('}'):
                    self.logger.info(f"Attempting to parse JSON content, length: {len(cleaned_content)}")
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
                        self.logger.info(f"Successfully parsed JSON format planting content with {len(planting_data)} items")
                    except json.JSONDecodeError as e:
                        # 如果JSON解析失败，记录错误并回退到原来的解析方法
                        self.logger.error(f"Failed to parse planting content as JSON: {str(e)}")
                        self.logger.error(f"Content that failed to parse: {cleaned_content[:-1]}...")
                        planting_data = parse_planting_content(planting_content)
                else:
                    # 使用原来的解析方法
                    self.logger.info("Using regex parser for planting content")
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

            
            # 更新单元格数据
            planting_captions_data = outline_data.get("planting_captions", "")
            self.logger.info(f"Parsed planting_captions:{planting_captions_data}")
            # 解析planting_captions JSON数据
            import json
            try:
                # 首先清理可能的代码块标记
                cleaned_captions_data = planting_captions_data.strip()
                
                # 处理可能存在的多重代码块标记
                while cleaned_captions_data.startswith("```") and cleaned_captions_data.endswith("```"):
                    # 提取代码块中的内容
                    lines = cleaned_captions_data.split('\n')
                    if len(lines) >= 3:
                        # 去掉第一行和最后一行（代码块标记）
                        cleaned_captions_data = '\n'.join(lines[1:-1]).strip()
                    else:
                        break  # 防止无限循环
                
                # 处理只有开头标记没有结尾标记的情况
                if cleaned_captions_data.startswith("```"):
                    lines = cleaned_captions_data.split('\n')
                    if len(lines) >= 2:
                        cleaned_captions_data = '\n'.join(lines[1:]).strip()
                
                # 处理可能存在的语言标识（如```json）
                if cleaned_captions_data.startswith("json"):
                    lines = cleaned_captions_data.split('\n')
                    if len(lines) >= 2:
                        cleaned_captions_data = '\n'.join(lines[1:]).strip()
                
                # 尝试直接解析
                parsed_captions = json.loads(cleaned_captions_data)
                self.logger.info("Successfully parsed planting_captions as JSON")
                
                # 提取captions内容
                if isinstance(parsed_captions, dict) and "captions" in parsed_captions:
                    captions_data = parsed_captions.get("captions", {})
                    # 构造B8内容，包含标题和正文
                    titles = captions_data.get("titles", [])
                    content = captions_data.get("content", "")
                    ending = captions_data.get("ending", "")
                    
                    # 格式化标题内容
                    titles_text = "\n".join([f"标题{i+1}：{title}" for i, title in enumerate(titles)])
                    
                    # 组合B8内容
                    b8_content = f"{titles_text}\n正文：{content}\n收尾：{ending}"
                else:
                    b8_content = parsed_captions.get("content", "") if parsed_captions else ""
                
                # 提取tags内容
                if isinstance(parsed_captions, dict) and "tags" in parsed_captions:
                    tags_data = parsed_captions.get("tags", [])
                    if isinstance(tags_data, list):
                        b9_tags = " ".join(tags_data)
                    else:
                        b9_tags = str(tags_data)
                else:
                    b9_tags = parsed_captions.get("tags", "") if parsed_captions else ""
            except (json.JSONDecodeError, AttributeError, TypeError) as e:
                # 如果解析失败，尝试修复JSON字符串
                self.logger.error(f"Error parsing planting_captions JSON: {e}")
                try:
                    # 尝试修复常见的JSON问题
                    fixed_data = cleaned_captions_data
                    # 替换可能导致问题的控制字符
                    fixed_data = ''.join(ch if ord(ch) >= 32 or ch in '\n\r\t' else ' ' for ch in fixed_data)
                    # 尝试解析修复后的数据
                    parsed_captions = json.loads(fixed_data)
                    self.logger.info("Successfully parsed fixed planting_captions JSON")
                    
                    # 提取captions内容
                    if isinstance(parsed_captions, dict) and "captions" in parsed_captions:
                        captions_data = parsed_captions.get("captions", {})
                        # 构造B8内容，包含标题和正文
                        titles = captions_data.get("titles", [])
                        content = captions_data.get("content", "")
                        ending = captions_data.get("ending", "")
                        
                        # 格式化标题内容
                        titles_text = "\n".join([f"标题{i+1}：{title}" for i, title in enumerate(titles)])
                        
                        # 组合B8内容
                        b8_content = f"{titles_text}\n正文：{content}\n收尾：{ending}"
                    else:
                        b8_content = parsed_captions.get("content", "") if parsed_captions else ""
                    
                    # 提取tags内容
                    if isinstance(parsed_captions, dict) and "tags" in parsed_captions:
                        tags_data = parsed_captions.get("tags", [])
                        if isinstance(tags_data, list):
                            b9_tags = " ".join(tags_data)
                        else:
                            b9_tags = str(tags_data)
                    else:
                        b9_tags = parsed_captions.get("tags", "") if parsed_captions else ""
                except (json.JSONDecodeError, AttributeError, TypeError) as e2:
                    # 如果仍然失败，尝试使用正则表达式提取
                    self.logger.error(f"Error parsing fixed planting_captions JSON: {e2}")
                    try:
                        import re
                        # 使用正则表达式提取titles
                        titles_match = re.search(r'"titles"\s*:\s*(\[[^\]]*\])', cleaned_captions_data)
                        titles = []
                        if titles_match:
                            titles_str = titles_match.group(1)
                            # 简单解析标题数组
                            # 支持带转义字符的字符串匹配
                            titles = re.findall(r'"((?:[^"\\]|\\.)*)"', titles_str)
                            # 处理转义字符
                            titles = [title.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t') for title in titles]
                        
                        # 使用正则表达式提取content
                        content_match = re.search(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', cleaned_captions_data)
                        content = content_match.group(1) if content_match else ""
                        # 处理转义字符
                        content = content.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
                        
                        # 使用正则表达式提取ending
                        ending_match = re.search(r'"ending"\s*:\s*"((?:[^"\\]|\\.)*)"', cleaned_captions_data)
                        ending = ending_match.group(1) if ending_match else ""
                        # 处理转义字符
                        ending = ending.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
                        
                        # 使用正则表达式提取tags
                        tags_match = re.search(r'"tags"\s*:\s*(\[[^\]]*\])', cleaned_captions_data)
                        tags = []
                        if tags_match:
                            tags_str = tags_match.group(1)
                            # 简单解析标签数组
                            # 支持带转义字符的字符串匹配
                            tags = re.findall(r'"((?:[^"\\]|\\.)*)"', tags_str)
                            # 处理转义字符
                            tags = [tag.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t') for tag in tags]
                        
                        # 格式化标题内容
                        titles_text = "\n".join([f"标题{i+1}：{title}" for i, title in enumerate(titles)])
                        
                        # 组合B8内容
                        b8_content = f"{titles_text}\n正文：{content}\n收尾：{ending}"
                        
                        # 组合B9标签
                        b9_tags = " ".join(tags)
                    except Exception as e3:
                        # 如果所有方法都失败，使用原始数据
                        self.logger.error(f"Error parsing planting_captions with regex: {e3}")
                        b8_content = planting_captions_data
                        b9_tags = ""
            cell_data.update({
                "B1": "",  
                "B2": "",  
                "B3": "",  
                "B4": "", 
                "B5": "",  
                "B6": "",  
                "B7": "",  
                "B8": b8_content,  
                "B9": b9_tags,  
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
            
            # 不再设置单元格格式，使用默认格式
            # await self._set_cell_format(spreadsheet_token, sheet_id, tenant_token, ["B1", "B2"])
            
            # 使用fill_cells_in_sheet方法填充数据
            result = await self.fill_cells_in_sheet(spreadsheet_token, sheet_id, cell_data)
            
            if result.get("status") != "success":
                raise Exception(f"Failed to fill cells: {result.get('error')}")
            
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
        
        # 获取当前请求ID
        request_id = get_request_id()
        
        try:
            # 从请求中提取数据
            topic = request.get("topic", "默认主题")
            outline_data = request.get("outline_data", {})
            record_link = request.get("record_link", None)
            
            # 如果提供了record_link，则记录日志
            if record_link:
                self.logger.info(f"Received record_link: {record_link}")
            
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
            
            # 如果提供了record_link，则更新飞书多维表格记录
            if record_link:
                try:
                    # 将结果转换为JSON字符串格式
                    result_json = json.dumps(result, ensure_ascii=False)
                    # 更新飞书多维表格记录
                    await process_feishu_record_cell(record_link, "图文大纲创作结果", result_json)
                    self.logger.info(f"Successfully updated Feishu bitable record for record_link: {record_link}")
                except DocumentVersionError as e:
                    # 特别处理文档版本冲突错误
                    error_msg = f"Document version conflict: {str(e)}"
                    self.logger.warning(f"Failed to update Feishu bitable record due to version conflict for record_link {record_link}: {error_msg}")
                except httpx.HTTPStatusError as e:
                    # 处理HTTP状态错误
                    error_msg = f"HTTP status error {e.response.status_code}: {e.response.text}"
                    self.logger.error(f"HTTP error when updating Feishu bitable record for record_link {record_link}: {error_msg}")
                except httpx.RequestError as e:
                    # 处理请求错误
                    error_msg = f"Request error: {str(e)}"
                    self.logger.error(f"Network error when updating Feishu bitable record for record_link {record_link}: {error_msg}")
                except json.JSONDecodeError as e:
                    # 处理JSON编码错误
                    error_msg = f"JSON encoding error: {str(e)}"
                    self.logger.error(f"Failed to encode result to JSON when updating Feishu bitable record for record_link {record_link}: {error_msg}")
                except Exception as e:
                    # 处理其他所有未预期的错误
                    error_msg = f"Unexpected error: {str(e)}"
                    self.logger.error(f"Unexpected error when updating Feishu bitable record for record_link {record_link}: {error_msg}")
                    # 不要中断主流程，继续执行
            
            self.logger.info(f"Successfully created Feishu sheet: {spreadsheet_token}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error creating Feishu sheet: {str(e)}")
            error_result = {
                "status": "error",
                "error": str(e),
                "request_id": request_id
            }
            
            # 如果提供了record_link，则尝试更新飞书多维表格记录（即使出错也要记录）
            try:
                record_link = request.get("record_link") if 'request' in locals() else None
                if record_link:
                    # 将错误结果转换为JSON字符串格式
                    error_result_json = json.dumps(error_result, ensure_ascii=False)
                    # 更新飞书多维表格记录
                    await process_feishu_record_cell(record_link, "图文大纲创作结果", error_result_json)
                    self.logger.info(f"Successfully updated Feishu bitable record with error for record_link: {record_link}")
            except Exception as update_error:
                self.logger.error(f"Failed to update Feishu bitable record with error for record_link {record_link}: {str(update_error)}")
            
            return error_result
    
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
            "record_link": request_data.get("record_link", ""),  # 添加record_link字段
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
            # "product_endorsement_extractor": "product_endorsement",
            #话题
            # "topic_extractor": "main_topic"
        }
        
        # 统一处理所有提取器数据
        for extractor_key, section_key in extractor_mapping.items():
            if extractor_key in aggregated_data:
                extractor_data = aggregated_data[extractor_key]
                sections[section_key] = extractor_data.get(section_key, "")
        self.logger.info(f"sections{sections}")
        processed_outline["sections"] = sections
        processed_outline["total_words"] = sum(len(str(content)) for content in sections.values())
        
        self.logger.info(f"Successfully aggregated and processed task results{processed_outline}")
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

## 强制输出格式和内容
{output_format_and_content}

## 限制
{restrictions}
"""
            
            # 使用用户提示词或系统提示词
            prompt = user_prompt if user_prompt else system_prompt
            
            # 添加日志记录输入参数
            self.logger.info(f"[_generate_planting_captions] Calling model with task_type: _generate_planting_captions")
            self.logger.debug(f"[_generate_planting_captions] Prompt: {prompt}")
            self.logger.debug(f"[_generate_planting_captions] Processed data: {processed_data}")
            self.logger.debug(f"[_generate_planting_captions] Planting content: {planting_content}")
            
            # 调用模型
            captions_content = await self.model_manager.call_model(
                "_generate_planting_captions", 
                prompt,
                response_format={"type": "json_object"}
            )
            
            # 添加日志记录模型返回结果
            self.logger.info(f"[_generate_planting_captions] Model call successful")
            self.logger.debug(f"[_generate_planting_captions] Model response: {captions_content}")
            
            # 尝试解析返回内容
            try:
                import json
                parsed_content = json.loads(captions_content)
                self.logger.debug(f"[_generate_planting_captions] Parsed JSON response: {parsed_content}")
            except json.JSONDecodeError as je:
                self.logger.warning(f"[_generate_planting_captions] Failed to parse model response as JSON: {je}")
            
        
            return captions_content
            
        except Exception as e:
            self.logger.error(f"Error generating planting captions: {str(e)}")
            # 添加堆栈跟踪信息
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return json.dumps({"content": "种草配文生成失败", "tags": ""}, ensure_ascii=False)
    
    def _extract_tags_from_content(self, content: str) -> Dict[str, str]:
        """
        从内容中提取标签部分
        
        Args:
            content: 包含标签的完整内容
            
        Returns:
            包含content和tags字段的字典
        """
        # 提取标签内容
        tags_pattern = r"- \*\*标签\*\*：(.*)"
        tags_match = re.search(tags_pattern, content)
        tags_content = ""
        
        if tags_match:
            tags_content = tags_match.group(1).strip()
            # 从原内容中移除标签行
            content = re.sub(tags_pattern, "", content).strip()
        
        # 构造返回结果，包含内容和标签
        return {
            "content": content,
            "tags": tags_content
        }
    
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
            
            # 添加日志记录输入参数
            self.logger.info(f"[_generate_planting_captions_cp] Calling model with task_type: _generate_planting_captions_cp")
            self.logger.debug(f"[_generate_planting_captions_cp] Prompt: {prompt}")
            self.logger.debug(f"[_generate_planting_captions_cp] Processed data: {processed_data}")
            self.logger.debug(f"[_generate_planting_captions_cp] Planting content: {planting_content}")
            
            # 调用模型，强制JSON输出
            captions_content = await self.model_manager.call_model(
                "_generate_planting_captions_cp", 
                prompt,
                response_format={"type": "json_object"}
            )
            
            # 添加日志记录模型返回结果
            self.logger.info(f"[_generate_planting_captions_cp] Model call successful")
            self.logger.debug(f"[_generate_planting_captions_cp] Model response: {captions_content}")
            
            # 尝试解析返回内容
            try:
                import json
                parsed_content = json.loads(captions_content)
                self.logger.debug(f"[_generate_planting_captions_cp] Parsed JSON response: {parsed_content}")
            except json.JSONDecodeError as je:
                self.logger.warning(f"[_generate_planting_captions_cp] Failed to parse model response as JSON: {je}")
            
            # 返回JSON格式的配文内容
            return captions_content
            
        except Exception as e:
            self.logger.error(f"Error generating planting captions: {str(e)}")
            # 添加堆栈跟踪信息
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return json.dumps({"content": "测评配文生成失败", "tags": ""}, ensure_ascii=False)
    
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
            requirements = processed_data.get("requirements", "")  # 内츠方向建议
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
            output_format_template = prompt_template.get("output_format", "")
            # 手动替换占位符以避免KeyError
            output_format = output_format_template.replace('{picture_number}', str(picture_number)).replace('{content_direction}', '')
            
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
            
            # 添加日志记录输入参数
            self.logger.info(f"[_generate_planting_content] Calling model with task_type: _generate_planting_content")
            self.logger.debug(f"[_generate_planting_content] Prompt: {prompt}")
            self.logger.debug(f"[_generate_planting_content] Processed data: {processed_data}")
            
            # 调用模型时添加response_format参数，要求JSON格式输出
            planting_content = await self.model_manager.call_model(
                "_generate_planting_content", 
                prompt, 
                response_format={"type": "json_object"}
            )
            
            # 添加日志记录模型返回结果
            self.logger.info(f"[_generate_planting_content] Model call successful")
            self.logger.debug(f"[_generate_planting_content] Model response: {planting_content}")
            
            # 尝试解析返回内容
            try:
                import json
                parsed_content = json.loads(planting_content)
                self.logger.debug(f"[_generate_planting_content] Parsed JSON response: {parsed_content}")
            except json.JSONDecodeError as je:
                self.logger.warning(f"[_generate_planting_content] Failed to parse model response as JSON: {je}")
            
            return planting_content
            
        except Exception as e:
            self.logger.error(f"Error generating planting content: {str(e)}")
            # 添加堆栈跟踪信息
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
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
            requirements = processed_data.get("requirements", "")  # 内茨方向建议
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
            output_format_template = prompt_template.get("output_format", "")
            # 手动替换占位符以避免KeyError
            output_format = output_format_template.replace('{picture_number}', str(picture_number)).replace('{content_direction}', '')
            
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
            
            # 添加日志记录输入参数
            self.logger.info(f"[_generate_planting_content_cp] Calling model with task_type: _generate_planting_content_cp")
            self.logger.debug(f"[_generate_planting_content_cp] Prompt: {prompt}")
            self.logger.debug(f"[_generate_planting_content_cp] Processed data: {processed_data}")
            
            # 调用模型时添加response_format参数，要求JSON格式输出
            planting_content = await self.model_manager.call_model(
                "_generate_planting_content_cp", 
                prompt, 
                response_format={"type": "json_object"}
            )
            
            # 添加日志记录模型返回结果
            self.logger.info(f"[_generate_planting_content_cp] Model call successful")
            self.logger.debug(f"[_generate_planting_content_cp] Model response: {planting_content}")
            
            # 尝试解析返回内容
            try:
                import json
                parsed_content = json.loads(planting_content)
                self.logger.debug(f"[_generate_planting_content_cp] Parsed JSON response: {parsed_content}")
            except json.JSONDecodeError as je:
                self.logger.warning(f"[_generate_planting_content_cp] Failed to parse model response as JSON: {je}")
            
            return planting_content
            
        except Exception as e:
            self.logger.error(f"Error generating planting content: {str(e)}")
            # 添加堆栈跟踪信息
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return "测评图文规划生成失败"


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
                # 处理转义字符
                remark = remark.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
            
            # 处理planning中的转义字符
            planning = planning.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
            
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
                # 处理转义字符
                remark = remark.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
            
            # 处理planning中的转义字符
            planning = planning.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
            
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
                        
                        # 处理planning中的转义字符
                        planning = planning.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
                        
                        # 提取备注
                        remark = ""
                        remark_match = re.search(r'备注：(.*?)(?=\n图片类型：|\Z)', section, re.DOTALL)
                        if remark_match:
                            remark = remark_match.group(1).strip()
                            # 处理转义字符
                            remark = remark.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
                        
                        image_info = {
                            "image_type": image_type,
                            "planning": planning,
                            "remark": remark,
                            "caption": ""
                        }
                        result.append(image_info)
    
    return result


