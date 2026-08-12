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