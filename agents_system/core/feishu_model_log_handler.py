"""
飞书多维表格模型调用日志处理模块
用于将模型调用记录统一写入飞书多维表格
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
import httpx

from utils.logger import get_logger
from models.feishu import get_feishu_client

logger = get_logger(__name__)


class FeishuModelLogHandler:
    """飞书多维表格模型调用日志处理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化飞书模型日志处理器
        
        Args:
            config: 飞书配置信息
        """
        self.config = config or {}
        self.app_token = self.config.get("app_token")
        self.table_id = self.config.get("table_id")
        
        logger.info("Initialized FeishuModelLogHandler")
    
    async def save_model_calls(self, request_id: str, model_calls: List[Dict[str, Any]]):
        """
        将模型调用记录保存到飞书多维表格
        
        Args:
            request_id: 请求ID
            model_calls: 模型调用记录列表
        """
        if not self.app_token or not self.table_id:
            logger.warning("Feishu bitable config not found, skipping save")
            return
            
        if not model_calls:
            logger.info("No model calls to save")
            return
            
        try:
            # 获取飞书客户端
            feishu_client = get_feishu_client()
            
            # 获取tenant_access_token
            tenant_token = await feishu_client.get_tenant_access_token()
            
            # 准备批量写入的数据
            records = []
            for call in model_calls:
                # 限制字段长度避免超出限制
                fields = {
                    "request_id": request_id,
                    "task_type": call["task_type"][:100],
                    "prompt": call["prompt"][:3000],
                    "response": call["response"][:3000],
                    "timestamp": call["timestamp"],
                    "model_params": call["model_params"][:1000],
                }
                records.append({"fields": fields})
            
            # 批量写入记录到多维表格
            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/batch_create"
            headers = {
                "Authorization": f"Bearer {tenant_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            payload = {
                "records": records
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()
                
                if result.get("code") != 0:
                    logger.error(f"Failed to save records to feishu bitable: {result}")
                else:
                    logger.info(f"Successfully saved {len(records)} model call records to feishu bitable")
                    
        except Exception as e:
            logger.error(f"Error saving model calls to feishu bitable: {str(e)}")
            raise