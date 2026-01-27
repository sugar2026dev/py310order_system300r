import json
import os
import shutil
import re
import pandas as pd
import io
import openpyxl
import requests

from django.http import HttpResponse
from datetime import datetime
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from django.core.cache import cache
from django.db import transaction

from .models import User, Order
from .decorators import superuser_required, normal_user_required


# ===================== 用户认证相关 =====================

@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    """用户登录 - 适配新用户模型"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        remember = data.get('remember', False)

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            # 设置session有效期
            if remember:
                request.session.set_expiry(1209600)  # 2周
            else:
                request.session.set_expiry(0)  # 浏览器关闭失效

            # 构建响应数据 - 适配新模型
            user_data = {
                'user_id': user.id,
                'username': user.username,
                'is_superuser': user.is_superuser,  # 使用 is_superuser
                # 为了兼容前端代码
                'user_type': 2 if user.is_superuser else 1,
                'user_type_name': '超级用户' if user.is_superuser else '普通用户',
                'is_super': user.is_superuser  # 兼容旧字段
            }

            return JsonResponse({
                'code': 200,
                'msg': '登录成功',
                'data': user_data
            })
        else:
            return JsonResponse({
                'code': 400,
                'msg': '用户名或密码错误',
                'data': None
            })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'msg': f'登录失败: {str(e)}',
            'data': None
        })


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def logout_view(request):
    """用户登出"""
    logout(request)
    return JsonResponse({
        'code': 200,
        'msg': '登出成功',
        'data': None
    })


@csrf_exempt
@require_http_methods(["GET"])
def check_auth(request):
    """检查认证状态 - 适配新用户模型"""
    # 频率限制
    client_ip = request.META.get('REMOTE_ADDR')
    cache_key = f"check_auth_{client_ip}"
    request_count = cache.get(cache_key, 0)

    if request_count > 3:
        return JsonResponse({
            'code': 429,
            'msg': '请求过于频繁',
            'data': None
        }, status=429)

    cache.set(cache_key, request_count + 1, timeout=1)

    # 检查认证状态
    if request.user.is_authenticated:
        user = request.user
        return JsonResponse({
            'code': 200,
            'msg': '已登录',
            'data': {
                'authenticated': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'is_superuser': user.is_superuser,  # 使用 is_superuser
                    # 兼容字段
                    'user_type': 2 if user.is_superuser else 1,
                    'user_type_name': '超级用户' if user.is_superuser else '普通用户',
                    'is_super': user.is_superuser
                }
            }
        })
    else:
        return JsonResponse({
            'code': 401,
            'msg': '未登录',
            'data': {
                'authenticated': False
            }
        })


@csrf_exempt
@require_http_methods(["POST"])
def register_view(request):
    """用户注册"""
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        print(f"📝 [REGISTER] 收到注册请求: 用户名={username}")

        # 验证用户名长度（9个字符以内）
        if len(username) > 9:
            print(f"❌ [REGISTER] 用户名超长: {len(username)}字符")
            return JsonResponse({
                'code': 400,
                'msg': '用户名不能超过9个字符',
                'data': None
            })

        # 验证用户名格式（字母、数字、下划线）
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            print(f"❌ [REGISTER] 用户名格式错误: {username}")
            return JsonResponse({
                'code': 400,
                'msg': '用户名只能包含字母、数字和下划线',
                'data': None
            })

        # 验证用户名长度至少3个字符
        if len(username) < 3:
            print(f"❌ [REGISTER] 用户名太短: {username}")
            return JsonResponse({
                'code': 400,
                'msg': '用户名至少需要3个字符',
                'data': None
            })

        # 验证用户名是否已存在
        if User.objects.filter(username=username).exists():
            print(f"❌ [REGISTER] 用户名已存在: {username}")
            return JsonResponse({
                'code': 400,
                'msg': '用户名已存在',
                'data': None
            })

        # 验证密码长度
        if len(password) < 6:
            print(f"❌ [REGISTER] 密码太短: {len(password)}字符")
            return JsonResponse({
                'code': 400,
                'msg': '密码长度至少6位',
                'data': None
            })

        # 创建普通用户（非超级用户）
        print(f"👤 [REGISTER] 创建用户: {username}")
        user = User.objects.create_user(
            username=username,
            password=password,
            email=None,  # 不要求邮箱
            is_staff=False,  # 普通用户不能访问 admin
            is_superuser=False  # 不是超级用户
        )

        print(f"✅ [REGISTER] 注册成功: {username}")

        return JsonResponse({
            'code': 200,
            'msg': '注册成功',
            'data': {
                'user_id': user.id,
                'username': user.username,
                'is_superuser': False,
                # 兼容字段
                'user_type': 1,
                'user_type_name': '普通用户',
                'is_super': False
            }
        })

    except json.JSONDecodeError as e:
        print(f"❌ [REGISTER] JSON解析失败: {e}")
        return JsonResponse({
            'code': 400,
            'msg': '请求数据格式错误',
            'data': None
        })
    except Exception as e:
        print(f"❌ [REGISTER] 注册异常: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'code': 500,
            'msg': f'注册失败: {str(e)}',
            'data': None
        })


# ===================== 普通用户功能 =====================
@csrf_exempt
@login_required
@normal_user_required
@require_http_methods(["POST"])
@transaction.atomic
def upload_image(request):
    """普通用户上传图片 - 适配新权限装饰器"""
    temp_path = None

    try:
        print(f"📤 [UPLOAD] 收到上传请求，用户: {request.user.username}")

        # 1. 验证请求
        if 'image' not in request.FILES:
            return JsonResponse({
                'code': 400,
                'msg': '请选择要上传的图片',
                'data': None
            })

        image_file = request.FILES['image']
        print(f"📁 [UPLOAD] 文件: {image_file.name}, {image_file.size}字节")

        # 2. 验证文件类型和大小
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/gif']
        if image_file.content_type not in allowed_types:
            return JsonResponse({
                'code': 400,
                'msg': '只支持JPEG、PNG、GIF格式的图片',
                'data': None
            })

        if image_file.size > 5 * 1024 * 1024:
            return JsonResponse({
                'code': 400,
                'msg': '图片大小不能超过5MB',
                'data': None
            })

        # 3. 保存临时文件
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        temp_filename = f"temp_{timestamp}_{image_file.name}"
        temp_path = os.path.join(temp_dir, temp_filename)

        print(f"💾 [UPLOAD] 保存临时文件到: {temp_path}")

        with open(temp_path, 'wb') as f:
            for chunk in image_file.chunks():
                f.write(chunk)

        # 4. 调用OCR服务
        print(f"🔗 [OCR] 调用OCR服务: {settings.FLASK_OCR_URL}")
        try:
            with open(temp_path, 'rb') as f:
                files = {'image': (temp_filename, f, image_file.content_type)}
                response = requests.post(
                    settings.FLASK_OCR_URL,
                    files=files,
                    params={'user': request.user.username},
                    timeout=600  # 修改为600秒
                )

            print(f"📥 [OCR] 响应状态码: {response.status_code}")

            if response.status_code != 200:
                error_msg = f'OCR服务异常: {response.status_code}'
                print(f"❌ [OCR] {error_msg}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return JsonResponse({
                    'code': 500,
                    'msg': error_msg,
                    'data': None
                })

            ocr_result = response.json()
            print(f"📄 [OCR] 响应接收成功")

            # 5. 检查OCR是否成功
            if not ocr_result.get('success', False):
                error_msg = ocr_result.get('error', 'OCR识别失败')
                print(f"❌ [OCR] 识别失败: {error_msg}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return JsonResponse({
                    'code': 500,
                    'msg': error_msg,
                    'data': None
                })

            # 6. 提取订单编号
            data = ocr_result.get('data', {})
            order_code = data.get('订单编号')

            if not order_code:
                print(f"❌ 未识别到订单编号")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return JsonResponse({
                    'code': 400,
                    'msg': '未识别到订单编号，请重新上传清晰的订单截图',
                    'data': None
                })

            print(f"✅ 识别到订单编号: {order_code}")

            # 7. 检查订单是否已存在
            existing_order = Order.objects.select_for_update().filter(
                order_code=order_code
            ).first()

            if existing_order:
                print(f"⚠️ 订单已存在! ID: {existing_order.id}, 上传者: {existing_order.upload_user}")

                # 检查当前用户是否可以更新
                if existing_order.upload_user == request.user.username:
                    return JsonResponse({
                        'code': 409,
                        'msg': f'您之前已经上传过订单 {order_code}',
                        'data': {
                            'order_code': order_code,
                            'order_id': existing_order.id,
                            'duplicate': True,
                            'existing_uploader': existing_order.upload_user,
                            'existing_time': existing_order.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                            'can_update': True,
                            'needs_confirmation': True,
                            'suggestion': '是否要用新图片替换原有图片？'
                        }
                    })
                else:
                    # 其他用户上传的订单，不允许更新
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                            print(f"🗑️ 已删除临时文件")
                        except Exception as e:
                            print(f"⚠️ 删除临时文件失败: {e}")

                    return JsonResponse({
                        'code': 403,
                        'msg': f'订单 {order_code} 已由 {existing_order.upload_user} 上传',
                        'data': {
                            'order_code': order_code,
                            'duplicate': True,
                            'existing_uploader': existing_order.upload_user,
                            'existing_time': existing_order.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                            'can_update': False,
                            'is_original_uploader': False
                        }
                    })

            print(f"✅ 数据库中不存在该订单，准备创建...")

            # 8. 保存图片到正式目录
            img_dir = os.path.join(settings.MEDIA_ROOT, 'order_images')
            os.makedirs(img_dir, exist_ok=True)

            # 生成唯一的文件名
            safe_filename = ''.join(c for c in image_file.name if c.isalnum() or c in ('_', '-', '.'))
            img_filename = f"{order_code}_{timestamp}_{safe_filename}"
            img_relative_path = f"order_images/{img_filename}"
            img_full_path = os.path.join(img_dir, img_filename)

            # 移动文件
            print(f"💾 移动文件到: {img_full_path}")
            if os.path.exists(temp_path):
                shutil.move(temp_path, img_full_path)

            # 9. 创建订单记录
            order = Order.objects.create(
                order_code=order_code,
                upload_user=request.user.username,
                ocr_result=json.dumps(ocr_result, ensure_ascii=False, indent=2),
                extracted_data=data,
                img_filename=img_filename,
                img_path=img_relative_path,
            )

            print(f"🎉 订单创建成功! ID: {order.id}")

            # 10. 返回成功响应
            return JsonResponse({
                'code': 200,
                'msg': '订单识别并保存成功',
                'data': {
                    'order_id': order.id,
                    'order_code': order_code,
                    'success': True,
                    'upload_user': order.upload_user,
                    'upload_time': order.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'is_update': False
                }
            })

        except requests.exceptions.RequestException as e:
            print(f"❌ OCR服务连接失败: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

            return JsonResponse({
                'code': 500,
                'msg': f'OCR服务连接失败: {str(e)}',
                'data': None
            })

    except Exception as e:
        print(f"❌ 上传处理异常: {e}")
        import traceback
        traceback.print_exc()

        # 确保清理临时文件
        if 'temp_path' in locals() and temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                print(f"🗑️ 异常时清理临时文件")
            except Exception as cleanup_error:
                print(f"⚠️ 清理临时文件失败: {cleanup_error}")

        return JsonResponse({
            'code': 500,
            'msg': f'上传失败: {str(e)}',
            'data': None
        })


@csrf_exempt
@login_required
@normal_user_required
@require_http_methods(["POST"])
@transaction.atomic
def update_existing_order(request):
    """更新已存在的订单（需要用户确认后调用）"""
    temp_path = None

    try:
        # 1. 验证请求 - 使用更安全的文件获取方式
        if 'image' not in request.FILES:
            return JsonResponse({
                'code': 400,
                'msg': '请选择要上传的新图片',
                'data': None
            })

        image_file = request.FILES['image']

        # 安全地获取表单数据
        order_code = request.POST.get('order_code', '').strip()
        confirm = request.POST.get('confirm', '').lower() == 'true'

        # 处理可能的编码问题
        if isinstance(order_code, bytes):
            try:
                order_code = order_code.decode('utf-8')
            except UnicodeDecodeError:
                # 尝试其他编码
                try:
                    order_code = order_code.decode('gbk')
                except:
                    order_code = order_code.decode('latin-1')

        if not order_code:
            return JsonResponse({
                'code': 400,
                'msg': '订单编号不能为空',
                'data': None
            })

        if not confirm:
            return JsonResponse({
                'code': 400,
                'msg': '需要确认才能更新',
                'data': None
            })

        print(f"🔄 [UPDATE] 用户 {request.user.username} 请求更新订单 {order_code}")

        # 2. 验证文件类型和大小
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/gif']
        if image_file.content_type not in allowed_types:
            return JsonResponse({
                'code': 400,
                'msg': '只支持JPEG、PNG、GIF格式的图片',
                'data': None
            })

        if image_file.size > 5 * 1024 * 1024:
            return JsonResponse({
                'code': 400,
                'msg': '图片大小不能超过5MB',
                'data': None
            })

        # 3. 保存临时文件 - 使用二进制模式避免编码问题
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')

        # 处理文件名编码问题
        original_filename = image_file.name
        safe_filename = ''

        # 方法1: 使用ASCII字符
        for c in original_filename:
            if c.isalnum() or c in ('_', '-', '.', ' '):
                safe_filename += c
            else:
                safe_filename += '_'

        # 方法2: 如果方法1结果为空，使用时间戳作为文件名
        if not safe_filename.strip():
            safe_filename = f"image_{timestamp}"

        temp_filename = f"update_temp_{timestamp}_{safe_filename}"
        temp_path = os.path.join(temp_dir, temp_filename)

        print(f"💾 [UPDATE] 保存临时文件: {temp_path}")

        # 使用二进制模式写入
        with open(temp_path, 'wb') as f:
            for chunk in image_file.chunks():
                f.write(chunk)

        # 4. 调用OCR服务
        print(f"🔗 [UPDATE-OCR] 调用OCR服务获取更新信息")
        try:
            with open(temp_path, 'rb') as f:  # 使用二进制模式读取
                files = {'image': (safe_filename, f, image_file.content_type)}  # 使用安全文件名
                response = requests.post(
                    settings.FLASK_OCR_URL,
                    files=files,
                    params={'user': request.user.username},
                    timeout=600  # 修改为600秒
                )

            if response.status_code != 200:
                error_msg = f'OCR服务异常: {response.status_code}'
                print(f"❌ [UPDATE-OCR] {error_msg}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return JsonResponse({
                    'code': 500,
                    'msg': error_msg,
                    'data': None
                })

            # 处理响应编码
            try:
                ocr_result = response.json()
            except UnicodeDecodeError:
                # 如果JSON解析失败，尝试指定编码
                ocr_result = response.json(encoding='utf-8')
            except Exception as e:
                print(f"⚠️ [UPDATE] JSON解析异常: {e}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return JsonResponse({
                    'code': 500,
                    'msg': 'OCR响应解析失败',
                    'data': None
                })

            if not ocr_result.get('success', False):
                error_msg = ocr_result.get('error', 'OCR识别失败')
                print(f"❌ [UPDATE-OCR] 识别失败: {error_msg}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return JsonResponse({
                    'code': 500,
                    'msg': error_msg,
                    'data': None
                })

            data = ocr_result.get('data', {})
            ocr_order_code = data.get('订单编号')

            # 验证订单编号
            if ocr_order_code and ocr_order_code != order_code:
                print(f"⚠️ [UPDATE] OCR识别订单编号 {ocr_order_code} 与请求订单编号 {order_code} 不一致，使用请求编号")
                # 继续使用请求的订单编号

        except requests.exceptions.RequestException as e:
            print(f"❌ [UPDATE] OCR服务连接失败: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return JsonResponse({
                'code': 500,
                'msg': f'OCR服务连接失败: {str(e)}',
                'data': None
            })

        # 5. 查找订单（必须是当前用户上传的）
        existing_order = Order.objects.select_for_update().filter(
            order_code=order_code,
            upload_user=request.user.username  # 只能更新自己上传的
        ).first()

        if not existing_order:
            print(f"❌ [UPDATE] 订单 {order_code} 不存在或用户 {request.user.username} 无权限更新")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return JsonResponse({
                'code': 404,
                'msg': f'订单 {order_code} 不存在或您没有权限更新',
                'data': None
            })

        print(f"✅ [UPDATE] 找到订单 ID: {existing_order.id}, 准备更新...")

        # 6. 删除旧图片文件
        old_img_relative_path = existing_order.img_path
        if old_img_relative_path:
            old_img_full_path = os.path.join(settings.MEDIA_ROOT, old_img_relative_path)

            if os.path.exists(old_img_full_path):
                try:
                    os.remove(old_img_full_path)
                    print(f"🗑️ [UPDATE] 删除旧图片文件: {old_img_full_path}")
                except Exception as e:
                    print(f"⚠️ [UPDATE] 删除旧图片失败: {e}")

        # 7. 保存新图片
        img_dir = os.path.join(settings.MEDIA_ROOT, 'order_images')
        os.makedirs(img_dir, exist_ok=True)

        # 生成新的安全文件名
        final_filename = f"{order_code}_update_{timestamp}_{safe_filename}"
        img_relative_path = f"order_images/{final_filename}"
        img_full_path = os.path.join(img_dir, final_filename)

        print(f"💾 [UPDATE] 移动文件到: {img_full_path}")
        if os.path.exists(temp_path):
            try:
                shutil.move(temp_path, img_full_path)
            except Exception as e:
                print(f"⚠️ [UPDATE] 移动文件失败: {e}")
                # 尝试复制
                shutil.copy2(temp_path, img_full_path)
                os.remove(temp_path)

        # 8. 更新订单记录
        try:
            # 处理JSON数据编码
            ocr_result_str = json.dumps(ocr_result, ensure_ascii=False)
            existing_order.ocr_result = ocr_result_str
            existing_order.extracted_data = data
            existing_order.img_filename = final_filename
            existing_order.img_path = img_relative_path
            existing_order.update_time = datetime.now()
            existing_order.save()

        except Exception as e:
            print(f"❌ [UPDATE] 更新数据库失败: {e}")
            # 如果保存失败，删除新图片
            if os.path.exists(img_full_path):
                os.remove(img_full_path)
            raise

        print(f"✅ [UPDATE] 订单更新成功! ID: {existing_order.id}")

        return JsonResponse({
            'code': 200,
            'msg': '订单已更新',
            'data': {
                'order_id': existing_order.id,
                'order_code': order_code,
                'action': 'updated',
                'upload_user': existing_order.upload_user,
                'update_time': existing_order.update_time.strftime('%Y-%m-%d %H:%M:%S'),
                'is_update': True
            }
        })

    except Exception as e:
        print(f"❌ [UPDATE] 更新处理异常: {e}")
        import traceback
        traceback.print_exc()

        # 确保清理临时文件
        if 'temp_path' in locals() and temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                print(f"🗑️ [UPDATE] 异常时清理临时文件")
            except Exception as cleanup_error:
                print(f"⚠️ [UPDATE] 清理临时文件失败: {cleanup_error}")

        # 返回更友好的错误信息
        error_msg = str(e)
        if 'utf-8' in error_msg.lower() and 'codec' in error_msg.lower():
            error_msg = '文件编码问题，请确保文件名只包含英文字母、数字和下划线'

        return JsonResponse({
            'code': 500,
            'msg': f'更新失败: {error_msg}',
            'data': None
        })


# ===================== 超级用户功能 =====================

@csrf_exempt
@login_required
@superuser_required
@require_http_methods(["GET"])
def order_list(request):
    """获取订单列表（分页）"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))
        keyword = request.GET.get('keyword', '').strip()
        start_date_str = request.GET.get('start_date', '').strip()
        end_date_str = request.GET.get('end_date', '').strip()

        # 构建查询
        queryset = Order.objects.all().order_by('-create_time')

        # 关键词搜索
        if keyword:
            queryset = queryset.filter(
                Q(order_code__icontains=keyword) |
                Q(upload_user__icontains=keyword) |
                Q(extracted_data__contains=keyword)
            )

        # 日期筛选
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                queryset = queryset.filter(create_time__range=[start_date, end_date])
            except ValueError:
                pass

        # 分页
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        # 构建响应数据
        orders_data = []
        for order in page_obj:
            orders_data.append(order.get_all_fields())

        return JsonResponse({
            'code': 200,
            'msg': '获取订单列表成功',
            'data': {
                'orders': orders_data,
                'pagination': {
                    'page': page_obj.number,
                    'page_size': page_size,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'has_previous': page_obj.has_previous(),
                    'has_next': page_obj.has_next(),
                }
            }
        })

    except Exception as e:
        return JsonResponse({
            'code': 500,
            'msg': f'获取订单列表失败: {str(e)}',
            'data': None
        })


