import yaml
import json
import os
import shutil

# Paths
UNIFIED_CONFIG = "config.yaml"
INTEGRATION_CONFIG = "integration_config.json"
BAIDU_CONFIG = "baidu-autosave/config/config.json"
BAIDU_CONFIG_TEMPLATE = "baidu-autosave/config/config.template.json"

def load_yaml(path):
    if not os.path.exists(path):
        print(f"Error: {path} not found.")
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def update_integration_config(config):
    """Updates integration_config.json used by webhook_server"""
    ver = {
        "feishu_app_id": config.get('feishu', {}).get('app_id', ''),
        "feishu_app_secret": config.get('feishu', {}).get('app_secret', ''),
        "feishu_folder_token": config.get('feishu', {}).get('folder_token', ''),
        "download_dir": config.get('baidu', {}).get('local_download_dir', 'temp_downloads'),
        "port": config.get('system', {}).get('port', 12345),
        "bilibili_users": config.get('bilibili', {}).get('users', []),
        "bilibili_interval": config.get('bilibili', {}).get('check_interval', 300),
        "bilibili_cookies": config.get('bilibili', {}).get('cookies', {})
    }
    
    with open(INTEGRATION_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(ver, f, indent=4)
    print(f"Updated {INTEGRATION_CONFIG}")

def update_baidu_config(config):
    """Updates baidu-autosave/config/config.json"""
    # Load existing or template
    base_config = {}
    if os.path.exists(BAIDU_CONFIG):
        with open(BAIDU_CONFIG, 'r', encoding='utf-8') as f:
            base_config = json.load(f)
    elif os.path.exists(BAIDU_CONFIG_TEMPLATE):
        with open(BAIDU_CONFIG_TEMPLATE, 'r', encoding='utf-8') as f:
            base_config = json.load(f)
            
    # Update Baidu specific fields
    baidu_settings = config.get('baidu', {})
    bduss = baidu_settings.get('bduss')
    stoken = baidu_settings.get('stoken')
    
    # Update User
    if bduss:
        # We use a default user "default_user" or update existing
        users = base_config.get('baidu', {}).get('users', {})
        current_user = base_config.get('baidu', {}).get('current_user')
        
        if not current_user and users:
            current_user = list(users.keys())[0]
        
        if not current_user:
            current_user = "user_from_config"
            
        if current_user not in users:
            users[current_user] = {"cookies": {}}
            
        users[current_user]['cookies']['BDUSS'] = bduss
        if stoken:
            users[current_user]['cookies']['STOKEN'] = stoken
            
        base_config['baidu']['users'] = users
        base_config['baidu']['current_user'] = current_user

    # Update Tasks
    yaml_tasks = baidu_settings.get('tasks', [])
    if yaml_tasks:
        # Convert YAML tasks to baidu-autosave tasks format
        # Baidu-autosave tasks usually look like: 
        # { "source": "link", "pwd": "pwd", "target": "path", "regex_pattern": ... }
        # NOTE: Baidu-autosave structure might be different, let's check template.
        # Template: "tasks": [] -> Inside User? Or Global?
        # Looking at template: "baidu": { "tasks": [] }
        
        new_tasks = []
        for t in yaml_tasks:
            new_tasks.append({
                "share_url": t.get('link'),
                "pwd": t.get('pwd', ''),
                "save_dir": t.get('save_to', '/'),
                "regex_pattern": "",
                "regex_replace": "",
                "description": "From Unified Config"
            })
        base_config['baidu']['tasks'] = new_tasks

    # Ensure Webhook is configured in baidu-autosave (Notification)
    # Baidu-autosave needs to call our webhook_server
    # We implemented `_send_to_feishu_webhook` in scheduler.py but it is hardcoded to call localhost:port?
    # Actually checking scheduler.py changes... 
    # Logic: requests.post("http://127.0.0.1:12345/baidu_event", ...)
    # So we just need to ensure the port matches system config. If port is dynamic, we might need to patch scheduler code or env var.
    # For now assume port 12345.
    
    # Save
    os.makedirs(os.path.dirname(BAIDU_CONFIG), exist_ok=True)
    with open(BAIDU_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(base_config, f, indent=4, ensure_ascii=False)
    print(f"Updated {BAIDU_CONFIG}")

def main():
    print("Applying unified configuration...")
    # Install dependencies for yaml if not exists (though we are running this script)
    # Assuming PyYAML is installed or we use a simple parser? 
    # Wait, PyYAML might not be in standard lib.
    # If config is YAML, we need PyYAML. 
    # If user doesn't have it, we should output error or use JSON for unified config.
    # The user asked for "A configuration file", YAML is best.
    # Let's try import, if fail, ask to install.
    
    config = load_yaml(UNIFIED_CONFIG)
    if not config:
        return

    update_integration_config(config)
    update_baidu_config(config)
    
    print("\nConfiguration applied successfully!")

if __name__ == "__main__":
    main()
