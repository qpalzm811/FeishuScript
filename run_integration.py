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
        
    app.run(host='0.0.0.0', port=12345)