@csrf_exempt
@login_required
@superuser_required
@require_http_methods(["GET"])
def order_detail(request, order_id):
    """获取订单详情"""
    try:
        order = Order.objects.get(id=order_id)

        return JsonResponse({
            'code': 200,
            'msg': '获取订单详情成功',
            'data': {
                'order': order.get_all_fields()
            }
        })

    except Order.DoesNotExist:
        return JsonResponse({
            'code': 404,
            'msg': '订单不存在',
            'data': None
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'msg': f'获取订单详情失败: {str(e)}',
            'data': None
        })


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def add_order(request):
    """添加订单"""
    try:
        data = json.loads(request.body)

        print(f"📥 [ADD_ORDER] 收到添加订单请求")

        # 验证必要字段
        required_fields = ['order_code', 'upload_user', 'product_name']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'code': 400,
                    'msg': f'缺少必要字段: {field}'
                })

        # 获取图片路径
        img_path = data.get('img_path', '')
        img_filename = data.get('img_filename', '')

        # 如果是完整的HTTP URL，转换为相对路径
        if img_path and img_path.startswith('http'):
            import re
            match = re.search(r'/media/(.+)$', img_path)
            if match:
                img_path = f'/media/{match.group(1)}'
            else:
                img_filename = img_path.split('/')[-1]
                img_path = f'/media/order_images/{img_filename}'

        # 构建 extracted_data
        extracted_data = {
            '订单编号': data.get('order_code', ''),
            '商品名称': data.get('product_name', ''),
            '商品规格': data.get('specification', ''),
            '商品价格': data.get('product_price', ''),
            '支付方式': data.get('payment_method', ''),
            '实付金额': data.get('actual_amount', ''),
            '物流公司': data.get('logistics_company', ''),
            '快递单号': data.get('tracking_number', ''),
            '订单状态': data.get('order_status', '待付款'),
            '收件人': data.get('receiver', ''),
            '联系方式': data.get('contact', ''),
            '收货地址': data.get('shipping_address', ''),
            '店铺名称': data.get('shop_name', ''),
            '下单时间': data.get('order_time', ''),
            '拼单时间': data.get('group_time', ''),
            '发货时间': data.get('ship_time', '')
        }

        # 移除空值
        extracted_data = {k: v for k, v in extracted_data.items() if v}

        # 检查订单是否已存在
        existing_order = Order.objects.filter(order_code=data['order_code']).first()
        if existing_order:
            return JsonResponse({
                'code': 409,
                'msg': f'订单编号 {data["order_code"]} 已存在',
                'data': None
            })

        # 创建订单记录
        order = Order.objects.create(
            order_code=data['order_code'],
            upload_user=data['upload_user'],
            img_path=img_path,
            img_filename=img_filename,
            extracted_data=extracted_data
        )

        print(f"✅ [ADD_ORDER] 订单保存成功 - ID: {order.id}")

        return JsonResponse({
            'code': 200,
            'msg': '添加成功',
            'data': {
                'id': order.id,
                'order_code': order.order_code,
                'img_path': img_path,
                'img_filename': img_filename
            }
        })

    except Exception as e:
        print(f"❌ [ADD_ORDER] 保存订单失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'code': 500,
            'msg': f'保存失败: {str(e)}'
        })


