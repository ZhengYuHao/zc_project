#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户昵称获取工具模块
提供通过用户UUID获取用户昵称的功能
"""

import httpx
from typing import Optional
from utils.logger import get_logger


logger = get_logger("utils.fetch_user_nickname")


async def fetch_user_nickname(user_uuid: str) -> Optional[str]:
    """
    通过用户UUID获取用户昵称
    
    Args:
        user_uuid: 用户UUID
        
    Returns:
        用户昵称，如果获取失败则返回None
    """
    if not user_uuid:
        return None
        
    try:
        api_url = f"https://zongsing.com/prod-api/platform/agent/homepage/getMostOrdersUsersByUserId/{user_uuid}"
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url)
            if response.status_code == 200:
                api_result = response.json()
                # 提取data数组中的第一个用户信息
                if "data" in api_result and isinstance(api_result["data"], list) and len(api_result["data"]) > 0:
                    first_user = api_result["data"][0]
                    if "nickname" in first_user:
                        return first_user["nickname"]
            else:
                logger.error(f"Failed to fetch user nickname, status code: {response.status_code}")
    except Exception as e:
        logger.error(f"Error fetching nickname from API: {str(e)}")
    
    return None