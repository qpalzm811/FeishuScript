import zipfile
import os
import shutil

zip_path = "d:/Project/FeishuScript/baidupcs.zip"
extract_path = "d:/Project/FeishuScript/temp_baidupcs_source"

if os.path.exists(extract_path):
    shutil.rmtree(extract_path)

try:
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    print("Unzipped successfully.")
    
    # Find the package dir
    root_dir = os.listdir(extract_path)[0] # baidupcs-py-master
    pkg_source = os.path.join(extract_path, root_dir, "baidupcs_py")
    
    # Target
    target_dir = "d:/Project/FeishuScript/baidu-autosave/libs/baidupcs_py"
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    
    # Copy
    shutil.copytree(pkg_source, target_dir)
    print(f"Installed to {target_dir}")
    
except Exception as e:
    print(f"Error: {e}")
