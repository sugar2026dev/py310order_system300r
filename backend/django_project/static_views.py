"""
静态文件服务视图
用于在开发环境中提供前端文件服务
"""

import os
from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from django.views.decorators.cache import never_cache


@never_cache
def serve_frontend_file(request, file_path=''):
    """
    提供前端文件服务

    Args:
        request: HTTP请求
        file_path: 相对于frontend目录的文件路径

    Returns:
        HttpResponse: 文件内容或错误响应
    """
    # 如果没有指定文件路径，默认返回index.html
    if not file_path:
        file_path = 'index.html'

    # 构建完整路径（frontend目录在backend的上一级）
    frontend_dir = os.path.join(settings.BASE_DIR, '..', 'frontend')
    full_path = os.path.join(frontend_dir, file_path)

    # 规范化路径，防止目录遍历攻击
    full_path = os.path.normpath(full_path)

    # 确保路径在frontend目录内
    if not full_path.startswith(os.path.abspath(frontend_dir)):
        return HttpResponseNotFound('禁止访问')

    # 如果路径是目录，返回index.html
    if os.path.isdir(full_path):
        full_path = os.path.join(full_path, 'index.html')

    # 检查文件是否存在
    if not os.path.exists(full_path):
        # 尝试查找文件
        possible_paths = [
            full_path,
            os.path.join(frontend_dir, file_path),
            os.path.join(frontend_dir, 'index.html'),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                full_path = path
                break
        else:
            return HttpResponseNotFound(f'文件未找到: {file_path}')

    # 根据文件扩展名设置MIME类型
    mime_map = {
        '.html': 'text/html',
        '.htm': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon',
        '.txt': 'text/plain',
        '.xml': 'application/xml',
        '.pdf': 'application/pdf',
        '.zip': 'application/zip',
        '.mp3': 'audio/mpeg',
        '.mp4': 'video/mp4',
    }

    ext = os.path.splitext(full_path)[1].lower()
    content_type = mime_map.get(ext, 'application/octet-stream')

    # 读取并返回文件
    try:
        # 二进制文件用rb模式，文本文件用r模式
        is_binary = ext in ['.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', '.mp3', '.mp4']
        mode = 'rb' if is_binary else 'r'
        encoding = None if is_binary else 'utf-8'

        with open(full_path, mode, encoding=encoding) as f:
            content = f.read()

        response = HttpResponse(content, content_type=content_type)

        # 添加缓存控制头
        if settings.DEBUG:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        return response

    except PermissionError:
        return HttpResponse('权限拒绝', status=403)
    except Exception as e:
        return HttpResponse(f'读取文件失败: {str(e)}', status=500)


# 快捷函数
@never_cache
def serve_index(request):
    """提供index.html页面"""
    return serve_frontend_file(request, 'index.html')


@never_cache
def serve_upload(request):
    """提供upload.html页面"""
    return serve_frontend_file(request, 'upload.html')


# 通用的前端文件服务
@never_cache
def serve_static(request, path):
    """
    通用静态文件服务
    匹配格式: /static/<file_path>
    """
    return serve_frontend_file(request, path)


@never_cache
def serve_css(request, path):
    """
    CSS文件服务
    匹配格式: /css/<file_path>
    """
    return serve_frontend_file(request, f'css/{path}')


@never_cache
def serve_js(request, path):
    """
    JavaScript文件服务
    匹配格式: /js/<file_path>
    """
    return serve_frontend_file(request, f'js/{path}')


@never_cache
def serve_images(request, path):
    """
    图片文件服务
    匹配格式: /images/<file_path>
    """
    return serve_frontend_file(request, f'images/{path}')