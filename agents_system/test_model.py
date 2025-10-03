import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.model_config import load_model_config
from models.model_manager import ModelManager
from core.task_processor import extract_blogger_style

async def test_model_call():
    # 加载配置
    config = load_model_config()
    
    # 创建模型管理器
    model_manager = ModelManager(config)
    
    # 显示模型配置信息
    print("Model configuration:")
    print(f"  Task model mapping: {model_manager._task_model_mapping}")
    
    # 测试调用 - 使用正确的任务类型
    test_prompt = "请生成一个简单的文本"
    task_type = "_generate_planting_content_cp"  # 使用配置文件中定义的任务类型
    
    print(f"\nTesting model call for task: {task_type}")
    print(f"Prompt: {test_prompt}")
    
    result = await model_manager.call_model(task_type, test_prompt)
    
    print(f"\nModel response: {result}")

async def test_blogger_style_extraction():
    """测试达人风格提取功能"""
    print("\n" + "="*50)
    print("测试达人风格提取功能")
    print("="*50)
    
    # 构造测试请求数据（使用小红书用户主页URL）
    test_request_data = {
        "url": "https://www.xiaohongshu.com/user/Profile/63611642000000001f0162a1"
    }
    
    print(f"测试URL: {test_request_data['url']}")
    print("注意：此测试需要有效的豆包视觉模型端点配置")
    print("当前配置的视觉模型端点: ep-20250925153000-mlvvp")
    print("如果该端点不存在或无法访问，将返回默认响应")
    
    try:
        # 调用函数
        result = await extract_blogger_style(test_request_data)
        
        print("\n达人风格分析结果:")
        print("-" * 30)
        print(f"风格分析: {result.get('blogger_style', 'N/A')}")
        print(f"语调: {result.get('tone', 'N/A')}")
        print(f"表达风格: {result.get('expression_style', 'N/A')}")
        
        # 判断是否使用了默认响应
        if "未分析出具体风格" in result.get('blogger_style', ''):
            print("\n注意：由于视觉模型端点配置问题，返回了默认响应")
            print("请检查并更新config/model_config.json中的blogger_style_analysis模型配置")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

