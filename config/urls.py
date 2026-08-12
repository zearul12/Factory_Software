from django.contrib import admin
from django.urls import path
from authentication.views import login_view, dashboard_view, logout_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_view, name='login'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('logout/', logout_view, name='logout'), # নতুন লগআউট লিংক
]