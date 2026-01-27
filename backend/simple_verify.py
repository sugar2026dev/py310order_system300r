#!/usr/bin/env python3
import os
import sys

# 添加正确的路径
sys.path.insert(0, '/opt/order_system/backend')
sys.path.insert(0, '/opt/order_system/backend/apps')

# 直接读取settings.py文件来获取配置
settings_path = '/opt/order_system/backend/django_project/settings.py'
with open(settings_path, 'r') as f:
    exec(f.read())

print("=== 配置验证 ===")
print("BASE_DIR:", BASE_DIR)
print("MEDIA_ROOT:", MEDIA_ROOT)
print("MEDIA_URL:", MEDIA_URL)
print("order_images_dir:", order_images_dir)
print("temp_dir:", temp_dir)

print("\n=== 路径存在性检查 ===")
import os
print("MEDIA_ROOT是否存在:", os.path.exists(str(MEDIA_ROOT)))
print("order_images_dir是否存在:", os.path.exists(order_images_dir))
print("temp_dir是否存在:", os.path.exists(temp_dir))

print("\n=== 符号链接检查 ===")
backend_media_path = '/opt/order_system/backend/media'
if os.path.islink(backend_media_path):
    print("backend/media是指向", os.readlink(backend_media_path), "的符号链接")
else:
    print("backend/media不是符号链接")

print("\n=== 文件计数检查 ===")
import glob
order_images_count = len(glob.glob(os.path.join(order_images_dir, '*')))
temp_count = len(glob.glob(os.path.join(temp_dir, '*')))
print("order_images目录文件数:", order_images_count)
print("temp目录文件数:", temp_count)
