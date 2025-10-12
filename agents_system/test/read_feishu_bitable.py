import asyncio
import json
import sys
import os
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional

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


async def write_feishu_bitable_record(app_token: str, table_id: str, fields: Dict[str, Any]) -> dict:
    """
    向飞书多维表格写入一条记录
    
    Args:
        app_token: 多维表格应用token
        table_id: 表格ID
        fields: 要写入的字段数据，格式为 {"字段名": "字段값", ...}
        
    Returns:
        包含写入结果的字典
    """
    print(f"Writing record to bitable app_token: {app_token}, table_id: {table_id}")
    
    # 获取飞书客户端
    feishu_client = get_feishu_client()
    
    try:
        # 获取tenant_access_token
        tenant_token = await feishu_client.get_tenant_access_token()
        
        # 写入记录到多维表格
        import httpx
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
        headers = {
            "Authorization": f"Bearer {tenant_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        payload = {
            "fields": fields
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 0:
                raise Exception(f"Failed to write record to bitable: {result}")
            
            print(f"Successfully wrote record: {result}")
            return result
            
    except Exception as e:
        print(f"Error writing to bitable: {str(e)}")
        raise


async def write_feishu_bitable_batch_records(app_token: str, table_id: str, records: list) -> dict:
    """
    批量向飞书多维表格写入记录
    
    Args:
        app_token: 多维表格应用token
        table_id: 表格ID
        records: 要写入的记录列表，每个元素为 {"fields": {...}} 格式
        
    Returns:
        包含写入结果的字典
    """
    print(f"Batch writing {len(records)} records to bitable app_token: {app_token}, table_id: {table_id}")
    
    # 获取飞书客户端
    feishu_client = get_feishu_client()
    
    try:
        # 获取tenant_access_token
        tenant_token = await feishu_client.get_tenant_access_token()
        
        # 批量写入记录到多维表格
        import httpx
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
        headers = {
            "Authorization": f"Bearer {tenant_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json={"records": records})
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 0:
                raise Exception(f"Failed to batch write records to bitable: {result}")
            
            print(f"Successfully batch wrote records: {result}")
            return result
            
    except Exception as e:
        print(f"Error batch writing to bitable: {str(e)}")
        raise


async def update_feishu_bitable_record(app_token: str, table_id: str, record_id: str, fields: Dict[str, Any]) -> dict:
    """
    更新飞书多维表格中的记录
    
    Args:
        app_token: 多维表格应用token
        table_id: 表格ID
        record_id: 记录ID
        fields: 要更新的字段数据，格式为 {"字段名": "字段값", ...}
        
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


async def update_feishu_bitable_cell(app_token: str, table_id: str, record_id: str, field_name: str, field_value: Any) -> dict:
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


def get_safe_field_value(field_name: str, field_value: str, existing_records: list) -> Any:
    """
    根据字段名和现有记录确定安全的字段值格式
    
    Args:
        field_name: 字段名
        field_value: 字段值
        existing_records: 现有记录列表
        
    Returns:
        安全的字段值
    """
    # 检查现有记录中该字段的值类型，以确定正确的写入格式
    for record in existing_records:
        fields = record.get("fields", {})
        if field_name in fields:
            existing_value = fields[field_name]
            # 如果现有值是字典或列表，说明这是一个特殊字段类型
            if isinstance(existing_value, dict):
                # 处理链接字段等特殊类型
                if "link" in existing_value:
                    # 链接字段需要特定格式
                    return {"text": field_value}
            elif isinstance(existing_value, list):
                # 数组类型字段
                if existing_value and isinstance(existing_value[0], dict):
                    # 处理链接列表等
                    return field_value
            break
    
    # 默认情况下直接返回字符串值
    return field_value


async def main():
    """
    主函数 - 读取飞书多维表格并显示数据，然后演示写入数据
    """
    # 示例URL，请替换为实际的多维表格URL
    bitable_url = "https://dkke3lyh7o.feishu.cn/base/Yun7b8neBakSzDscIUmcmOMNnQv?login_redirect_times=1&table=tblWEf5vmSdEUBFi&view=vewBkURqsq"
    
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
        
        # 演示写入数据（使用实际字段名）
        print("\n开始演示写入数据...")
        
        # 获取现有记录的字段名作为参考
        field_names = set()
        if bitable_data['records']:
            # 收集所有记录中的字段名
            for record in bitable_data['records']:
                field_names.update(record['fields'].keys())
            print(f"发现的字段名: {list(field_names)}")
        
        # 创建写入数据（使用实际存在的字段名，避免链接类型字段）
        new_record_fields = {}
        text_fields = []  # 收集文本类型的字段
        
        # 识别文本类型字段（排除链接类型字段）
        for record in bitable_data['records'][:3]:  # 检查前3条记录
            for field_name, field_value in record['fields'].items():
                # 简单判断是否为文本字段（不是字典或列表）
                if isinstance(field_value, str):
                    text_fields.append(field_name)
        
        # 去重
        text_fields = list(set(text_fields))
        print(f"识别出的文本字段: {text_fields}")
        
        # 如果有文本字段，使用它们来创建新记录
        if text_fields:
            for i, field_name in enumerate(text_fields[:3]):  # 只使用前3个文本字段
                new_record_fields[field_name] = f"测试数据{i+1}"
        else:
            # 如果没有识别出文本字段，则尝试使用非链接字段
            safe_fields = []
            for record in bitable_data['records'][:1]:  # 检查第一条记录
                for field_name, field_value in record['fields'].items():
                    # 排除明显的链接字段
                    if not isinstance(field_value, dict) or "link" not in field_value:
                        safe_fields.append(field_name)
            
            if safe_fields:
                for i, field_name in enumerate(safe_fields[:3]):
                    new_record_fields[field_name] = f"测试数据{i+1}"
            else:
                # 最后的备选方案
                new_record_fields["文本字段"] = "测试数据"
        
        print(f"准备写入的字段数据: {new_record_fields}")
        
        try:
            write_result = await write_feishu_bitable_record(
                bitable_data['app_token'], 
                bitable_data['table_id'], 
                new_record_fields
            )
            print(f"写入单条记录结果: {write_result}")
        except Exception as e:
            print(f"写入单条记录失败: {str(e)}")
            print("尝试使用更简单的字段...")
            # 使用最简单的字段尝试
            simple_fields = {"名称": "测试数据"}
            try:
                write_result = await write_feishu_bitable_record(
                    bitable_data['app_token'], 
                    bitable_data['table_id'], 
                    simple_fields
                )
                print(f"使用简单字段写入成功: {write_result}")
            except Exception as e2:
                print(f"使用简单字段也失败了: {str(e2)}")
        
        # 批量写入记录
        batch_records = []
        if new_record_fields:
            # 创建与单条记录相同结构的批量记录
            batch_records = [
                {"fields": {list(new_record_fields.keys())[0] if new_record_fields.keys() else "名称": 
                           f"批量测试1"}},
                {"fields": {list(new_record_fields.keys())[0] if new_record_fields.keys() else "名称": 
                           f"批量测试2"}}
            ]
        else:
            # 使用通用字段
            batch_records = [
                {"fields": {"名称": "批量测试1"}},
                {"fields": {"名称": "批量测试2"}}
            ]
        
        try:
            batch_write_result = await write_feishu_bitable_batch_records(
                bitable_data['app_token'],
                bitable_data['table_id'],
                batch_records
            )
            print(f"批量写入记录结果: {batch_write_result}")
        except Exception as e:
            print(f"批量写入记录失败: {str(e)}")
        
        # 如果有记录，则更新第一条记录
        if bitable_data['records']:
            first_record_id = bitable_data['records'][0]['record_id']
            # 使用第一个安全字段进行更新
            update_fields = {}
            if new_record_fields:
                update_fields[list(new_record_fields.keys())[0]] = "已更新的记录"
            else:
                update_fields["名称"] = "已更新的记录"
            
            try:
                update_result = await update_feishu_bitable_record(
                    bitable_data['app_token'],
                    bitable_data['table_id'],
                    first_record_id,
                    update_fields
                )
                print(f"更新记录结果: {update_result}")
            except Exception as e:
                print(f"更新记录失败: {str(e)}")
            
            # 演示指定单元格更新（更新第一条记录的第一个字段）
            if field_names:
                first_field_name = list(field_names)[0]
                try:
                    cell_update_result = await update_feishu_bitable_cell(
                        bitable_data['app_token'],
                        bitable_data['table_id'],
                        first_record_id,
                        first_field_name,
                        "指定单元格更新的值"
                    )
                    print(f"指定单元格更新结果: {cell_update_result}")
                except Exception as e:
                    print(f"指定单元格更新失败: {str(e)}")
        
    except Exception as e:
        print(f"处理过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())