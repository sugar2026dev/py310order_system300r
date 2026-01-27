#!/usr/bin/env python3
import os
import re

def fix_html_file(filepath):
    if not os.path.exists(filepath):
        print(f"文件不存在: {filepath}")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"\n🔧 修复 {filepath}:")
    
    # 1. 检查当前的OCR接口配置
    if '/api/simple-ocr-upload/' in content:
        print("  ✅ 已使用Django OCR接口")
    elif '5001' in content:
        print("  ✅ 已使用Flask OCR接口")
    else:
        print("  ⚠️ 未找到明确的OCR接口配置")
    
    # 2. 修复常见的JavaScript问题
    fixed_content = content
    
    # 确保使用正确的Django OCR接口
    patterns_to_check = [
        # 检查是否直接调用5001端口（应该改为通过Django代理）
        (r'http://127\.0\.0\.1:5001/pic', '/api/simple-ocr-upload/'),
        (r'http://101\.201\.31\.24:5001/pic', '/api/simple-ocr-upload/'),
        # 检查是否使用了绝对路径但应该用相对路径
        (r'http://127\.0\.0\.1:8000/api/simple-ocr-upload/', '/api/simple-ocr-upload/'),
    ]
    
    for pattern, replacement in patterns_to_check:
        if re.search(pattern, fixed_content):
            fixed_content = re.sub(pattern, replacement, fixed_content)
            print(f"  🔄 替换: {pattern} -> {replacement}")
    
    # 3. 添加调试信息
    if 'console.log' in fixed_content:
        print("  ✅ 已有调试信息")
    else:
        # 在关键位置添加调试信息
        lines = fixed_content.split('\n')
        for i, line in enumerate(lines):
            if 'fetch(' in line or 'axios.post(' in line or '.ajax(' in line:
                # 在上面的行添加调试信息
                debug_line = f'        console.log("🚀 开始OCR上传请求...");'
                lines.insert(i, debug_line)
                print(f"  🔧 在第{i+1}行前添加调试信息")
                break
        
        fixed_content = '\n'.join(lines)
    
    if content != fixed_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        print(f"  ✅ 文件已更新")
    else:
        print(f"  ✅ 文件无需修改")
    
    return True

# 修复所有相关HTML文件
files_to_fix = [
    'test_ocr.html',
    'simple_test.html',
    'upload.html'
]

print("=" * 60)
print("修复前端OCR接口配置")
print("=" * 60)

for file in files_to_fix:
    if os.path.exists(file):
        fix_html_file(file)
    else:
        print(f"\n⚠️ 文件不存在: {file}")

print("\n" + "=" * 60)
print("修复完成！")
print("\n验证步骤:")
print("1. 访问 http://101.201.31.24:8000/test_ocr.html")
print("2. 打开浏览器开发者工具 (F12)")
print("3. 上传图片并查看Console标签页的日志")
print("4. 查看Network标签页的请求详情")
print("=" * 60)
