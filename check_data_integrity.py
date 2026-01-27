#!/usr/bin/env python3
import os
import sys
import subprocess

print("🔍 ========== 数据完整性检查 ==========")

print("\n1. 检查media目录:")
media_path = "/opt/order_system/media"
if os.path.exists(media_path):
    # 使用find命令统计文件
    result = subprocess.run(['find', media_path, '-type', 'f'], 
                          capture_output=True, text=True)
    files = result.stdout.strip().split('\n')
    if files[0]:  # 非空
        print(f"   ✅ media目录存在，有 {len(files)} 个文件")
        # 检查子目录
        subdirs = ['order_images', 'temp']
        for subdir in subdirs:
            subdir_path = os.path.join(media_path, subdir)
            if os.path.exists(subdir_path):
                result = subprocess.run(['find', subdir_path, '-type', 'f'], 
                                      capture_output=True, text=True)
                subfiles = result.stdout.strip().split('\n')
                count = len(subfiles) if subfiles[0] else 0
                print(f"   📁 {subdir}: {count} 个文件")
            else:
                print(f"   ⚠️  {subdir}: 目录不存在")
    else:
        print(f"   ⚠️  media目录存在，但为空")
else:
    print(f"   ❌ media目录不存在")

print("\n2. 检查符号链接:")
symlink_path = "/opt/order_system/backend/media"
if os.path.islink(symlink_path):
    target = os.readlink(symlink_path)
    print(f"   ✅ 符号链接存在，指向: {target}")
    
    # 测试访问
    test_file = None
    for root, dirs, files in os.walk(media_path):
        if files:
            test_file = os.path.join(root, files[0])
            break
    
    if test_file:
        # 通过符号链接访问
        rel_path = os.path.relpath(test_file, media_path)
        symlink_file = os.path.join(symlink_path, rel_path)
        if os.path.exists(symlink_file):
            print(f"   ✅ 符号链接可访问文件")
        else:
            print(f"   ❌ 符号链接无法访问文件")
else:
    print(f"   ❌ 符号链接不存在或不是符号链接")

print("\n3. 检查备份目录:")
backup_path = "/opt/order_system/backend/media.backup.old"
if os.path.exists(backup_path):
    result = subprocess.run(['du', '-sh', backup_path], 
                          capture_output=True, text=True)
    size = result.stdout.strip().split('\t')[0]
    print(f"   📦 备份目录存在，大小: {size}")
else:
    print(f"   ℹ️  备份目录不存在（可能已清理）")

print("\n🎯 ========== 检查完成 ==========")
print("根据以上结果判断:")
print("1. 如果media目录有文件且符号链接工作正常 → 迁移成功")
print("2. 如果备份目录还有文件 → 原始数据还在")
print("3. 可以安全清理备份目录: rm -rf /opt/order_system/backend/media.backup.old")
