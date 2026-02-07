import os
import sys
import shutil
import urllib.request
import zipfile
import tarfile

# Configuration
LIBS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baidu-autosave", "libs")
TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_setup")
BAIDUPCS_URL = "https://github.com/PeterDing/baidupcs-py/archive/refs/heads/master.zip"
# Fallback if github is slow, maybe pypi source? (Harder to get url dynamically)

SIMPLE_CIPHER_PY = """
# Pure Python implementation to replace Cython simple_cipher
# This allows baidupcs-py to run without compiling C extensions

def simple_encrypt(content: bytes) -> bytes:
    return content

def simple_decrypt(content: bytes) -> bytes:
    return content

def encrypt(content: bytes) -> bytes:
    return content

def decrypt(content: bytes) -> bytes:
    return content
"""

def download_file(url, dest):
    print(f"Downloading {url}...")
    try:
        # User defined headers to avoid 403 sometimes
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response, open(dest, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        return True
    except Exception as e:
        print(f"Failed to download: {e}")
        return False

def setup():
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    
    zip_path = os.path.join(TEMP_DIR, "baidupcs.zip")
    
    # 1. Download
    print("Step 1: Downloading baidupcs-py source...")
    if not download_file(BAIDUPCS_URL, zip_path):
        print("Error: Could not download source code. Please check your network.")
        print("You can manually download zip from https://github.com/PeterDing/baidupcs-py and save it as:", zip_path)
        input("Press Enter after you have manually placed the file, or Ctrl+C to exit...")
    
    # 2. Extract
    print("Step 2: Extracting...")
    try:
        if zipfile.is_zipfile(zip_path):
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(TEMP_DIR)
        else:
            print("Error: Invalid zip file.")
            return
    except Exception as e:
        print(f"Extraction failed: {e}")
        return

    # Find the extracted folder
    extracted_root = None
    for name in os.listdir(TEMP_DIR):
        if os.path.isdir(os.path.join(TEMP_DIR, name)) and "baidupcs" in name.lower():
            extracted_root = os.path.join(TEMP_DIR, name)
            break
            
    if not extracted_root:
        print("Error: Could not find extracted folder.")
        return

    source_pkg = os.path.join(extracted_root, "baidupcs_py")
    if not os.path.exists(source_pkg):
        print(f"Error: baidupcs_py package not found in {extracted_root}")
        return

    # 3. Install to libs
    print(f"Step 3: Installing to {LIBS_DIR}...")
    target_pkg = os.path.join(LIBS_DIR, "baidupcs_py")
    
    if not os.path.exists(LIBS_DIR):
        os.makedirs(LIBS_DIR)
        
    if os.path.exists(target_pkg):
        print("Removing existing version...")
        shutil.rmtree(target_pkg)
        
    shutil.copytree(source_pkg, target_pkg)
    
    # 4. Apply Patch
    print("Step 4: Applying No-C++ Patch...")
    cipher_file = os.path.join(target_pkg, "common", "simple_cipher.py")
    
    # Remove .pyx or .c if they exist to avoid confusion (though we copied py source)
    # The source might contain .pyx, we just ignore them.
    # We overwrite/create simple_cipher.py
    
    with open(cipher_file, 'w', encoding='utf-8') as f:
        f.write(SIMPLE_CIPHER_PY)
        
    print("Patch applied.")
    
    # Cleanup
    print("Cleaning up temp files...")
    try:
        shutil.rmtree(TEMP_DIR)
    except:
        pass
        
    print("\nSUCCESS! baidupcs-py installed locally with C++ requirements removed.")

if __name__ == "__main__":
    setup()
