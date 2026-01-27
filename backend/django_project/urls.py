from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.views.generic import RedirectView
import os

# 前端目录
FRONTEND_DIR = os.path.join(settings.BASE_DIR.parent, 'frontend')

print(f"✅ 前端目录: {FRONTEND_DIR}")
print(f"✅ 前端目录存在: {os.path.exists(FRONTEND_DIR)}")

# 如果前端目录不存在，创建一个简单的
if not os.path.exists(FRONTEND_DIR):
    print(f"⚠️  前端目录不存在，尝试创建...")
    try:
        os.makedirs(FRONTEND_DIR, exist_ok=True)
        print(f"✅ 已创建前端目录: {FRONTEND_DIR}")
    except Exception as e:
        print(f"❌ 创建前端目录失败: {e}")

urlpatterns = [
    # ========== API 路由 ==========
    path('api/', include('order.urls')),

    # ========== Django 管理后台 ==========
    path('admin/', admin.site.urls),

    # ========== 媒体文件 ==========
    path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),

    # ========== 前端页面路由 ==========
    # 首页
    path('', lambda request: serve(request, 'index.html', document_root=FRONTEND_DIR)),

    # 上传页面
    path('upload.html', lambda request: serve(request, 'upload.html', document_root=FRONTEND_DIR)),
    path('upload', lambda request: serve(request, 'upload.html', document_root=FRONTEND_DIR)),

    # 静态文件（CSS, JS）
    path('css/<path:path>', lambda request, path: serve(request, f'css/{path}', document_root=FRONTEND_DIR)),
    path('js/<path:path>', lambda request, path: serve(request, f'js/{path}', document_root=FRONTEND_DIR)),

    # 其他静态资源
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.ico', permanent=True)),

    # 其他前端文件（放在最后）
    path('<path:path>', lambda request, path: serve(request, path, document_root=FRONTEND_DIR)),
]

# 调试模式下服务静态文件
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)