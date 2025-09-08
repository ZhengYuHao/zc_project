#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试飞书文件夹相关API，用于获取文件夹token
"""

import sys
import os
import asyncio
import httpx

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.feishu import get_feishu_client


async def get_root_folder_meta():
    """
    获取根文件夹元数据
    """
    print("获取根文件夹元数据...")
    
    try:
        # 获取飞书访问令牌
        feishu_client = get_feishu_client()
        tenant_token = await feishu_client.get_tenant_access_token()
        
        # 飞书获取根文件夹元数据的API endpoint
        url = "https://open.feishu.cn/open-apis/drive/explorer/v2/root_folder/meta"
        headers = {
            "Authorization": f"Bearer {tenant_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            print(f"根文件夹元数据: {result}")
            
            if result.get("code") == 0 and "data" in result:
                root_folder_token = result["data"].get("token")
                print(f"根文件夹 token: {root_folder_token}")
                return root_folder_token
            else:
                print(f"获取根文件夹元数据失败: {result}")
                return None
                
    except Exception as e:
        print(f"获取根文件夹元数据时出错: {e}")
        import traceback
        traceback.print_exc()
        return None


async def list_files_in_folder(folder_token: str, page_token: str = None):
    """
    获取文件夹中的文件清单
    
    Args:
        folder_token: 文件夹token
        page_token: 分页token（可选）
        
    Returns:
        文件列表和下一页token
    """
    print(f"获取文件夹 {folder_token} 中的文件清单...")
    
    try:
        # 获取飞书访问令牌
        feishu_client = get_feishu_client()
        tenant_token = await feishu_client.get_tenant_access_token()
        
        # 飞书获取文件夹中文件清单的API endpoint
        url = "https://open.feishu.cn/open-apis/drive/v1/files"
        headers = {
            "Authorization": f"Bearer {tenant_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        # 查询参数
        params = {
            "folder_token": folder_token
        }
        
        if page_token:
            params["page_token"] = page_token
            
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            print(f"文件夹 {folder_token} 中的文件清单: {result}")
            
            if result.get("code") == 0 and "data" in result:
                files = result["data"].get("files", [])
                next_page_token = result["data"].get("next_page_token")
                
                print(f"找到 {len(files)} 个文件/文件夹:")
                for file in files:
                    file_type = file.get("type", "unknown")
                    file_name = file.get("name", "unknown")
                    file_token = file.get("token", "unknown")
                    print(f"  - 类型: {file_type}, 名称: {file_name}, Token: {file_token}")
                
                return files, next_page_token
            else:
                print(f"获取文件夹中的文件清单失败: {result}")
                return [], None
                
    except Exception as e:
        print(f"获取文件夹中的文件清单时出错: {e}")
        import traceback
        traceback.print_exc()
        return [], None


async def find_folder_by_name(target_folder_name: str, parent_folder_token: str = None):
    """
    根据文件夹名称查找文件夹token
    
    Args:
        target_folder_name: 目标文件夹名称
        parent_folder_token: 父文件夹token（如果为None，则从根文件夹开始搜索）
        
    Returns:
        找到的文件夹token，如果未找到则返回None
    """
    print(f"查找文件夹: {target_folder_name}")
    
    try:
        # 如果没有指定父文件夹，则从根文件夹开始
        if not parent_folder_token:
            print("未指定父文件夹，从根文件夹开始搜索...")
            parent_folder_token = await get_root_folder_meta()
            if not parent_folder_token:
                print("无法获取根文件夹token")
                return None
        
        # 获取父文件夹中的所有文件和文件夹
        files, next_page_token = await list_files_in_folder(parent_folder_token)
        
        # 查找目标文件夹
        for file in files:
            if file.get("type") == "folder" and file.get("name") == target_folder_name:
                folder_token = file.get("token")
                print(f"找到目标文件夹 '{target_folder_name}'，token为: {folder_token}")
                return folder_token
        
        # 如果有下一页，继续搜索
        while next_page_token:
            files, next_page_token = await list_files_in_folder(parent_folder_token, next_page_token)
            for file in files:
                if file.get("type") == "folder" and file.get("name") == target_folder_name:
                    folder_token = file.get("token")
                    print(f"找到目标文件夹 '{target_folder_name}'，token为: {folder_token}")
                    return folder_token
        
        print(f"在文件夹 {parent_folder_token} 中未找到目标文件夹 '{target_folder_name}'")
        return None
        
    except Exception as e:
        print(f"查找文件夹时出错: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """
    主函数，演示如何获取文件夹token
    """
    print("=== 飞书文件夹token获取测试 ===")
    
    # 1. 获取根文件夹元数据
    print("\n1. 获取根文件夹元数据")
    root_folder_token = await get_root_folder_meta()
    if not root_folder_token:
        print("无法获取根文件夹token，程序退出")
        return
    
    # 2. 列出根文件夹中的文件和文件夹
    print("\n2. 列出根文件夹中的文件和文件夹")
    files, _ = await list_files_in_folder(root_folder_token)
    
    # 3. 演示如何查找特定名称的文件夹
    print("\n3. 查找特定名称的文件夹")
    # 这里可以替换为你实际要查找的文件夹名称
    target_folder_name = "飞书文档"  # 示例名称，请根据实际情况修改
    folder_token = await find_folder_by_name(target_folder_name, root_folder_token)
    
    if folder_token:
        print(f"成功找到文件夹 '{target_folder_name}'，token为: {folder_token}")
    else:
        print(f"未找到文件夹 '{target_folder_name}'")


if __name__ == "__main__":
    asyncio.run(main())