@csrf_exempt
@login_required
@superuser_required
@require_http_methods(["POST"])
def update_order(request):
    """更新订单"""
    try:
        data = json.loads(request.body)
        order_id = data.get('id')

        if not order_id:
            return JsonResponse({
                'code': 400,
                'msg': '订单ID不能为空',
                'data': None
            })

        order = Order.objects.get(id=order_id)

        # 更新 extracted_data
        extracted_data = order.extracted_data.copy()

        # 更新字段
        field_mapping = {
            'product_name': '商品名称',
            'specification': '商品规格',
            'product_price': '商品价格',
            'payment_method': '支付方式',
            'actual_amount': '实付金额',
            'logistics_company': '物流公司',
            'tracking_number': '快递单号',
            'order_status': '订单状态',
            'receiver': '收件人',
            'contact': '联系方式',
            'shipping_address': '收货地址',
            'shop_name': '店铺名称',
            'order_time': '下单时间',
            'group_time': '拼单时间',
            'ship_time': '发货时间',
        }

        for field, chinese_field in field_mapping.items():
            if field in data:
                extracted_data[chinese_field] = data[field]

        order.extracted_data = extracted_data
        order.save()

        return JsonResponse({
            'code': 200,
            'msg': '订单更新成功',
            'data': {
                'order_id': order.id,
                'order_code': order.order_code
            }
        })

    except Order.DoesNotExist:
        return JsonResponse({
            'code': 404,
            'msg': '订单不存在',
            'data': None
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'msg': f'更新订单失败: {str(e)}',
            'data': None
        })


