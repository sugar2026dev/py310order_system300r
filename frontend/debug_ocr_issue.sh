#!/bin/bash
echo "=" * 60
echo "OCR问题调试工具"
echo "=" * 60

# 1. 检查服务状态
echo "1️⃣ 检查服务状态:"
echo -n "  Flask OCR (5001): "
if curl -s http://127.0.0.1:5001/ > /dev/null; then
    echo "✅ 运行中"
else
    echo "❌ 未运行"
fi

echo -n "  Django (8000): "
if curl -s http://127.0.0.1:8000/api/check-auth/ > /dev/null; then
    echo "✅ 运行中"
else
    echo "❌ 未运行"
fi

# 2. 测试Django OCR接口
echo -e "\n2️⃣ 测试Django OCR接口:"
python3 -c "
import requests
import json

print('  测试 /api/simple-ocr-upload/ ...')
try:
    # 创建测试图片数据
    test_data = b'test image content'
    files = {'image': ('test_ocr_debug.jpg', test_data, 'image/jpeg')}
    
    response = requests.post('http://127.0.0.1:8000/api/simple-ocr-upload/', files=files, timeout=10)
    
    print(f'  状态码: {response.status_code}')
    
    if response.status_code == 200:
        try:
            result = response.json()
            print(f'  响应: {json.dumps(result, ensure_ascii=False, indent=2)}')
            
            if result.get('success'):
                print('  ✅ OCR接口工作正常')
            else:
                print(f'  ❌ OCR失败: {result.get(\"error\")}')
        except json.JSONDecodeError:
            print(f'  响应不是JSON: {response.text[:200]}')
    else:
        print(f'  ❌ HTTP错误: {response.status_code}')
        print(f'  错误信息: {response.text[:200]}')
        
except Exception as e:
    print(f'  ❌ 测试异常: {e}')
"

# 3. 检查Django日志
echo -e "\n3️⃣ 检查Django日志:"
tail -10 /tmp/django.log 2>/dev/null | grep -i "ocr\|error\|exception" || echo "  未找到相关日志"

# 4. 检查Flask日志
echo -e "\n4️⃣ 检查Flask OCR日志:"
tail -10 /tmp/flask_ocr.log 2>/dev/null | grep -i "收到\|返回\|error" || echo "  未找到相关日志"

# 5. 检查HTML文件中的JavaScript
echo -e "\n5️⃣ 检查前端配置:"
echo "  upload.html 中的OCR接口:"
grep -n "simple-ocr-upload\|5001" upload.html 2>/dev/null | head -5 || echo "    未找到相关配置"

echo "  test_ocr.html 中的OCR接口:"
grep -n "simple-ocr-upload\|5001" test_ocr.html 2>/dev/null | head -5 || echo "    未找到相关配置"

echo -e "\n6️⃣ 建议的解决方案:"
echo "  A. 确保前端调用的是 /api/simple-ocr-upload/ 而不是直接调用5001端口"
echo "  B. 检查浏览器控制台错误 (F12 -> Console)"
echo "  C. 检查网络请求 (F12 -> Network)"
echo "  D. 重启所有服务: cd /opt/order_system/backend && ./start_all_services.sh"

echo -e "\n" "=" * 60
