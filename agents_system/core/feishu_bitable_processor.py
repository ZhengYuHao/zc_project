"""
飞书多维表格链接解析和数据回填处理器
用于从飞书链接中提取必要信息并实现数据回填功能
只支持完整格式的URL
"""

import asyncio
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from models.feishu import get_feishu_client


def extract_info_from_feishu_url(url: str) -> Dict[str, str]:
    """
    从飞书多维表格URL中提取必要信息
    
    Args:
        url: 飞书多维表格URL，只支持完整格式:
            https://dkke3lyh7o.feishu.cn/base/Yun7b8neBakSzDscIUmcmOMNnQv?table=tblWEf5vmSdEUBFi&view=vewBkURqsq&field=fldw2TicQY&record=recIAENn3o
            
    Returns:
        包含提取信息的字典:
        - app_token: 应用标识
        - table_id: 表格标识
        - record_id: 记录标识
    """
    parsed_url = urlparse(url)
    
    # 初始化返回值
    app_token = None
    table_id = None
    record_id = None
    
    # 提取查询参数
    query_params = parse_qs(parsed_url.query)
    
    # 提取table_id和record_id (从查询参数中)
    if 'table' in query_params:
        table_id = query_params['table'][0]
    if 'record' in query_params:
        record_id = query_params['record'][0]
    
    # 提取app_token (从路径中)
    if '/base/' in parsed_url.path:
        path_parts = parsed_url.path.split('/')
        for part in path_parts:
            if part and not part.endswith('.cn') and not part == 'base':
                app_token = part
                break
    
    # 如果app_token仍然为空，尝试从域名中获取
    if not app_token:
        domain_parts = parsed_url.netloc.split('.')
        if len(domain_parts) > 0:
            app_token = domain_parts[0]
    
    # 构建返回结果，避免IDE语法高亮误报
    result = {}
    result["app_token"] = app_token
    result["table_id"] = table_id
    result["record_id"] = record_id
    
    return result


async def update_feishu_bitable_record(app_token: str, table_id: str, record_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    更新飞书多维表格中的记录
    
    Args:
        app_token: 多维表格应用token
        table_id: 表格ID
        record_id: 记录ID
        fields: 要更新的字段数据，格式为 {"字段名": "字段值", ...}
        
    Returns:
        包含更新结果的字典
    """
    print(f"Updating record {record_id} in bitable app_token: {app_token}, table_id: {table_id}")
    
    # 获取飞书客户端
    feishu_client = get_feishu_client()
    
    try:
        # 获取tenant_access_token
        tenant_token = await feishu_client.get_tenant_access_token()
        
        # 更新记录
        import httpx
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
        headers = {
            "Authorization": f"Bearer {tenant_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        payload = {
            "fields": fields
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.put(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 0:
                raise Exception(f"Failed to update record in bitable: {result}")
            
            print(f"Successfully updated record: {result}")
            return result
            
    except Exception as e:
        print(f"Error updating record in bitable: {str(e)}")
        raise


async def update_feishu_bitable_cell(app_token: str, table_id: str, record_id: str, field_name: str, field_value: Any) -> Dict[str, Any]:
    """
    更新飞书多维表格中的指定单元格（记录的特定字段）
    
    Args:
        app_token: 多维表格应用token
        table_id: 表格ID
        record_id: 记录ID（行标识）
        field_name: 字段名（列标识）
        field_value: 字段值
        
    Returns:
        包含更新结果的字典
    """
    print(f"Updating cell in record {record_id}, field '{field_name}' in bitable app_token: {app_token}, table_id: {table_id}")
    
    # 构造字段数据
    fields = {field_name: field_value}
    
    # 复用更新记录的函数
    return await update_feishu_bitable_record(app_token, table_id, record_id, fields)


async def process_feishu_record_url(url: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理飞书记录URL并回填数据
    
    Args:
        url: 飞书记录URL (只支持完整格式)
        fields: 要更新的字段数据
        
    Returns:
        处理结果
    """
    # 1. 从URL中提取信息
    info = extract_info_from_feishu_url(url)
    app_token = info["app_token"]
    table_id = info["table_id"]
    record_id = info["record_id"]
    
    # 检查必要信息是否存在
    if not app_token:
        raise ValueError("无法从URL中提取app_token")
    
    if not table_id:
        raise ValueError("无法从URL中提取table_id")
    
    if not record_id:
        raise ValueError("无法从URL中提取record_id")
    
    # 2. 更新记录
    result = await update_feishu_bitable_record(app_token, table_id, record_id, fields)
    return result


async def process_feishu_record_cell(url: str, field_name: str, field_value: Any) -> Dict[str, Any]:
    """
    处理飞书记录URL并更新指定单元格
    
    Args:
        url: 飞书记录URL (只支持完整格式)
        field_name: 字段名
        field_value: 字段值
        
    Returns:
        处理结果
    """
    # 1. 从URL中提取信息
    info = extract_info_from_feishu_url(url)
    app_token = info["app_token"]
    table_id = info["table_id"]
    record_id = info["record_id"]
    
    # 检查必要信息是否存在
    if not app_token:
        raise ValueError("无法从URL中提取app_token")
    
    if not table_id:
        raise ValueError("无法从URL中提取table_id")
    
    if not record_id:
        raise ValueError("无法从URL中提取record_id")
    
    # 2. 更新单元格
    result = await update_feishu_bitable_cell(app_token, table_id, record_id, field_name, field_value)
    return result