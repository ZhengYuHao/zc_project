"""
脚本用于更新飞书多维表格中指定记录的特定字段
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.feishu_bitable_processor import (
    extract_info_from_feishu_url,
    update_feishu_bitable_cell
)


async def update_record_field(url: str, field_name: str, field_value: str):
    """
    更新飞书多维表格中指定记录的特定字段
    
    Args:
        url: 飞书多维表格URL
        field_name: 要更新的字段名
        field_value: 要写入的字段值
    """
    print(f"处理URL: {url}")
    print(f"更新字段: {field_name}")
    print(f"字段值: {field_value}")
    
    # 1. 提取URL信息
    print("\n1. 提取URL信息...")
    info = extract_info_from_feishu_url(url)
    print(f"提取的信息: {info}")
    
    # 检查必要信息
    if not info.get("app_token"):
        raise ValueError("无法从URL中提取app_token")
    
    if not info.get("table_id"):
        raise ValueError("无法从URL中提取table_id")
        
    if not info.get("record_id"):
        raise ValueError("无法从URL中提取record_id")
    
    print("✓ URL信息提取成功")
    
    # 2. 更新指定字段
    print(f"\n2. 更新字段 '{field_name}'...")
    try:
        result = await update_feishu_bitable_cell(
            info["app_token"],
            info["table_id"],
            info["record_id"],
            field_name,
            field_value
        )
        print(f"✓ 字段更新成功: {result}")
        return result
    except Exception as e:
        print(f"✗ 字段更新失败: {str(e)}")
        raise


async def main():
    """主函数"""
    # 使用您提供的实际URL
    url = "https://dkke3lyh7o.feishu.cn/base/Yun7b8neBakSzDscIUmcmOMNnQv?table=tblWEf5vmSdEUBFi&view=vewBkURqsq&field=fldw2TicQY&record=recIAENn3o"
    
    # 更新"图文大纲创作结果"字段为"好的"
    await update_record_field(url, "图文大纲创作结果", "好的")


if __name__ == "__main__":
    asyncio.run(main())