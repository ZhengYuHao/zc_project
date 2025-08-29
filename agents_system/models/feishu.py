import httpx
import hashlib
import base64
import hmac
import time
import sys
import os
from typing import Optional, Dict, Any

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


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
        self.client = httpx.AsyncClient()
        self.tenant_access_token = None
        self.token_expire_time = 0
        logger.info("Initialized FeishuClient")
    
    async def get_tenant_access_token(self) -> str:
        """
        获取tenant_access_token
        
        Returns:
            tenant_access_token
        """
        # 检查token是否过期
        if self.tenant_access_token and time.time() < self.token_expire_time:
            return self.tenant_access_token
        
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            logger.info("Getting tenant_access_token from Feishu")
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") != 0:
                raise Exception(f"Failed to get tenant_access_token: {result}")
            
            self.tenant_access_token = result["tenant_access_token"]
            self.token_expire_time = time.time() + result["expire"] - 60  # 提前60秒过期
            logger.info("Successfully got tenant_access_token")
            
            return self.tenant_access_token
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
        url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        try:
            logger.info(f"Reading document {document_id} from Feishu")
            # 先获取文档元数据
            meta_response = await self.client.get(url, headers=headers)
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
            
            logger.info(f"Successfully read document {document_id}")
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
        
        url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        try:
            logger.info(f"Writing to document {document_id} in Feishu")
            response = await self.client.post(url, headers=headers, json=content)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") != 0:
                # 检查是否是版本冲突错误
                if result.get("code") == 99991666:  # 假设这是版本冲突的错误码
                    raise DocumentVersionError(f"Document version conflict when writing: {result}")
                raise Exception(f"Failed to write document: {result}")
            
            logger.info(f"Successfully wrote to document {document_id}")
            return True
        except DocumentVersionError:
            raise
        except Exception as e:
            logger.error(f"Error writing to document {document_id}: {str(e)}")
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
            
            logger.info(f"Successfully replied to message {message_id}")
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


# 全局飞书客户端实例
feishu_client: Optional[FeishuClient] = None


def get_feishu_client() -> FeishuClient:
    """获取飞书客户端实例"""
    global feishu_client
    if feishu_client is None:
        feishu_client = FeishuClient()
    return feishu_client