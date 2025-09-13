#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元格填充工具模块
提供简单的按单元格引用填充数据功能
"""

import httpx
from typing import Dict, Any, Optional
from utils.logger import get_logger


class CellFiller:
    """单元格填充工具类"""
    
    def __init__(self):
        self.logger = get_logger("utils.cell_filler")
    
    async def fill_cells(self, 
                        spreadsheet_token: str, 
                        sheet_id: str, 
                        tenant_token: str,
                        cell_data: Dict[str, Any]) -> bool:
        """
        按单元格引用填充数据
        
        Args:
            spreadsheet_token: 电子表格token
            sheet_id: 工作表ID
            tenant_token: 租户访问令牌
            cell_data: 单元格数据，格式 {"A1": "值1", "B2": "值2"}
            
        Returns:
            是否填充成功
        """
        self.logger.info(f"Filling cells for spreadsheet: {spreadsheet_token}")
        
        try:
            headers = {
                "Authorization": f"Bearer {tenant_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            # 构造请求数据 - 使用正确的API格式
            value_ranges = []
            for cell_ref, value in cell_data.items():
                value_ranges.append({
                    "range": f"{sheet_id}!{cell_ref}:{cell_ref}",
                    "values": [[value]]
                })
            
            payload = {
                "valueRanges": value_ranges
            }
            
            # 发送请求
            url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values_batch_update"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()
                
                if result.get("code") != 0:
                    raise Exception(f"Failed to fill cells: {result}")
            
            self.logger.info(f"Successfully filled cells for spreadsheet: {spreadsheet_token}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error filling cells for spreadsheet {spreadsheet_token}: {str(e)}")
            raise


# 使用示例
"""
from utils.cell_filler import CellFiller

# 创建填充器实例
filler = CellFiller()

# 准备数据
cell_data = {
    "A1": "标题内容",
    "B1": "副标题",
    "A2": "作者信息"
}

# 执行填充
await filler.fill_cells(spreadsheet_token, sheet_id, tenant_token, cell_data)
"""