@csrf_exempt
@login_required
@superuser_required
@require_http_methods(["POST"])
def batch_delete_orders(request):
    """批量删除订单"""
    try:
        data = json.loads(request.body)
        order_ids = data.get('order_ids', [])

        print(f"🗑️ [BATCH-DELETE] 收到批量删除请求，用户: {request.user.username}")

        if not order_ids:
            return JsonResponse({
                'code': 400,
                'msg': '请选择要删除的订单',
                'data': None
            })

        # 删除订单
        deleted_count = 0
        orders = Order.objects.filter(id__in=order_ids)

        for order in orders:
            # 删除图片文件
            if order.img_path:
                img_full_path = os.path.join(settings.MEDIA_ROOT, order.img_path.lstrip('/media/'))
                if os.path.exists(img_full_path):
                    try:
                        os.remove(img_full_path)
                    except Exception as e:
                        print(f"⚠️ [BATCH-DELETE] 删除图片失败: {e}")

            order.delete()
            deleted_count += 1

        print(f"✅ [BATCH-DELETE] 成功删除 {deleted_count} 个订单")

        return JsonResponse({
            'code': 200,
            'msg': f'成功删除 {deleted_count} 个订单',
            'data': {
                'deleted_count': deleted_count
            }
        })

    except Exception as e:
        print(f"❌ [BATCH-DELETE] 批量删除失败: {e}")
        return JsonResponse({
            'code': 500,
            'msg': f'批量删除失败: {str(e)}',
            'data': None
        })


