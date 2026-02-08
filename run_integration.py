import os
import sys

# Ensure current directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Add local libs to path for baidu-autosave dependencies
libs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baidu-autosave", "libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)

from webhook_server import app

if __name__ == "__main__":
    print("Starting Feishu Integration Server...")
    print("Please ensure 'integration_config.json' is configured with your Feishu credentials.")
    
    # Check if config exists
    config_file = "integration_config.json"
    if not os.path.exists(config_file):
        print(f"Warning: {config_file} not found. A template will be created when server starts.")
    else:
        # Start Bilibili Monitor if configured
        try:
            with open(config_file, 'r') as f:
                conf = json.load(f)
                users = conf.get('bilibili_users', [])
                interval = conf.get('bilibili_interval', 300)
                cookies = conf.get('bilibili_cookies', {})
                
                if users:
                    print(f"Starting Bilibili Monitor for {len(users)} users...")
                    from bilibili_monitor import BilibiliMonitor
                    from webhook_server import get_feishu_uploader # Helper we might need to expose or duplicate logic
                    
                    # Define callback to upload file
                    def upload_callback(file_path):
                        print(f"New dynamic found: {file_path}")
                        try:
                            # We need to instantiate uploader here or use a shared instance
                            # For simplicity, create new instance or fetch from server config
                            # But server config is loaded inside app context. 
                            # Let's load from conf directly.
                            from feishu_uploader import FeishuUploader
                            uploader = FeishuUploader(conf.get('feishu_app_id'), conf.get('feishu_app_secret'))
                            token = conf.get('feishu_folder_token')
                            
                            print(f"Uploading {file_path} to Feishu...")
                            res = uploader.upload_file(file_path, token)
                            print(f"Upload result: {res}")
                            
                            # Cleanup
                            if res and res.get('code') == 0:
                                # os.remove(file_path)  # Keep file for local archive as requested
                                print("File uploaded. Local copy preserved in 'downloaded_dynamics'.")
                            else:
                                print("Upload failed, file kept.")
                                
                        except Exception as e:
                            print(f"Error in upload callback: {e}")

                    monitor = BilibiliMonitor(users, interval, upload_callback, cookies)
                    monitor.start()
        except Exception as e:
            print(f"Failed to start Bilibili Monitor: {e}")
        
    app.run(host='0.0.0.0', port=12345)
