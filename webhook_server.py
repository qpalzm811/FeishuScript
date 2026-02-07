import os
import json
import logging
import requests
import sys

# Add local libs to path for baidu-autosave dependencies
libs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baidu-autosave", "libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)

from flask import Flask, request, jsonify
from feishu_uploader import FeishuUploader
from urllib.parse import quote

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("IntegrationServer")

app = Flask(__name__)

# CONFIGURATION - TO BE FILLED BY USER or LOADED
# Ideally load from a separate config file
CONFIG_FILE = "integration_config.json"
BAIDU_CONFIG = "baidu-autosave/config/config.json"

class SimpleBaiduPCS:
    def __init__(self, bduss, stoken=None):
        self.session = requests.Session()
        self.session.cookies.update({"BDUSS": bduss})
        if stoken:
            self.session.cookies.update({"STOKEN": stoken})
        self.session.headers.update({
            "User-Agent": "netdisk;7.0.3.2;PC;PC-Windows;10.0.19041;WindowsBaiduYunGuanJia"
        })

    def download_file(self, remote_path, local_path):
        api_url = "http://pcs.baidu.com/rest/2.0/pcs/file"
        params = {
            "method": "download",
            "path": remote_path,
            "app_id": "250528"
        }
        
        logger.info(f"Downloading from Baidu: {remote_path}")
        with self.session.get(api_url, params=params, stream=True) as r:
            r.raise_for_status()
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def get_feishu_uploader():
    config = load_config()
    app_id = config.get("feishu_app_id")
    app_secret = config.get("feishu_app_secret")
    if not app_id or not app_secret:
        logger.error("Feishu credentials not found in config")
        return None
    return FeishuUploader(app_id, app_secret)

def get_baidu_pcs():
    try:
        if os.path.exists(BAIDU_CONFIG):
            with open(BAIDU_CONFIG, 'r', encoding='utf-8') as f:
                baidu_conf = json.load(f)
                users = baidu_conf.get("baidu", {}).get("users", {})
                if not users:
                    return None
                current_user_id = baidu_conf.get("baidu", {}).get("current_user")
                user = users.get(current_user_id) if current_user_id else list(users.values())[0]
                
                bduss = user.get("bduss") or user.get("cookies", {}).get("BDUSS")
                stoken = user.get("stoken") or user.get("cookies", {}).get("STOKEN")
                
                if bduss:
                    return SimpleBaiduPCS(bduss=bduss, stoken=stoken)
    except Exception as e:
        logger.error(f"Failed to load Baidu config: {e}")
    return None

@app.route('/baidu_event', methods=['POST'])
def handle_baidu_event():
    """
    Expects JSON: { "files": ["/remote/path/to/file.mp4"] }
    """
    data = request.json
    files = data.get("files", [])
    logger.info(f"Received Baidu event with {len(files)} files")
    
    pcs = get_baidu_pcs()
    uploader = get_feishu_uploader()
    
    if not pcs:
        return jsonify({"error": "Baidu PCS not configured"}), 500
    if not uploader:
        return jsonify({"error": "Feishu uploader not configured"}), 500
        
    config = load_config()
    download_dir = config.get("download_dir", "temp_downloads")
    os.makedirs(download_dir, exist_ok=True)
    
    results = []
    
    for remote_path in files:
        try:
            filename = os.path.basename(remote_path)
            local_path = os.path.join(download_dir, filename)
            
            logger.info(f"Downloading {remote_path} to {local_path}...")
            pcs.download_file(remote_path, local_path)
            
            logger.info(f"Downloaded. Uploading to Feishu...")
            target_folder = config.get("feishu_folder_token")
            upload_res = uploader.upload_file(local_path, target_folder)
            logger.info(f"Uploaded: {upload_res}")
            
            # Cleanup
            os.remove(local_path)
            results.append({"file": remote_path, "status": "success"})
            
        except Exception as e:
            logger.error(f"Error processing {remote_path}: {e}")
            results.append({"file": remote_path, "status": "error", "message": str(e)})

    return jsonify({"results": results})

@app.route('/bilibili_event', methods=['POST'])
def handle_bilibili_event():
    """
    Expects BililiveRecorder Webhook Payload.
    Usually: { "EventType": "FileClosed", "EventData": { "RelativePath": "...", "Path": "..." } }
    """
    data = request.json
    logger.info(f"Received Bilibili event: {data.get('EventType')}")
    
    if data.get("EventType") == "FileClosed":
        file_info = data.get("EventData", {})
        file_path = file_info.get("Path")
        
        if file_path and os.path.exists(file_path):
            try:
                uploader = get_feishu_uploader()
                if not uploader:
                     return jsonify({"error": "Feishu uploader not configured"}), 500
                     
                config = load_config()
                target_folder = config.get("feishu_folder_token")
                
                logger.info(f"Uploading {file_path} to Feishu...")
                res = uploader.upload_file(file_path, target_folder)
                logger.info(f"Uploaded: {res}")
                return jsonify({"status": "success", "feishu_res": res})
            except Exception as e:
                logger.error(f"Error uploading {file_path}: {e}")
                return jsonify({"error": str(e)}), 500
        else:
             logger.warning(f"File not found or invalid path: {file_path}")
    
    return jsonify({"status": "ignored"})

if __name__ == '__main__':
    # Initialize empty config if not exists
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "feishu_app_id": "",
                "feishu_app_secret": "",
                "feishu_folder_token": "",
                "download_dir": "temp_downloads"
            }, f, indent=4)
        print(f"Created {CONFIG_FILE}. Please fill in your Feishu credentials.")
    
    app.run(host='0.0.0.0', port=12345)
