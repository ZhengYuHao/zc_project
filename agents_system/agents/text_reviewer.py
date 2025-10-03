import sys
import os
from typing import Dict, Any, List, Optional
import asyncio
import json
from pydantic import BaseModel

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base_agent import BaseAgent
from models.feishu import get_feishu_client, DocumentVersionError
from utils.ac_automaton import ACAutomaton
from core.request_context import get_request_id
from models.model_manager import ModelManager


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
    
    def __init__(self, model_manager: ModelManager):
        super().__init__("text_reviewer")
        self.feishu_client = get_feishu_client()
        # 添加文档处理锁，防止同一文档并发处理
        self.document_locks = {}
        # 添加特定路由
        self.router.post("/review", response_model=TextReviewResponse)(self.review_text)
        self.router.post("/feishu/document", response_model=dict)(self.process_feishu_document)
        self.router.post("/feishu/message", response_model=dict)(self.process_feishu_message)
        
        # 模型管理器
        self.model_manager = model_manager
        
        # 初始化AC自动机并加载违禁词
        self.ac_automaton = ACAutomaton()
        # self._init_prohibited_words()
    
    def _init_prohibited_words(self):
        """
        初始化违禁词AC自动机
        """
        self.logger.info("开始初始化违禁词AC自动机")
        try:
            # 从目录中的所有文本文件构建AC自动机
            prohibited_words_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                              "prohibited_words_output_v2")
            
            if os.path.exists(prohibited_words_dir):
                # self.ac_automaton.build_from_directory(prohibited_words_dir)
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
        对文本进行审稿
        
        Args:
            request: 文本审稿请求
            
        Returns:
            文本审稿结果
        """
        self.logger.info(f"Reviewing text with DeepSeek model: {request.text[:50]}...")
        
        # 获取当前请求ID
        request_id = get_request_id()
        
        # 使用AC自动机检测并标记违禁词
        # self.logger.info(f"[违禁词处理前] 文本: {request.text}")
        # marked_text = self._mark_prohibited_words(request.text)
        # self.logger.info(f"[违禁词处理后] 文本: {marked_text}")
        # 构建提示词
    # ​违禁词处理​：替换所有用{{}}标记的违禁词（只能替换不能删除），替换后删除{{}}标记。
    # ​口语化转换​：将书面化表达转换为自然口语表述（如"承托"改为"支撑"等），特别适合口播场景
    # ​原意保持​：所有修改不得改变原文核心含义和意图
        marked_text = request.text
        prompt = f"""
        请作为专业内容审核员，对以下文本进行全面审查和优化：

    ​审核文本：​​
    {marked_text}

    一、核心审核要求
    ​错别字纠正​：精准识别并修正所有拼写错误、错别字和语法错误
    语句通顺​：确保句子结构合理，表达清晰流畅，语义相近的句子删除。
    
    ​逻辑优化​：调整内容逻辑顺序，确保产品卖点介绍符合使用流程（如洗烘套装先洗衣机后烘干机）和认知逻辑（如康师傅喝开水先工艺后口感）
    
    ​原意保持​：所有修改不得改变原文核心含义和意图
    二、输出格式要求
    直接返回修改后的完整文本
    不添加任何额外说明或解释！！！！
    使用{request.language}语言输出
    确保文本格式与原文一致
    三、审核标准参考
    采用千万级专业词库和数十亿训练语料的检测标准
    符合内容安全与合规性要求
    保持语言自然流畅且适合口语传播
    ​请现在开始审核并返回修改后的文本。如果文本已经完美无需修改，请直接返回原始文本内容，不要添加任何说明。
        """
        
        if request.style:
            prompt += f"\n5. 文本风格要求：{request.style}"
        
        # 调用大模型（通过模型管理器）
        corrected_text = await self.model_manager.call_model("text_review", prompt)
        
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
    
    def _extract_text_from_document(self, doc_content: Dict[str, Any]) -> str:
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
    
    def _get_first_text_block_id(self, doc_content: Dict[str, Any]) -> Optional[str]:
        """
        获取文档中第一个文本块的ID，用于更新
        
        Args:
            doc_content: 飞书文档内容
            
        Returns:
            第一个文本块的ID，如果找不到则返回None
        """
        self.logger.info(f"Document content structure: {json.dumps(doc_content, ensure_ascii=False, indent=2)[:1000]}...")
        
        # 飞书文档内容结构解析
        blocks = doc_content.get("items", [])
        
        if not blocks:
            blocks = doc_content.get("blocks", [])
            
        if not blocks:
            self.logger.warning("No blocks found in document content")
            return None
        
        self.logger.info(f"Found {len(blocks)} blocks in document")
        
        # 查找第一个文本块
        for i, block in enumerate(blocks):
            self.logger.info(f"Block {i}: {json.dumps(block, ensure_ascii=False)[:200]}...")
            block_id = block.get("block_id")
            block_type = block.get("block_type")
            
            self.logger.info(f"Block ID: {block_id}, Block Type: {block_type}")
            
            # 查找段落块(类型为2)
            if block_type == 2 and block_id:
                self.logger.info(f"Found first text block with ID: {block_id}")
                return block_id
                
        self.logger.warning("No text block (type 2) found in document")
        return None
    
    def _mark_prohibited_words(self, text: str) -> str:
        """
        使用AC自动机检测并标记违禁词
        
        Args:
            text: 输入文本
            
        Returns:
            标记后的文本
        """
        if not text or not self.ac_automaton:
            return text
        
        # 查找所有匹配的违禁词
        matches = self.ac_automaton.search(text)
        
        # 输出违禁词匹配日志
        if matches:
            self.logger.info(f"发现违禁词: {matches}")
        else:
            self.logger.info("未发现违禁词")
        
        if not matches:
            return text
        
        # 按照位置逆序排列，从后往前替换，避免位置偏移
        matches.sort(key=lambda x: x[1], reverse=True)
        
        # 标记违禁词
        marked_text = text
        for word, start, end in matches:
            # 检查是否为误匹配，例如单个数字或过于常见的词汇
            if self._is_false_positive(word, text, start, end):
                self.logger.info(f"跳过误匹配的违禁词: {word} 位置: [{start}:{end}] 上下文: [{text[max(0, start-10):end+10]}]")
                continue
            
            # 记录匹配到的违禁词及上下文
            context_start = max(0, start - 10)
            context_end = min(len(text), end + 10)
            context = text[context_start:context_end]
            self.logger.info(f"匹配到违禁词: {word} 位置: [{start}:{end}] 上下文: [{context}]")
            
            # 执行替换
            original_fragment = marked_text[start:end]
            new_fragment = f"{{{word}}}"
            marked_text = marked_text[:start] + new_fragment + marked_text[end:]
            
            self.logger.info(f"替换违禁词: {word} 位置: {start} 新文本片段: ...{marked_text[max(0, start-20):start+len(new_fragment)+20]}...")
        
        self.logger.info(f"原始文本: {text}")
        self.logger.info(f"标记后文本: {marked_text}")
        
        return marked_text
    
    def _is_false_positive(self, word: str, text: str, start: int, end: int) -> bool:
        """
        判断是否为误匹配的违禁词
        
        Args:
            word: 匹配到的词
            text: 原始文本
            start: 匹配开始位置
            end: 匹配结束位置
            
        Returns:
            是否为误匹配
        """
        # 单个数字通常不是违禁词
        if word.isdigit() and len(word) == 1:
            return True
        
        # 单个字符通常不是违禁词（除非是特殊字符）
        if len(word) == 1 and word.isalpha():
            # 检查前后字符是否也是字母或数字，如果是，则可能是误匹配
            if (start > 0 and text[start-1].isalnum()) or (end < len(text) and text[end].isalnum()):
                return True
        
        # 常见词汇但可能被误判为违禁词的词
        common_words = {"第一", "最后", "最新", "最好", "最高", "最多", "最少", "最低", "最新"}
        if word in common_words:
            # 检查是否在特定语境下（如数字前）才可能是违禁词
            if start > 0 and text[start-1].isdigit():
                return True
        
        return False
    
    async def process_feishu_document(self, request: FeishuDocumentRequest) -> dict:
        """
        处理飞书文档
        
        Args:
            request: 飞书文档处理请求
            
        Returns:
            处理结果
        """
        # 从URL中提取文档ID（如果输入的是完整URL）
        document_id = request.document_id
        if document_id.startswith("http"):
            # 提取URL最后一部分作为文档ID
            document_id = document_id.rstrip('/').split('/')[-1]
            self.logger.info(f"Extracted document ID from URL: {document_id}")
        
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
                    return await self._process_feishu_spreadsheet(document_id, request_id or "")
                
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
                
                # 获取文档中的第一个文本块ID用于更新
                first_text_block_id = self._get_first_text_block_id(doc_content)
                
                if first_text_block_id:
                    # 使用更新块接口更新第一个文本块的内容
                    update_content = {
                        "elements": [
                            {
                                "text_run": {
                                    "content": review_result.corrected_text
                                }
                            }
                        ]
                    }
                    
                    self.logger.info(f"Attempting to update block {first_text_block_id} with content: {review_result.corrected_text}")
                    
                    # 更新特定块的内容
                    await self.feishu_client.update_block(document_id, first_text_block_id, {"text": update_content})
                else:
                    # 如果找不到合适的块进行更新，则使用原来的写入方式
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
                        ]
                        # 移除index参数，使用batch_delete方式实现内容替换而不是插入
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
                
                # 提取文本内容及其单元格位置
                value_ranges = read_result.get("data", {}).get("valueRanges", [])
                if not value_ranges:
                    original_text = "示例文本内容"
                    self.logger.warning(f"No data found in spreadsheet {spreadsheet_token}, using sample text")
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
                    
                    # 返回结果
                    return {
                        "status": "success",
                        "document_id": spreadsheet_token,
                        "request_id": request_id
                    }
                else:
                    # 从二维数组中提取所有文本及其位置
                    cell_data = {}  # 存储单元格数据 { "A1": "内容", "B1": "内容", ...}
                    values = value_ranges[0].get("values", [])
                    for row_index, row in enumerate(values):
                        for col_index, cell in enumerate(row):
                            if cell and isinstance(cell, str) and cell.strip():
                                # 将行列索引转换为单元格引用 (如 0,0 -> A1)
                                cell_ref = self._index_to_cell_ref(col_index, row_index)
                                cell_data[cell_ref] = cell.strip()
                    
                    if not cell_data:
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
                        
                        # 返回结果
                        return {
                            "status": "success",
                            "document_id": spreadsheet_token,
                            "request_id": request_id
                        }
                    else:
                        # 对所有单元格内容进行违禁词标记
                        marked_cell_data = {}
                        for cell_ref, content in cell_data.items():
                            # self.logger.info(f"[违禁词处理前] 单元格: {cell_ref}, 内容: {content}")
                            # marked_content = self._mark_prohibited_words(content)
                            marked_content = content
                            marked_cell_data[cell_ref] = marked_content
                            # self.logger.info(f"[违禁词处理后] 单元格: {cell_ref}, 内容: {marked_content}")
                        
                        # 构建JSON格式的单元格数据用于模型处理
                        json_cell_data = json.dumps(marked_cell_data, ensure_ascii=False, indent=2)
                        
                        # 构建提示词
                        prompt = f"""
