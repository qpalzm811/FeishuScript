
import unittest
import os
import sys
import shutil
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# Ensure paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from bilibili_monitor import BilibiliMonitor

class TestBilibiliMonitorWithAuth(unittest.TestCase):
    def setUp(self):
        self.download_dir = os.path.join(project_root, "temp_downloads")
        os.makedirs(self.download_dir, exist_ok=True)
        
    def tearDown(self):
        if os.path.exists(self.download_dir):
            shutil.rmtree(self.download_dir)

    @patch('bilibili_monitor.user.User')
    def test_auth_initialization(self, MockUser):
        print("\n=== Testing Bilibili Monitor Authentication ===")
        
        cookies = {
            'sessdata': 'fake_sessdata',
            'bili_jct': 'fake_jct',
            'buvid3': 'fake_buvid3'
        }
        
        mock_callback = MagicMock()
        
        # Initialize Monitor with cookies
        monitor = BilibiliMonitor([123456], 1, mock_callback, cookies)
        
        # Check if Credential object is created
        self.assertIsNotNone(monitor.credential)
        self.assertEqual(monitor.credential.sessdata, 'fake_sessdata')
        self.assertEqual(monitor.credential.bili_jct, 'fake_jct')
        print("✓ Credential object created correctly")
        
        # Check if User is initialized with credential
        mock_user_instance = MockUser.return_value
        monitor._get_user(123456)
        MockUser.assert_called_with(123456, credential=monitor.credential)
        print("✓ User object initialized with credential")

if __name__ == '__main__':
    unittest.main()
