import sys
import os
from pydantic import BaseModel
from typing import Optional
import asyncio

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base_agent import BaseAgent
from models.doubao import get_doubao_model
from models.feishu import get_feishu_client, DocumentVersionError
from utils.ac_automaton import ACAutomaton
from core.request_context import get_request_id


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
    request_id: Optional[str] = None


class FeishuDocumentRequest(BaseModel):
    """飞书文档处理请求模型"""
    document_id: str
    # 可以添加更多处理选项


class FeishuMessageRequest(BaseModel):
    """飞书消息处理请求模型"""
    message_id: str
    text: str


class TextReviewerAgent(BaseAgent):
    """文本审稿智能体，用于处理文本中的错别字和语言逻辑问题"""
    
    def __init__(self):
        super().__init__("text_reviewer")
        self.llm = get_doubao_model()
        self.feishu_client = get_feishu_client()
        # 添加文档处理锁，防止同一文档并发处理
        self.document_locks = {}
        # 添加特定路由
        self.router.post("/review", response_model=TextReviewResponse)(self.review_text)
        self.router.post("/feishu/document", response_model=dict)(self.process_feishu_document)
        self.router.post("/feishu/message", response_model=dict)(self.process_feishu_message)
        
        # 初始化AC自动机并加载违禁词
        self._init_prohibited_words()
    
    def _init_prohibited_words(self):
        """
        初始化违禁词AC自动机
        """
        self.logger.info("开始初始化违禁词AC自动机")
        try:
            self.ac_automaton = ACAutomaton()
            
            # 从目录中的所有文本文件构建AC自动机
            prohibited_words_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                              "prohibited_words_output_v2")
            
            if os.path.exists(prohibited_words_dir):
                self.ac_automaton.build_from_directory(prohibited_words_dir)
                self.logger.info("违禁词AC自动机初始化完成")
            else:
                self.logger.warning(f"违禁词目录不存在: {prohibited_words_dir}")
                
        except Exception as e:
            self.logger.error(f"初始化违禁词AC自动机失败: {e}")
            self.ac_automaton = None
    
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
        
        # 获取当前请求ID
        request_id = get_request_id()
        
        # 使用AC自动机检测并标记违禁词
        marked_text = self._mark_prohibited_words(request.text)
        self.logger.info(f"Marked text: {marked_text}")
        # 构建提示词
        prompt = f"""
        请作为专业内容审核员，对以下文本进行全面审查和优化：

    ​审核文本：​​
    {marked_text}

    一、核心审核要求
    ​错别字纠正​：精准识别并修正所有拼写错误、错别字和语法错误
    语句通顺​：确保句子结构合理，表达清晰流畅，语义相近的句子删除。
    ​违禁词处理​：对原文中{{}}标记的违禁词必须替换（只能替换不能删除），替换后删除{{}}标记。
    ​逻辑优化​：调整内容逻辑顺序，确保产品卖点介绍符合使用流程（如洗烘套装先洗衣机后烘干机）和认知逻辑（如康师傅喝开水先工艺后口感）
    ​口语化转换​：将书面化表达转换为自然口语表述（如"承托"改为"支撑"等），特别适合口播场景
    ​原意保持​：所有修改不得改变原文核心含义和意图
    二、输出格式要求
    直接返回修改后的完整文本
    在完整的修改后的文本之后，添加一段详细的修改说明，每一处的违禁词替代或者修改都必须做说明,对语句的优化和删出也得详细说明。
    使用{request.language}语言输出
    确保文本格式与原文一致
    三、审核标准参考
    采用千万级专业词库和数十亿训练语料的检测标准
    符合内容安全与合规性要求
    保持语言自然流畅且适合口语传播
    ​请现在开始审核并返回修改后的文本
        """
        #不添加任何额外说明或解释
        if request.style:
            prompt += f"\n5. 文本风格要求：{request.style}"
        
        # 调用大模型
        corrected_text = await self.llm.generate_text(prompt)
        
        # 构造响应
        response = TextReviewResponse(
            original_text=request.text,
            corrected_text=corrected_text,
            errors=[],  # 在实际应用中可以详细列出错误
            suggestions=[],  # 在实际应用中可以提供改进建议
            request_id=request_id
        )
        
        self.logger.info("Text review completed")
        return response
    
    def _mark_prohibited_words(self, text: str) -> str:
        """
        使用AC自动机检测文本中的违禁词，并用{}标记
        
        Args:
            text: 要检测的文本
            
        Returns:
            标记了违禁词的文本
        """
        if not self.ac_automaton:
            self.logger.warning("AC自动机未初始化，无法检测违禁词")
            return text

        matches = self.ac_automaton.search(text)
        if not matches:
            return text

        # Sort matches by start index descending to avoid offset issues
        matches.sort(key=lambda x: x[1], reverse=True)

        # Use a list for efficient insertions
        result = list(text)

        for word, start, end in matches:
            # Replace the word with the wrapped version
            result[start:end] = ['{'] + list(word) + ['}']

        return ''.join(result)
    
    async def process_feishu_document(self, request: FeishuDocumentRequest) -> dict:
        """
        处理飞书文档
        
        Args:
            request: 飞书文档处理请求
            
        Returns:
            处理结果
        """
        document_id = request.document_id
        self.logger.info(f"Processing Feishu document: {document_id}")
        
        # 获取当前请求ID
        request_id = get_request_id()
        
        # 获取文档锁，防止同一文档并发处理
        if document_id not in self.document_locks:
            self.document_locks[document_id] = asyncio.Lock()
        
        lock = self.document_locks[document_id]
        
        async with lock:
            try:
                # 读取飞书文档内容
                doc_data = await self.feishu_client.read_document(document_id)
                doc_revision = doc_data.get("revision", 0)
                doc_content = doc_data.get("content", {})
                
                self.logger.info(f"Document {document_id} revision: {doc_revision}")
                
                # 检查是否为电子表格
                doc_meta = doc_data.get("meta", {})
                doc_type = doc_meta.get("type", "")
                
                if doc_type == "sheet":
                    # 处理电子表格
                    self.logger.info(f"Processing Feishu spreadsheet: {document_id}")
                    return await self._process_feishu_spreadsheet(document_id, request_id)
                
                # 从文档内容中提取文本
                original_text = self._extract_text_from_document(doc_content)
                
                # 如果没有提取到文本，则使用示例文本
                if not original_text:
                    original_text = "示例文本内容"
                    self.logger.warning(f"No text extracted from document {document_id}, using sample text")
                
                # 创建审稿请求
                review_request = TextReviewRequest(
                    text=original_text,
                    language="zh"
                )
                
                # 处理文本
                review_result = await self.review_text(review_request)
                
                # 构造写入内容
                # 根据飞书API文档，正确的格式应该包含children字段
                write_content = {
                    "children": [
                        {
                            "block_type": 2,  # paragraph
                            "text": {
                                "elements": [
                                    {
                                        "text_run": {
                                            "content": review_result.corrected_text
                                        }
                                    }
                                ]
                            }
                        }
                    ],
                    "index": 0  # 插入到开头位置
                }
                
                # 将处理结果写回飞书文档，带上版本号以防止冲突
                await self.feishu_client.write_document(document_id, write_content, doc_revision)
                
                result = {
                    "status": "success",
                    "document_id": document_id,
                    "revision": doc_revision,
                    "original_text": original_text,
                    "corrected_text": review_result.corrected_text,
                    "request_id": request_id
                }
                
                self.logger.info(f"Successfully processed Feishu document: {document_id}")
                return result
                
            except DocumentVersionError as e:
                self.logger.warning(f"Document version conflict when processing {document_id}: {str(e)}")
                return {
                    "status": "conflict",
                    "document_id": document_id,
                    "error": "Document was modified during processing. Please try again.",
                    "details": str(e),
                    "request_id": request_id
                }
            except Exception as e:
                self.logger.error(f"Error processing Feishu document {document_id}: {str(e)}")
                return {
                    "status": "error",
                    "document_id": document_id,
                    "error": str(e),
                    "request_id": request_id
                }
    
    async def _process_feishu_spreadsheet(self, spreadsheet_token: str, request_id: str) -> dict:
        """
        处理飞书电子表格
        
        Args:
            spreadsheet_token: 电子表格token
            request_id: 请求ID
            
        Returns:
            处理结果
        """
        try:
            # 获取飞书访问令牌
            tenant_token = await self.feishu_client.get_tenant_access_token()
            
            # 获取电子表格元数据，确定工作表
            import httpx
            meta_url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/metainfo"
            headers = {
                "Authorization": f"Bearer {tenant_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            async with httpx.AsyncClient() as client:
                # 获取电子表格元数据
                meta_response = await client.get(meta_url, headers=headers)
                meta_response.raise_for_status()
                meta_result = meta_response.json()
                
                if meta_result.get("code") != 0:
                    raise Exception(f"Failed to get spreadsheet metadata: {meta_result}")
                
                # 获取第一个工作表的sheet_id (根据实际响应结构调整)
                if "data" in meta_result and "sheets" in meta_result["data"] and len(meta_result["data"]["sheets"]) > 0:
                    first_sheet = meta_result["data"]["sheets"][0]
                    # 检查是否存在sheet_id字段，如果不存在则使用其他可能的字段
                    sheet_id = first_sheet.get("sheetId", first_sheet.get("sheet_id", first_sheet.get("index", "0")))
                else:
                    raise Exception(f"Unexpected metainfo API response structure: {meta_result}")
                
                self.logger.info(f"Using sheet_id: {sheet_id}")
                
                # 读取电子表格内容
                read_url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values_batch_get"
                read_params = {
                    "ranges": [f"{sheet_id}!A1:Z1000"]  # 读取较大范围的数据
                }
                
                read_response = await client.get(read_url, headers=headers, params=read_params)
                read_response.raise_for_status()
                read_result = read_response.json()
                
                if read_result.get("code") != 0:
                    raise Exception(f"Failed to read spreadsheet data: {read_result}")
                
                # 提取文本内容
                value_ranges = read_result.get("data", {}).get("valueRanges", [])
                if not value_ranges:
                    original_text = "示例文本内容"
                    self.logger.warning(f"No data found in spreadsheet {spreadsheet_token}, using sample text")
                else:
                    # 从二维数组中提取所有文本
                    values = value_ranges[0].get("values", [])
                    text_parts = []
                    for row in values:
                        for cell in row:
                            if cell and isinstance(cell, str):
                                text_parts.append(cell)
                    
                    original_text = "\n".join(text_parts)
                    if not original_text:
                        original_text = "示例文本内容"
                        self.logger.warning(f"No text extracted from spreadsheet {spreadsheet_token}, using sample text")
                
                # 创建审稿请求
                review_request = TextReviewRequest(
                    text=original_text,
                    language="zh"
                )
                
                # 处理文本
                review_result = await self.review_text(review_request)
                
                # 将处理结果写回电子表格的第一个单元格
                write_url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values"
                write_payload = {
                    "valueRange": {
                        "range": f"{sheet_id}!A1:A1",  # 使用正确的范围格式
                        "values": [[review_result.corrected_text]]
                    }
                }
                
                write_response = await client.put(write_url, headers=headers, json=write_payload)
                write_response.raise_for_status()
                write_result = write_response.json()
                
                if write_result.get("code") != 0:
                    raise Exception(f"Failed to write data to spreadsheet: {write_result}")
                
                result = {
                    "status": "success",
                    "document_id": spreadsheet_token,
                    "original_text": original_text,
                    "corrected_text": review_result.corrected_text,
                    "request_id": request_id
                }
                
                self.logger.info(f"Successfully processed Feishu spreadsheet: {spreadsheet_token}")
                return result
                
        except Exception as e:
            self.logger.error(f"Error processing Feishu spreadsheet {spreadsheet_token}: {str(e)}")
            return {
                "status": "error",
                "document_id": spreadsheet_token,
                "error": str(e),
                "request_id": request_id
            }

    def _extract_text_from_document(self, doc_content: dict) -> str:
        """
        从飞书文档内容中提取文本
        
        Args:
            doc_content: 飞书文档内容
            
        Returns:
            提取的文本内容
        """
        # 飞书文档内容结构解析
        # 根据飞书文档API，内容在blocks字段中
        blocks = doc_content.get("items", [])  # 使用items而不是blocks
        
        if not blocks:
            # 如果items为空，尝试直接从content中获取blocks
            blocks = doc_content.get("blocks", [])
            
        if not blocks:
            return ""
        
        text_parts = []
        
        # 遍历所有块，提取文本内容
        for block in blocks:
            # 根据飞书文档API结构，处理不同类型的块
            block_type = block.get("block_type")
            
            # 处理页面块
            if "page" in block:
                elements = block["page"].get("elements", [])
                for element in elements:
                    if "text_run" in element:
                        content = element["text_run"].get("content", "")
                        if content:
                            text_parts.append(content)
            
            # 处理文本块
            elif "text" in block:
                elements = block["text"].get("elements", [])
                for element in elements:
                    if "text_run" in element:
                        content = element["text_run"].get("content", "")
                        if content:
                            text_parts.append(content)
            
            # 处理段落块
            elif block_type == 2:  # paragraph
                children = block.get("children", [])
                for child in children:
                    if "text_run" in child:
                        content = child["text_run"].get("content", "")
                        if content:
                            text_parts.append(content)
            
            # 处理标题块
            elif block_type in [1, 3, 4, 5, 6, 7, 8, 9]:  # heading blocks
                if "heading" + str(block_type) in block:
                    heading = block["heading" + str(block_type)]
                    if "elements" in heading:
                        elements = heading["elements"]
                        for element in elements:
                            if "text_run" in element:
                                content = element["text_run"].get("content", "")
                                if content:
                                    text_parts.append(content)
        
        # 将所有文本部分连接起来
        return "\n".join(text_parts)
    
    async def process_feishu_message(self, request: FeishuMessageRequest) -> dict:
        """
        处理飞书消息
        
        Args:
            request: 飞书消息处理请求
            
        Returns:
            处理结果
        """
        self.logger.info(f"Processing Feishu message: {request.message_id}")
        
        # 获取当前请求ID
        request_id = get_request_id()
        
        try:
            # 创建审稿请求
            review_request = TextReviewRequest(
                text=request.text,
                language="zh"
            )
            
            # 处理文本
            review_result = await self.review_text(review_request)
            
            # 回复消息
            await self.feishu_client.reply_message(request.message_id, review_result.corrected_text)
            
            result = {
                "status": "success",
                "message_id": request.message_id,
                "original_text": request.text,
                "corrected_text": review_result.corrected_text,
                "request_id": request_id
            }
            
            self.logger.info(f"Successfully processed Feishu message: {request.message_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing Feishu message {request.message_id}: {str(e)}")
            return {
                "status": "error",
                "message_id": request.message_id,
                "error": str(e),
                "request_id": request_id
            }