@csrf_exempt
@login_required
@superuser_required
@require_http_methods(["POST"])
def query_orders(request):
    """查询订单"""
    try:
        data = json.loads(request.body)

        queryset = Order.objects.all()

        # 订单编号查询
        order_code = data.get('order_code')
        if order_code:
            queryset = queryset.filter(order_code__icontains=order_code)

        # 商品名称查询
        product_name = data.get('product_name')
        if product_name:
            queryset = queryset.filter(extracted_data__商品名称__icontains=product_name)

        # 时间范围查询
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(create_time__range=[start_date, end_date])

        # 订单状态查询
        order_status = data.get('order_status')
        if order_status:
            queryset = queryset.filter(extracted_data__订单状态=order_status)

        # 排序
        queryset = queryset.order_by('-create_time')

        # 转换为列表数据
        orders_data = []
        for order in queryset:
            orders_data.append(order.get_all_fields())

        return JsonResponse({
            'code': 200,
            'msg': '查询成功',
            'data': {
                'orders': orders_data,
                'total_count': len(orders_data)
            }
        })

    except Exception as e:
        return JsonResponse({
            'code': 500,
            'msg': f'查询失败: {str(e)}',
            'data': None
        })


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def ocr_upload(request):
    """OCR上传（预填充表单）- 增强版 - 所有登录用户都可以访问"""
    try:
        if 'image' not in request.FILES:
            return JsonResponse({
                'code': 400,
                'msg': '请选择要上传的图片',
                'data': None
            })

        image_file = request.FILES['image']

        # 验证文件
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/gif']
        if image_file.content_type not in allowed_types:
            return JsonResponse({
                'code': 400,
                'msg': '只支持JPEG、PNG、GIF格式的图片',
                'data': None
            })

        # 保存临时文件
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_filename = f"ocr_temp_{timestamp}_{image_file.name}"
        temp_path = os.path.join(temp_dir, temp_filename)

        with open(temp_path, 'wb') as f:
            for chunk in image_file.chunks():
                f.write(chunk)

        # 调用OCR服务
        try:
            with open(temp_path, 'rb') as f:
                files = {'image': (temp_filename, f, image_file.content_type)}
                response = requests.post(
                    settings.FLASK_OCR_URL,
                    files=files,
                    params={'user': request.user.username},
                    timeout=600  # 修改为600秒
                )

            if response.status_code == 200:
                ocr_result = response.json()
                data = ocr_result.get('data', {})

                # 检查OCR识别质量
                extracted_fields = len([v for v in data.values() if v])
                recognition_quality = 'high' if extracted_fields >= 8 else 'medium' if extracted_fields >= 5 else 'low'

                # 关键字段提取情况
                key_fields_status = {
                    '订单编号': bool(data.get('订单编号')),
                    '商品名称': bool(data.get('商品名称')),
                    '实付金额': bool(data.get('实付金额')),
                    '收件人': bool(data.get('收件人')),
                    '联系方式': bool(data.get('联系方式'))
                }

                missing_key_fields = [k for k, v in key_fields_status.items() if not v]

                # 构建详细的预填充数据
                prefill_data = {
                    'order_code': data.get('订单编号', ''),
                    'product_name': data.get('商品名称', ''),
                    'specification': data.get('商品规格', ''),
                    'product_price': data.get('商品价格', ''),
                    'payment_method': data.get('支付方式', ''),
                    'actual_amount': data.get('实付金额', ''),
                    'logistics_company': data.get('物流公司', ''),
                    'tracking_number': data.get('快递单号', ''),
                    'order_status': data.get('订单状态', '待付款'),
                    'receiver': data.get('收件人', ''),
                    'contact': data.get('联系方式', ''),
                    'shipping_address': data.get('收货地址', ''),
                    'shop_name': data.get('店铺名称', ''),
                    'img_filename': temp_filename,
                    'extracted_data': data,
                    'recognition_info': {
                        'quality': recognition_quality,
                        'extracted_fields': extracted_fields,
                        'total_fields': len(data),
                        'key_fields_status': key_fields_status,
                        'missing_key_fields': missing_key_fields,
                        'success': ocr_result.get('success', False),
                        'message': ocr_result.get('message', '')
                    }
                }

                # 清理临时文件
                if os.path.exists(temp_path):
                    os.remove(temp_path)

                return JsonResponse({
                    'code': 200,
                    'msg': 'OCR识别成功',
                    'data': prefill_data
                })
            else:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return JsonResponse({
                    'code': 500,
                    'msg': 'OCR识别失败，请重新上传清晰的图片',
                    'data': None
                })

        except requests.exceptions.RequestException as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return JsonResponse({
                'code': 500,
                'msg': f'OCR服务连接失败: {str(e)}',
                'data': None
            })

    except Exception as e:
        return JsonResponse({
            'code': 500,
            'msg': f'上传失败: {str(e)}',
            'data': None
        })


def debug_media(request):
    """调试媒体文件路径"""
    media_root = settings.MEDIA_ROOT
    order_images_dir = os.path.join(media_root, 'order_images')

    # 检查目录是否存在
    dir_exists = os.path.exists(order_images_dir)

    # 列出文件
    files = []
    if dir_exists:
        files = os.listdir(order_images_dir)

    # 查找特定文件
    target_file = '251109-349689618030662_20251230.jpg'
    file_exists = target_file in files if dir_exists else False

    # 检查文件实际位置
    file_paths = []
    possible_locations = [
        os.path.join(order_images_dir, target_file),
        os.path.join(media_root, target_file),
        os.path.join(os.path.dirname(media_root), 'backend', 'media', 'order_images', target_file),
        os.path.join(os.path.dirname(media_root), 'backend', 'media', target_file),
        os.path.join(os.path.dirname(os.path.dirname(media_root)), 'media', 'order_images', target_file),
    ]

    for path in possible_locations:
        if os.path.exists(path):
            file_paths.append({
                'path': path,
                'size': os.path.getsize(path),
                'exists': True
            })

    return JsonResponse({
        'settings': {
            'MEDIA_ROOT': settings.MEDIA_ROOT,
            'MEDIA_URL': settings.MEDIA_URL,
            'BASE_DIR': str(settings.BASE_DIR)
        },
        'directories': {
            'media_root': media_root,
            'order_images_dir': order_images_dir,
            'dir_exists': dir_exists
        },
        'files_in_order_images': files[:20],  # 只显示前20个文件
        'target_file': {
            'filename': target_file,
            'exists_in_dir': file_exists,
            'possible_locations': file_paths
        },
        'system_info': {
            'cwd': os.getcwd(),
            'project_root': os.path.dirname(media_root) if media_root else None
        }
    })


