import re
import httpx
from typing import Optional


def get_accessible_image(image_url: str) -> Optional[str]:
    """
    获取可访问的图片URL
    
    Args:
        image_url: 原始图片URL
        
    Returns:
        可访问的图片URL，如果找不到则返回None
    """
    if is_image_accessible(image_url):
        return image_url
    else:
        url_1 = rule_1(image_url)
        if is_image_accessible(url_1):
            return url_1
    return None


def is_image_accessible(image_url: str) -> bool:
    """
    判断图片是否能访问
    
    Args:
        image_url: 图片URL
        
    Returns:
        如果图片可访问返回True，否则返回False
    """
    try:
        # 发送HEAD请求，只获取响应头不获取内容
        response = httpx.head(image_url, timeout=5.0)
        
        # 检查状态码和Content-Type
        content_type = response.headers.get('content-type', '')
        return response.status_code == 200 and content_type.startswith('image/')
    except Exception:
        return False


def rule_1(url: str) -> str:
    """
    规则一:
    http://sns-note-i6.xhscdn.com/spectrum/1040g0k031kkqpuqg2a005pvct58j9a9k7o0aca8?imageView2/2/w/540/format/webp|imageMogr2/strip&redImage/frame/0&ap=18&sc=DFF_PRV&sign=ace523231cbaa56de45dfbe8ad0d56f3&t=688cb973
    替换成
    http://ci.xiaohongshu.com/spectrum/1040g0k031kkqpuqg2a005pvct58j9a9k7o0aca8?imageView2/2/w/540/format/jpg/q/75
    
    Args:
        url: 原始URL
        
    Returns:
        转换后的URL
    """
    # 正则表达式匹配.com/和?之间的内容
    pattern = re.compile(r"\.com/([^?]+)")
    matcher = pattern.search(url)
    if matcher:
        return "http://ci.xiaohongshu.com/" + matcher.group(1) + "?imageView2/2/w/540/format/jpg/q/75"
    else:
        return url


def test_module():
    """
    测试模块功能
    """
    t=get_accessible_image("http://sns-note-i6.xhscdn.com/1040g00831kjus36rj2005ptmrtqh9l8j2bjrp3o?imageView2/2/w/540/format/webp|imageMogr2/strip&redImage/frame/0&ap=18&sc=DFF_PRV&sign=e4dbc4446d5d999849123811f4c6879b&t=68980127")
    print(t)
    
if __name__ == "__main__":
    test_module()