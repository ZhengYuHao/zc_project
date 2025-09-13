import pandas as pd

# 读取Excel文件
excel_file = pd.ExcelFile('2025.xlsx')

print('工作表数量:', len(excel_file.sheet_names))
print('工作表名称:', excel_file.sheet_names)

# 分析每个工作表的结构
for i, sheet_name in enumerate(excel_file.sheet_names):
    print(f"\n=== 工作表 {i+1}: {sheet_name} ===")
    df = pd.read_excel('2025.xlsx', sheet_name=sheet_name)
    
    print(f"行数: {len(df)}, 列数: {len(df.columns)}")
    print("列名:", df.columns.tolist())
    
    # 显示前10行数据
    print("前10行数据:")
    print(df.head(10))
    
    # 统计非空单元格数量
    print("每列非空值数量:")
    for col in df.columns:
        non_null_count = df[col].count()
        print(f"  {col}: {non_null_count}")
    
    # 如果查看前几个工作表就够了，可以提前结束
    if i >= 2:  # 只查看前3个工作表的详细信息
        print("...")
        break