@csrf_exempt
@login_required
@require_http_methods(["GET"])
def export_orders_excel(request):
    """导出订单到Excel"""
    try:
        print(f"📤 [EXPORT] 收到导出请求，用户: {request.user.username}")

        # 获取查询参数
        keyword = request.GET.get('keyword', '').strip()
        start_date_str = request.GET.get('start_date', '')
        end_date_str = request.GET.get('end_date', '')
        export_all = request.GET.get('export_all', 'false') == 'true'

        # 构建查询
        queryset = Order.objects.all().order_by('-create_time')

        # 关键词搜索
        if keyword:
            queryset = queryset.filter(
                Q(order_code__icontains=keyword) |
                Q(upload_user__icontains=keyword) |
                Q(extracted_data__contains=keyword)
            )

        # 日期筛选
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                end_date = end_date.replace(hour=23, minute=59, second=59)
                queryset = queryset.filter(create_time__range=[start_date, end_date])
            except ValueError as e:
                print(f"⚠️ [EXPORT] 日期格式错误: {e}")
                return JsonResponse({
                    'code': 400,
                    'msg': '日期格式不正确，请使用YYYY-MM-DD格式',
                    'data': None
                })

        # 检查数据量
        total_count = queryset.count()

        if total_count == 0:
            return JsonResponse({
                'code': 404,
                'msg': '没有找到符合条件的订单数据',
                'data': None
            })

        # 准备数据
        orders_data = []
        for order in queryset:
            try:
                orders_data.append({
                    '订单编号': order.order_code or '',
                    '上传者': order.upload_user or '',
                    '商品名称': order.get_product_name() or '',
                    '商品规格': order.get_specification() or '',
                    '商品价格': order.get_product_price() or '',
                    '支付方式': order.get_payment_method() or '',
                    '实付金额': order.get_actual_amount() or '',
                    '物流公司': order.get_logistics_company() or '',
                    '快递单号': order.get_tracking_number() or '',
                    '下单时间': order.get_order_time() or '',
                    '拼单时间': order.get_group_time() or '',
                    '发货时间': order.get_ship_time() or '',
                    '订单状态': order.get_order_status() or '',
                    '收件人': order.get_receiver() or '',
                    '联系方式': order.get_contact() or '',
                    '收货地址': order.get_shipping_address() or '',
                    '店铺名称': order.get_shop_name() or '',
                    '创建时间': order.create_time.strftime('%Y-%m-%d %H:%M:%S') if order.create_time else '',
                    '更新时间': order.update_time.strftime('%Y-%m-%d %H:%M:%S') if order.update_time else '',
                    '图片文件名': order.img_filename or '',
                })
            except Exception as e:
                print(f"⚠️ [EXPORT] 处理订单 {order.id} 时出错: {e}")
                continue

        if not orders_data:
            return JsonResponse({
                'code': 404,
                'msg': '没有可导出的数据',
                'data': None
            })

        # 创建DataFrame
        df = pd.DataFrame(orders_data)

        # 创建Excel文件
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='订单数据', index=False)
            worksheet = writer.sheets['订单数据']

            # 设置列宽
            for i, column in enumerate(df.columns, 1):
                column_letter = openpyxl.utils.get_column_letter(i)
                max_length = max(
                    df[column].astype(str).map(len).max(),
                    len(column)
                ) + 2
                worksheet.column_dimensions[column_letter].width = min(max_length, 30)

            # 设置表头样式
            for cell in worksheet[1]:
                cell.font = openpyxl.styles.Font(bold=True, color="FFFFFF")
                cell.fill = openpyxl.styles.PatternFill(start_color="2E8B57", end_color="2E8B57", fill_type="solid")
                cell.alignment = openpyxl.styles.Alignment(horizontal="center", vertical="center")

            worksheet.freeze_panes = 'A2'
            worksheet.auto_filter.ref = worksheet.dimensions

        output.seek(0)

        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = '订单数据'

        if keyword:
            filename += f'_{keyword}'
        if start_date_str and end_date_str:
            filename += f'_{start_date_str}_至_{end_date_str}'
        filename += f'_{timestamp}.xlsx'

        # 创建HTTP响应
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        print(f"❌ [EXPORT] 导出失败: {e}")
        return JsonResponse({
            'code': 500,
            'msg': f'导出失败: {str(e)}',
            'data': None
        })


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def ocr_for_form(request):
    """用于对话框表单的OCR识别"""
    temp_path = None

    try:
        print(f"📸 [FORM-OCR] 收到表单OCR请求，用户: {request.user.username}")

        # 1. 验证请求
        if 'image' not in request.FILES:
            return JsonResponse({
                'code': 400,
                'msg': '请选择要上传的图片',
                'data': None
            })

        image_file = request.FILES['image']
        print(f"📁 [FORM-OCR] 文件: {image_file.name}, {image_file.size}字节")

        # 2. 验证文件类型和大小
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/gif']
        if image_file.content_type not in allowed_types:
            return JsonResponse({
                'code': 400,
                'msg': '只支持JPEG、PNG、GIF格式的图片',
                'data': None
            })

        if image_file.size > 5 * 1024 * 1024:
            return JsonResponse({
                'code': 400,
                'msg': '图片大小不能超过5MB',
                'data': None
            })

        # 3. 保存临时文件
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')

        # 处理文件名，避免特殊字符
        safe_filename = ''.join(c for c in image_file.name if c.isalnum() or c in ('_', '-', '.', ' '))
        if not safe_filename.strip():
            safe_filename = f"image_{timestamp}"

        temp_filename = f"form_ocr_{timestamp}_{safe_filename}"
        temp_path = os.path.join(temp_dir, temp_filename)

        print(f"💾 [FORM-OCR] 保存临时文件到: {temp_path}")

        with open(temp_path, 'wb') as f:
            for chunk in image_file.chunks():
                f.write(chunk)

        # 4. 调用OCR服务
        print(f"🔗 [FORM-OCR] 调用OCR服务: {settings.FLASK_OCR_URL}")
        try:
            with open(temp_path, 'rb') as f:
                files = {'image': (safe_filename, f, image_file.content_type)}
                response = requests.post(
                    settings.FLASK_OCR_URL,
                    files=files,
                    params={'user': request.user.username},
                    timeout=600  # 修改为600秒
                )

            print(f"📥 [FORM-OCR] OCR响应状态码: {response.status_code}")

            if response.status_code != 200:
                error_msg = f'OCR服务异常: {response.status_code}'
                print(f"❌ [FORM-OCR] {error_msg}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return JsonResponse({
                    'code': 500,
                    'msg': error_msg,
                    'data': None
                })

            ocr_result = response.json()
            print(f"📄 [FORM-OCR] 响应接收成功")

            # 5. 检查OCR是否成功
            if not ocr_result.get('success', False):
                error_msg = ocr_result.get('error', 'OCR识别失败')
                print(f"❌ [FORM-OCR] 识别失败: {error_msg}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return JsonResponse({
                    'code': 500,
                    'msg': error_msg,
                    'data': None
                })

            # 6. 提取数据
            data = ocr_result.get('data', {})
            order_code = data.get('订单编号')

            print(f"✅ [FORM-OCR] 识别到数据，订单编号: {order_code}")
            print(f"📊 [FORM-OCR] 提取的字段: {list(data.keys())}")

            # 7. 关键：检查是否识别到订单编号
            if not order_code or order_code.strip() == '':
                print(f"❌ [FORM-OCR] 未识别到订单编号")

                # 🔥 清理临时文件
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                        print(f"🗑️ [FORM-OCR] 未识别到订单编号，删除临时文件")
                    except Exception as e:
                        print(f"⚠️ [FORM-OCR] 清理临时文件失败: {e}")

                return JsonResponse({
                    'code': 400,
                    'msg': '未识别到订单编号，请重新上传清晰的订单截图',
                    'data': None
                })

            # 8. 保存图片到服务器（永久目录）
            img_dir = os.path.join(settings.MEDIA_ROOT, 'order_images')
            os.makedirs(img_dir, exist_ok=True)

            # 生成最终文件名
            final_filename = f"{order_code}_{timestamp}_{safe_filename}"
            img_relative_path = f"order_images/{final_filename}"
            img_full_path = os.path.join(img_dir, final_filename)

            print(f"💾 [FORM-OCR] 移动文件到永久目录: {img_full_path}")

            # 移动临时文件到永久目录
            if os.path.exists(temp_path):
                try:
                    shutil.move(temp_path, img_full_path)
                    print(f"✅ [FORM-OCR] 文件保存成功")
                except Exception as e:
                    print(f"❌ [FORM-OCR] 移动文件失败: {e}")
                    # 尝试复制
                    shutil.copy2(temp_path, img_full_path)
                    os.remove(temp_path)

            # 9. 分析识别结果
            extracted_fields = len([v for v in data.values() if v])
            total_fields = len(data)

            # 计算识别质量
            if extracted_fields >= 10:
                recognition_quality = 'high'
                quality_text = '高质量识别'
            elif extracted_fields >= 5:
                recognition_quality = 'medium'
                quality_text = '中等质量识别'
            else:
                recognition_quality = 'low'
                quality_text = '低质量识别'

            # 关键字段状态
            key_fields = ['订单编号', '商品名称', '实付金额', '收件人', '联系方式', '物流公司']
            key_fields_status = {field: bool(data.get(field)) for field in key_fields}
            missing_key_fields = [k for k, v in key_fields_status.items() if not v]

            # 10. 检查订单是否已存在
            duplicate_info = None
            existing_order = Order.objects.filter(order_code=order_code).first()
            if existing_order:
                duplicate_info = {
                    'exists': True,
                    'uploader': existing_order.upload_user,
                    'upload_time': existing_order.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'can_update': existing_order.upload_user == request.user.username
                }
                print(f"⚠️ [FORM-OCR] 订单已存在: {order_code}, 上传者: {existing_order.upload_user}")

            # 11. 构建响应数据
            result_data = {
                'order_code': order_code or '',
                'product_name': data.get('商品名称', ''),
                'specification': data.get('商品规格', ''),
                'product_price': data.get('商品价格', ''),
                'payment_method': data.get('支付方式', ''),
                'actual_amount': data.get('实付金额', ''),
                'logistics_company': data.get('物流公司', ''),
                'tracking_number': data.get('快递单号', ''),
                'order_status': data.get('订单状态', '待付款'),
                'receiver': data.get('收件人', ''),
                'contact': data.get('联系方式', ''),
                'shipping_address': data.get('收货地址', ''),
                'shop_name': data.get('店铺名称', ''),
                'order_time': data.get('下单时间', ''),
                'group_time': data.get('拼单时间', ''),
                'ship_time': data.get('发货时间', ''),
                # 🔥 关键：返回图片路径
                'img_path': f'/media/order_images/{final_filename}',
                'img_filename': final_filename,
                'recognition_info': {
                    'success': True,
                    'has_order_code': bool(order_code),
                    'quality': recognition_quality,
                    'quality_text': quality_text,
                    'extracted_fields': extracted_fields,
                    'total_fields': total_fields,
                    'key_fields_status': key_fields_status,
                    'missing_key_fields': missing_key_fields,
                    'duplicate': duplicate_info
                }
            }

            print(f"✅ [FORM-OCR] 处理完成，返回数据")

            return JsonResponse({
                'code': 200,
                'msg': 'OCR识别成功',
                'data': result_data
            })

        except requests.exceptions.RequestException as e:
            print(f"❌ [FORM-OCR] OCR服务连接失败: {e}")
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

            return JsonResponse({
                'code': 500,
                'msg': f'OCR服务连接失败: {str(e)}',
                'data': None
            })

    except Exception as e:
        print(f"❌ [FORM-OCR] 处理异常: {e}")
        import traceback
        traceback.print_exc()

        # 确保清理临时文件
        if 'temp_path' in locals() and temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                print(f"🗑️ [FORM-OCR] 异常时清理临时文件")
            except Exception as cleanup_error:
                print(f"⚠️ [FORM-OCR] 清理临时文件失败: {cleanup_error}")

        return JsonResponse({
            'code': 500,
            'msg': f'识别失败: {str(e)}',
            'data': None
        })


