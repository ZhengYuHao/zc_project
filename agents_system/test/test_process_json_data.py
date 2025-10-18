import json
import os
import sys
import re
from typing import Dict, List, Any

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def load_json_data(file_path: str) -> Dict[str, Any]:
    """
    加载JSON数据文件
    
    Args:
        file_path: JSON文件路径
        
    Returns:
        JSON数据字典
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_link_from_g_column(content: str) -> str:
    """
    从G列单元格内容中提取链接URL
    
    Args:
        content: G列单元格内容
        
    Returns:
        提取到的链接URL，如果没有找到则返回原始内容
    """
    # 处理类似 "[{'cellPosition': None, 'link': 'https://...', 'text': 'https://...', 'type': 'url'}]" 的数据
    if content.startswith("[{") and "'link':" in content:
        try:
            # 使用正则表达式提取link字段的值
            link_match = re.search(r"'link':\s*'([^']+)'", content)
            if link_match:
                return link_match.group(1)
        except:
            pass
    
    # 如果是其他格式，尝试用正则表达式匹配URL
    url_pattern = r'https?://[^\s"\']+)'
    urls = re.findall(url_pattern, content)
    if urls:
        return urls[0]
    
    # 如果没有找到链接，返回原始内容
    return content


def extract_range_data(cell_data: Dict[str, str], start_col: str = 'A', end_col: str = 'K', 
                       start_row: int = 2, end_row: int = 21) -> Dict[str, List[Dict[str, Any]]]:
    """
    从单元格数据中提取指定范围的数据
    
    Args:
        cell_data: 单元格数据字典，格式为 {"A1": "内容", "B1": "内容", ...}
        start_col: 起始列（默认'A'）
        end_col: 结束列（默认'K'）
        start_row: 起始行（默认2）
        end_row: 结束行（默认21）
        
    Returns:
        按列组织的数据字典，格式为 {"列名": [{"row": 行号, "content": 内容}, ...]}
    """
    # 计算列的索引范围
    start_col_index = ord(start_col) - ord('A')
    end_col_index = ord(end_col) - ord('A')
    
    # 存储结果的字典，初始化所有列为空列表
    result = {}
    for col_index in range(start_col_index, end_col_index + 1):
        col_letter = chr(ord('A') + col_index)
        result[col_letter] = []
    
    # 遍历指定的列范围
    for col_index in range(start_col_index, end_col_index + 1):
        col_letter = chr(ord('A') + col_index)
        
        # 遍历指定的行范围
        for row in range(start_row, end_row + 1):
            cell_ref = f"{col_letter}{row}"
            if cell_ref in cell_data and cell_data[cell_ref].strip():
                content = cell_data[cell_ref].strip()
                
                # 对G列进行特殊处理，只提取链接URL
                if col_letter == 'G':
                    content = extract_link_from_g_column(content)
                
                result[col_letter].append({
                    "row": row,
                    "content": content
                })
    
    return result


def generate_post_requests(column_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    生成POST请求数据，只保留链接URL
    
    Args:
        column_data: 按列组织的数据
        
    Returns:
        包含所有列数据的大JSON集，G列只包含链接URL
    """
    # 构建大JSON集
    post_requests = {
        "columns": {}
    }
    
    # 为每一列创建一个小JSON集
    for col_letter, cells in column_data.items():
        # 对于G列，只保留content字段中的链接URL
        if col_letter == 'G':
            post_requests["columns"][col_letter] = {
                "column": col_letter,
                "data": [cell["content"] for cell in cells]  # 只保留链接URL
            }
        else:
            # 其他列保持原有结构
            post_requests["columns"][col_letter] = {
                "column": col_letter,
                "data": cells
            }
    
    return post_requests


def save_post_requests(post_requests: Dict[str, Any], output_file: str):
    """
    保存POST请求数据到文件
    
    Args:
        post_requests: POST请求数据
        output_file: 输出文件路径
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(post_requests, f, ensure_ascii=False, indent=2)


def main():
    """
    主函数 - 处理JSON数据并生成POST请求
    """
    # 输入文件名
    input_filename = "spreadsheet_post_data_图文大纲创作.json"
    
    # 检查文件是否存在
    if not os.path.exists(input_filename):
        print(f"错误: 文件 {input_filename} 不存在")
        return
    
    try:
        # 加载JSON数据
        print(f"正在加载 {input_filename}...")
        cell_data = load_json_data(input_filename)
        print(f"成功加载 {len(cell_data)} 个单元格数据")
        
        # 提取指定范围的数据 (A到K列，2到21行)
        print("正在提取指定范围的数据 (A-K列, 2-21行)...")
        column_data = extract_range_data(cell_data, 'A', 'K', 2, 21)
        
        # 统计提取的数据
        total_cells = 0
        print("\n各列数据统计:")
        for col_letter in [chr(ord('A') + i) for i in range(11)]:  # A到K
            cells = column_data.get(col_letter, [])
            print(f"  列 {col_letter}: {len(cells)} 个单元格")
            total_cells += len(cells)
        print(f"总共提取 {total_cells} 个单元格数据")
        
        # 显示G列处理后的数据示例
        if 'G' in column_data and column_data['G']:
            print("\nG列数据示例（已处理，只保留链接URL）:")
            for i, item in enumerate(column_data['G'][:5]):  # 显示前5个
                print(f"  {i+1}. {item['content']}")
        
        # 生成POST请求数据
        print("正在生成POST请求数据...")
        post_requests = generate_post_requests(column_data)
        
        # 显示G列最终数据结构示例
        if 'G' in post_requests["columns"]:
            g_data = post_requests["columns"]['G']["data"]
            print(f"\nG列最终数据结构（只包含 {len(g_data)} 个链接URL）:")
            for i, url in enumerate(g_data[:3]):  # 显示前3个
                print(f"  {i+1}. {url}")
        
        # 保存到文件
        output_filename = "processed_post_requests.json"
        save_post_requests(post_requests, output_filename)
        print(f"\n数据已保存到 {output_filename} 文件")
        
        # 显示完整的输出结构示例
        print("\n输出数据结构示例:")
        example_output = {
            "columns": {}
        }
        
        # 显示前几列作为示例
        for col in ['A', 'B', 'C', 'D', 'G', 'K']:
            if col in post_requests["columns"]:
                example_output["columns"][col] = post_requests["columns"][col]
        
        print(json.dumps(example_output, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"处理过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()