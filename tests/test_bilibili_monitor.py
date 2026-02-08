
import unittest
import os
import sys
import shutil
import shutil
import asyncio
import json
from unittest.mock import MagicMock, patch, AsyncMock

# Ensure paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from bilibili_monitor import BilibiliMonitor

class TestBilibiliMonitor(unittest.TestCase):
    def setUp(self):
        self.download_dir = os.path.join(project_root, "temp_downloads")
        os.makedirs(self.download_dir, exist_ok=True)
        
    def tearDown(self):
        if os.path.exists(self.download_dir):
            shutil.rmtree(self.download_dir)

    @patch('bilibili_monitor.requests.get')
    @patch('bilibili_monitor.user.User')
    def test_monitor_logic(self, MockUser, MockRequestsGet):
        print("\n=== Testing Bilibili Monitor Logic ===")
        
        # Mock Image Download
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'fake_image_bytes'
        MockRequestsGet.return_value = mock_response
        
        # Mock User instance
        mock_user_instance = MockUser.return_value
        
        # 1. Baseline fetch
        old_card = {
            'desc': {
                'dynamic_id': 1000,
                'type': 4,
                'timestamp': 1600000000,
                'user_profile': {'info': {'uname': 'TestUser'}}
            },
            'card': '{"item": {"content": "Old Content"}}'
        }
        
        # 2. Update fetch: New Picture Dynamic
        new_card = {
            'desc': {
                'dynamic_id': 2000,
                'type': 2, # Picture type
                'timestamp': 1700000000,
                'user_profile': {'info': {'uname': 'TestUser'}}
            },
            'card': json.dumps({
                "item": {
                    "description": "Look at this picture",
                    "pictures": [{"img_src": "http://example.com/pic.jpg"}]
                }
            })
        }
        
        # Async mock side effect
        mock_user_instance.get_dynamics = AsyncMock(side_effect=[
            {'cards': [old_card]},
            {'cards': [new_card, old_card]}
        ])
        
        # Callback mock
        mock_callback = MagicMock()
        
        # Initialize Monitor
        monitor = BilibiliMonitor([123456], 1, mock_callback)
        
        # Run
        asyncio.run(monitor._init_baseline())
        asyncio.run(monitor._check_updates())
        
        # Verify
        self.assertTrue(mock_callback.called)
        args, _ = mock_callback.call_args
        file_path = args[0]
        print(f"✓ Callback triggered with file: {file_path}")
        
        # Verify Filename Pattern (YYYY-MM-DD...)
        self.assertIn("TestUser_2000.md", file_path)
        self.assertIn("[", file_path)
        
        # Verify Content and Image Link
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("images/", content)
            self.assertIn(".jpg", content)
            print("✓ Markdown maps to local image in images/ folder")
            
        # Verify Image File Exists
        images_dir = os.path.join(os.path.dirname(file_path), "images")
        self.assertTrue(os.path.exists(images_dir))
        # Find the image file
        files = os.listdir(images_dir)
        self.assertTrue(len(files) > 0)
        print(f"✓ Image file downloaded: {files[0]}")

if __name__ == '__main__':
    unittest.main()