@csrf_exempt
@login_required
@require_http_methods(["GET"])
def check_order_exists(request, order_code):
    """检查订单是否存在"""
    try:
        order_exists = Order.objects.filter(order_code=order_code).exists()

        if order_exists:
            # 如果订单存在，返回详细信息
            order = Order.objects.get(order_code=order_code)
            return JsonResponse({
                'code': 200,
                'msg': '订单存在',
                'data': {
                    'exists': True,
                    'order': {
                        'id': order.id,
                        'order_code': order.order_code,
                        'upload_user': order.upload_user,
                        'create_time': order.create_time.strftime('%Y-%m-%d %H:%M:%S') if order.create_time else '',
                        'product_name': order.get_product_name(),
                        'actual_amount': order.get_actual_amount()
                    }
                }
            })
        else:
            # 订单不存在
            return JsonResponse({
                'code': 200,
                'msg': '订单不存在',
                'data': {
                    'exists': False,
                    'order_code': order_code
                }
            })

    except Order.DoesNotExist:
        return JsonResponse({
            'code': 200,
            'msg': '订单不存在',
            'data': {
                'exists': False,
                'order_code': order_code
            }
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'msg': f'检查订单失败: {str(e)}',
            'data': None
        })


# ========== 简单 OCR 测试视图（不需要认证） ==========
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import requests
import time


@csrf_exempt
def simple_ocr_upload(request):
    """简单的 OCR 上传测试（不需要认证）"""
    if request.method != 'POST':
        return JsonResponse({'error': '只支持 POST 请求'}, status=405)

    if 'image' not in request.FILES:
        return JsonResponse({'error': '没有上传图片'}, status=400)

    image_file = request.FILES['image']

    try:
        # 调用 Flask OCR 服务
        start_time = time.time()

        # 读取图片数据
        image_data = image_file.read()

        # 准备文件
        files = {'image': (image_file.name, image_data, image_file.content_type)}

        # 调用 OCR 服务（使用长超时）
        ocr_response = requests.post(
            'http://127.0.0.1:5000/pic',
            files=files,
            timeout=600  # 修改为600秒
        )

        elapsed = time.time() - start_time

        if ocr_response.status_code == 200:
            ocr_data = ocr_response.json()
            return JsonResponse({
                'success': True,
                'message': f'OCR 处理成功，耗时 {elapsed:.2f}秒',
                'data': ocr_data.get('data', {}),
                'ocr_response': ocr_data,
                'processing_time': elapsed
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'OCR 服务返回错误: {ocr_response.status_code}',
                'ocr_response': ocr_response.json() if ocr_response.content else {},
                'processing_time': elapsed
            }, status=500)

    except requests.exceptions.Timeout:
        return JsonResponse({
            'success': False,
            'error': 'OCR 服务处理超时（600秒）'
        }, status=504)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'处理失败: {str(e)}'
        }, status=500)


