from django.contrib import admin
from .models import FactorySetting

# অ্যাডমিন প্যানেলে FactorySetting যুক্ত করা হলো
admin.site.register(FactorySetting)
from django.contrib import admin
from .models import OrderMaster, OrderPO, OrderColor, OrderSizeBreakdown, PageApprover, SystemNotification

# ডাটাবেজে সুন্দর করে টেবিল আকারে দেখার জন্য কাস্টম এডমিন প্যানেল
class OrderMasterAdmin(admin.ModelAdmin):
    list_display = ('job_no', 'buyer', 'style_no', 'total_order_qty', 'status', 'created_at', 'created_by')
    search_fields = ('job_no', 'style_no')

class OrderSizeBreakdownAdmin(admin.ModelAdmin):
    list_display = ('order', 'po', 'color', 'size_name', 'qty', 'sort_order')
    list_filter = ('order', 'po', 'color')

# টেবিলগুলো এডমিন প্যানেলে রেজিস্টার করা হলো
admin.site.register(OrderMaster, OrderMasterAdmin)
admin.site.register(OrderPO)
admin.site.register(OrderColor)
admin.site.register(OrderSizeBreakdown, OrderSizeBreakdownAdmin)
admin.site.register(PageApprover)
admin.site.register(SystemNotification)