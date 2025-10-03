import httpx
import hashlib
import base64
import hmac
import time
import sys
import os
import json
import asyncio
from typing import Dict, Any, Optional
from utils.logger import get_logger
# from utils.settings import settings
# from .exceptions import DocumentVersionError

logger = get_logger(__name__)

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# 添加调试信息，检查settings是否正确加载
logger.info(f"FEISHU_APP_ID from settings: {settings.FEISHU_APP_ID}")
logger.info(f"FEISHU_APP_SECRET from settings: {settings.FEISHU_APP_SECRET}")
logger.info(f"FEISHU_VERIFY_TOKEN from settings: {settings.FEISHU_VERIFY_TOKEN}")
logger.info(f"FEISHU_ENCRYPT_KEY from settings: {settings.FEISHU_ENCRYPT_KEY}")

# 全局飞书客户端实例
_feishu_client = None

def get_feishu_client():
    """
    获取全局飞书客户端实例
    
    Returns:
        FeishuClient: 飞书客户端实例
    """
    global _feishu_client
    if _feishu_client is None:
        _feishu_client = FeishuClient()
    return _feishu_client


class DocumentVersionError(Exception):
    """文档版本冲突异常"""
    pass


class FeishuClient:
    """飞书API客户端"""
    
    def __init__(self):
        self.app_id = settings.FEISHU_APP_ID
        self.app_secret = settings.FEISHU_APP_SECRET
        self.verify_token = settings.FEISHU_VERIFY_TOKEN
        self.encrypt_key = settings.FEISHU_ENCRYPT_KEY
        # 配置客户端，增加超时和基础URL
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(300),
            base_url="https://open.feishu.cn"
        )
        self.tenant_access_token = None
        self.token_expire_time = 0
    
    async def get_tenant_access_token(self) -> str:
        """
        获取tenant_access_token
        
        Returns:
            tenant_access_token
        """
        # 检查token是否过期
        if self.tenant_access_token and time.time() < self.token_expire_time:
            return self.tenant_access_token
        
        url = "/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            logger.info(f"Requesting tenant_access_token from {url}")
            logger.info(f"Request payload: {payload}")
            
            response = await self.client.post(url, headers=headers, json=payload)
            
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Response JSON: {result}")
            
            if result.get("code") != 0:
                raise Exception(f"Failed to get tenant_access_token: {result}")
            
            self.tenant_access_token = result["tenant_access_token"]
            self.token_expire_time = time.time() + result["expire"] - 60  # 提前60秒过期
            
            logger.info("Successfully obtained tenant_access_token")
            return self.tenant_access_token
        except httpx.ConnectError as e:
            logger.error(f"Connection error when getting tenant_access_token: {str(e)}")
            logger.error("This might be due to network issues, firewall or proxy settings")
            raise Exception(f"无法连接到飞书服务器，请检查网络连接: {str(e)}")
        except httpx.TimeoutException as e:
            logger.error(f"Timeout error when getting tenant_access_token: {str(e)}")
            raise Exception(f"请求飞书服务器超时，请检查网络连接: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting tenant_access_token: {str(e)}")
            raise
    
    async def read_document(self, document_id: str) -> Dict[str, Any]:
        """
        读取飞书文档内容
        
        Args:
            document_id: 文档ID
            
        Returns:
            文档内容和元数据
        """
        token = await self.get_tenant_access_token()
        url = f"/open-apis/docx/v1/documents/{document_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        try:
            logger.info(f"Reading document {document_id} from Feishu")
            # 先获取文档元数据
            meta_response = await self.client.get(url, headers=headers)
            
            # 检查响应状态
            if meta_response.status_code == 404:
                # 尝试作为电子表格获取元信息
                sheet_meta_url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{document_id}/metainfo"
                sheet_meta_response = await self.client.get(sheet_meta_url, headers=headers)
                if sheet_meta_response.status_code == 200:
                    sheet_meta_result = sheet_meta_response.json()
                    if sheet_meta_result.get("code") == 0:
                        # 这是一个电子表格
                        result = {
                            "meta": {"type": "sheet"},
                            "content": {},
                            "revision": 0,
                            "document_id": document_id
                        }
                        return result
                # 如果电子表格获取也失败，则抛出原始错误
                meta_response.raise_for_status()
            
            meta_response.raise_for_status()
            meta_result = meta_response.json()
            
            # 获取文档内容
            content_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks"
            content_response = await self.client.get(content_url, headers=headers)
            content_response.raise_for_status()
            content_result = content_response.json()
            
            result = {
                "meta": meta_result.get("data", {}),
                "content": content_result.get("data", {}),
                "revision": meta_result.get("data", {}).get("revision", 0),
                "document_id": document_id
            }
            
            return result
        except Exception as e:
            logger.error(f"Error reading document {document_id}: {str(e)}")
            raise
    
    async def write_document(self, document_id: str, content: Dict[str, Any], expected_revision: Optional[int] = None) -> bool:
        """
        写入内容到飞书文档
        
        Args:
            document_id: 文档ID
            content: 要写入的内容
            expected_revision: 期望的文档版本号，用于冲突检测
            
        Returns:
            是否写入成功
            
        Raises:
            DocumentVersionError: 当文档版本冲突时
        """
        token = await self.get_tenant_access_token()
        
        # 如果提供了期望版本号，先检查当前版本
        if expected_revision is not None:
            current_doc = await self.read_document(document_id)
            current_revision = current_doc.get("revision", 0)
            if current_revision != expected_revision:
                logger.warning(f"Document version conflict: expected {expected_revision}, got {current_revision}")
                raise DocumentVersionError(f"Document version conflict: expected {expected_revision}, got {current_revision}")
        
        # 首先获取文档的根block_id
        doc_info = await self.read_document(document_id)
        # 根据飞书API文档，要向文档添加内容，需要使用文档的根块ID作为block_id参数
        # 根文档块的ID通常在meta数据中的document_id字段
        root_block_id = doc_info.get("meta", {}).get("document_id", document_id)
        
        # 正确的API路径: https://open.feishu.cn/open-apis/docx/v1/documents/:document_id/blocks/:block_id/children
        url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{root_block_id}/children"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        try:
            logger.info(f"Writing to document {document_id} in Feishu")
            logger.info(f"Write URL: {url}")
            logger.info(f"Write content: {content}")
            
            # 根据飞书文档内容更新与覆盖操作规范，使用POST方法直接写入内容
            # 这会自动替换所有现有子块，实现原子性覆盖
            response = await self.client.post(url, headers=headers, json=content)
            logger.info(f"Write response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Write document failed with status {response.status_code}")
                logger.error(f"Write document response text: {response.text}")
            
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Write document result: {result}")
            
            if result.get("code") != 0:
                # 检查是否是版本冲突错误
                if result.get("code") == 99991666:  # 假设这是版本冲突的错误码
                    raise DocumentVersionError(f"Document version conflict when writing: {result}")
                raise Exception(f"Failed to write document: {result}")
            
            return True
        except DocumentVersionError:
            raise
        except Exception as e:
            logger.error(f"Error writing to document {document_id}: {str(e)}")
            raise
    
    async def update_block(self, document_id: str, block_id: str, content: Dict[str, Any]) -> bool:
        """
        更新飞书文档中的特定块
        
        Args:
            document_id: 文档ID
            block_id: 块ID
            content: 要更新的内容，格式为 {"text": {...}}
            
        Returns:
            是否更新成功
        """
        token = await self.get_tenant_access_token()
        # 使用飞书更新块API: https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{block_id}
        url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{block_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        # 根据飞书文档API规范，更新块内容应该使用PATCH方法
        # 并且内容格式应该是update_text_elements
        update_content = {
            "update_text_elements": content.get("text", {})
        }
        
        try:
            logger.info(f"Updating block {block_id} in document {document_id}")
            logger.info(f"Update URL: {url}")
            logger.info(f"Update content: {json.dumps(update_content, ensure_ascii=False)}")
            
            # 使用PATCH方法更新块内容
            response = await self.client.patch(url, headers=headers, json=update_content)
            logger.info(f"Update response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Update block failed with status {response.status_code}")
                logger.error(f"Update block response text: {response.text}")
            
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Update block result: {json.dumps(result, ensure_ascii=False)}")
            
            if result.get("code") != 0:
                raise Exception(f"Failed to update block: {result}")
            
            return True
        except Exception as e:
            logger.error(f"Error updating block {block_id} in document {document_id}: {str(e)}")
            raise
    
    async def reply_message(self, message_id: str, content: str) -> bool:
        """
        回复飞书消息
        
        Args:
            message_id: 消息ID
            content: 回复内容
            
        Returns:
            是否回复成功
        """
        token = await self.get_tenant_access_token()
        url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        payload = {
            "content": f'{{"text":"{content}"}}',
            "msg_type": "text"
        }
        
        try:
            logger.info(f"Replying to message {message_id} in Feishu")
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") != 0:
                raise Exception(f"Failed to reply message: {result}")
            
            return True
        except Exception as e:
            logger.error(f"Error replying to message {message_id}: {str(e)}")
            raise
    
    def validate_callback(self, timestamp: str, nonce: str, signature: str, body: str) -> bool:
        """
        验证飞书回调签名
        
        Args:
            timestamp: 时间戳
            nonce: 随机数
            signature: 签名
            body: 请求体
            
        Returns:
            是否验证通过
        """
        if not self.encrypt_key:
            logger.warning("Encrypt key is not set, skipping signature validation")
            return True
        
        # 构造签名字符串
        to_sign = f"{timestamp}\n{nonce}\n{body}"
        
        # 计算签名
        signature_bytes = base64.b64decode(self.encrypt_key)
        hmac_code = hmac.new(signature_bytes, to_sign.encode(), hashlib.sha256).digest()
        calculated_signature = base64.b64encode(hmac_code).decode()
        
        # 比较签名
        is_valid = calculated_signature == signature
        if not is_valid:
            logger.warning("Feishu callback signature validation failed")
        
        return is_valid
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()