async def test_blogger_style_logic_only():
    """仅测试达人风格提取的逻辑功能，不调用实际模型"""
    print("\n" + "="*50)
    print("测试达人风格提取逻辑功能（不调用实际模型）")
    print("="*50)
    
    # 模拟小红书用户主页URL
    xhs_profile_url = "https://www.xiaohongshu.com/user/Profile/63611642000000001f0162a1"
    
    # 测试从URL中提取userUuid的逻辑
    from urllib.parse import urlparse
    parsed_url = urlparse(xhs_profile_url)
    path_parts = parsed_url.path.strip('/').split('/')
    user_uuid = path_parts[-1] if path_parts else None
    
    print(f"原始URL: {xhs_profile_url}")
    print(f"提取的userUuid: {user_uuid}")
    
    # 验证提取的userUuid是否正确
    expected_uuid = "63611642000000001f0162a1"
    if user_uuid == expected_uuid:
        print("✓ userUuid提取正确")
    else:
        print(f"✗ userUuid提取错误，期望: {expected_uuid}, 实际: {user_uuid}")
    
    # 模拟API返回的数据
    mock_api_response = {
        "code": "200",
        "msg": "SUCCESS",
        "data": [
            {
                "id": "68b28d3a000000001b01ed6e",
                "title": "徒步318川藏线｜全季融解高原倦意",
                "userUuid": "671f2bc6000000001d0224aa",
                "description": "🧗‍♂️在木格措深一脚蹚过整日，重装背包压得肩颈发红，寒风裹着沙砾往衣领里钻时，终于盼到康定全季酒店的灯💡\n推门便有哈达携酥油香轻落肩头，房间里弥散式供氧早已调至舒适浓度，呼吸瞬间卸去滞涩；24小时恒温热水冲净泥尘，酸痛肌肉慢慢舒展，脏污的冲锋衣丢进自助洗衣房，便卸下了行囊的沉。次日早餐袋里，糌粑配白粥的温热，恰好续上徒步所需的能量💪\n最心动是318限定的吉祥八宝拓印，跟着木格措的土豆师傅蘸墨、拓纹，古老符号在纸上渐次清晰，指尖触到的不仅是墨香，更是当地文化的温。公区落地窗能瞥见雪山一角，随手拍都是辽阔意境🏔️\n今年华住会20周年，全季的贴心从不是空谈：供氧设备驱散高反不适，洗衣房解放负重的行囊，还有这些和当地文化相连的活动。它懂徒步人的累，也懂旅人想贴近土地的心，让4580公里征途，总有处安心停靠。\n#全季酒店[话题]# #此生必驾318[话题]# #华住会给你出行的勇气[话题]# #318川藏线[话题]# #徒步丈量世界[话题]#",
                "imagesList": "http://ci.xiaohongshu.com/notes_pre_post/1040g3k031lq1cc0g5u005pov5f37c95ag4l25cg?imageView2/2/w/540/format/jpg/q/75",
                "videoUrl": None,
                "publicTime": "2025-08-30T00:00:00",
                "noteType": 0,
                "isAdvertise": "false",
                "modelType": "normal",
                "noteClass": "出行旅游",
                "secondaryLabel": "户外",
                "notePrice": 4000.0,
                "likedCount": 182,
                "collectedCount": 37,
                "commentsCount": 0,
                "sharedCount": 0,
                "interactionNum": 219,
                "readNum": None,
                "readPredict": 1752,
                "exposureNum": None,
                "exposurePredict": 15768
            }
        ]
    }
    
    # 直接测试内容构建逻辑
    from core.task_processor import get_logger
    logger = get_logger("test")
    
    # 模拟函数中的数据处理部分
    blogger_posts = mock_api_response.get("data", [])
    
    # 构建提示词文本部分
    text_prompt = """## 角色
你是一位专业的内容分析与创作顾问，擅长为品牌合作达人制定定制化商单内容方向。你的任务是基于达人过往的内容风格与表达习惯，为团队提供清晰的内容创作切入点。

**目标说明**：本分析用于商单合作前的内容大纲制定环节，基于达人既有内容风格与表达特征，辅助内容策划人员精准匹配品牌核心信息，明确内容切入角度与表达策略。

### 技能
## 技能 1：达人内容风格分析  
请根据达人多篇笔记的【达人笔记封面图】和【配文】，分析以下要素：
- **笔记视觉风格**：如配色、构图、场景、花字使用等  
- **表达语言风格**：是否口语化/情绪感强/标语化/数据型/故事化等  
- **人设定位、性别**：结合其内容表达方式，描述其在用户心中的角色形象 ；分析该达人的性别
- **风格关键词标签**：如 #吐槽型 #干货控 #生活流 #踩坑党

## 限制  
- 回复仅围绕达人风格分析，不输出脚本、不进行达人选择判断；
- 所有内容必须结构清晰、术语通用、语言自然，便于下游节点直接使用。

请分析以下达人笔记内容：
"""

    # 构建消息内容（包括文本和图片）
    content = [{"type": "text", "text": text_prompt}]
    
    # 添加笔记内容到消息中
    for i, post in enumerate(blogger_posts, 1):
        content.append({"type": "text", "text": f"\n笔记 {i}:\n"})
        
        # 添加图片（如果存在）
        image_url = post.get('imagesList')
        if image_url:
            content.append({
                "type": "text", 
                "text": f"【达人笔记封面图】：\n"
            })
            # 添加图片URL到内容中
            image_content = {
                "type": "image_url",
                "image_url": {"url": image_url}
            }
            content.append(image_content)
        
        # 添加配文（如果存在）
        caption = post.get('description')
        if caption:
            content.append({
                "type": "text", 
                "text": f"\n【配文】：{caption}\n"
            })

    print(f"成功构建 {len(blogger_posts)} 篇笔记的内容")
    print(f"构建的消息内容项数: {len(content)}")
    print("消息内容结构:")
    for i, item in enumerate(content):
        print(f"  {i+1}. 类型: {item['type']}")
        if item['type'] == 'text':
            text_preview = item['text'][:50] + "..." if len(item['text']) > 50 else item['text']
            print(f"     内容预览: {text_preview}")
        elif item['type'] == 'image_url':
            print(f"     图片URL: {item['image_url']['url']}")

if __name__ == "__main__":
    # 运行模型测试
    # asyncio.run(test_model_call())
    
    # 运行达人风格提取测试
    # asyncio.run(test_blogger_style_extraction())
    
    # 运行逻辑测试（不调用实际模型）
    asyncio.run(test_blogger_style_logic_only())