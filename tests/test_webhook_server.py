import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock baidupcs_py before importing webhook_server
mock_baidupcs = MagicMock()
sys.modules['baidupcs_py'] = mock_baidupcs
sys.modules['baidupcs_py.baidupcs'] = mock_baidupcs
sys.modules['baidupcs_py.common'] = mock_baidupcs
sys.modules['baidupcs_py.common.downloader'] = mock_baidupcs

from webhook_server import app

class TestWebhookServer(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    @patch('webhook_server.get_baidu_pcs')
    @patch('webhook_server.get_feishu_uploader')
    @patch('webhook_server.load_config')
    @patch('builtins.open')
    @patch('os.makedirs')
    @patch('os.remove')
    @patch('requests.get')
    def test_baidu_event(self, mock_get, mock_remove, mock_makedirs, mock_open, mock_load, mock_get_uploader, mock_get_pcs):
        mock_load.return_value = {"feishu_folder_token": "ft123", "download_dir": "tmp"}
        mock_uploader = MagicMock()
        mock_get_uploader.return_value = mock_uploader
        
        mock_pcs = MagicMock()
        mock_get_pcs.return_value = mock_pcs
        mock_pcs.download_link.return_value = [MagicMock(dlink="http://baidu.com/file")]
        mock_pcs.bduss = "bduss"
        
        mock_get.return_value.__enter__.return_value.iter_content.return_value = [b'chunk']
        
        # FIX: Set return value for upload_file to a dict so jsonify works
        mock_uploader.upload_file.return_value = {"code": 0, "msg": "success"}

        resp = self.client.post('/baidu_event', json={"files": ["/test/video.mp4"]})
        
        self.assertEqual(resp.status_code, 200)
        res_json = resp.json
        self.assertEqual(len(res_json['results']), 1)
        self.assertEqual(res_json['results'][0]['status'], 'success')
        
        mock_uploader.upload_file.assert_called()

    @patch('webhook_server.get_feishu_uploader')
    @patch('webhook_server.load_config')
    @patch('os.path.exists', return_value=True)
    def test_bilibili_event(self, mock_exists, mock_load, mock_get_uploader):
        mock_load.return_value = {"feishu_folder_token": "ft123"}
        mock_uploader = MagicMock()
        mock_get_uploader.return_value = mock_uploader
        mock_uploader.upload_file.return_value = {"code": 0, "msg": "success"}
        
        payload = {
            "EventType": "FileClosed",
            "EventData": {
                "Path": "C:\\records\\video.flv"
            }
        }
        resp = self.client.post('/bilibili_event', json=payload)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json['status'], 'success')
        mock_uploader.upload_file.assert_called_with("C:\\records\\video.flv", "ft123")

if __name__ == '__main__':
    unittest.main()
