from django.db import models

class FactorySetting(models.Model):
    # ফ্যাক্টরির নাম, ফোন নাম্বার এবং ঠিকানা সেভ করার জায়গা
    factory_name = models.CharField(max_length=200, default="Smart Factory System")
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.factory_name