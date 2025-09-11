#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GraphicOutlineAgent.process_request函数测试模块
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from agents.graphic_outline_agent import GraphicOutlineAgent
from utils.logger import get_logger

# 获取logger实例
logger = get_logger("test.graphic_outline_process_request")


async def test_process_request():
    """测试process_request函数"""
    logger.info("Testing GraphicOutlineAgent.process_request function")
    
    # 创建GraphicOutlineAgent实例
    agent = GraphicOutlineAgent()
    
    # 准备测试数据
    test_request = {
        "topic": "夏季护肤指南",
        "product_highlights": ''' 
        一、产品名（花字需体现）：海信新风空调X3Pro
海信品牌为FIFA世俱杯官方合作伙伴。此款为FIFA世俱杯定制款空调
海信作为牵头制定新风行业标准的品牌，在2008年就生产了第一台新风空调；

二、主要卖点
核心卖点排序：1、增氧新风2、AI倍省电3、仿真自然风（字幕必带）4、凝脂白机身+哑光拉丝面板

本次测评需要主要打：增氧新风卖点-好新风看得见、上下新风口新风扩散更快、16分贝静音好睡眠；
背景：这次推广希望能让用户观众理解到海信新风空调的新风能力比较强，针对不同的人群不同的场景都能解决他们的问题；
人群主要分为：

人群: 母婴、萌宠、数码科技、家居家装
场景: 生活（生活痛点）、睡眠、天气异常、聚会、科技感、家庭装修
母婴场景: 生活、天气异常
萌宠场景: 生活
数码科技: 聚会、科技感
家居家装: 家庭装修、家电适配

达人需要根据自己的定位找到对应的生活场景输出相应的痛点内容
输出论点如：

母婴群体-场景：生活痛点（日常起居）、天气异常（雾霾/花粉天）、鼻炎：

✔ HEPA滤网+Hi-cat抗病毒技术，PM0.3、花粉、细菌统统过滤掉，宝宝呼吸更干净~/对鼻炎量人更加友好，不会老打喷嚏

✔ 绿色灯带实时显示新风状态，空气好不好一眼就知道！

✔ 上下双新风口，室内氧气更充足更均匀，孩子睡眠质量高第二天活力满满，学习更有效率

“养猫狗的家庭都懂！开窗怕毛乱飞，关窗又闷得慌…海信新风空调X3Pro，双新风口快速换气，宠物异味秒散！”

✔ HEPA滤网拦截99.5%的宠物毛发和粉丝，空气清爽，主子们再也不打喷嚏~

✔ 新风运行只有16分贝，比猫走路还安静！毛孩子午睡都不怕吵醒~

✔ 高层养猫需要封窗也不方便随时开窗，新风空调超大新风量可以随时换新空气，赶走猫咪

数码科技人群-场景：聚会（火锅/看球）、语音智控？

“朋友来家必问的黑科技！我家空气系统会自己思考，APP实时显示甲醛温湿度，聚会火锅快快速清空”

✔ 聚会场景：吃完火锅一键换气，房间空气迅速焕新，朋友来了不尴尬~

✔ 晚上睡觉开窗不仅吵闹更没隐私，不如单独开启新风功能，室内含氧量变高睡眠质量自然会好，1晚等于多睡1小时；

家居家装人群-场景：生活痛点（操作便捷）、睡眠（舒适）、天气异常（雾霾天）

“装修师傅不会告诉你的事！墙面刷完直接装新风，隐藏式设计不破坏风格，入住当天甲醛就达标”

✔ 绿色灯带实时显示新风状态，空气好不好一目了然~

✔ 抗病毒技术+超强过滤，雾霾天不开窗也能呼吸新鲜空气，爸妈少生病！

✔ 自然风轻柔不直吹，关节不怕受凉，睡觉更踏实~

核心卖点1：增氧新风：针对圈定人群的文案方向：

卖点输出关键点:上下双新风口，60m³/h超大新风量，室内含氧量更大更均匀，房间含氧量高1晚多睡1小时

（此部分达人可重点讲解，其中烘房除醛功能易卡审可略提）

好新风看得见：新风开启后，绿色可视灯带打开，空调运行状态一眼便知

看新风效率：60m³/h的超大新风量，上下两个新风口，新风扩散效率提升超11%，上出风口充氧，下出风口补量，让屋内氧气更加均匀；关键下风口还有个挡板不直吹人，使用上下双出新风对流技术，在不扩孔就能实现40m³/h大新风量，如果想要安装大面积房间或比较多的房间，只需要微微扩一点孔可以达到60m³/h的超大新风量，做过功课的宝子都知道这个新风量的含金量

海信新风空调X3Pro，可达到60m³/h洁净新风量，每1m³洁净新风，都会过5重净化考验。（普通空调新风量测试时即滤网，数据虚高）

安装方式：新开孔可实现60m³/h洁净新风量，需新开90mm孔(机身背面打孔)，配件箱+开孔费约180元，无需扩孔实现40m³/h洁净新风量

看新风洁净度：新风五重净化，其中Hepa滤尘+Hi-cat抗病毒双保险系统，除菌抗病毒更安全：
H11级Hepa滤网搭配Hi-cat抗病毒技术能够有效去除细菌病毒及颗粒粉尘，开机就有好空气，保障
新风洁净，享受干净鲜氧；PM0.3去除率97%，甲醛置换率98.05%，花粉过滤效率99.5%，大肠杆
菌、金黄色葡萄球菌的除菌率99.99%，H1N1病毒99.98%；

看运行分贝：16分贝安静好睡眠，行业最安静新风空调-搭载了单进双吸离心新风风扇，降低运行
噪音，实现新风运行低至16分贝，像猫咪跳脚走路的声音。

烘房除醛2.0：海信爱家APP一键开启，晾房不开窗，提前半年住新家（除醛有卡申概率）

用户痛点关联：

空气浑浊憋闷，紧闭门窗，空气不流通，CO2浓度超标，睡醒后头晕胸闷；

房间异味久不散，养宠等异味久；

粉尘多易过敏，花粉/PM2.5/粉尘/宠物毛发易呼吸不畅；

病菌多易感冒，老人孩子免疫力弱，容易感冒生病；

甲醛潜伏隐患大，装修甲醛反复释放，潜伏周期长，危害呼吸系统；

核心卖点2：AI倍省电

卖点输出关键点：AI倍省电多种节能buff叠加，舒适不打折，电费省到底（强调AI倍省电这一大功
能，以下为其支撑点）

AI算法省电41%舒适不打折：AI大数据智能省电模式，一键开启，温度、湿度、能耗值动态维持黄
金平衡，电费省更多，舒适无负担

真材实料大双排，省电实力派：内外机双排设计（双排蒸发器+双排铜管），用料更扎实；升级电
子膨胀阀冷媒调节更精确，在大幅提升性能同时优化节能

10代变频技术，行业变频革命引领者：磁场增强，提升压缩机效率，压缩机旋转又稳又准，电量相
同冷量更大

用户痛点关联：

超一级能效，APF值5.5

家里一般不止1台空调，使用电费较贵；

吹空调一时爽，月底电费蹭蹭涨；

省电模式只省电；制冷制热全摆烂；

核心卖点3：仿真自然风

卖点输出关键点：

自然风向摆动算法+蝶翼导板，吹面不要自然风：自然风算法-分阶段、多区域的摆动控制模式，将
风打散，风感轻柔（常规的风感是周期性摆动的机械风）；曲面导板搭配仿生蝶翼导板-打散集中气
流，通过多向分流结构实现紊流均匀送风，体感舒适

2、一键防直吹：通过导板控制空调的送风角度，实现冷风上行不吹人，暖风从脚起（导板上扬0°，向
下摆75°）​
品牌背书：行业标准制定者，买的放心（可根据达人内容酌情添加）
海信也是行业内牵头制定首个新风团体标准的企业，2008年就上市了中国第一台新风空调，并制定了
行业首个新风增氧评价标准。
核心卖点4：凝脂白机身+哑光拉丝面板​
✨百搭凝脂白机身：如羊脂玉般温润，线条流畅简约，柔光漫射间消解冷白刺目感。​
✨哑光细腻拉丝面板：经过多道工序淬炼，指纹不留痕、岁月不褪色，细腻拉丝纹理交织出轻奢美
学。
✨一见倾心的优雅，历久弥新的质感，完美适配各种家居风格。​
三、话题
#海信新风空调X3Pro #增氧新风 #AI倍省电​
附：产品卖点一页纸

核心技术点/参数（新）

1、行业首创上下双出新风对流技术，提升室内新风扩散效率11%；
2、不扩孔实现40m³/h新风量，对比国标提升33%
3、新鲜看得见，绿色可视灯带，空调运行状态一眼便知
4、搭载了单进双吸离心新风风扇，降低运行噪音，实现新风运行低至16分贝，像猫咪跳脚走路的声音。
5、蝶翼导板仿生降噪。能听到蜻蜓的翅膀扇动，但听不到蝴蝶的。

1、海信爱家APP，一键开启烘房去壁模式
2、实时联动室外天气动态提升室内温度，加快甲醛释放。
3、烘房去壁3个月=自然晾房6个月，入住新房时间缩短一半

1、初效滤网采用Hi-cat纳米触媒抗病毒技术
①抗菌率达99.99%，抗病毒率99.99%-大肠杆菌、金黄色葡萄球菌、H1N1病毒（99.98%）、白色念珠球菌（99%）
2、滤网，可重复、长期使用
3、HEPA滤网（小字：H11级）可达pmo.3

1、行业首创温湿软解霜智能节能算法，省电高达41%；
2、节能舒适一键开启，温度、湿度、能耗值动态维持黄金平衡；
3、APP可查实时耗电量，个人定制省电方案

超一级能效（APF值5.5）双排满配，实；省电；
1、外机冷凝器：双排48根7mm高密度纯铜钢管，铜管量加倍，大宽43.3mm亲水膜翅片，冷凝长度外排796mm，内排762mm，室外铜管长度（37.2m）/面为上一代产品升1.86倍；
2、内机蒸发器双排5.0mm铜管，长度内外625mm，宽27.2mm，16U/32根铜管
3、节流部件：500级电子膨胀阀，级步数越高，调节精度提高，控温更精

信任状

新风空调行业标准的牵头制定者

烘房去壁报告

中科院大连化物所联合研发证书

省电41%报告；国家轻工科技进步奖一等奖；''',
        "note_style": "种草",
        "product_name": "海信新风空调X3 Pro（海信X3 Pro）",
        "direction": ''' 
        1. 针对母婴人群

核心场景：日常生活、天气异常（雾霾/花粉季）、宝宝睡眠、鼻炎患者关怀

内容方向：

痛点切入：担心宝宝呼吸不健康空气？雾霾天花粉季不敢开窗？宝宝睡觉不安稳，醒来没精神？

解决方案：强调HEPA滤网+Hi-cat抗病毒技术，能有效过滤PM0.3、花粉、细菌，给宝宝一个洁净的呼吸环境。突出绿色可视灯带，让妈妈“一眼看见”好空气。利用上下双新风口说明室内氧气更充足均匀，提升孩子睡眠质量，从而“一晚多睡一小时”，学习更有效率。

情感共鸣：体现对宝宝健康成长的呵护，以及对鼻炎家人的关爱。

2. 针对萌宠人群

核心场景：宠物家庭日常、宠物异味、宠物毛发、高层封窗

内容方向：

痛点切入：开窗怕宠物毛乱飞、宠物跑丢；关窗又闷又有异味？

解决方案：强调双新风口快速换气，能“秒散”宠物异味。突出HEPA滤网对宠物毛发的高效拦截（99.5%）。重点渲染16分贝超静音新风运行，“比猫走路还安静”，不打扰宠物休息。解决高层养猫家庭封窗不便、无法频繁开窗的痛点。

生动表达：使用“主子”、“毛孩子”等爱宠人士常用语，增强亲切感。

3. 针对数码科技人群

核心场景：朋友聚会（火锅、看球）、智能家居体验、科技感展示

内容方向：

痛点切入：聚会后满屋火锅味难散？晚上开窗吵且没隐私？

解决方案：主打“黑科技”属性，展示一键快速换气功能，解决聚会后的空气尴尬。强调可单独开启静音新风，提升室内含氧量，改善睡眠（“一晚等于多睡1小时”）。可通过展示海信爱家APP的实时空气数据（甲醛、温湿度）来体现智能化和科技感。

内容调性：突出产品的极客属性、智能互联功能和数据可视化。

4. 针对家居家装人群

核心场景：新房装修、家电适配、家居美学、父母健康

内容方向：

痛点切入：新装修担心甲醛？空调破坏装修风格？雾霾天父母呼吸健康？

解决方案：强力主打“烘房除醛”功能（注意审核风险，可委婉表述为“加速晾房过程”），结合APP控制，强调“提前半年住新家”。突出“凝脂白机身+哑光拉丝面板”的简约轻奢设计，强调其“百搭”、“不破坏装修风格”、“指纹不留痕”的特性。针对有老人的家庭，强调抗病毒技术、超强过滤和仿真自然风（防直吹）对健康的益处。

价值提升：将产品从功能性家电提升为提升整体家居美学和健康生活的关键部分。
        ''',
        "blogger_link": "https://xiaohongshu.com/user/12345",
        "requirements": '''
        1.从达人的生活日常或者家装分享角度切入，结合达人的生活理念来植入产品 2.要有3张家居家装整体展示（包括1张空调展示）、3张生活日常状态场景图（有人有宠物出镜）、2张产品特写图、3张产品功能展示图（具体卖点和功能演示）
        ''',
        "style": "活泼"
    }
    
    logger.info("Test request data:")
    for key, value in test_request.items():
        logger.info(f"  {key}: {value}")
    
    try:
        # 调用process_request函数
        result = await agent.process_request(test_request)
        
        # 输出结果
        logger.info("Test result:")
        logger.info(f"  Status: {result.get('status')}")
        logger.info(f"  Has spreadsheet: {'spreadsheet' in result}")
        logger.info(f"  Has processed_data: {'processed_data' in result}")
        
        if result.get('status') == 'success':
            processed_data = result.get('processed_data', {})
            logger.info(f"  Note style: {processed_data.get('note_style')}")
            logger.info(f"  Has planting_content: {'planting_content' in processed_data}")
            logger.info(f"  Has planting_captions: {'planting_captions' in processed_data}")
            
            spreadsheet = result.get('spreadsheet', {})
            logger.info(f"  Spreadsheet status: {spreadsheet.get('status')}")
            if spreadsheet.get('status') == 'success':
                logger.info(f"  Spreadsheet token: {spreadsheet.get('spreadsheet_token')}")
                logger.info(f"  Sheet ID: {spreadsheet.get('sheet_id')}")
        else:
            logger.error(f"  Error: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def test_process_request_tuwen_mode():
    """测试process_request函数的图文规划模式"""
    logger.info("Testing GraphicOutlineAgent.process_request function (图文规划模式)")
    
    # 创建GraphicOutlineAgent实例
    agent = GraphicOutlineAgent()
    
    # 准备测试数据
    test_request = {
        "topic": "夏季护肤指南",
        "product_highlights": "防晒、保湿、温和配方",
        "note_style": "图文规划(测试)",
        "product_name": "水润防晒霜",
        "direction": "重点介绍防晒效果和使用感受",
        "blogger_link": "https://xiaohongshu.com/user/12345",
        "requirements": "需要包含使用前后对比，适合敏感肌",
        "style": "活泼"
    }
    
    logger.info("Test request data (图文规划模式):")
    for key, value in test_request.items():
        logger.info(f"  {key}: {value}")
    
    try:
        # 调用process_request函数
        result = await agent.process_request(test_request)
        
        # 输出结果
        logger.info("Test result (图文规划模式):")
        logger.info(f"  Status: {result.get('status')}")
        logger.info(f"  Has spreadsheet: {'spreadsheet' in result}")
        logger.info(f"  Has processed_data: {'processed_data' in result}")
        
        if result.get('status') == 'success':
            processed_data = result.get('processed_data', {})
            logger.info(f"  Note style: {processed_data.get('note_style')}")
            logger.info(f"  Has planting_content: {'planting_content' in processed_data}")
            logger.info(f"  Has planting_captions: {'planting_captions' in processed_data}")
            
            spreadsheet = result.get('spreadsheet', {})
            logger.info(f"  Spreadsheet status: {spreadsheet.get('status')}")
            if spreadsheet.get('status') == 'success':
                logger.info(f"  Spreadsheet token: {spreadsheet.get('spreadsheet_token')}")
                logger.info(f"  Sheet ID: {spreadsheet.get('sheet_id')}")
        else:
            logger.error(f"  Error: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    logger.info("Starting GraphicOutlineAgent.process_request tests")
    
    # 运行测试
    asyncio.run(test_process_request())
    # logger.info("="*50)
    # asyncio.run(test_process_request_tuwen_mode())
    
    logger.info("Tests completed!")