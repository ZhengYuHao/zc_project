import asyncio
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from models.feishu import get_feishu_client


async def create_spreadsheet():
    """
    直接创建一个飞书电子表格并返回URL
    """
    # 获取飞书客户端
    feishu_client = get_feishu_client()
    
    try:
        # 获取tenant_access_token
        print("正在获取tenant_access_token...")
        try:
            token = await feishu_client.get_tenant_access_token()
            print(f"获取到tenant_access_token: {token}")
        except Exception as e:
            print(f"获取tenant_access_token失败: {str(e)}")
            print("请检查以下几点:")
            print("1. 网络连接是否正常")
            print("2. FEISHU_APP_ID和FEISHU_APP_SECRET环境变量是否正确配置")
            print("3. 飞书API服务是否可访问")
            return None
        
        # 使用飞书电子表格API创建电子表格
        url = "https://open.feishu.cn/open-apis/sheets/v3/spreadsheets"
        
        # 请求头
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        # 请求体 - 创建电子表格只需要标题
        payload = {
            "title": "测试表格.xlsx"
        }
        
        print("正在创建电子表格...")
        print(f"请求URL: {url}")
        print(f"请求头: {headers}")
        print(f"请求体: {payload}")
        
        # 发送POST请求创建电子表格
        try:
            response = await feishu_client.client.post(url, headers=headers, json=payload, timeout=30.0)
            print(f"响应状态码: {response.status_code}")
            print(f"响应头: {response.headers}")
            print(f"响应内容: {response.text}")
            
            response.raise_for_status()
        except Exception as e:
            print(f"发送请求失败: {str(e)}")
            print("请检查网络连接和飞书API服务状态")
            return None
        
        # 解析响应
        try:
            result = response.json()
            print(f"API响应: {result}")
        except Exception as e:
            print(f"解析响应失败: {str(e)}")
            print(f"响应内容: {response.text}")
            return None
        
        if result.get("code") != 0:
            print(f"创建电子表格失败: {result}")
            return None
            
        # 提取文件信息（根据飞书API文档）
        spreadsheet_data = result.get("data", {}).get("spreadsheet", {})
        spreadsheet_token = spreadsheet_data.get("spreadsheet_token")
        spreadsheet_url = spreadsheet_data.get("url")
        
        if spreadsheet_token and spreadsheet_url:
            print(f"成功创建电子表格!")
            print(f"电子表格Token: {spreadsheet_token}")
            print(f"电子表格URL: {spreadsheet_url}")
            return spreadsheet_url
        else:
            print("未能从响应中提取电子表格信息")
            return None
            
    except Exception as e:
        print(f"创建电子表格时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """
    主函数
    """
    print("开始测试飞书电子表格创建功能...")
    url = await create_spreadsheet()
    
    if url:
        print(f"电子表格创建成功，访问地址: {url}")
    else:
        print("电子表格创建失败")


if __name__ == "__main__":
    asyncio.run(main())