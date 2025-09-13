import pandas as pd

# 读取Excel文件
excel_file = pd.ExcelFile('2025.xlsx')

print('工作表数量:', len(excel_file.sheet_names))
print('工作表名称:', excel_file.sheet_names)

# 详细分析每个工作表的结构
all_words = []
for i, sheet_name in enumerate(excel_file.sheet_names):
    print(f"\n=== 工作表 {i+1}: '{sheet_name}' ===")
    df = pd.read_excel('2025.xlsx', sheet_name=sheet_name)
    
    print(f"行数: {len(df)}, 列数: {len(df.columns)}")
    print("列名:", df.columns.tolist())
    
    # 显示所有数据
    print("完整数据:")
    print(df.to_string())
    
    # 提取违禁词
    sheet_words = []
    for index, row in df.iterrows():
        # 跳过标题行
        if index == 0:
            continue
            
        # 根据列数采用不同策略
        if len(df.columns) >= 3:
            # 通常第3列是违禁词列
            if len(row) >= 3 and pd.notna(row[2]) and str(row[2]).strip() != "":
                word = str(row[2]).strip()
                # 过滤掉说明性文字
                if not any(keyword in word for keyword in 
                         ['说明', '原理', '平替词', '替代词', '禁用原理', 'NaN', 'Unnamed']):
                    sheet_words.append(word)
                    all_words.append((sheet_name, word))
        elif len(df.columns) == 2:
            # 2列的情况，第2列可能是违禁词列
            if len(row) >= 2 and pd.notna(row[1]) and str(row[1]).strip() != "":
                word = str(row[1]).strip()
                # 过滤掉说明性文字
                if not any(keyword in word for keyword in 
                         ['说明', '原理', '平替词', '替代词', '禁用原理', 'NaN', 'Unnamed']):
                    sheet_words.append(word)
                    all_words.append((sheet_name, word))
    
    print(f"提取到 {len(sheet_words)} 个违禁词:")
    for word in sheet_words:
        print(f"  - {word}")
    
    # 为避免输出过多信息，只显示前几个工作表的详细信息
    if i >= 2:
        print("...")
        break

print(f"\n总共提取到 {len(all_words)} 个违禁词")