from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    # 使用 Django 默认的 is_superuser 字段

    # 邮箱设为可选，允许为空
    email = models.EmailField(blank=True, null=True, verbose_name='邮箱')

    class Meta:
        db_table = 'order_user'
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return self.username

    # 为了兼容现有代码，添加 user_type 属性
    @property
    def user_type(self):
        """兼容现有代码的 user_type 属性"""
        return 2 if self.is_superuser else 1

    @property
    def user_type_name(self):
        """兼容现有代码的 user_type_name 属性"""
        return '超级用户' if self.is_superuser else '普通用户'

    def is_super(self):
        """兼容现有代码的 is_super 方法"""
        return self.is_superuser


class Order(models.Model):
    # 订单编号（唯一）
    order_code = models.CharField(max_length=100, unique=True, verbose_name="订单编号")

    # 上传者
    upload_user = models.CharField(max_length=100, verbose_name="上传者")

    # OCR结果
    ocr_result = models.TextField(null=True, blank=True, verbose_name="OCR原始结果")

    # 提取的结构化数据（JSON格式）
    extracted_data = models.JSONField(default=dict, verbose_name="提取数据")

    # 图片信息
    img_filename = models.CharField(max_length=255, null=True, blank=True, verbose_name="图片文件名")
    img_path = models.CharField(max_length=500, null=True, blank=True, verbose_name="图片路径")

    # 系统字段
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'order_info'
        verbose_name = '订单'
        verbose_name_plural = '订单'
        ordering = ['-create_time']

    def __str__(self):
        return f"{self.order_code} - {self.get_product_name()}"

    def get_image_url(self):
        """获取图片访问URL"""
        if self.img_filename:
            return f"/media/order_images/{self.img_filename}"
        return None

    # 从 extracted_data 中获取字段的方法
    def get_product_name(self):
        return self.extracted_data.get('商品名称', self.extracted_data.get('product_name', ''))

    def get_specification(self):
        return self.extracted_data.get('商品规格', self.extracted_data.get('specification', ''))

    def get_product_price(self):
        return self.extracted_data.get('商品价格', self.extracted_data.get('product_price', ''))

    def get_payment_method(self):
        return self.extracted_data.get('支付方式', self.extracted_data.get('payment_method', ''))

    def get_actual_amount(self):
        return self.extracted_data.get('实付金额', self.extracted_data.get('actual_amount', ''))

    def get_logistics_company(self):
        return self.extracted_data.get('物流公司', self.extracted_data.get('logistics_company', ''))

    def get_tracking_number(self):
        return self.extracted_data.get('快递单号', self.extracted_data.get('tracking_number', ''))

    def get_order_time(self):
        return self.extracted_data.get('下单时间', self.extracted_data.get('order_time', ''))

    def get_group_time(self):
        return self.extracted_data.get('拼单时间', self.extracted_data.get('group_time', ''))

    def get_ship_time(self):
        return self.extracted_data.get('发货时间', self.extracted_data.get('ship_time', ''))

    def get_order_status(self):
        return self.extracted_data.get('订单状态', self.extracted_data.get('order_status', ''))

    def get_receiver(self):
        return self.extracted_data.get('收件人', self.extracted_data.get('receiver', ''))

    def get_contact(self):
        return self.extracted_data.get('联系方式', self.extracted_data.get('contact', ''))

    def get_shipping_address(self):
        return self.extracted_data.get('收货地址', self.extracted_data.get('shipping_address', ''))

    def get_shop_name(self):
        return self.extracted_data.get('店铺名称', self.extracted_data.get('shop_name', ''))

    def get_all_fields(self):
        """获取所有字段的字典"""
        return {
            'id': self.id,
            'order_code': self.order_code,
            'upload_user': self.upload_user,
            'product_name': self.get_product_name(),
            'specification': self.get_specification(),
            'product_price': self.get_product_price(),
            'payment_method': self.get_payment_method(),
            'actual_amount': self.get_actual_amount(),
            'logistics_company': self.get_logistics_company(),
            'tracking_number': self.get_tracking_number(),
            'order_time': self.get_order_time(),
            'group_time': self.get_group_time(),
            'ship_time': self.get_ship_time(),
            'order_status': self.get_order_status(),
            'receiver': self.get_receiver(),
            'contact': self.get_contact(),
            'shipping_address': self.get_shipping_address(),
            'shop_name': self.get_shop_name(),
            'img_filename': self.img_filename,
            'img_url': self.get_image_url(),
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            'update_time': self.update_time.strftime('%Y-%m-%d %H:%M:%S'),
            'extracted_data': self.extracted_data,
            'ocr_result': self.ocr_result,
        }