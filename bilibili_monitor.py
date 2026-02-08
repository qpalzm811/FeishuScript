
import asyncio
import time
import os
import threading
import logging
import requests
from datetime import datetime
from bilibili_api import user, dynamic, sync, Credential

# Configure logging
logger = logging.getLogger("BilibiliMonitor")

class BilibiliMonitor:
    def __init__(self, uids: list, check_interval: int, callback_func, cookies: dict = None):
        """
        :param uids: List of Bilibili User IDs to monitor
        :param check_interval: Check interval in seconds
        :param callback_func: Function to call when new dynamic is found (args: file_path)
        :param cookies: Dict containing sessdata, bili_jct, buvid3
        """
        self.uids = uids
        self.check_interval = check_interval
        self.callback = callback_func
        self.running = False
        self.last_dynamic_ids = {} # {uid: max_dynamic_id}
        
        self.credential = None
        if cookies and cookies.get('sessdata'):
            self.credential = Credential(
                sessdata=cookies.get('sessdata'),
                bili_jct=cookies.get('bili_jct'),
                buvid3=cookies.get('buvid3')
            )
            logger.info("BilibiliMonitor authenticated with provided cookies.")
        else:
            logger.info("BilibiliMonitor running in guest mode (no cookies).")

    def _get_user(self, uid):
        return user.User(uid, credential=self.credential)
        
    def start(self):
        """Start the monitor in a separate thread"""
        if self.running:
            return
        self.running = True
        thread = threading.Thread(target=self._monitor_loop, daemon=True)
        thread.start()
        logger.info(f"BilibiliMonitor started. Monitoring UIDs: {self.uids}")

    def stop(self):
        self.running = False

    def _monitor_loop(self):
        # Initial fetch to set baseline (don't alert on existing dynamics)
        asyncio.run(self._init_baseline())
        
        while self.running:
            try:
                asyncio.run(self._check_updates())
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
            
            # Sleep in chunks to allow quick stop
            for _ in range(self.check_interval):
                if not self.running:
                    break
                time.sleep(1)

    async def _init_baseline(self):
        """Fetch latest dynamic ID for each user to avoid alerting on startup"""
        logger.info("Initializing baseline for Bilibili monitor...")
        for uid in self.uids:
            try:
                # Get latest dynamics (offset=0 means latest)
                # Structure: {'cards': [...], 'has_more': 1, 'next_offset': ...}
                u = self._get_user(uid)
                # bilibili_api dynamic.get_dynamic_space might be deprecated or different version
                # Let's try user.get_dynamics
                res = await u.get_dynamics(offset=0)
                if res and 'cards' in res and len(res['cards']) > 0:
                    latest_id = res['cards'][0]['desc']['dynamic_id']
                    self.last_dynamic_ids[uid] = latest_id
                    logger.info(f"Baseline for UID {uid}: {latest_id}")
                else:
                    self.last_dynamic_ids[uid] = 0
            except Exception as e:
                logger.error(f"Failed to init baseline for {uid}: {e}")
        logger.info("Baseline initialized.")

    async def _check_updates(self):
        for uid in self.uids:
            try:
                u = self._get_user(uid)
                res = await u.get_dynamics(offset=0)
                
                if not res or 'cards' not in res:
                    continue
                    
                new_dynamics = []
                last_id = self.last_dynamic_ids.get(uid, 0)
                current_max_id = last_id
                
                for card in res['cards']:
                    dyn_id = card['desc']['dynamic_id']
                    if dyn_id <= last_id:
                        break
                    new_dynamics.append(card)
                    if dyn_id > current_max_id:
                        current_max_id = dyn_id
                
                # Update max id
                if current_max_id > last_id:
                    self.last_dynamic_ids[uid] = current_max_id
                
                # Process new dynamics (oldest first to keep order)
                for card in reversed(new_dynamics):
                    await self._process_dynamic(card, uid)
                    
            except Exception as e:
                logger.error(f"Error checking updates for {uid}: {e}")

    async def _process_dynamic(self, card, uid):
        """Parse dynamic card and generate markdown"""
        logger.info(f"New dynamic found for {uid}: {card['desc']['dynamic_id']}")
        
        try:
            desc = card['desc']
            card_data = card['card'] # JSON string, needs parsing
            # Usually card_data is a dict if using this library? 
            # Note: bilibili-api returns parsed dict for 'card' usually, 
            # but raw API returns string. The library might auto-parse.
            # Let's assume it is parsed or handle it.
            import json
            if isinstance(card_data, str):
                card_data = json.loads(card_data)
                
            user_profile = card['desc']['user_profile']
            uname = user_profile['info']['uname']
            timestamp = desc['timestamp']
            time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            
            # Content Parsing
            content = ""
            image_urls = []
            
            # Check type
            # 1: 转发, 2: 图文, 4: 文字, 8: 视频, 64: 专栏
            dtype = desc['type']
            
            if dtype == 1: # Forward
                content = f"**[转发动态]**\n\n"
                original = card_data.get('origin')
                if original:
                    if isinstance(original, str):
                        original = json.loads(original)
                    # Recursively parse original? Keep effective.
                    content += f"> {original.get('item', {}).get('description', '转发内容')}\n"
                current_content = card_data.get('item', {}).get('content', '')
                content += f"\n评论: {current_content}"
                
            elif dtype == 2: # Picture
                content = card_data.get('item', {}).get('description', '')
                pics = card_data.get('item', {}).get('pictures', [])
                for p in pics:
                    image_urls.append(p.get('img_src'))
                    
            elif dtype == 4: # Text
                content = card_data.get('item', {}).get('content', '')
                
            elif dtype == 8: # Video
                content = f"**[发布视频]** {card_data.get('title', '')}\n{card_data.get('desc', '')}"
                content += f"\n[链接]({card_data.get('short_link')})"
                image_urls.append(card_data.get('pic'))
            
            else:
                content = f"**[未支持的动态类型 {dtype}]**"

            # Prepare directories and filenames
            date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d_%H-%M')
            safe_uname = "".join([c for c in uname if c.isalnum() or c in (' ', '-', '_')]).strip()
            base_filename = f"[{date_str}] {safe_uname}_{desc['dynamic_id']}"
            
            download_dir = os.path.join(os.getcwd(), "downloaded_dynamics")
            images_dir = os.path.join(download_dir, "images")
            os.makedirs(images_dir, exist_ok=True)
            
            md_filename = f"{base_filename}.md"
            md_filepath = os.path.join(download_dir, md_filename)
            
            # Download Images
            local_image_paths = []
            if image_urls:
                for i, img_url in enumerate(image_urls):
                    if not img_url: continue
                    try:
                        # Extract extension or default to jpg
                        ext = os.path.splitext(img_url)[1].split('?')[0]  # remove query params
                        if not ext: ext = ".jpg"
                        
                        img_filename = f"{base_filename}_img_{i+1}{ext}"
                        img_filepath = os.path.join(images_dir, img_filename)
                        
                        # Download
                        r = requests.get(img_url, timeout=10)
                        if r.status_code == 200:
                            with open(img_filepath, 'wb') as f:
                                f.write(r.content)
                            # Use relative path for Markdown
                            relative_path = f"images/{img_filename}"
                            local_image_paths.append(relative_path)
                        else:
                            local_image_paths.append(img_url) # Fallback to URL
                    except Exception as e:
                        logger.error(f"Failed to download image {img_url}: {e}")
                        local_image_paths.append(img_url) # Fallback

            # Generate Markdown
            md_content = f"# {uname} 的新动态\n\n"
            md_content += f"**时间**: {time_str}\n\n"
            md_content += f"{content}\n\n"
            
            if local_image_paths:
                md_content += "**图片**:\n"
                for img_path in local_image_paths:
                    md_content += f"![img]({img_path})\n"
            
            link = f"https://t.bilibili.com/{desc['dynamic_id']}"
            md_content += f"\n[查看原文]({link})"
            
            with open(md_filepath, 'w', encoding='utf-8') as f:
                f.write(md_content)
                
            # Trigger callback (Upload)
            if self.callback:
                self.callback(md_filepath)
                
        except Exception as e:
            logger.error(f"Error parsing dynamic: {e}", exc_info=True)

if __name__ == "__main__":
    # Test stub
    def cb(path):
        print(f"Callback: {path}")
    
    # Example UID (Bilibili Official: 208259)
    monitor = BilibiliMonitor([208259], 10, cb)
    monitor.start()
    while True:
        time.sleep(1)
