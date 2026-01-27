from functools import wraps
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required


def superuser_required(view_func):
    """超级用户权限装饰器"""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        user = request.user

        # 检查是否是超级用户（基于 is_superuser）
        if not user.is_superuser:
            return JsonResponse({
                'code': 403,
                'msg': '权限不足，仅超级用户可访问',
                'data': None
            }, status=403)
        return view_func(request, *args, **kwargs)

    return wrapper


def normal_user_required(view_func):
    """普通用户权限装饰器"""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        user = request.user

        # 检查是否是普通用户（基于 is_superuser）
        if user.is_superuser:
            return JsonResponse({
                'code': 403,
                'msg': '权限不足，仅普通用户可访问',
                'data': None
            }, status=403)
        return view_func(request, *args, **kwargs)

    return wrapper