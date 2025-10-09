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


# 将两个辅助函数提前，确保在 read_feishu_spreadsheet 函数调用它们时已经定义

# 此处已将函数移动至上方，此处删除原位置的重复定义


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
            
            # 读取电子表格内容，扩大读取范围以确保能读取到所有需要的列
            read_url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values_batch_get"
            read_params = {
                "ranges": [f"{actual_sheet_id}!A1:Z1000"]  # 读取较大范围的数据，确保包含D到K列
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
                print(f"读取到 {len(values)} 行数据")
                
                # 遍历所有行和列，确保不遗漏任何数据
                for row_index, row in enumerate(values):
                    # 确保row是一个列表
                    if isinstance(row, list):
                        for col_index, cell in enumerate(row):
                            # 检查单元格是否包含数据
                            if cell is not None:
                                # 将行列索引转换为单元格引用 (如 0,0 -> A1)
                                cell_ref = _index_to_cell_ref(col_index, row_index)
                                
                                # 处理不同类型的单元格值
                                cell_value = ""
                                if isinstance(cell, str) and cell.strip():
                                    cell_value = cell.strip()
                                elif isinstance(cell, (int, float)):
                                    cell_value = str(cell)
                                elif cell:  # 其他非空值
                                    cell_value = str(cell)
                                
                                # 特别处理E、G、I、K列的数据
                                col_letter = _index_to_column_letter(col_index)
                                if col_letter == 'E':
                                    # E列使用专用函数提取纯文本内容
                                    cell_data[cell_ref] = extract_text_from_content(cell_value)
                                elif col_letter == 'G':
                                    # G列使用专用函数提取链接
                                    cell_data[cell_ref] = extract_link_from_g_column(cell_value)
                                elif col_letter == 'I':
                                    # I列使用文本提取函数提取纯文本内容
                                    cell_data[cell_ref] = extract_text_from_content(cell_value)
                                elif col_letter == 'K':
                                    # K列使用文本提取函数提取纯文本内容
                                    cell_data[cell_ref] = extract_text_from_content(cell_value)
                                else:
                                    cell_data[cell_ref] = cell_value
                                
                                # 特别关注D到K列的数据
                                if col_letter in ['D', 'E', 'F', 'G', 'H', 'I', 'J', 'K'] and cell:
                                    print(f"  发现{col_letter}列数据 ({cell_ref}): {cell_data[cell_ref]}")
            
            # 显示读取到的关键列数据统计
            d_col_count = sum(1 for ref in cell_data.keys() if ref.startswith('D'))
            e_col_count = sum(1 for ref in cell_data.keys() if ref.startswith('E'))
            f_col_count = sum(1 for ref in cell_data.keys() if ref.startswith('F'))
            g_col_count = sum(1 for ref in cell_data.keys() if ref.startswith('G'))
            h_col_count = sum(1 for ref in cell_data.keys() if ref.startswith('H'))
            i_col_count = sum(1 for ref in cell_data.keys() if ref.startswith('I'))
            j_col_count = sum(1 for ref in cell_data.keys() if ref.startswith('J'))
            k_col_count = sum(1 for ref in cell_data.keys() if ref.startswith('K'))
            
            print(f"D列数据数量: {d_col_count}")
            print(f"E列数据数量: {e_col_count}")
            print(f"F列数据数量: {f_col_count}")
            print(f"G列数据数量: {g_col_count}")
            print(f"H列数据数量: {h_col_count}")
            print(f"I列数据数量: {i_col_count}")
            print(f"J列数据数量: {j_col_count}")
            print(f"K列数据数量: {k_col_count}")
            
            return cell_data, sheet_title
            
    except Exception as e:
        print(f"Error reading spreadsheet: {str(e)}")
        raise


def _index_to_column_letter(col_index: int) -> str:
    """
    将列索引转换为列字母
    
    Args:
        col_index: 列索引 (从0开始)
        
    Returns:
        列字母 (如 A, B, ..., Z, AA, AB, ...)
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
    
    return col_letter


def extract_text_from_content(content: str) -> str:
    """
    从单元格内容中提取纯文本
    
    Args:
        content: 单元格原始内容
        
    Returns:
        提取的纯文本
    """
    # 确保输入是字符串
    if not isinstance(content, str):
        return str(content).strip()
    
    content = content.strip()
    if not content:
        return ""
        
    # 如果内容是字符串且看起来像JSON数组
    if content.startswith('[') and content.endswith(']'):
        try:
            # 尝试解析JSON
            data_list = json.loads(content)
            if isinstance(data_list, list):
                # 提取所有text字段并拼接
                texts = []
                for item in data_list:
                    if isinstance(item, dict):
                        # 优先检查最常见的情况: {'text': '...'}
                        if 'text' in item and isinstance(item['text'], str):
                            text = item['text'].strip()
                            if text and text not in ['\\n', '\n']:
                                texts.append(text)
                        # 检查嵌套情况: {'segment': {'text': '...'}}
                        elif ('segment' in item 
                              and isinstance(item['segment'], dict) 
                              and 'text' in item['segment'] 
                              and isinstance(item['segment']['text'], str)):
                            text = item['segment']['text'].strip()
                            if text and text not in ['\\n', '\n']:
                                texts.append(text)
                        # 检查其他可能的结构
                        elif ('elements' in item 
                              and isinstance(item['elements'], list)):
                            for element in item['elements']:
                                if (isinstance(element, dict) 
                                    and 'text' in element 
                                    and isinstance(element['text'], str)):
                                    text = element['text'].strip()
                                    if text and text not in ['\\n', '\n']:
                                        texts.append(text)
                        # 处理包含formattedText的情况
                        elif ('formattedText' in item 
                              and isinstance(item['formattedText'], str)):
                            text = item['formattedText'].strip()
                            if text and text not in ['\\n', '\n']:
                                texts.append(text)
                # 合并文本并清理多余空格
                result = ''.join(texts)
                return re.sub(r'\s+', ' ', result).strip()
        except (json.JSONDecodeError, KeyError, TypeError):
            # 解析失败时，不抛出异常，继续执行下面的逻辑
            pass
    
    # 处理类似 "[{...}]" 的字符串格式（E列数据）
    if content.startswith('[{') and content.endswith('}]'):
        try:
            # 用正则表达式提取所有text字段
            text_matches = re.findall(r"['\"]text['\"]\s*:\s*['\"](.*?)['\"]", content)
            if text_matches:
                # 过滤掉换行符等特殊字符
                filtered_texts = [text.replace('\\\\n', '').replace('\\n', '').replace('\n', '') 
                                  for text in text_matches 
                                  if text not in ['\\\\n', '\\n', '\n']]
                result = ''.join(filtered_texts)
                return re.sub(r'\s+', ' ', result).strip()
        except:
            pass
    
    # 移除常见的转义字符和HTML标签痕迹，只保留纯文本
    clean_content = re.sub(r'<[^>]+>', '', content)  # 移除HTML标签
    clean_content = clean_content.replace('\\\\n', ' ').replace('\\n', ' ').replace('\n', ' ')
    clean_content = re.sub(r'\s+', ' ', clean_content)  # 合并多个空白字符
    return clean_content.strip()


def extract_link_from_g_column(content: str) -> str:
    """
    从G列单元格内容中提取链接URL
    
    Args:
        content: G列单元格内容
        
    Returns:
        提取到的链接URL，如果没有找到则返回空字符串
    """
    # 确保输入是字符串
    if not isinstance(content, str):
        return str(content).strip()
        
    content = content.strip()
    if not content:
        return ""
    
    # 特殊处理类似 "[{'cellPosition': None, 'link': 'https://...', 'text': 'https://...', 'type': 'url'}]" 的数据
    if content.startswith("[{") and "'link':" in content:
        try:
            # 使用正则表达式直接提取link字段的值
            link_match = re.search(r"'link':\s*'([^']+)'", content)
            if link_match:
                url = link_match.group(1).strip()
                # 验证是否为有效的URL
                if url.startswith('http://') or url.startswith('https://'):
                    return url
        except:
            pass
    
    # 首选方法：尝试从结构化的JSON-like字符串中解析
    if content.startswith('[{') or content.startswith('{'):
        try:
            # 特殊处理单引号的JSON-like字符串
            # 将单引号替换为双引号以使其成为有效的JSON
            json_like = content.replace("'", '"')
            # 处理转义字符
            json_like = json_like.replace('\\', '\\\\')
            data = json.loads(json_like)
            
            # 统一处理data为列表
            if isinstance(data, dict):
                data = [data]
                
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        # 直接查找link键
                        if 'link' in item and isinstance(item['link'], str):
                            potential_url = item['link'].strip()
                            if potential_url.startswith('http://') or potential_url.startswith('https://'):
                                return potential_url
                        # 有时链接在'url'字段
                        elif 'url' in item and isinstance(item['url'], str):
                            potential_url = item['url'].strip()
                            if potential_url.startswith('http://') or potential_url.startswith('https://'):
                                return potential_url
        except (json.JSONDecodeError, KeyError, TypeError):
            # 解析失败，进入备用方案
            pass
    
    # 备用方案：使用字符串方法在字符串中搜索HTTP(S)链接
    try:
        # 查找http或https链接
        http_pos = content.find('http://')
        https_pos = content.find('https://')
        
        # 找到第一个出现的链接
        link_pos = max(http_pos, https_pos) if http_pos != -1 and https_pos != -1 else max(http_pos, https_pos)
        
        if link_pos != -1:
            # 从链接位置开始提取，直到遇到空格、引号或结束
            link_end_chars = [' ', '"', "'", '\n', '\r', '\t', ')', ']', '}']
            link_end_pos = len(content)
            
            for char in link_end_chars:
                pos = content.find(char, link_pos)
                if pos != -1 and pos < link_end_pos:
                    link_end_pos = pos
            
            url = content[link_pos:link_end_pos].strip()
            # 验证是否为有效的URL
            if url.startswith('http://') or url.startswith('https://'):
                return url
    except:
        pass
    
    # 最后的尝试，使用正则表达式匹配URL
    url_pattern = r'https?://[^\s\'"<>{}[\]()\\]+'
    matches = re.findall(url_pattern, content)
    if matches:
        # 返回找到的第一个有效链接
        url = matches[0].strip()
        if url.startswith('http://') or url.startswith('https://'):
            return url
    
    # 如果以上方法都失败，返回空字符串而不是原始内容
    return ""


def _index_to_cell_ref(col_index: int, row_index: int) -> str:
    """
    将行列索引转换为单元格引用 (如 0,0 -> A1)
    
    Args:
        col_index: 列索引 (从0开始)
        row_index: 行索引 (从0开始)
        
    Returns:
        单元格引用 (如 A1, B2)
    """
    col_letter = _index_to_column_letter(col_index)
    
    # 行号从1开始
    row_number = row_index + 1
    
    return f"{col_letter}{row_number}"


def generate_post_json(cell_data: dict) -> dict:
    """
    根据单元格数据生成POST请求的JSON（包含D到K列的数据，按行组织）
    
    Args:
        cell_data: 单元格数据字典
        
    Returns:
        用于POST请求的JSON数据（按行组织，包含D到K列）
    """
    # 按行组织数据，包含D到K列
    row_data = {}
    
    # 遍历所有单元格数据
    for cell_ref, content in cell_data.items():
        # 检查是否是D到K列的数据
        if cell_ref[0] in ['D', 'E', 'F', 'G', 'H', 'I', 'J', 'K'] or \
           (len(cell_ref) > 1 and cell_ref[:2] in ['D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']):
            # 提取行号
            row_number = int(''.join([c for c in cell_ref if c.isdigit()]))
            
            # 初始化行数据
            if row_number not in row_data:
                row_data[row_number] = {"row": row_number}
            
            # 添加列数据并特别处理E列和G列
            col_letter = cell_ref[0] if len(cell_ref) == 2 else cell_ref[:2]
            if col_letter == 'E':
                # 对E列使用文本提取函数
                row_data[row_number][col_letter] = extract_text_from_content(content)
            elif col_letter == 'G':
                # 对G列使用链接提取函数
                row_data[row_number][col_letter] = extract_link_from_g_column(content)
            elif col_letter == 'I':
                # 对I列也使用文本提取函数
                row_data[row_number][col_letter] = extract_text_from_content(content)
            elif col_letter == 'K':
                # 对K列也使用文本提取函数
                row_data[row_number][col_letter] = extract_text_from_content(content)
            else:
                row_data[row_number][col_letter] = content
    
    # 转换为列表形式，并按行号排序
    result = [row_data[row] for row in sorted(row_data.keys())]
    
    return result


async def main():
    """
    主函数 - 读取飞书电子表格并生成POST请求JSON
    """
    # 示例URL，包含特定的工作表ID
    spreadsheet_url = "https://dkke3lyh7o.feishu.cn/sheets/TzHesTaSqhFpJwttU2ucH8QjnKb?sheet=85q1XJ"
    
    print("开始读取飞书电子表格...")
    
    try:
        # 读取电子表格数据
        cell_data, sheet_title = await read_feishu_spreadsheet(spreadsheet_url)
        print(f"成功读取 {len(cell_data)} 个单元格数据")
        
        # 显示读取的数据，特别是D到K列
        print("\n读取的D到K列数据:")
        relevant_data = {k: v for k, v in cell_data.items() if k[0] in ['D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']}
        
        # 按行显示数据
        row_groups = {}
        for cell_ref, content in relevant_data.items():
            row_number = int(''.join([c for c in cell_ref if c.isdigit()]))
            if row_number not in row_groups:
                row_groups[row_number] = {}
            row_groups[row_number][cell_ref] = content
        
        for row_number in sorted(row_groups.keys()):
            print(f"\n第{row_number}行:")
            for cell_ref, content in sorted(row_groups[row_number].items()):
                print(f"  {cell_ref}: {content}")
        
        # 显示前10个数据作为示例
        print(f"\n前10个单元格数据:")
        count = 0
        for cell_ref, content in sorted(cell_data.items()):
            if count >= 10:
                break
            print(f"  {cell_ref}: {content}")
            count += 1
        
        # 生成POST请求JSON（按行组织，只包含D到J列）
        post_json = generate_post_json(cell_data)
        print("\n生成的POST请求JSON (按行组织，只包含D到J列):")
        print(json.dumps(post_json, ensure_ascii=False, indent=2)[:1000] + "..." if len(json.dumps(post_json, ensure_ascii=False, indent=2)) > 1000 else json.dumps(post_json, ensure_ascii=False, indent=2))
        
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