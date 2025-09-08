# 直接调用接口方式使用示例

## 功能说明

本文档展示了如何在图文大纲模块中使用直接调用接口的方式按单元格引用填充数据。

## 使用方法

### 1. 创建图文大纲智能体实例

```python
from agents.graphic_outline_agent import GraphicOutlineAgent

# 创建智能体实例
agent = GraphicOutlineAgent()
```

### 2. 创建电子表格（可选）

```python
# 准备创建请求数据
create_request = {
    "topic": "人工智能发展现状",
    "outline_data": {
        "topic": "人工智能发展现状",
        "sections": [
            {
                "title": "引言",
                "content": "人工智能作为当今科技发展的前沿领域，正深刻改变着我们的生活和工作方式。",
                "images": ["ai_intro.jpg"],
                "word_count": 150
            },
            {
                "title": "技术发展",
                "content": "从机器学习到深度学习，人工智能技术不断突破，应用领域日益广泛。",
                "images": ["ai_tech.jpg", "ml_chart.png"],
                "word_count": 300
            }
        ],
        "total_words": 450,
        "estimated_time": "5分钟"
    },
    "fill_outline_data": False  # 不自动填充大纲数据，后续通过直接调用接口填充
}

# 创建电子表格
create_result = await agent.create_feishu_sheet(create_request)

# 获取电子表格token和sheet_id
spreadsheet_token = create_result["spreadsheet_token"]
sheet_id = create_result["sheet_id"]
```

### 3. 直接调用接口填充单元格数据

```python
# 准备要填充的单元格数据
cell_data = {
    "A1": "人工智能发展现状分析报告",
    "B1": "2025年度",
    "A2": "报告作者：AI研究团队",
    "A3": "报告日期：2025-09-07",
    "A5": "1",
    "B5": "引言",
    "C5": "人工智能作为当今科技发展的前沿领域，正深刻改变着我们的生活和工作方式。",
    "D5": "ai_intro.jpg",
    "E5": "150",
    "A6": "2",
    "B6": "技术发展",
    "C6": "从机器学习到深度学习，人工智能技术不断突破，应用领域日益广泛。",
    "D6": "ai_tech.jpg, ml_chart.png",
    "E6": "300"
}

# 直接调用接口填充单元格数据
fill_result = await agent.fill_cells_in_sheet(spreadsheet_token, sheet_id, cell_data)

# 检查填充结果
if fill_result.get("status") == "success":
    print("单元格数据填充成功!")
else:
    print(f"单元格数据填充失败: {fill_result.get('error')}")
```

### 4. 部分单元格填充示例

```python
# 只填充标题行
title_data = {
    "A1": "人工智能发展现状分析报告",
    "B1": "2025年度"
}

# 只填充作者信息
author_data = {
    "A2": "报告作者：AI研究团队"
}

# 分别调用接口填充不同部分
await agent.fill_cells_in_sheet(spreadsheet_token, sheet_id, title_data)
await agent.fill_cells_in_sheet(spreadsheet_token, sheet_id, author_data)
```

## 完整示例代码

```python
import asyncio
from agents.graphic_outline_agent import GraphicOutlineAgent

async def main():
    # 创建图文大纲智能体实例
    agent = GraphicOutlineAgent()
    
    # 创建电子表格
    create_request = {
        "topic": "人工智能发展现状",
        "fill_outline_data": False  # 不自动填充大纲数据
    }
    
    create_result = await agent.create_feishu_sheet(create_request)
    spreadsheet_token = create_result["spreadsheet_token"]
    sheet_id = create_result["sheet_id"]
    
    # 准备并填充单元格数据
    cell_data = {
        "A1": "人工智能发展现状分析报告",
        "B1": "2025年度",
        "A2": "报告作者：AI研究团队",
        "A5": "1",
        "B5": "引言",
        "C5": "人工智能作为当今科技发展的前沿领域，正深刻改变着我们的生活和工作方式。",
        "D5": "ai_intro.jpg",
        "E5": "150"
    }
    
    # 直接调用接口填充数据
    fill_result = await agent.fill_cells_in_sheet(spreadsheet_token, sheet_id, cell_data)
    
    if fill_result.get("status") == "success":
        print("数据填充成功!")
    else:
        print(f"数据填充失败: {fill_result.get('error')}")

# 运行示例
# asyncio.run(main())
```

## 注意事项

1. 使用直接调用接口方式时，需要先创建电子表格获取 `spreadsheet_token` 和 `sheet_id`
2. 可以一次性填充多个单元格，也可以分多次填充不同单元格
3. 只有明确指定的单元格会被修改，未指定的单元格保持原状
4. 单元格引用格式应为标准的Excel格式（如 "A1", "B2" 等）
5. 如果需要覆盖已有的数据，直接指定相同单元格引用即可