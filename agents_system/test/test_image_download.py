#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
图片下载测试模块
用于测试从链接下载图片的功能
"""

import os
import sys
import asyncio
import httpx
from typing import List, Optional
from urllib.parse import urlparse, parse_qs

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import get_logger

logger = get_logger(__name__)

class ImageDownloader:
    """图片下载器"""
    
    def __init__(self, download_dir: str = "downloaded_images"):
        self.download_dir = download_dir
        # 添加请求头以避免403错误
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.xiaohongshu.com/",
        }
        self.client = httpx.AsyncClient(timeout=30.0, headers=headers)
        
        # 创建下载目录
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
    
    async def download_image(self, url: str, filename: Optional[str] = None) -> str:
        """
        下载单张图片
        
        Args:
            url: 图片URL
            filename: 保存的文件名，如果为None则自动生成
            
        Returns:
            保存的文件路径
        """
        try:
            logger.info(f"开始下载图片: {url}")
            
            # 如果URL包含管道符，只取第一部分
            if '|' in url:
                original_url = url
                url = url.split('|')[0]
                logger.info(f"处理前的URL: {original_url}")
                logger.info(f"处理后的URL: {url}")
            
            # 解析URL参数，检查是否有签名过期问题
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            # 检查是否有签名相关的参数
            has_sign = 'sign' in query_params
            has_t = 't' in query_params
            
            if has_sign and has_t:
                logger.warning("检测到URL包含签名参数，可能存在过期问题")
            
            # 如果没有指定文件名，则从URL中提取
            if not filename:
                filename = url.split('/')[-1].split('?')[0]
                # 如果提取不到文件名，使用默认名称
                if not filename or '.' not in filename:
                    # 根据URL参数确定文件扩展名
                    if 'format/webp' in url:
                        filename = "image.webp"
                    elif 'format/jpg' in url or 'format/jpeg' in url:
                        filename = "image.jpg"
                    elif 'format/png' in url:
                        filename = "image.png"
                    else:
                        filename = "image.jpg"  # 默认jpg格式
            
            file_path = os.path.join(self.download_dir, filename)
            
            # 发送请求下载图片
            logger.info(f"发送请求到: {url}")
            response = await self.client.get(url)
            logger.info(f"响应状态码: {response.status_code}")
            
            # 检查响应状态
            if response.status_code == 200:
                # 保存图片
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"图片下载成功: {file_path}")
                return file_path
            elif response.status_code == 403:
                logger.error(f"下载失败，状态码: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                # 尝试不带签名参数的URL
                clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                logger.info(f"尝试不带签名参数的URL: {clean_url}")
                
                clean_response = await self.client.get(clean_url)
                if clean_response.status_code == 200:
                    with open(file_path, 'wb') as f:
                        f.write(clean_response.content)
                    logger.info(f"使用不带签名参数的URL下载成功: {file_path}")
                    return file_path
                else:
                    logger.error(f"不带签名参数的URL也失败了，状态码: {clean_response.status_code}")
                    response.raise_for_status()
            else:
                logger.error(f"下载失败，状态码: {response.status_code}")
                response.raise_for_status()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP错误: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"下载图片失败: {url}, 错误: {str(e)}")
            raise
        
        # 如果所有尝试都失败，抛出异常而不是返回空字符串
        raise Exception(f"无法下载图片: {url}")
    
    async def download_images(self, urls: List[str]) -> List[str]:
        """
        批量下载图片
        
        Args:
            urls: 图片URL列表
            
        Returns:
            保存的文件路径列表
        """
        logger.info(f"开始批量下载 {len(urls)} 张图片")
        
        saved_paths = []
        for i, url in enumerate(urls):
            try:
                filename = f"image_{i+1}.jpg"
                path = await self.download_image(url, filename)
                saved_paths.append(path)
            except Exception as e:
                logger.error(f"下载第 {i+1} 张图片失败: {str(e)}")
        
        logger.info(f"批量下载完成，成功下载 {len(saved_paths)} 张图片")
        return saved_paths
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()


async def main():
    """主函数，用于测试图片下载功能"""
    # 测试图片URL
    test_urls = [
        "http://sns-note-i6.xhscdn.com/1040g00831kjus36rj2005ptmrtqh9l8j2bjrp3o?imageView2/2/w/540/format/webp|imageMogr2/strip&redImage/frame/0&ap=18&sc=DFF_PRV&sign=e4dbc4446d5d999849123811f4c6879b&t=68980127"
    ]
    
    # 创建下载器实例
    downloader = ImageDownloader()
    
    try:
        # 下载单张图片
        logger.info("开始测试单张图片下载")
        saved_path = await downloader.download_image(test_urls[0])
        logger.info(f"单张图片下载测试完成，保存路径: {saved_path}")
        
        # 测试批量下载
        logger.info("开始测试批量图片下载")
        saved_paths = await downloader.download_images(test_urls)
        logger.info(f"批量图片下载测试完成，保存路径: {saved_paths}")
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
    finally:
        # 关闭下载器
        await downloader.close()


if __name__ == "__main__":
    asyncio.run(main())