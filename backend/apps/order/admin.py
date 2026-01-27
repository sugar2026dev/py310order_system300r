from django.contrib import admin
from .models import User, Order


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'get_user_type', 'date_joined', 'is_staff', 'is_superuser')
    list_filter = ('is_superuser', 'is_staff', 'is_active')
    search_fields = ('username', 'email')
    ordering = ('-date_joined',)

    def get_user_type(self, obj):
        return obj.user_type_name

    get_user_type.short_description = '用户类型'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_code', 'upload_user', 'create_time')
    list_filter = ('create_time',)
    search_fields = ('order_code', 'upload_user')
    ordering = ('-create_time',)
    readonly_fields = ('create_time', 'update_time')