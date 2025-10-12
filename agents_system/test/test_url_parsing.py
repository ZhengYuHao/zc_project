"""
测试URL解析功能
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.feishu_bitable_processor import extract_info_from_feishu_url


def test_url_parsing():
    """测试URL解析"""
    # 使用您提供的实际URL
    url = "https://dkke3lyh7o.feishu.cn/base/Yun7b8neBakSzDscIUmcmOMNnQv?table=tblWEf5vmSdEUBFi&view=vewBkURqsq&field=fldw2TicQY&record=recIAENn3o"
    
    print(f"解析URL: {url}")
    
    info = extract_info_from_feishu_url(url)
    print(f"提取信息: {info}")
    
    # 分析各部分
    print("\n各部分分析:")
    print(f"app_token (从域名提取): {info['app_token']}")
    print(f"table_id (从参数提取): {info['table_id']}")
    print(f"record_id (从参数提取): {info['record_id']}")
    
    # 检查是否与预期一致
    expected = {
        "app_token": "dkke3lyh7o",
        "table_id": "tblWEf5vmSdEUBFi",
        "record_id": "recIAENn3o"
    }
    
    print("\n验证结果:")
    for key, value in expected.items():
        if info[key] == value:
            print(f"✓ {key}: {value}")
        else:
            print(f"✗ {key}: 期望 {value}, 实际 {info[key]}")


if __name__ == "__main__":
    test_url_parsing()