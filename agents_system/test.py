import requests
import json

def get_tenant_access_token(app_id, app_secret):
    """获取飞书tenant_access_token"""
    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        "app_id": app_id,
        "app_secret": app_secret
    }

    response = requests.post(url, headers=headers, json=data)
    
    print("Status Code:", response.status_code)
    print("Response Text:", response.text)

    if response.status_code == 200:
        result = response.json()
        if result.get('code') == 0:
            tenant_access_token = result.get('tenant_access_token')
            print("获取到的 tenant_access_token:", tenant_access_token)
            return tenant_access_token
        else:
            print("接口返回错误:", result.get('msg'))
            print("错误代码:", result.get('code'))
            print("完整响应:", result)
            return None
    else:
        print("请求失败，状态码:", response.status_code)
        return None

def get_root_folder_meta(token):
    """获取根文件夹元信息"""
    url = 'https://open.feishu.cn/open-apis/drive/explorer/v2/root_folder/meta'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    print("\n正在获取根文件夹元信息...")
    response = requests.get(url, headers=headers)
    
    print("根文件夹元信息请求状态码:", response.status_code)
    if response.status_code == 200:
        result = response.json()
        print("根文件夹元信息响应:", json.dumps(result, indent=2, ensure_ascii=False))
        return result
    else:
        print("获取根文件夹元信息失败:", response.text)
        return None

def list_files_in_root(token):
    """列出根目录下的文件"""
    # 使用正确的API路径：https://open.feishu.cn/open-apis/drive/v1/files
    url = 'https://open.feishu.cn/open-apis/drive/v1/files'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    print("\n正在列出根目录下的文件...")
    response = requests.get(url, headers=headers)
    
    print("列出文件请求状态码:", response.status_code)
    if response.status_code == 200:
        result = response.json()
        print("根目录文件列表响应:", json.dumps(result, indent=2, ensure_ascii=False))
        return result
    else:
        print("列出根目录文件失败:", response.text)
        return None

def check_api_capabilities(token):
    """检查API能力"""
    print("此系统可以处理的飞书文档类型：")
    print("1. 飞书新版文档（docx）")
    print("   - 支持读取文档内容")
    print("   - 支持修改文档内容")
    print("   - 支持处理文本审稿")
    print("2. 飞书消息")
    print("   - 支持接收消息")
    print("   - 支持回复消息")
    print("\n主要功能：")
    print("- 文本审稿：检查错别字和语言逻辑问题")
    print("- 文档处理：读取飞书文档内容并进行文本审稿")
    print("- 消息处理：处理飞书消息并回复处理结果")

def main(args):
    # 从环境变量或直接输入获取飞书应用凭证
    # 注意：在实际使用中，建议从环境变量或配置文件中读取
    app_id = "cli_a72f342d747c5013"  # 替换为你的App ID
    app_secret = "DHKko4zWCtFiQT7UY2J7eeeO3PrdJpsx"  # 替换为你的App Secret
    
    print("正在获取tenant_access_token...")
    token = get_tenant_access_token(app_id, app_secret)
    
    if token:
        print("\n成功获取token，检查API能力...")
        check_api_capabilities(token)
        
        print("\n尝试调用云文档API...")
        # 获取根文件夹元信息
        get_root_folder_meta(token)
        
        # 列出根目录下的文件
        list_files_in_root(token)
    else:
        print("\n获取token失败，无法继续检查API能力")

if __name__ == '__main__':
    main(None)