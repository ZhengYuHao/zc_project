import asyncio
import json
import sys
import os
from urllib.parse import urlparse, parse_qs

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from models.feishu import get_feishu_client


def extract_bitable_info(url: str) -> tuple:
    """
    从飞书多维表格URL中提取app_token和table_id
    
    Args:
        url: 飞书多维表格的完整URL
        
    Returns:
        (app_token, table_id) 元组
    """
    # 示例URL: https://example.feishu.cn/base/PGCGbbB92aGzl4sRwqCcF1jFnVh?table=tblR28yF5Z1YzVvj
    
    # 使用urlparse解析URL
    parsed_url = urlparse(url)
    
    # 提取app_token (路径中的部分)
    path_parts = parsed_url.path.split('/')
    app_token = None
    for part in path_parts:
        if part and not part.endswith('.cn') and not part == 'base':
            app_token = part
            break
    
    # 提取table_id (查询参数中的部分)
    query_params = parse_qs(parsed_url.query)
    table_id = query_params.get('table', [None])[0]
    
    return app_token, table_id


async def read_feishu_bitable(bitable_url_or_token: str, specified_table_id: str = None) -> dict:
    """
    读取飞书多维表格数据
    
    Args:
        bitable_url_or_token: 多维表格URL或app_token
        specified_table_id: 指定的表格ID（可选）
        
    Returns:
        包含表格数据的字典
    """
    # 从URL中提取信息
    app_token, table_id_from_url = extract_bitable_info(bitable_url_or_token)
    
    # 如果没有从URL中提取到token，则认为输入的是token
    if not app_token:
        app_token = bitable_url_or_token
    
    # 优先使用指定的table_id，否则使用URL中的table_id
    target_table_id = specified_table_id or table_id_from_url
    
    print(f"Bitable app token: {app_token}")
    print(f"Target table ID: {target_table_id}")
    
    # 获取飞书客户端
    feishu_client = get_feishu_client()
    
    try:
        # 获取tenant_access_token
        tenant_token = await feishu_client.get_tenant_access_token()
        
        # 获取多维表格元数据
        import httpx
        headers = {
            "Authorization": f"Bearer {tenant_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        async with httpx.AsyncClient() as client:
            # 如果没有指定table_id，则获取应用下的所有表格
            if not target_table_id:
                # 获取多维表格应用下的所有表格
                tables_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables"
                tables_response = await client.get(tables_url, headers=headers)
                tables_response.raise_for_status()
                tables_result = tables_response.json()
                
                if tables_result.get("code") != 0:
                    raise Exception(f"Failed to get bitable tables: {tables_result}")
                
                tables = tables_result.get("data", {}).get("items", [])
                if not tables:
                    raise Exception("No tables found in bitable app")
                
                # 使用第一个表格
                target_table_id = tables[0].get("table_id")
                table_name = tables[0].get("name", "Unknown")
                print(f"Using first table: {table_name} (ID: {target_table_id})")
            else:
                # 获取指定表格信息
                table_name = "Unknown"
            
            # 读取表格记录
            records_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{target_table_id}/records"
            records_response = await client.get(records_url, headers=headers)
            records_response.raise_for_status()
            records_result = records_response.json()
            
            if records_result.get("code") != 0:
                raise Exception(f"Failed to read bitable records: {records_result}")
            
            # 提取记录数据
            records = records_result.get("data", {}).get("items", [])
            print(f"成功读取 {len(records)} 条记录")
            
            # 处理记录数据
            processed_records = []
            for record in records:
                record_id = record.get("record_id")
                fields = record.get("fields", {})
                processed_records.append({
                    "record_id": record_id,
                    "fields": fields
                })
            
            return {
                "app_token": app_token,
                "table_id": target_table_id,
                "table_name": table_name,
                "records": processed_records
            }
            
    except Exception as e:
        print(f"Error reading bitable: {str(e)}")
        raise


async def main():
    """
    主函数 - 读取飞书多维表格并显示数据
    """
    # 示例URL，请替换为实际的多维表格URL
    bitable_url = "https://dkke3lyh7o.feishu.cn/base/Yun7b8neBakSzDscIUmcmOMNnQv?login_redirect_times=1&table=tblbyvlDSEwZzCUv&view=vewHX9GV9d"
    
    print("开始读取飞书多维表格...")
    
    try:
        # 读取多维表格数据
        bitable_data = await read_feishu_bitable(bitable_url)
        print(f"成功读取多维表格数据:")
        print(f"应用Token: {bitable_data['app_token']}")
        print(f"表格ID: {bitable_data['table_id']}")
        print(f"表格名称: {bitable_data['table_name']}")
        print(f"记录数量: {len(bitable_data['records'])}")
        
        # 显示前几条记录作为示例
        print("\n前3条记录:")
        for i, record in enumerate(bitable_data['records'][:3]):
            print(f"  记录 {i+1}:")
            print(f"    Record ID: {record['record_id']}")
            print(f"    字段数据:")
            for field_name, field_value in record['fields'].items():
                print(f"      {field_name}: {field_value}")
        
        # 保存到文件
        filename = f"bitable_data.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(bitable_data, f, ensure_ascii=False, indent=2)
        print(f"\n数据已保存到 {filename} 文件")
        
    except Exception as e:
        print(f"处理过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())