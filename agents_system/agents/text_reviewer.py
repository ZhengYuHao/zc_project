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
    
    def _extract_text_from_document(self, doc_content: dict) -> str:
        """
        从飞书文档内容中提取文本
        
        Args:
            doc_content: 飞书文档内容
            
        Returns:
            提取的文本内容
        """
        if not doc_content:
            self.logger.warning("文档内容为空")
            return ""
        
        # 直接尝试提取所有文本内容
        def extract_all_text(obj):
            """递归提取对象中的所有文本"""
            texts = []
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == "content" and isinstance(value, str):
                        texts.append(value)
                    elif isinstance(value, (dict, list)):
                        texts.extend(extract_all_text(value))
            elif isinstance(obj, list):
                for item in obj:
                    texts.extend(extract_all_text(item))
            return texts
        
        # 提取所有文本
        all_texts = extract_all_text(doc_content)
        extracted_text = "\n".join(all_texts).strip()
        
        self.logger.info(f"提取到的文本长度: {len(extracted_text)}")
        if len(extracted_text) > 100:
            self.logger.info(f"提取到的文本前100个字符: {extracted_text[:100]}")
        else:
            self.logger.info(f"提取到的文本: {extracted_text}")
        
        return extracted_text
    
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
                        
                        # 构建表格格式的文本用于模型处理
                        # 创建行列结构
                        max_row = 0
                        max_col = 0
                        cell_positions = {}  # {cell_ref: (row, col)}
                        
                        # 解析单元格引用获取行列信息
                        for cell_ref in marked_cell_data.keys():
                            col_str = ''.join(filter(str.isalpha, cell_ref))
                            row_str = ''.join(filter(str.isdigit, cell_ref))
                            if col_str and row_str:
                                col_num = self._cell_ref_to_index(col_str)
                                row_num = int(row_str) - 1
                                cell_positions[cell_ref] = (row_num, col_num)
                                max_row = max(max_row, row_num)
                                max_col = max(max_col, col_num)
                        
                        # 构建表格矩阵
                        table_matrix = [["" for _ in range(max_col + 1)] for _ in range(max_row + 1)]
                        for cell_ref, content in marked_cell_data.items():
                            if cell_ref in cell_positions:
                                row, col = cell_positions[cell_ref]
                                table_matrix[row][col] = content  # 使用标记后的内容
                        
                        # 转换为制表符分隔的文本
                        table_text = "\n".join(["\t".join(row) for row in table_matrix])
                        
                        # 构建提示词
                        # 3. 违禁词替换：将用{{}}标记的违禁词必须替换成合适的内容，替换后必须删除{{}}标记。这是强制要求，不能跳过。
                        # 5. 口语化转换：将书面表达转换为自然口语表述
                        # 重要说明：
                        # - 对于包含{{}}标记的内容，必须进行替换并移除括号，这是最重要的要求
                        # - 不要删除包含{{}}标记的单元格内容
                        # - 不要忽略任何{{}}标记
                        prompt = f"""
你是一个专业的表格内容审核员。请审核以下电子表格内容，并按原格式返回优化后的内容。

表格结构说明：
- 每行用换行符分隔
- 每列用制表符(\\t)分隔
- 保持原有行列结构不变

审核要求：
1. 错别字纠正：找出并修正所有错别字和语法错误
2. 语句优化：确保句子结构合理，表达清晰流畅，对于句子中明显的逻辑错误要进行替代。

4. 逻辑优化：调整内容逻辑，确保符合认知顺序

6. 保持原意：所有修改不能改变原文的核心意思
7. 格式保持：严格按照原有表格格式返回结果
8. 如果单元格内容无需修改，请直接返回原始内容，不要添加任何说明



原始表格内容：
{table_text}

优化后表格内容：
"""
                        self.logger.info(f"调用大模型处理整个表格{table_text}")
                        # 调用大模型处理整个表格
                        corrected_table_text = await self.llm.generate_text(prompt)
                        self.logger.info(f"调用大模型处理整个表格后{corrected_table_text}")
                        # 解析处理后的表格文本
                        corrected_lines = corrected_table_text.strip().split('\n')
                        corrected_matrix = [line.split('\t') for line in corrected_lines]
                        
                        self.logger.info(f"模型返回的处理后表格行数: {len(corrected_matrix)}")
                        for i, row in enumerate(corrected_matrix):
                            self.logger.info(f"第{i+1}行单元格数: {len(row)}")
                            for j, cell in enumerate(row):
                                self.logger.info(f"  第{i+1}行第{j+1}列: '{cell}'")
                        
                        # 将处理后的数据按原位置写回
                        write_errors = []  # 记录写入错误
                        for cell_ref, (row, col) in cell_positions.items():
                            try:
                                self.logger.info(f"准备写回单元格 {cell_ref} (row={row}, col={col})")
                                
                                # 确保行列索引在处理后矩阵范围内
                                if row < len(corrected_matrix) and col < len(corrected_matrix[row]):
                                    corrected_content = corrected_matrix[row][col]
                                    self.logger.info(f"从模型结果中获取内容: '{corrected_content}'")
                                    
                                    # 检查内容是否为空
                                    if not corrected_content.strip():
                                        self.logger.warning(f"模型返回空内容，使用标记后的内容: '{marked_cell_data.get(cell_ref, cell_data.get(cell_ref, ''))}'")
                                        corrected_content = marked_cell_data.get(cell_ref, cell_data.get(cell_ref, ""))
                                    
                                    # 清理处理后的文本，确保不包含提示词
                                    cleaned_content = self._clean_model_response(corrected_content)
                                    self.logger.info(f"清理后的内容: '{cleaned_content}'")
                                    
                                    # 再次检查清理后的内容是否为空
                                    if not cleaned_content.strip():
                                        self.logger.warning(f"清理后内容为空，使用标记后的内容: '{marked_cell_data.get(cell_ref, cell_data.get(cell_ref, ''))}'")
                                        cleaned_content = marked_cell_data.get(cell_ref, cell_data.get(cell_ref, ""))
                                    
                                    # 记录即将写入电子表格的数据
                                    self.logger.info(f"[写入电子表格前] 单元格: {cell_ref}, 内容: '{cleaned_content}'")
                                    
                                    # 写回单个单元格
                                    write_url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values"
                                    write_payload = {
                                        "valueRange": {
                                            "range": f"{sheet_id}!{cell_ref}:{cell_ref}",
                                            "values": [[cleaned_content]]
                                        }
                                    }
                                    
                                    write_response = await client.put(write_url, headers=headers, json=write_payload)
                                    write_response.raise_for_status()
                                    write_result = write_response.json()
                                    
                                    if write_result.get("code") != 0:
                                        error_msg = f"写入单元格 {cell_ref} 失败: {write_result}"
                                        self.logger.error(error_msg)
                                        write_errors.append(error_msg)
                                    else:
                                        self.logger.info(f"[写入电子表格成功] 单元格: {cell_ref}")
                                else:
                                    # 如果处理后的矩阵不包含该位置，使用原始内容（标记后的）
                                    original_marked_content = marked_cell_data.get(cell_ref, cell_data.get(cell_ref, ""))
                                    self.logger.info(f"[写入电子表格前] 单元格: {cell_ref}, 内容: '{original_marked_content}' (使用标记后的内容)")
                                    
                                    write_url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values"
                                    write_payload = {
                                        "valueRange": {
                                            "range": f"{sheet_id}!{cell_ref}:{cell_ref}",
                                            "values": [[original_marked_content]]
                                        }
                                    }
                                    
                                    write_response = await client.put(write_url, headers=headers, json=write_payload)
                                    write_response.raise_for_status()
                                    write_result = write_response.json()
                                    
                                    if write_result.get("code") != 0:
                                        error_msg = f"写入单元格 {cell_ref} 失败: {write_result}"
                                        self.logger.error(error_msg)
                                        write_errors.append(error_msg)
                                    else:
                                        self.logger.info(f"[写入电子表格成功] 单元格: {cell_ref}")
                            except Exception as e:
                                error_msg = f"写入单元格 {cell_ref} 时出错: {str(e)}"
                                self.logger.error(error_msg)
                                write_errors.append(error_msg)
                                
                                # 出错时尝试写回原始内容（标记后的）
                                try:
                                    original_marked_content = marked_cell_data.get(cell_ref, cell_data.get(cell_ref, ""))
                                    self.logger.info(f"[出错回退] 单元格: {cell_ref}, 内容: '{original_marked_content}'")
                                    
                                    write_url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values"
                                    write_payload = {
                                        "valueRange": {
                                            "range": f"{sheet_id}!{cell_ref}:{cell_ref}",
                                            "values": [[original_marked_content]]
                                        }
                                    }
                                    
                                    write_response = await client.put(write_url, headers=headers, json=write_payload)
                                    write_response.raise_for_status()
                                    write_result = write_response.json()
                                    
                                    if write_result.get("code") != 0:
                                        fallback_error_msg = f"[出错回退] 写入单元格 {cell_ref} 失败: {write_result}"
                                        self.logger.error(fallback_error_msg)
                                        write_errors.append(fallback_error_msg)
                                    else:
                                        self.logger.info(f"[出错回退] 写入电子表格成功: {cell_ref}")
                                except Exception as fallback_e:
                                    fallback_error_msg = f"[出错回退] 写入单元格 {cell_ref} 时再次出错: {str(fallback_e)}"
                                    self.logger.error(fallback_error_msg)
                                    write_errors.append(fallback_error_msg)
                        
                        # 汇总写入结果
                        if write_errors:
                            self.logger.warning(f"处理飞书电子表格时出现 {len(write_errors)} 个写入错误")
                            for error in write_errors:
                                self.logger.warning(f"写入错误: {error}")
                        else:
                            self.logger.info("所有单元格写入成功")
                
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
        清理模型响应，移除提示词相关内容
        
        Args:
            text: 模型响应文本
            
        Returns:
            清理后的文本
        """
        # 如果文本包含解释性内容，尝试提取原始文本
        if "没有错别字" in text and "无需任何修改" in text and "处理后的文本仍为" in text:
            # 提取引号中的内容
            import re
            quote_pattern = r'“([^”]+)”'
            matches = re.findall(quote_pattern, text)
            if matches:
                return matches[-1]  # 返回最后一个引号中的内容
        
        # 定义需要过滤的提示词片段
        filter_patterns = [
            "你是一个专业的表格内容审核员。请审核以下电子表格内容，并按原格式返回优化后的内容。",
            "表格结构说明：",
            "每行用换行符分隔",
            "每列用制表符(\\t)分隔",
            "保持原有行列结构不变",
            "审核要求：",
            "1. 错别字纠正：找出并修正所有错别字和语法错误",
            "2. 语句优化：确保句子结构合理，表达清晰流畅",
            "3. 违禁词替换：将用{}标记的违禁词必须替换成合适的内容，替换后必须删除{}标记。这是强制要求，不能跳过。",
            "4. 逻辑优化：调整内容逻辑，确保符合认知顺序",
            "5. 口语化转换：将书面表达转换为自然口语表述",
            "6. 保持原意：所有修改不能改变原文的核心意思",
            "7. 格式保持：严格按照原有表格格式返回结果",
            "8. 如果单元格内容无需修改，请直接返回原始内容，不要添加任何说明",
            "重要说明：",
            "对于包含{}标记的内容，必须进行替换并移除括号，这是最重要的要求",
            "不要删除包含{}标记的单元格内容",
            "不要忽略任何{}标记",
            "原始表格内容：",
            "优化后表格内容：",
            "请作为专业内容审核员，对以下文本进行全面审查和优化：",
            "审核文本：",
            "一、核心审核要求",
            "错别字纠正：精准识别并修正所有拼写错误、错别字和语法错误",
            "语句通顺：确保句子结构合理，表达清晰流畅，语义相近的句子删除。",
            "违禁词处理：替换所有用{}标记的违禁词（只能替换不能删除），替换后删除{}标记。",
            "逻辑优化：调整内容逻辑顺序，确保产品卖点介绍符合使用流程（如洗烘套装先洗衣机后烘干机）和认知逻辑（如康师傅喝开水先工艺后口感）",
            "口语化转换：将书面化表达转换为自然口语表述（如",
            "原意保持：所有修改不得改变原文核心含义和意图",
            "二、输出格式要求",
            "直接返回修改后的完整文本",
            "不添加任何额外说明或解释！！！！",
            "使用zh语言输出",
            "确保文本格式与原文一致",
            "三、审核标准参考",
            "采用千万级专业词库和数十亿训练语料的检测标准",
            "符合内容安全与合规性要求",
            "保持语言自然流畅且适合口语传播",
            "请现在开始审核并返回修改后的文本",
            "请现在开始审核并返回修改后的文本。如果文本已经完美无需修改，请直接返回原始文本内容，不要添加任何说明。",
            "请你提供具体需要审核的文本内容，以便我按照要求进行审核和优化 。",
            "错别字纠正：精确找出并改正所有拼写错误、错别字以及语法错误",
            "语句通顺：保证句子结构恰当，表达清晰、通顺，把语义相近的句子删掉。",
            "违禁词处理：替换所有用{}标注的违禁词（只能替换不能删除），替换后去掉{}标注。",
            "逻辑优化：调整内容的逻辑顺序，要让产品卖点介绍符合使用流程（像洗烘套装先介绍洗衣机再介绍烘干机）以及认知逻辑（比如康师傅喝开水先讲工艺再讲口感）",
            "口语化转换：把书面化表述转变成自然的口语说法（例如",
            "原意保持：所有修改都不能改变原文的核心意思和意图",
            "审核标准参考",
            "内容安全与合规性要求",
            "自然流畅且适合口语传播",
            "你是一个专业的文本优化助手，请对以下文本进行审核和优化。",
            "请严格按照以下要求进行处理：",
            "1. 如果文本存在错别字、语法错误或违禁词，请进行修正",
            "2. 如果文本已经完美，无需任何修改，请直接返回原始文本内容，不要添加任何说明",
            "3. 不要添加任何解释、说明或其他额外内容",
            "4. 直接返回处理后的文本内容",
            "处理后文本：",
            "你提供的文本",
            "没有错别字、语法错误、违禁词等需要处理的问题",
            "句子结构简单清晰",
            "逻辑上也无需调整",
            "口语化和原意方面也无需变动",
            "所以处理后的文本仍为"
        ]
        
        # 过滤掉所有提示词片段
        cleaned_text = text
        for pattern in filter_patterns:
            cleaned_text = cleaned_text.replace(pattern, "")
        
        # 移除可能的修改说明部分
        if "修改说明" in cleaned_text:
            cleaned_text = cleaned_text.split("修改说明")[0].strip()
        
        # 清理多余的空白行和空格
        lines = cleaned_text.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        cleaned_text = '\n'.join(cleaned_lines).strip()
        
        # 如果处理后的文本为空，则返回原文本
        if not cleaned_text:
            return text
        
        return cleaned_text

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