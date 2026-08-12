from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    employee_id = models.CharField(max_length=50, blank=True, null=True) # নতুন ফিল্ড
    company_name = models.CharField(max_length=150, blank=True, null=True)
    designation = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    is_active_user = models.BooleanField(default=True)

    def __str__(self):
        return self.user.username

class PagePermission(models.Model):
    ACCESS_CHOICES = (
        ('Editor', 'Editor'),
        ('Viewer', 'Viewer'),
        ('Not', 'Not'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='page_permissions')
    page_name = models.CharField(max_length=100)
    access_level = models.CharField(max_length=20, choices=ACCESS_CHOICES, default='Not')

    def __str__(self):
        return f"{self.user.username} - {self.page_name} - {self.access_level}"