"""
调试脚本用于诊断飞书多维表格更新问题
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.feishu_bitable_processor import extract_info_from_feishu_url
from models.feishu import get_feishu_client


async def read_record_info(app_token: str, table_id: str, record_id: str):
    """读取记录信息"""
    print(f"读取记录信息: app_token={app_token}, table_id={table_id}, record_id={record_id}")
    
    # 获取飞书客户端
    feishu_client = get_feishu_client()
    
    try:
        # 获取tenant_access_token
        tenant_token = await feishu_client.get_tenant_access_token()
        
        # 读取记录
        import httpx
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
        headers = {
            "Authorization": f"Bearer {tenant_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 0:
                raise Exception(f"Failed to read record: {result}")
            
            print(f"记录信息: {result}")
            return result
            
    except Exception as e:
        print(f"读取记录失败: {str(e)}")
        raise


async def list_table_fields(app_token: str, table_id: str):
    """列出表格的所有字段"""
    print(f"列出表格字段: app_token={app_token}, table_id={table_id}")
    
    # 获取飞书客户端
    feishu_client = get_feishu_client()
    
    try:
        # 获取tenant_access_token
        tenant_token = await feishu_client.get_tenant_access_token()
        
        # 列出字段
        import httpx
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
        headers = {
            "Authorization": f"Bearer {tenant_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 0:
                raise Exception(f"Failed to list fields: {result}")
            
            print(f"表格字段: {result}")
            return result
            
    except Exception as e:
        print(f"列出字段失败: {str(e)}")
        raise


async def update_record_field_directly(app_token: str, table_id: str, record_id: str, field_name: str, field_value: str):
    """直接更新记录字段"""
    print(f"更新记录字段: app_token={app_token}, table_id={table_id}, record_id={record_id}")
    print(f"字段名: {field_name}, 字段值: {field_value}")
    
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
            "fields": {
                field_name: field_value
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.put(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 0:
                raise Exception(f"Failed to update record: {result}")
            
            print(f"更新结果: {result}")
            return result
            
    except Exception as e:
        print(f"更新记录失败: {str(e)}")
        raise


async def debug_update_process():
    """调试更新过程"""
    # 使用您提供的实际URL
    url = "https://dkke3lyh7o.feishu.cn/base/Yun7b8neBakSzDscIUmcmOMNnQv?table=tblWEf5vmSdEUBFi&view=vewBkURqsq&field=fldw2TicQY&record=recIAENn3o"
    
    print(f"处理URL: {url}")
    
    # 1. 提取URL信息
    print("\n1. 提取URL信息...")
    info = extract_info_from_feishu_url(url)
    print(f"提取的信息: {info}")
    
    app_token = info["app_token"]
    table_id = info["table_id"]
    record_id = info["record_id"]
    
    # 2. 读取记录信息
    print("\n2. 读取记录信息...")
    try:
        record_info = await read_record_info(app_token, table_id, record_id)
        fields = record_info.get("data", {}).get("fields", {})
        print(f"现有字段: {list(fields.keys())}")
    except Exception as e:
        print(f"无法读取记录信息: {str(e)}")
        return
    
    # 3. 列出表格所有字段
    print("\n3. 列出表格所有字段...")
    try:
        table_fields = await list_table_fields(app_token, table_id)
        field_names = [field.get("field_name") for field in table_fields.get("data", {}).get("items", [])]
        print(f"表格所有字段: {field_names}")
    except Exception as e:
        print(f"无法列出表格字段: {str(e)}")
    
    # 4. 检查目标字段是否存在
    target_field = "图文大纲创作结果"
    if target_field in field_names:
        print(f"\n✓ 字段 '{target_field}' 存在")
    else:
        print(f"\n✗ 字段 '{target_field}' 不存在")
        print("可用字段:", field_names)
        return
    
    # 5. 尝试更新字段
    print(f"\n4. 尝试更新字段 '{target_field}'...")
    try:
        result = await update_record_field_directly(
            app_token, 
            table_id, 
            record_id, 
            target_field, 
            "好的"
        )
        print(f"✓ 字段更新成功: {result}")
    except Exception as e:
        print(f"✗ 字段更新失败: {str(e)}")


if __name__ == "__main__":
    asyncio.run(debug_update_process())