
import unittest
import os
import sys
import json
import yaml
import shutil
import time
from unittest.mock import MagicMock, patch

# Ensure paths are correct
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

# Import our scripts
import apply_config
from webhook_server import app, SimpleBaiduPCS

class TestManualFlow(unittest.TestCase):
    """
    Test the entire manual flow described in USER_MANUAL.md
    1. Fill config.yaml
    2. Run apply_config.py
    3. Run run_integration.py (Simulated by starting Flask test client)
    4. Trigger Webhooks
    """

    def setUp(self):
        self.test_config_path = os.path.join(project_root, "config_test.yaml")
        # Backup original config if exists
        self.original_config_path = os.path.join(project_root, "config.yaml")
        self.config_backup = None
        if os.path.exists(self.original_config_path):
            with open(self.original_config_path, 'r', encoding='utf-8') as f:
                self.config_backup = f.read()

        # Create dummy config
        self.dummy_config = {
            "feishu": {
                "app_id": "cli_test_app",
                "app_secret": "test_secret",
                "folder_token": "fld_test_token"
            },
            "baidu": {
                "bduss": "test_bduss",
                "stoken": "test_stoken",
                "tasks": [
                    {"link": "http://pan.baidu.com/s/test1", "pwd": "123", "save_to": "/test/downloads"}
                ],
                "local_download_dir": "test_downloads"
            },
            "bilibili": {
                "webhook_url": "http://127.0.0.1:12345/bilibili_event",
                "quality": "avc"
            },
            "system": {
                "port": 54321,
                "debug": True
            }
        }
        with open(self.test_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.dummy_config, f)

        # Patch apply_config to use our test config
        self.original_unified_config = apply_config.UNIFIED_CONFIG
        apply_config.UNIFIED_CONFIG = self.test_config_path
        
        # Setup Flask client
        app.config['TESTING'] = True
        self.client = app.test_client()

    def tearDown(self):
        # Restore config
        if self.config_backup:
            with open(self.original_config_path, 'w', encoding='utf-8') as f:
                f.write(self.config_backup)
        
        if os.path.exists(self.test_config_path):
            os.remove(self.test_config_path)
            
        apply_config.UNIFIED_CONFIG = self.original_unified_config
        
        # Cleanup generated configs
        if os.path.exists("integration_config.json"):
            # ideally restore it too, but for now we just leave it or generated during test
            pass

    @patch('webhook_server.get_feishu_uploader')
    @patch('webhook_server.SimpleBaiduPCS')
    def test_full_process(self, MockPCS, mock_get_uploader):
        print("\n=== Starting End-to-End Process Test ===")
        
        # 1. Apply Configuration
        print("[Step 1] Applying Configuration...")
        apply_config.main()
        
        # Verify integration_config.json
        with open("integration_config.json", 'r') as f:
            int_conf = json.load(f)
            self.assertEqual(int_conf['feishu_app_id'], "cli_test_app")
            self.assertEqual(int_conf['port'], 54321)
            print("✓ integration_config.json updated correctly")
            
        # Verify baidu config
        baidu_conf_path = "baidu-autosave/config/config.json"
        if os.path.exists(baidu_conf_path):
            with open(baidu_conf_path, 'r', encoding='utf-8') as f:
                baidu_conf = json.load(f)
                users = baidu_conf.get('baidu', {}).get('users', {})
                # Check if bduss is set in one of the users
                found_bduss = False
                for u in users.values():
                    if u.get('cookies', {}).get('BDUSS') == "test_bduss":
                        found_bduss = True
                        break
                self.assertTrue(found_bduss, "BDUSS not found in baidu config")
                print("✓ baidu-autosave config updated correctly")

        # 2. Mock Services
        mock_uploader = MagicMock()
        mock_get_uploader.return_value = mock_uploader
        mock_uploader.upload_file.return_value = {"code": 0, "msg": "success", "data": {"token": "file_token"}}
        
        mock_pcs_instance = MockPCS.return_value
        # Mock download to actually create a file
        def side_effect_download(remote, local):
            with open(local, 'w') as f:
                f.write("dummy content")
        mock_pcs_instance.download_file.side_effect = side_effect_download

        # 3. Simulate Baidu Webhook Trigger
        print("[Step 2] Triggering Baidu Webhook...")
        baidu_payload = {"files": ["/test/downloads/anime.mp4"]}
        resp = self.client.post('/baidu_event', json=baidu_payload)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json['results'][0]['status'], 'success')
        
        # Verify logic
        mock_pcs_instance.download_file.assert_called()
        mock_uploader.upload_file.assert_called()
        print("✓ Baidu Webhook handled successfully (Download -> Upload)")

        # 4. Simulate Bilibili Webhook Trigger
        print("[Step 3] Triggering Bilibili Webhook...")
        # Create a dummy file for bilibili to upload
        dummy_bili_file = "test_bili.flv"
        with open(dummy_bili_file, 'w') as f:
            f.write("bili content")
            
        try:
            bili_payload = {
                "EventType": "FileClosed",
                "EventData": {
                    "Path": os.path.abspath(dummy_bili_file)
                }
            }
            # Mock get_feishu_uploader again because it's called inside the route
            # Actually patch mock_get_uploader is global for the test method
            
            resp = self.client.post('/bilibili_event', json=bili_payload)
            self.assertEqual(resp.status_code, 200)
            
            # Verify upload called for bilibili file
            # Check last call
            args, _ = mock_uploader.upload_file.call_args
            self.assertIn("test_bili.flv", args[0])
            print("✓ Bilibili Webhook handled successfully (Upload)")
            
        finally:
            if os.path.exists(dummy_bili_file):
                os.remove(dummy_bili_file)

        print("=== Test Complete: All Systems Go ===")

if __name__ == '__main__':
    unittest.main()