@csrf_exempt
def test_ocr_connection(request):
    """测试 OCR 服务连接（不需要认证）"""
    import requests

    tests = []

    # 测试1: 直接连接
    try:
        response = requests.get('http://127.0.0.1:5000/', timeout=10)
        tests.append({
            'test': 'OCR 服务 GET',
            'status': 'success' if response.status_code == 200 else 'failed',
            'status_code': response.status_code,
            'message': '服务可访问' if response.status_code == 200 else '服务不可用'
        })
    except Exception as e:
        tests.append({
            'test': 'OCR 服务 GET',
            'status': 'error',
            'error': str(e),
            'message': '连接失败'
        })

    # 测试2: POST 请求（不带文件）
    try:
        response = requests.post('http://127.0.0.1:5000/pic', timeout=30)
        tests.append({
            'test': 'OCR 服务 POST',
            'status': 'success' if response.status_code == 200 else 'failed',
            'status_code': response.status_code,
            'message': 'POST 接口可用' if response.status_code == 200 else 'POST 接口错误'
        })
    except Exception as e:
        tests.append({
            'test': 'OCR 服务 POST',
            'status': 'error',
            'error': str(e),
            'message': 'POST 请求失败'
        })

    return JsonResponse({
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
        'tests': tests,
        'summary': {
            'total': len(tests),
            'success': sum(1 for t in tests if t['status'] == 'success'),
            'failed': sum(1 for t in tests if t['status'] == 'failed'),
            'error': sum(1 for t in tests if t['status'] == 'error')
        }
    })


# ========== OCR 服务紧急修复 ==========

@csrf_exempt
def diagnose_ocr_service(request):
    """诊断OCR服务状态"""
    import requests
    import socket
    import time
    from urllib.parse import urlparse

    diagnostic_info = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'server_time': time.strftime("%Y-%m-%d %H:%M:%S"),
        'settings': {
            'FLASK_OCR_URL': settings.FLASK_OCR_URL,
            'DEBUG': settings.DEBUG,
            'server_ip': '101.201.31.24'
        },
        'tests': []
    }

    # 测试1: 检查settings中的OCR_URL配置
    ocr_url = settings.FLASK_OCR_URL
    diagnostic_info['tests'].append({
        'name': '配置检查',
        'status': '已配置' if ocr_url else '未配置',
        'ocr_url': ocr_url,
        'message': f'当前OCR服务地址: {ocr_url}'
    })

    # 测试2: 测试基本连接
    try:
        base_url = ocr_url.replace('/pic', '/')
        resp = requests.get(base_url, timeout=5)
        diagnostic_info['tests'].append({
            'name': 'OCR服务根目录访问',
            'url': base_url,
            'status': '成功' if resp.status_code == 200 else '失败',
            'status_code': resp.status_code,
            'content_type': resp.headers.get('Content-Type'),
            'content_preview': resp.text[:100] if resp.text else '无内容'
        })
    except Exception as e:
        diagnostic_info['tests'].append({
            'name': 'OCR服务根目录访问',
            'url': base_url,
            'status': '连接失败',
            'error': str(e)
        })

    # 测试3: 测试/pic端点
    try:
        # 创建一个小测试文件
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp.write(b'test image content')
            tmp_path = tmp.name

        with open(tmp_path, 'rb') as f:
            files = {'image': ('test.jpg', f, 'image/jpeg')}
            resp = requests.post(ocr_url, files=files, timeout=30)

        os.unlink(tmp_path)

        diagnostic_info['tests'].append({
            'name': '/pic端点测试',
            'url': ocr_url,
            'status': '成功' if resp.status_code == 200 else '失败',
            'status_code': resp.status_code,
            'content_type': resp.headers.get('Content-Type'),
            'is_json': 'application/json' in resp.headers.get('Content-Type', ''),
            'response_preview': resp.text[:200] if resp.text else '无内容'
        })
    except Exception as e:
        diagnostic_info['tests'].append({
            'name': '/pic端点测试',
            'url': ocr_url,
            'status': '请求失败',
            'error': str(e)
        })

    # 测试4: 端口连通性
    try:
        parsed_url = urlparse(ocr_url)
        hostname = parsed_url.hostname or 'localhost'
        port = parsed_url.port or 5000

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((hostname, port))
        sock.close()

        diagnostic_info['tests'].append({
            'name': '端口连通性',
            'host': hostname,
            'port': port,
            'status': '成功' if result == 0 else '失败',
            'result_code': result,
            'message': f'端口 {port} 可访问' if result == 0 else f'端口 {port} 不可访问'
        })
    except Exception as e:
        diagnostic_info['tests'].append({
            'name': '端口连通性',
            'status': '测试失败',
            'error': str(e)
        })

    # 测试5: 本地回环测试
    try:
        resp = requests.get('http://127.0.0.1:5000/', timeout=3)
        diagnostic_info['tests'].append({
            'name': '本地回环测试(127.0.0.1:5000)',
            'status': '成功' if resp.status_code == 200 else '失败',
            'status_code': resp.status_code
        })
    except Exception as e:
        diagnostic_info['tests'].append({
            'name': '本地回环测试(127.0.0.1:5000)',
            'status': '不可达',
            'error': '本地Flask服务可能未启动'
        })

    # 统计
    total = len(diagnostic_info['tests'])
    success = sum(1 for t in diagnostic_info['tests'] if t.get('status') in ['成功', '已配置'])

    diagnostic_info['summary'] = {
        'total_tests': total,
        'successful': success,
        'failed': total - success,
        'health': '良好' if success == total else '有问题' if success > total / 2 else '严重问题'
    }

    return JsonResponse({
        'code': 200,
        'msg': 'OCR服务诊断完成',
        'data': diagnostic_info
    })


@csrf_exempt
@login_required
def mock_ocr_service(request):
    """模拟OCR服务，用于紧急情况"""
    import random
    import time

    if request.method != 'POST':
        return JsonResponse({'error': '只支持POST请求'}, status=405)

    print(f"🤖 [MOCK-OCR] 收到模拟OCR请求，用户: {request.user.username}")

    # 模拟处理时间
    time.sleep(1)

    # 如果有真实图片，也尝试处理
    has_real_image = 'image' in request.FILES

    if has_real_image:
        image_file = request.FILES['image']
        print(f"📸 [MOCK-OCR] 收到真实图片: {image_file.name}, {image_file.size}字节")

    # 生成模拟数据
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    mock_data = {
        'success': True,
        'message': '模拟OCR识别成功',
        'data': {
            '订单编号': f'MOCK{timestamp[:8]}{random.randint(1000, 9999)}',
            '商品名称': f'模拟商品{random.randint(1, 100)}号',
            '商品规格': '标准规格',
            '商品价格': f'{random.randint(50, 500)}.00',
            '支付方式': random.choice(['微信支付', '支付宝', '银行卡']),
            '实付金额': f'{random.randint(40, 450)}.00',
            '物流公司': random.choice(['顺丰速运', '圆通快递', '中通快递', '韵达快递']),
            '快递单号': f'YT{random.randint(1000000000, 9999999999)}',
            '订单状态': random.choice(['待付款', '待发货', '已发货', '已完成']),
            '收件人': random.choice(['张先生', '李女士', '王先生', '刘女士']),
            '联系方式': f'138{random.randint(10000000, 99999999)}',
            '收货地址': random.choice(['北京市海淀区', '上海市浦东新区', '广州市天河区', '深圳市南山区']) + '测试地址',
            '店铺名称': random.choice(['旗舰店', '官方店', '专卖店', '直营店']),
            '下单时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '发货时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S') if random.random() > 0.3 else ''
        }
    }

    print(f"✅ [MOCK-OCR] 返回模拟数据: {mock_data['data']['订单编号']}")

    return JsonResponse(mock_data)