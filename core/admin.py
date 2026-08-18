from django.contrib import admin
from .models import (
    FactorySetting, AppSetting, Buyer, KnitMachine,
    PageApprover, SystemNotification,
    KnittingOrder, KnittingColor, KnittingSize
)

# Basic Settings & Master Data
admin.site.register(FactorySetting)
admin.site.register(AppSetting)
admin.site.register(Buyer)
admin.site.register(KnitMachine)
admin.site.register(PageApprover)
admin.site.register(SystemNotification)

# Order Models with customized display
class KnittingOrderAdmin(admin.ModelAdmin):
    list_display = ('system_id', 'job_no', 'buyer', 'style_no', 'total_order_qty', 'status', 'created_at')
    search_fields = ('system_id', 'job_no', 'style_no')
    list_filter = ('status', 'buyer')

class KnittingSizeAdmin(admin.ModelAdmin):
    list_display = ('color', 'size_name', 'order_qty', 'plan_qty', 'total_lbs')

admin.site.register(KnittingOrder, KnittingOrderAdmin)
admin.site.register(KnittingColor)
admin.site.register(KnittingSize, KnittingSizeAdmin)