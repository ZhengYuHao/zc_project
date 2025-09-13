import pandas as pd

# 读取Excel文件
excel_file = pd.ExcelFile('2025.xlsx')

# 打印所有工作表名称
print('工作表名称:', excel_file.sheet_names)

# 读取第一个工作表
df = pd.read_excel('2025.xlsx', sheet_name=excel_file.sheet_names[0])

# 打印列名
print('\n第一个工作表的列名:')
print(df.columns.tolist())

# 打印前几行数据
print('\n前5行数据:')
print(df.head())