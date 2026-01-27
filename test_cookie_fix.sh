#!/bin/bash
echo "🍪 测试 Cookie 修复效果..."
echo "=" * 60

# 测试 1: 检查 Set-Cookie 头
echo "1. 测试 Set-Cookie 头:"
echo "请求: curl -I http://101.201.31.24/api/check-auth/"
curl -I "http://101.201.31.24/api/check-auth/" 2>&1 | grep -i "set-cookie\|http"

echo -e "\n2. 测试 Cookie 传递:"
echo "请求: curl -v -c cookie.jar -b cookie.jar http://101.201.31.24/api/check-auth/"
curl -v -c cookie.jar -b cookie.jar "http://101.201.31.24/api/check-auth/" 2>&1 | grep -E "(> Cookie|< Set-Cookie|HTTP)"

echo -e "\n3. 检查 Cookie 文件内容:"
if [ -f "cookie.jar" ]; then
    echo "Cookie 文件内容:"
    cat cookie.jar
    echo -e "\nCookie 字段分析:"
    grep -E "csrftoken|sessionid" cookie.jar || echo "未找到 Cookie"
fi

echo -e "\n4. 测试登录流程:"
echo "步骤 1: 获取初始 Cookie"
curl -s -c login_cookies.txt -b login_cookies.txt "http://101.201.31.24/api/check-auth/" > /dev/null

echo "步骤 2: 提取 CSRF token"
CSRF_TOKEN=$(grep csrftoken login_cookies.txt | awk '{print $7}' 2>/dev/null || echo "")
echo "CSRF Token: ${CSRF_TOKEN:0:20}..."

echo "步骤 3: 登录请求"
curl -v -c login_cookies.txt -b login_cookies.txt \
  -X POST "http://101.201.31.24/api/login/" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -d '{"username":"admin","password":"admin123","remember":true}' \
  2>&1 | grep -E "(HTTP|< Set-Cookie|> Cookie|{)" | head -20

echo -e "\n5. 测试订单获取:"
curl -s -c login_cookies.txt -b login_cookies.txt \
  "http://101.201.31.24/api/orders/?page=1&page_size=5" \
  -w "HTTP状态: %{http_code}\n" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print('响应:', json.dumps(data, ensure_ascii=False)[:200], '...')
except:
    response = sys.stdin.read()
    if 'HTTP状态' not in response:
        print('原始响应:', response[:200])
"

# 清理
rm -f cookie.jar login_cookies.txt 2>/dev/null

echo -e "\n✅ 测试完成"
echo "=" * 60