你是一个专业的文本审核员，专注于电子表格内容的错别字校正和语义逻辑优化。

输入格式：
一个JSON对象，键为单元格坐标（如"A1"、"B2"），值为单元格内容。

输出格式：
严格按照输入的JSON格式返回，键为单元格坐标，值为审核后的内容，不要有任何额外说明。

审核要求：
1. 错别字纠正：找出并修正所有错别字和语法错误
2. 语句优化：确保句子结构合理，表达清晰流畅
3. 保持原意：所有修改不能改变原文的核心意思
4. 位置保持：严格按照原始单元格坐标返回内容，不要添加或删除单元格

原始数据：
{json_cell_data}
"""
                        self.logger.info(f"调用大模型处理整个表格，单元格数量: {len(marked_cell_data)}")
                        # 调用大模型处理整个表格（通过模型管理器）
                        corrected_json_text = await self.model_manager.call_model("text_review", prompt)
                        self.logger.info(f"调用大模型处理整个表格后: {corrected_json_text}")
                        
                        # 解析处理后的JSON数据
                        try:
                            corrected_cell_data = json.loads(corrected_json_text)
                        except json.JSONDecodeError as e:
                            self.logger.error(f"解析模型返回的JSON数据失败: {e}")
                            # 回退到原始内容
                            corrected_cell_data = marked_cell_data
                        
                        # 使用批量写入接口一次性写回所有数据
                        write_data = []
                        write_errors = []  # 记录写入错误
                        
                        # 处理模型返回的数据
                        for cell_ref, content in corrected_cell_data.items():
                            try:
                                self.logger.info(f"准备写回单元格 {cell_ref}，内容: '{content}'")
                                
                                # 清理处理后的文本，确保不包含提示词
                                cleaned_content = self._clean_model_response(content)
                                self.logger.info(f"清理后的内容: '{cleaned_content}'")
                                
                                # 检查内容是否为空
                                if not cleaned_content.strip():
                                    self.logger.warning(f"模型返回空内容，使用标记后的内容: '{marked_cell_data.get(cell_ref, cell_data.get(cell_ref, ''))}'")
                                    cleaned_content = marked_cell_data.get(cell_ref, cell_data.get(cell_ref, ""))
                                
                                # 再次检查清理后的内容是否为空
                                if not cleaned_content.strip():
                                    self.logger.warning(f"清理后内容为空，使用标记后的内容: '{marked_cell_data.get(cell_ref, cell_data.get(cell_ref, ''))}'")
                                    cleaned_content = marked_cell_data.get(cell_ref, cell_data.get(cell_ref, ""))
                                
                                # 记录即将写入电子表格的数据
                                self.logger.info(f"[批量写入准备] 单元格: {cell_ref}, 内容: '{cleaned_content}'")
                                
                                # 添加到批量写入数据中
                                write_data.append({
                                    "range": f"{sheet_id}!{cell_ref}:{cell_ref}",
                                    "values": [[cleaned_content]]
                                })
                            except Exception as e:
                                error_msg = f"处理单元格 {cell_ref} 时出错: {str(e)}"
                                self.logger.error(error_msg)
                                write_errors.append(error_msg)
                        
                        # 处理原始数据中存在但模型返回结果中没有的单元格
                        for cell_ref in marked_cell_data.keys():
                            if cell_ref not in corrected_cell_data:
                                try:
                                    original_marked_content = marked_cell_data.get(cell_ref, cell_data.get(cell_ref, ""))
                                    self.logger.info(f"[补充写入] 单元格: {cell_ref}, 内容: '{original_marked_content}'")
                                    
                                    # 添加到批量写入数据中
                                    write_data.append({
                                        "range": f"{sheet_id}!{cell_ref}:{cell_ref}",
                                        "values": [[original_marked_content]]
                                    })
                                except Exception as e:
                                    error_msg = f"[补充写入] 处理单元格 {cell_ref} 时出错: {str(e)}"
                                    self.logger.error(error_msg)
                                    write_errors.append(error_msg)
                        
                        # 执行批量写入操作
                        if write_data:
                            try:
                                batch_write_url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values_batch_update"
                                batch_write_payload = {
                                    "valueRanges": write_data
                                }
                                
                                self.logger.info(f"执行批量写入，共 {len(write_data)} 个单元格")
                                batch_write_response = await client.post(batch_write_url, headers=headers, json=batch_write_payload)
                                batch_write_response.raise_for_status()
                                batch_write_result = batch_write_response.json()
                                
                                if batch_write_result.get("code") != 0:
                                    error_msg = f"批量写入失败: {batch_write_result}"
                                    self.logger.error(error_msg)
                                    write_errors.append(error_msg)
                                else:
                                    self.logger.info(f"批量写入成功，共写入 {len(write_data)} 个单元格")
                            except Exception as e:
                                error_msg = f"批量写入时出错: {str(e)}"
                                self.logger.error(error_msg)
                                write_errors.append(error_msg)
                        else:
                            self.logger.warning("没有数据需要写入")
                
                result = {
                    "status": "success",
                    "document_id": spreadsheet_token,
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

    def _index_to_cell_ref(self, col_index: int, row_index: int) -> str:
        """
        将行列索引转换为单元格引用 (如 0,0 -> A1)
        
        Args:
            col_index: 列索引 (从0开始)
            row_index: 行索引 (从0开始)
            
        Returns:
            单元格引用 (如 A1, B2)
        """
        # 将列索引转换为字母 (0->A, 1->B, ..., 25->Z, 26->AA, ...)
        col_letter = ""
        if col_index < 26:
            col_letter = chr(ord('A') + col_index)
        else:
            # 处理超过Z的列 (AA, AB, ...)
            first_letter = chr(ord('A') + col_index // 26 - 1)
            second_letter = chr(ord('A') + col_index % 26)
            col_letter = first_letter + second_letter
        
        # 行号从1开始
        row_number = row_index + 1
        
        return f"{col_letter}{row_number}"
    
    def _cell_ref_to_index(self, col_str: str) -> int:
        """
        将列字母转换为索引 (如 A->0, B->1, ..., Z->25, AA->26, ...)
        
        Args:
            col_str: 列字母 (如 A, B, AA)
            
        Returns:
            列索引
        """
        result = 0
        for char in col_str:
            result = result * 26 + (ord(char) - ord('A') + 1)
        return result - 1
    
    def _clean_model_response(self, text: str) -> str:
        """
        清理模型返回的文本，去除可能包含的提示词
        
        Args:
            text: 模型返回的文本
            
        Returns:
            清理后的文本
        """
        if not text:
            return ""
        
        # 去除首尾空白字符
        cleaned = text.strip()
        
        # 去除可能的引号
        if cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1]
        elif cleaned.startswith("'") and cleaned.endswith("'"):
            cleaned = cleaned[1:-1]
        
        # 去除可能的JSON键值格式
        if cleaned.startswith(":"):
            cleaned = cleaned[1:].strip()
        
        # 去除可能的代码块标记
        if cleaned.startswith("``") and cleaned.endswith("```"):
            # 找到最后一个```
            last_backticks = cleaned.rfind("```")
            if last_backticks > 3:
                cleaned = cleaned[3:last_backticks].strip()
        
        # 去除可能的JSON对象标记
        if cleaned.startswith("{") and cleaned.endswith("}"):
            try:
                # 尝试解析为JSON对象
                json_obj = json.loads(cleaned)
                # 如果是字符串类型，则返回该字符串
                if isinstance(json_obj, str):
                    cleaned = json_obj
            except json.JSONDecodeError:
                # 如果不是有效的JSON，则保持原样
                pass
        
        return cleaned
    
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