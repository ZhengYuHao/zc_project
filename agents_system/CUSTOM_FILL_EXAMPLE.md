### 方法二：使用简单的单元格填充接口

如果您已经有了电子表格的 token 和 sheet_id，可以直接调用 [fill_cells_in_sheet](file:///e:\pyProject\zc_project\agents_system\agents\graphic_outline_agent.py#L485-L522) 方法：

```python
from agents.graphic_outline_agent import GraphicOutlineAgent

# 创建智能体实例
agent = GraphicOutlineAgent()

# 准备要填充的数据
cell_data = {
    "A1": "这是A1单元格的内容",
    "B1": "这是B1单元格的内容",
    "A2": "这是A2单元格的内容"
}

# 调用填充方法
result = await agent.fill_cells_in_sheet(spreadsheet_token, sheet_id, cell_data)
```
# 自定义填充功能使用示例

## 功能说明

在图文大纲智能体中添加了自定义填充功能，允许用户在基于模板生成新表后，按照特定的单元格位置手动填充数据。

## 使用方法

### 方法一：在创建电子表格时填充（推荐）

在调用 `/feishu/sheet` 接口时，添加 `custom_fill_data` 字段来指定要填充的数据。

### 按单元格填充数据

```json
{
  "topic": "测试主题",
  "outline_data": {
    // ... 大纲数据
  },
  "custom_fill_data": {
    "cells": {
      "A1": "文档标题",
      "B1": "测试主题",
      "A2": "作者：张三",
      "A3": "创建日期：2025-01-01"
    }
  }
}
```

### 完整示例

```json
{
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
  "custom_fill_data": {
    "cells": {
      "A1": "人工智能发展现状分析报告",
      "B1": "2025年度",
      "A2": "报告作者：AI研究团队",
      "A3": "报告日期：2025-09-07"
    }
  }
}
```

## 注意事项

1. `custom_fill_data` 字段是可选的，如果不需要自定义填充可以不提供
2. 请确保提供的单元格引用格式正确（如 "A1", "B2" 等）
3. 自定义填充会在大纲数据填充之后进行，如果位置冲突，自定义数据会覆盖大纲数据
4. 使用 [fill_cells_in_sheet](file:///e:\pyProject\zc_project\agents_system\agents\graphic_outline_agent.py#L485-L522) 方法时，需要先确保电子表格已创建并获取到 spreadsheet_token 和 sheet_id