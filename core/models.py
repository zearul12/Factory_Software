from django.db import models

class FactorySetting(models.Model):
    factory_name = models.CharField(max_length=200, default="Smart Factory System")
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    # ফুটারের জন্য নতুন ফিল্ড
    app_version = models.CharField(max_length=20, default="Version 1.0.0")
    copyright_text = models.CharField(max_length=200, default="© 2026 Pandora Sweaters Ltd.")
    developer_credit = models.CharField(max_length=200, default="Designed & Developed by IE_Zearul")

    def __str__(self):
        return self.factory_name

from django.db import models

# আগের FactorySetting কোডটি যেমন আছে তেমনই থাকুক...
class FactorySetting(models.Model):
    factory_name = models.CharField(max_length=200, default="Smart Factory System")
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    app_version = models.CharField(max_length=20, default="Version 1.0.0")
    copyright_text = models.CharField(max_length=200, default="© 2026 Pandora Sweaters Ltd.")
    developer_credit = models.CharField(max_length=200, default="Designed & Developed by Zearul")
    def __str__(self): return self.factory_name

# --- আপনার আইডিয়া অনুযায়ী নতুন ডায়নামিক সেটিংস টেবিল ---
class AppSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.key

from django.db import models

# ... (আগের FactorySetting এবং AppSetting কোডগুলো থাকবে) ...

class Buyer(models.Model):
    buyer_name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True) # Active নাকি Hold তা বোঝার জন্য
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.buyer_name
    # ... (আগের Buyer কোডগুলোর নিচে এটি দিন) ...

class KnitMachine(models.Model):
    brand_name = models.CharField(max_length=100)
    gauge = models.CharField(max_length=20, blank=True)
    line_no = models.CharField(max_length=50)
    machine_no = models.CharField(max_length=50)
    line_mc_no = models.CharField(max_length=100, unique=True) # Ex: SH-A-01
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.line_mc_no

from django.contrib.auth.models import User

# ... (আগের KnitMachine এবং অন্যান্য মডেলগুলো থাকবে) ...

# ১. অ্যাপ্রুভার (Approver) ম্যানেজমেন্ট টেবিল
class PageApprover(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    page_name = models.CharField(max_length=100) # Ex: 'Confirm Order Entry'

    def __str__(self):
        return f"{self.user.username} - {self.page_name}"

# ২. নোটিফিকেশন (Notification) টেবিল
class SystemNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE) # যার কাছে নোটিফিকেশন যাবে
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# ৩. মূল অর্ডার মাস্টার টেবিল
class OrderMaster(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Hold', 'Hold'),
    )
    job_no = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=100)
    buyer = models.ForeignKey(Buyer, on_delete=models.PROTECT) # Buyer ডিলিট হলে অর্ডার ডিলিট হবে না
    style_no = models.CharField(max_length=100)
    development_mc = models.CharField(max_length=100)
    style_description = models.TextField(blank=True, null=True)
    additional_process = models.TextField(blank=True, null=True) # কমা দিয়ে সেভ হবে
    shipment_date = models.DateField()
    file_handover_date = models.DateField()
    avg_fob = models.DecimalField(max_digits=10, decimal_places=2)
    discounted_fob = models.DecimalField(max_digits=10, decimal_places=2)
    remarks = models.TextField(blank=True, null=True)
    total_order_qty = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    reject_reason = models.TextField(blank=True, null=True) # রিজেক্ট হলে কারণ লেখার জন্য
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    changed_fields = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.job_no

# ৪. অর্ডারের কালার (Color) টেবিল
class OrderColor(models.Model):
    order = models.ForeignKey(OrderMaster, on_delete=models.CASCADE, related_name='colors')
    color_name = models.CharField(max_length=100)

# ৫. অর্ডারের পিও (PO) টেবিল
class OrderPO(models.Model):
    order = models.ForeignKey(OrderMaster, on_delete=models.CASCADE, related_name='pos')
    po_number = models.CharField(max_length=100)

# ৬. সাইজ ব্রেকডাউন ম্যাট্রিক্স (সবচেয়ে ইম্পর্টেন্ট)
class OrderSizeBreakdown(models.Model):
    order = models.ForeignKey(OrderMaster, on_delete=models.CASCADE, related_name='size_breakdowns')
    po = models.ForeignKey(OrderPO, on_delete=models.CASCADE)
    color = models.ForeignKey(OrderColor, on_delete=models.CASCADE)
    size_name = models.CharField(max_length=50)
    qty = models.IntegerField(default=0)
    sort_order = models.IntegerField(default=0) # ম্যাজিক ফিল্ড: কাস্টম সাইজ সিরিয়াল ধরে রাখার জন্য!