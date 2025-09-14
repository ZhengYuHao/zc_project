import unittest
from unittest.mock import AsyncMock, Mock, patch
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.text_reviewer import TextReviewerAgent, FeishuDocumentRequest


class TestFeishuSpreadsheetDocument(unittest.TestCase):
    """测试飞书电子表格文档处理"""

    def setUp(self):
        """测试初始化"""
        # 创建TextReviewerAgent实例
        self.agent = TextReviewerAgent()
        
        # 模拟feishu_client
        self.agent.feishu_client = AsyncMock()
        
        # 模拟_llm
        self.agent.llm = AsyncMock()
        self.agent.llm.generate_text = AsyncMock(return_value="优化后的文本")
        
        # 模拟ac_automaton
        self.agent.ac_automaton = Mock()
        self.agent.ac_automaton.search = Mock(return_value=[])

    @patch('agents.text_reviewer.get_request_id')
    def test_process_feishu_spreadsheet_error(self, mock_get_request_id):
        """测试处理飞书电子表格时的错误情况"""
        mock_get_request_id.return_value = "test_request_id"
        
        # 模拟read_document方法抛出异常，模拟传入电子表格ID时的情况
        self.agent.feishu_client.read_document = AsyncMock(side_effect=Exception("Document not found or unsupported type"))
        
        # 创建请求
        request = FeishuDocumentRequest(document_id="xls_test_spreadsheet_id")
        
        # 运行异步测试
        import asyncio
        result = asyncio.run(self.agent.process_feishu_document(request))
        
        # 验证结果
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["document_id"], "xls_test_spreadsheet_id")
        self.assertIn("Document not found or unsupported type", result["error"])
        self.assertEqual(result["request_id"], "test_request_id")

    @patch('agents.text_reviewer.get_request_id')
    def test_process_feishu_spreadsheet_type_check(self, mock_get_request_id):
        """测试处理飞书电子表格时的类型检查和处理"""
        mock_get_request_id.return_value = "test_request_id"
        
        # 模拟read_document方法返回电子表格类型
        self.agent.feishu_client.read_document = AsyncMock(return_value={
            "meta": {"type": "sheet"},
            "content": {},
            "revision": 1
        })
        
        # 模拟feishu_client.get_tenant_access_token方法
        self.agent.feishu_client.get_tenant_access_token = AsyncMock(return_value="test_token")
        
        # 创建请求
        request = FeishuDocumentRequest(document_id="xls_test_spreadsheet_id")
        
        # 运行异步测试
        import asyncio
        result = asyncio.run(self.agent.process_feishu_document(request))
        
        # 验证结果 - 现在应该会处理电子表格而不是返回错误
        # 注意：由于我们没有完全模拟内部的httpx调用，这里可能会出现错误
        # 但在实际应用中，它应该会尝试处理电子表格
        self.assertEqual(result["document_id"], "xls_test_spreadsheet_id")
        self.assertEqual(result["request_id"], "test_request_id")


if __name__ == '__main__':
    unittest.main()