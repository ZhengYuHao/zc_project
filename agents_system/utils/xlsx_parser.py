import pandas as pd
from typing import Dict, List, Any, Tuple
import os
from utils.logger import get_logger

logger = get_logger(__name__)


class XLSXParser:
    """
    XLSX文件解析器，用于解析包含违禁词的Excel文件
    """
    
    def __init__(self):
        self.logger = logger

    def parse_prohibited_words(self, file_path: str, sheet_names: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        解析XLSX文件中的违禁词
        
        Args:
            file_path: XLSX文件路径
            sheet_names: 需要解析的工作表名称列表，如果为None则解析所有工作表
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: 以工作表名为键，违禁词列表为值的字典
            每个违禁词包含: sensitive_word, replacement, level, comment 等字段
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件 {file_path} 不存在")
        
        self.logger.info(f"开始解析XLSX文件: {file_path}")
        
        # 读取Excel文件
        excel_file = pd.ExcelFile(file_path)
        
        # 如果未指定工作表，则解析所有工作表
        if sheet_names is None:
            sheet_names = excel_file.sheet_names
            
        result = {}
        
        for sheet_name in sheet_names:
            if sheet_name not in excel_file.sheet_names:
                self.logger.warning(f"工作表 {sheet_name} 不存在于文件 {file_path} 中")
                continue
                
            self.logger.info(f"解析工作表: {sheet_name}")
            
            # 读取工作表数据
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # 解析违禁词数据
            prohibited_words = []
            
            # 跳过标题行（第一行）
            for index, row in df.iterrows():
                # 跳过标题行
                if index == 0:
                    continue
                    
                try:
                    # 根据工作表的列数采用不同的解析策略
                    if len(df.columns) >= 3:
                        # 对于3列及以上的工作表，第3列通常是违禁词列
                        if len(row) >= 3 and pd.notna(row[2]) and str(row[2]).strip() != "":
                            sensitive_word = str(row[2]).strip()
                            
                            # 过滤掉明显不是违禁词的内容
                            if not any(keyword in sensitive_word for keyword in 
                                     ['说明', '原理', '平替词', '替代词', '禁用原理', 'NaN', 'Unnamed', '违禁词', '改写方案']):
                                word_info = {
                                    'sensitive_word': sensitive_word,
                                    'replacement': '***',  # 默认替换词
                                    'level': 1,  # 默认级别
                                    'comment': str(row[1]).strip() if len(row) > 1 and pd.notna(row[1]) else ''  # 第2列为类别/备注
                                }
                                prohibited_words.append(word_info)
                                
                    elif len(df.columns) == 2:
                        # 对于2列的工作表，第2列可能是违禁词列
                        if len(row) >= 2 and pd.notna(row[1]) and str(row[1]).strip() != "":
                            sensitive_word = str(row[1]).strip()
                            
                            # 过滤掉明显不是违禁词的内容
                            if not any(keyword in sensitive_word for keyword in 
                                     ['说明', '原理', '平替词', '替代词', '禁用原理', 'NaN', 'Unnamed', '违禁词', '改写方案']):
                                word_info = {
                                    'sensitive_word': sensitive_word,
                                    'replacement': '***',  # 默认替换词
                                    'level': 1,  # 默认级别
                                    'comment': str(row[0]).strip() if len(row) > 0 and pd.notna(row[0]) else ''  # 第1列为类别/备注
                                }
                                prohibited_words.append(word_info)
                                
                except (ValueError, KeyError, IndexError) as e:
                    self.logger.warning(f"工作表 {sheet_name} 第 {index+1} 行数据解析失败: {e}")
                    continue
            
            result[sheet_name] = prohibited_words
            self.logger.info(f"从工作表 {sheet_name} 解析到 {len(prohibited_words)} 个违禁词")
        
        self.logger.info(f"XLSX文件解析完成，共处理 {len(result)} 个工作表")
        return result

    def parse_all_sheets(self, file_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        解析XLSX文件中的所有工作表
        
        Args:
            file_path: XLSX文件路径
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: 以工作表名为键，违禁词列表为值的字典
        """
        return self.parse_prohibited_words(file_path)

    def parse_specific_sheets(self, file_path: str, sheet_names: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        解析XLSX文件中的指定工作表
 
       Args:
            file_path: XLSX文件路径
            sheet_names: 需要解析的工作表名称列表
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: 以工作表名为键，违禁词列表为值的字典
        """
        return self.parse_prohibited_words(file_path, sheet_names)
        
    def export_to_text_files(self, parsed_data: Dict[str, List[Dict[str, Any]]], output_dir: str = "prohibited_words_output") -> None:
        """
        将解析后的违禁词数据导出到文本文件中，每个工作表对应一个文本文件
        
        Args:
            parsed_data: 解析后的违禁词数据，以工作表名为键，违禁词列表为值的字典
            output_dir: 输出目录路径，默认为"prohibited_words_output"
        """
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            self.logger.info(f"创建输出目录: {output_dir}")
        
        # 为每个工作表创建一个文本文件
        for sheet_name, words in parsed_data.items():
            # 清理文件名中的非法字符
            safe_sheet_name = "".join(c for c in sheet_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            file_name = f"{safe_sheet_name}.txt"
            file_path = os.path.join(output_dir, file_name)
            
            self.logger.info(f"导出工作表 {sheet_name} 到文件: {file_path}")
            
            # 写入违禁词到文件，每行一个违禁词，便于后续作为set使用
            with open(file_path, 'w', encoding='utf-8') as f:
                for word_info in words:
                    f.write(f"{word_info['sensitive_word']}\n")
            
            self.logger.info(f"工作表 {sheet_name} 的数据已导出到: {file_path}")
        
        self.logger.info(f"所有违禁词数据已导出到目录: {output_dir}")
        
    def export_all_to_single_file(self, parsed_data: Dict[str, List[Dict[str, Any]]], output_file: str = "all_prohibited_words.txt") -> None:
        """
        将所有解析后的违禁词数据导出到单个文本文件中，每行一个违禁词
        
        Args:
            parsed_data: 解析后的违禁词数据，以工作表名为键，违禁词列表为值的字典
            output_file: 输出文件路径，默认为"all_prohibited_words.txt"
        """
        all_words = []
        for sheet_name, words in parsed_data.items():
            for word_info in words:
                all_words.append(word_info['sensitive_word'])
        
        # 去重
        unique_words = list(set(all_words))
        
        # 写入所有违禁词到单个文件
        with open(output_file, 'w', encoding='utf-8') as f:
            for word in sorted(unique_words):
                f.write(f"{word}\n")
        
        self.logger.info(f"所有 {len(unique_words)} 个唯一违禁词已导出到文件: {output_file}")