from django.contrib import admin
from django.urls import path
from authentication.views import login_view, dashboard_view, logout_view, user_management, update_user_ajax
from core.views import system_settings_view  # নতুন ইম্পোর্ট

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_view, name='login'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('logout/', logout_view, name='logout'),
    path('users/', user_management, name='user_management'),
    path('users/update-ajax/', update_user_ajax, name='update_user_ajax'),
    
    # সিস্টেম সেটিংসের নতুন লিংক
    path('settings/', system_settings_view, name='system_settings'), 
]