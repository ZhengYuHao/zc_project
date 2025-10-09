import asyncio
import json
import sys
import os
import re
from urllib.parse import urlparse, parse_qs

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from models.feishu import get_feishu_client
from config.settings import settings


def extract_spreadsheet_info(url: str) -> tuple:
    """
    从飞书电子表格URL中提取spreadsheet_token和sheet_id
    
    Args:
        url: 飞书电子表格的完整URL
        
    Returns:
        (spreadsheet_token, sheet_id) 元组
    """
    # 示例URL: https://dkke3lyh7o.feishu.cn/sheets/TzHesTaSqhFpJwttU2ucH8QjnKb?sheet=85q1XJ
    
    # 使用urlparse解析URL
    parsed_url = urlparse(url)
    
    # 提取spreadsheet_token (路径中的部分)
    path_parts = parsed_url.path.split('/')
    spreadsheet_token = None
    for part in path_parts:
        if part and not part.endswith('.cn') and not part == 'sheets':
            spreadsheet_token = part
            break
    
    # 提取sheet_id (查询参数中的部分)
    query_params = parse_qs(parsed_url.query)
    sheet_id = query_params.get('sheet', [None])[0]
    
    return spreadsheet_token, sheet_id


async def read_feishu_spreadsheet(spreadsheet_url_or_token: str, specified_sheet_id: str = None) -> tuple:
    """
    读取飞书电子表格数据，并按单元格位置收集信息
    
    Args:
        spreadsheet_url_or_token: 电子表格URL或token
        specified_sheet_id: 指定的工作表ID（可选）
        
    Returns:
        (单元格数据字典, 工作表标题) 元组
    """
    # 从URL中提取信息
    spreadsheet_token, sheet_id_from_url = extract_spreadsheet_info(spreadsheet_url_or_token)
    
    # 如果没有从URL中提取到token，则认为输入的是token
    if not spreadsheet_token:
        spreadsheet_token = spreadsheet_url_or_token
    
    # 优先使用指定的sheet_id，否则使用URL中的sheet_id
    target_sheet_id = specified_sheet_id or sheet_id_from_url
    
    print(f"Spreadsheet token: {spreadsheet_token}")
    print(f"Target sheet ID: {target_sheet_id}")
    
    # 获取飞书客户端
    feishu_client = get_feishu_client()
    
    try:
        # 获取tenant_access_token
        tenant_token = await feishu_client.get_tenant_access_token()
        
        # 获取电子表格元数据
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
            
            # 获取工作表信息
            sheets = meta_result.get("data", {}).get("sheets", [])
            
            # 如果指定了sheet_id，则查找对应的工作表；否则使用第一个工作表
            target_sheet = None
            if target_sheet_id:
                for sheet in sheets:
                    # 检查多种可能的sheet_id字段
                    sheet_ids = [
                        sheet.get("sheetId"),
                        sheet.get("sheet_id"),
                        sheet.get("index")
                    ]
                    if target_sheet_id in sheet_ids:
                        target_sheet = sheet
                        break
                
                if not target_sheet:
                    print(f"Warning: Specified sheet_id '{target_sheet_id}' not found, using first sheet")
                    target_sheet = sheets[0] if sheets else None
            else:
                # 使用第一个工作表
                target_sheet = sheets[0] if sheets else None
            
            if not target_sheet:
                raise Exception("No sheets found in spreadsheet")
            
            # 获取实际的sheet_id用于API调用
            actual_sheet_id = target_sheet.get("sheetId") or target_sheet.get("sheet_id") or target_sheet.get("index", "0")
            sheet_title = target_sheet.get("title", "Unknown")
            
            print(f"Using sheet: {sheet_title} (ID: {actual_sheet_id})")
            
            # 读取电子表格内容
            read_url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values_batch_get"
            read_params = {
                "ranges": [f"{actual_sheet_id}!A1:Z1000"]  # 读取较大范围的数据
            }
            
            read_response = await client.get(read_url, headers=headers, params=read_params)
            read_response.raise_for_status()
            read_result = read_response.json()
            
            if read_result.get("code") != 0:
                raise Exception(f"Failed to read spreadsheet data: {read_result}")
            
            # 提取文本内容及其单元格位置
            value_ranges = read_result.get("data", {}).get("valueRanges", [])
            cell_data = {}  # 存储单元格数据 { "A1": "内容", "B1": "内容", ...}
            
            if value_ranges:
                values = value_ranges[0].get("values", [])
                for row_index, row in enumerate(values):
                    for col_index, cell in enumerate(row):
                        if cell and isinstance(cell, str) and cell.strip():
                            # 将行列索引转换为单元格引用 (如 0,0 -> A1)
                            cell_ref = _index_to_cell_ref(col_index, row_index)
                            cell_data[cell_ref] = cell.strip()
            
            return cell_data, sheet_title
            
    except Exception as e:
        print(f"Error reading spreadsheet: {str(e)}")
        raise


def _index_to_cell_ref(col_index: int, row_index: int) -> str:
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


def generate_post_json(cell_data: dict) -> dict:
    """
    根据单元格数据生成POST请求的JSON（只包含单元格数据）
    
    Args:
        cell_data: 单元格数据字典
        
    Returns:
        用于POST请求的JSON数据（只包含单元格数据）
    """
    # 直接返回单元格数据，不包含额外的元数据
    return cell_data


async def main():
    """
    主函数 - 读取飞书电子表格并生成POST请求JSON
    """
    # 示例URL，包含特定的工作表ID
    spreadsheet_url = "https://dkke3lyh7o.feishu.cn/sheets/TzHesTaSqhFpJwttU2ucH8QjnKb?sheet=BRYeAx"
    
    print("开始读取飞书电子表格...")
    
    try:
        # 读取电子表格数据
        cell_data, sheet_title = await read_feishu_spreadsheet(spreadsheet_url)
        print(f"成功读取 {len(cell_data)} 个单元格数据")
        
        # 显示读取的数据
        print("\n读取的单元格数据:")
        for cell_ref, content in cell_data.items():
            print(f"  {cell_ref}: {content}")
        
        # 生成POST请求JSON
        post_json = generate_post_json(cell_data)
        print("\n生成的POST请求JSON:")
        print(json.dumps(post_json, ensure_ascii=False, indent=2))
        
        # 生成包含工作表名称的文件名
        # 清理工作表标题中的非法字符
        safe_sheet_title = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', sheet_title)
        filename = f"spreadsheet_post_data_{safe_sheet_title}.json"
        
        # 保存到文件
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(post_json, f, ensure_ascii=False, indent=2)
        print(f"\n数据已保存到 {filename} 文件")
        
    except Exception as e:
        print(f"处理过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())