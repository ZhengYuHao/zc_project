#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GraphicOutlineAgent模块单元测试
"""

import asyncio
import sys
import os
import unittest
from unittest.mock import AsyncMock, patch, MagicMock

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from agents.graphic_outline_agent import GraphicOutlineAgent
from agents.task_processor import task_processor
from utils.logger import get_logger

# 获取logger实例
logger = get_logger("test.graphic_outline_agent")


class TestGraphicOutlineAgent(unittest.TestCase):
    """GraphicOutlineAgent测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.agent = GraphicOutlineAgent()
        logger.info("Setting up TestGraphicOutlineAgent")
    
    def tearDown(self):
        """测试后清理"""
        logger.info("Tearing down TestGraphicOutlineAgent")
    
    async def _mock_execute_tasks(self, request_data):
        """模拟execute_tasks方法"""
        return {
            "target_audience_extractor": {
                "status": "success",
                "data": {
                    "target_audience": "适合户外活动较多的年轻女性"
                }
            },
            "required_content_extractor": {
                "status": "success",
                "data": {
                    "required_content": "需要展示防晒效果和使用感受"
                }
            },
            "blogger_style_extractor": {
                "status": "success",
                "data": {
                    "blogger_style": "小红书风格，轻松活泼"
                }
            },
            "product_category_extractor": {
                "status": "success",
                "data": {
                    "product_category": "护肤品"
                }
            },
            "selling_points_extractor": {
                "status": "success",
                "data": {
                    "selling_points": "防晒指数高，温和不刺激，保湿效果好"
                }
            },
            "product_endorsement_extractor": {
                "status": "success",
                "data": {
                    "product_endorsement": "专业护肤品牌"
                }
            },
            "topic_extractor": {
                "status": "success",
                "data": {
                    "main_topic": "夏季防晒的重要性"
                }
            }
        }
    
    async def _mock_create_feishu_sheet(self, data):
        """模拟create_feishu_sheet方法"""
        return {
            "status": "success",
            "document_id": "test_doc_id",
            "spreadsheet_token": "test_spreadsheet_token"
        }
    
    async def _mock_generate_planting_content(self, processed_data):
        """模拟_generate_planting_content方法"""
        return """图片类型：封面图
图文规划：
在阳光明媚的户外草地场景中，一位年轻女性手持水润防晒霜，防晒霜瓶身特写清晰展示品牌和产品名，旁边花字写着"水润防晒来袭"，整体画面氛围明亮清新。
图片的文字内容：水润防晒霜，户外必备！
备注：光线充足，人物表情自然甜美。"""
    
    async def _mock_generate_planting_captions(self, processed_data, planting_content):
        """模拟_generate_planting_captions方法"""
        return """配文：我超爱户外活动，可每次都担心被晒黑晒伤，尤其是我这敏感肌，选防晒可纠结了。最近在户外玩耍时发现了这款水润防晒霜，真的太香啦！"""
    
    async def _mock_generate_formatted_output(self, processed_data, planting_content, planting_captions):
        """模拟_generate_formatted_output方法"""
        return """# 种草图文规划完整版

## 产品信息
- 产品名称：水润防晒霜
- 产品品类：护肤品
- 目标人群：适合户外活动较多的年轻女性
- 核心卖点：防晒指数高，温和不刺激，保湿效果好

## 创作要求
- 核心要求：需要包含使用前后对比，适合敏感肌
- 达人风格：种草
- 内容方向：需要展示防晒效果和使用感受

## 图文规划详情
### 图片1
图片类型：封面图
图文规划：
在阳光明媚的户外草地场景中，一位年轻女性手持水润防晒霜，防晒霜瓶身特写清晰展示品牌和产品名，旁边花字写着"水润防晒来袭"，整体画面氛围明亮清新。
图片的文字内容：水润防晒霜，户外必备！
配文：我超爱户外活动，可每次都担心被晒黑晒伤，尤其是我这敏感肌，选防晒可纠结了。最近在户外玩耍时发现了这款水润防晒霜，真的太香啦！
备注：光线充足，人物表情自然甜美。"""
    
    @patch('agents.task_processor.task_processor.execute_tasks')
    @patch('agents.graphic_outline_agent.GraphicOutlineAgent.create_feishu_sheet')
    @patch('agents.graphic_outline_agent.GraphicOutlineAgent._generate_planting_content')
    @patch('agents.graphic_outline_agent.GraphicOutlineAgent._generate_planting_captions')
    @patch('agents.graphic_outline_agent.GraphicOutlineAgent._generate_formatted_output')
    async def test_process_request_zhongcao_mode(self, mock_formatted_output, mock_captions, mock_planting_content, mock_feishu_sheet, mock_execute_tasks):
        """测试process_request函数的种草模式"""
        logger.info("Testing process_request with '种草' mode")
        
        # 设置mock返回值
        mock_execute_tasks.side_effect = self._mock_execute_tasks
        mock_feishu_sheet.side_effect = self._mock_create_feishu_sheet
        mock_planting_content.side_effect = self._mock_generate_planting_content
        mock_captions.side_effect = self._mock_generate_planting_captions
        mock_formatted_output.side_effect = self._mock_generate_formatted_output
        
        # 准备测试数据
        test_request = {
            "topic": "夏季护肤指南",
            "product_highlights": "防晒、保湿、温和配方",
            "note_style": "种草",
            "product_name": "水润防晒霜",
            "direction": "重点介绍防晒效果和使用感受",
            "blogger_link": "https://xiaohongshu.com/user/12345",
            "requirements": "需要包含使用前后对比，适合敏感肌",
            "style": "活泼"
        }
        
        # 调用被测试函数
        result = await self.agent.process_request(test_request)
        
        # 验证结果
        self.assertEqual(result["status"], "success")
        self.assertIn("task_results", result)
        self.assertIn("processed_data", result)
        self.assertIn("spreadsheet", result)
        
        # 验证processed_data中的关键字段
        processed_data = result["processed_data"]
        self.assertIn("planting_content", processed_data)
        self.assertIn("planting_captions", processed_data)
        self.assertIn("formatted_output", processed_data)
        self.assertEqual(processed_data["note_style"], "种草")
        
        # 验证mock被正确调用
        mock_execute_tasks.assert_called_once()
        mock_feishu_sheet.assert_called_once()
        mock_planting_content.assert_called_once()
        mock_captions.assert_called_once()
        mock_formatted_output.assert_called_once()
        
        logger.info("test_process_request_zhongcao_mode passed")
    
    @patch('agents.task_processor.task_processor.execute_tasks')
    @patch('agents.graphic_outline_agent.GraphicOutlineAgent.create_feishu_sheet')
    @patch('agents.graphic_outline_agent.GraphicOutlineAgent._generate_planting_content')
    @patch('agents.graphic_outline_agent.GraphicOutlineAgent._generate_planting_captions')
    @patch('agents.graphic_outline_agent.GraphicOutlineAgent._generate_formatted_output')
    async def test_process_request_tuwen_test_mode(self, mock_formatted_output, mock_captions, mock_planting_content, mock_feishu_sheet, mock_execute_tasks):
        """测试process_request函数的图文规划(测试)模式"""
        logger.info("Testing process_request with '图文规划(测试)' mode")
        
        # 设置mock返回值
        mock_execute_tasks.side_effect = self._mock_execute_tasks
        mock_feishu_sheet.side_effect = self._mock_create_feishu_sheet
        mock_planting_content.side_effect = self._mock_generate_planting_content
        mock_captions.side_effect = self._mock_generate_planting_captions
        mock_formatted_output.side_effect = self._mock_generate_formatted_output
        
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
        
        # 调用被测试函数
        result = await self.agent.process_request(test_request)
        
        # 验证结果
        self.assertEqual(result["status"], "success")
        self.assertIn("task_results", result)
        self.assertIn("processed_data", result)
        self.assertIn("spreadsheet", result)
        
        # 验证processed_data中的关键字段
        processed_data = result["processed_data"]
        self.assertIn("planting_content", processed_data)
        self.assertIn("planting_captions", processed_data)
        self.assertIn("formatted_output", processed_data)
        self.assertEqual(processed_data["note_style"], "图文规划(测试)")
        
        # 验证mock被正确调用
        mock_execute_tasks.assert_called_once()
        mock_feishu_sheet.assert_called_once()
        mock_planting_content.assert_called_once()
        mock_captions.assert_called_once()
        mock_formatted_output.assert_called_once()
        
        logger.info("test_process_request_tuwen_test_mode passed")
    
    @patch('agents.task_processor.task_processor.execute_tasks')
    async def test_process_request_task_failure(self, mock_execute_tasks):
        """测试process_request函数在任务执行失败时的处理"""
        logger.info("Testing process_request with task execution failure")
        
        # 模拟任务执行失败
        async def mock_execute_tasks_failure(request_data):
            return {
                "target_audience_extractor": {
                    "status": "error",
                    "error": "Task execution failed"
                }
            }
        
        mock_execute_tasks.side_effect = mock_execute_tasks_failure
        
        # 准备测试数据
        test_request = {
            "topic": "夏季护肤指南",
            "product_highlights": "防晒、保湿、温和配方",
            "note_style": "种草",
            "product_name": "水润防晒霜",
            "direction": "重点介绍防晒效果和使用感受",
            "blogger_link": "https://xiaohongshu.com/user/12345",
            "requirements": "需要包含使用前后对比，适合敏感肌",
            "style": "活泼"
        }
        
        # 调用被测试函数
        result = await self.agent.process_request(test_request)
        
        # 验证结果
        self.assertEqual(result["status"], "success")  # 即使部分任务失败，整体仍应成功
        self.assertIn("task_results", result)
        self.assertIn("processed_data", result)
        
        logger.info("test_process_request_task_failure passed")


async def run_tests():
    """运行测试"""
    logger.info("Starting GraphicOutlineAgent tests")
    
    # 创建测试套件
    suite = unittest.TestSuite()
    
    # 创建测试类实例
    test_case = TestGraphicOutlineAgent()
    
    # 添加测试方法到测试套件
    suite.addTest(TestGraphicOutlineAgent('test_process_request_zhongcao_mode'))
    suite.addTest(TestGraphicOutlineAgent('test_process_request_tuwen_test_mode'))
    suite.addTest(TestGraphicOutlineAgent('test_process_request_task_failure'))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    logger.info("GraphicOutlineAgent tests completed")
    return result


if __name__ == "__main__":
    # 运行异步测试
    asyncio.run(run_tests())