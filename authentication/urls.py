from django.urls import path
from .views import login_view, dashboard_view, logout_view, user_management, update_user_ajax

urlpatterns = [
    path('', login_view, name='login'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('logout/', logout_view, name='logout'),
    
    # User Management
    path('users/', user_management, name='user_management'),
    path('users/update-ajax/', update_user_ajax, name='update_user_ajax'),
]