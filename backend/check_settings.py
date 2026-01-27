import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')

import django
django.setup()

from django.conf import settings

print("🔧 当前 Django 设置:")
print("=" * 60)

# 会话相关
print("\n📋 会话设置:")
print(f"SESSION_COOKIE_NAME: {settings.SESSION_COOKIE_NAME}")
print(f"SESSION_COOKIE_AGE: {settings.SESSION_COOKIE_AGE}")
print(f"SESSION_COOKIE_HTTPONLY: {settings.SESSION_COOKIE_HTTPONLY}")
print(f"SESSION_COOKIE_SAMESITE: {settings.SESSION_COOKIE_SAMESITE}")
print(f"SESSION_SAVE_EVERY_REQUEST: {settings.SESSION_SAVE_EVERY_REQUEST}")
print(f"SESSION_EXPIRE_AT_BROWSER_CLOSE: {settings.SESSION_EXPIRE_AT_BROWSER_CLOSE}")

print("\n🔐 CSRF 设置:")
print(f"CSRF_COOKIE_NAME: {settings.CSRF_COOKIE_NAME}")
print(f"CSRF_COOKIE_AGE: {settings.CSRF_COOKIE_AGE}")
print(f"CSRF_COOKIE_HTTPONLY: {settings.CSRF_COOKIE_HTTPONLY}")
print(f"CSRF_COOKIE_SAMESITE: {settings.CSRF_COOKIE_SAMESITE}")
print(f"CSRF_USE_SESSIONS: {settings.CSRF_USE_SESSIONS}")
print(f"CSRF_TRUSTED_ORIGINS: {settings.CSRF_TRUSTED_ORIGINS}")

print("\n🌐 CORS 设置:")
print(f"CORS_ALLOW_ALL_ORIGINS: {settings.CORS_ALLOW_ALL_ORIGINS}")
print(f"CORS_ALLOW_CREDENTIALS: {settings.CORS_ALLOW_CREDENTIALS}")

print("\n🏠 主机设置:")
print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
print(f"DEBUG: {settings.DEBUG}")

print("=" * 60)
