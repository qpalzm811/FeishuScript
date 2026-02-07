import tarfile
import os
import shutil

src_dir = "d:/Project/FeishuScript/temp_src"
dest_dir = "d:/Project/FeishuScript/temp_baidupcs"

# Find the tar.gz file
for filename in os.listdir(src_dir):
    if filename.endswith(".tar.gz") and "baidupcs-py" in filename:
        file_path = os.path.join(src_dir, filename)
        print(f"Extracting {file_path}...")
        
        with tarfile.open(file_path, "r:gz") as tar:
            tar.extractall(path=dest_dir)
            
        print("Done.")
        
        # Move inner folder to libs
        extracted_root = os.listdir(dest_dir)[0] # baidupcs-py-x.y.z
        inner_pkg = os.path.join(dest_dir, extracted_root, "baidupcs_py")
        target_pkg = "d:/Project/FeishuScript/baidu-autosave/libs/baidupcs_py"
        
        if os.path.exists(target_pkg):
            shutil.rmtree(target_pkg)
        
        shutil.copytree(inner_pkg, target_pkg)
        print(f"Copied package to {target_pkg}")
        break
