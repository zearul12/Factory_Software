from django.db import models
from django.contrib.auth.models import User

# --- Settings Models ---
class FactorySetting(models.Model):
    factory_name = models.CharField(max_length=200, default="Smart Factory System")
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    app_version = models.CharField(max_length=20, default="Version 1.0.0")
    copyright_text = models.CharField(max_length=200, default="© 2026 Pandora Sweaters Ltd.")
    developer_credit = models.CharField(max_length=200, default="Designed & Developed by Zearul")
    def __str__(self): return self.factory_name

class AppSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    def __str__(self): return self.key

# --- Master Data Models ---
class Buyer(models.Model):
    buyer_name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.buyer_name

class KnitMachine(models.Model):
    brand_name = models.CharField(max_length=100)
    gauge = models.CharField(max_length=20, blank=True)
    line_no = models.CharField(max_length=50)
    machine_no = models.CharField(max_length=50)
    line_mc_no = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.line_mc_no

# --- Auth & Notifications ---
class PageApprover(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    page_name = models.CharField(max_length=100)
    def __str__(self): return f"{self.user.username} - {self.page_name}"

class SystemNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.title

# --- NEW: Knitting Order Master Models ---
class KnittingOrder(models.Model):
    system_id = models.CharField(max_length=20, unique=True) # Auto Generate (00000001)
    job_no = models.CharField(max_length=50)
    buyer = models.ForeignKey(Buyer, on_delete=models.PROTECT)
    style_no = models.CharField(max_length=100)
    po_numbers = models.TextField()
    
    plan_pct = models.IntegerField(default=0)
    gauge = models.CharField(max_length=50, blank=True, null=True)
    kcd_date = models.DateField()
    operations = models.TextField()
    
    # Summary Totals
    total_color = models.IntegerField(default=0)
    total_lot = models.IntegerField(default=0)
    total_size = models.IntegerField(default=0)
    total_order_qty = models.IntegerField(default=0)
    total_plan_qty = models.IntegerField(default=0)
    total_weight_lbs = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    avg_weight_dz = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    status = models.CharField(max_length=20, default='Pending')
    reject_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_fields = models.TextField(blank=True, null=True)

    def __str__(self): return self.job_no

class KnittingColor(models.Model):
    order = models.ForeignKey(KnittingOrder, on_delete=models.CASCADE, related_name='colors')
    color_name = models.CharField(max_length=100)
    lots = models.TextField() # কমা দিয়ে সেভ হবে (A15, B20)

class KnittingSize(models.Model):
    color = models.ForeignKey(KnittingColor, on_delete=models.CASCADE, related_name='sizes')
    size_name = models.CharField(max_length=50)
    order_qty = models.IntegerField(default=0)
    plan_qty = models.IntegerField(default=0)
    size_wt_gm = models.IntegerField(default=0)
    total_lbs = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sort_order = models.IntegerField(default=0)