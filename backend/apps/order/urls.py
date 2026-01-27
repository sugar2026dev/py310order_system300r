from django.urls import path
from . import views

urlpatterns = [
    path('simple-ocr-upload/', views.simple_ocr_upload, name='simple_ocr_upload'),
    path('test-ocr-connection/', views.test_ocr_connection, name='test_ocr_connection'),
    # 用户认证
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('check-auth/', views.check_auth, name='check_auth'),
    path('register/', views.register_view, name='register'),

    # 普通用户功能
    path('upload/', views.upload_image, name='upload_image'),
    path('update-order/', views.update_existing_order, name='update_order'),

    # 超级用户功能
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/batch-delete/', views.batch_delete_orders, name='batch_delete'),
    path('orders/query/', views.query_orders, name='query_orders'),
    path('orders/add/', views.add_order, name='add_order'),
    path('orders/update/', views.update_order, name='update_order'),
    path('orders/ocr-upload/', views.ocr_upload, name='ocr_upload'),

    path('debug/media/', views.debug_media, name='debug_media'),
    # 导出Excel
    path('orders/export/', views.export_orders_excel, name='export_orders'),
    # 表单OCR识别
    path('orders/ocr-for-form/', views.ocr_for_form, name='ocr_for_form'),
    path('orders/check/<str:order_code>/', views.check_order_exists, name='check_order'),

    # 测试功能（新增）
    path('test-ocr-connection/', views.test_ocr_connection, name='test_ocr_connection'),
    path('simple-ocr-test/', views.simple_ocr_upload, name='simple_ocr_test'),
    path('diagnose-ocr/', views.diagnose_ocr_service, name='diagnose_ocr'),
    path('mock-ocr/', views.mock_ocr_service, name='mock_ocr'),
]
