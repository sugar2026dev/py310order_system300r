import sys
sys.path.insert(0, '/opt/order_system/backend/django_project')
import settings

print("检查关键配置:")
print(f"1. ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
print(f"2. FLASK_OCR_URL: {getattr(settings, 'FLASK_OCR_URL', '未找到')}")
print(f"3. STATIC_URL: {settings.STATIC_URL}")
print(f"4. DATABASES 配置: {'已配置' if settings.DATABASES.get('default') else '未配置'}")
print(f"5. DEBUG 模式: {settings.DEBUG}")
