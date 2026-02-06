import unittest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feishu_uploader import FeishuUploader

class TestFeishuUploader(unittest.TestCase):
    def setUp(self):
        self.uploader = FeishuUploader("app_id", "app_secret")

    @patch('requests.post')
    def test_get_tenant_access_token(self, mock_post):
        mock_post.return_value.json.return_value = {
            "code": 0,
            "tenant_access_token": "fake_token",
            "expire": 7200
        }
        token = self.uploader.get_tenant_access_token()
        self.assertEqual(token, "fake_token")
        self.assertEqual(self.uploader.token, "fake_token")

    @patch('requests.post')
    @patch('os.path.exists', return_value=True)
    @patch('os.path.getsize', return_value=1024)
    @patch('builtins.open', new_callable=mock_open, read_data=b'data')
    def test_upload_small_file(self, mock_file, mock_getsize, mock_exists, mock_post):
        # Mock token response
        mock_post.side_effect = [
            MagicMock(json=lambda: {"code": 0, "tenant_access_token": "token"}), # get_token
            MagicMock(json=lambda: {"code": 0, "data": {"file_token": "f123"}}) # upload
        ]
        
        res = self.uploader.upload_file("test.txt", "parent_token")
        self.assertEqual(res["code"], 0)
        
        # Verify upload called
        args, kwargs = mock_post.call_args_list[1]
        self.assertEqual(args[0], "https://open.feishu.cn/open-apis/drive/v1/files/upload_all")

if __name__ == '__main__':
    unittest.main()
