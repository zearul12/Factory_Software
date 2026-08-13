from django.contrib import admin
from django.urls import path
from authentication.views import login_view, dashboard_view, logout_view, user_management, update_user_ajax
# core.views থেকে ফাংশনগুলো ইম্পোর্ট করা হলো
from core.views import system_settings_view, buyer_entry_view, update_buyer_ajax, knit_machine_entry_view, update_knit_machine_ajax, confirm_order_entry_view, search_buyer_ajax

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_view, name='login'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('logout/', logout_view, name='logout'),
    
    path('users/', user_management, name='user_management'),
    path('users/update-ajax/', update_user_ajax, name='update_user_ajax'),
    
    path('settings/', system_settings_view, name='system_settings'), 
    
    # Buyer Entry এর নতুন লিংক
    path('planning/buyers/', buyer_entry_view, name='buyer_entry'),
    path('planning/buyers/ajax/', update_buyer_ajax, name='update_buyer_ajax'),
    # Knit Machine Entry
    path('hr-admin/knit-machine/', knit_machine_entry_view, name='knit_machine_entry'),
    path('hr-admin/knit-machine/ajax/', update_knit_machine_ajax, name='update_knit_machine_ajax'),
    # Order Management
    path('marketing/confirm-order/', confirm_order_entry_view, name='confirm_order_entry'),
    path('marketing/ajax/search-buyer/', search_buyer_ajax, name='search_buyer_ajax'),
]