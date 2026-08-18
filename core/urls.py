from django.urls import path
from .views import (
    system_settings_view, buyer_entry_view, update_buyer_ajax, 
    knit_machine_entry_view, update_knit_machine_ajax, 
    confirm_order_entry_view, search_buyer_ajax, 
    save_confirm_order_ajax, get_order_details_ajax, 
    get_notifications_ajax, search_old_job_ajax, order_action_ajax
)

urlpatterns = [
    # Settings
    path('settings/', system_settings_view, name='system_settings'),
    
    # Buyer Entry
    path('planning/buyers/', buyer_entry_view, name='buyer_entry'),
    path('planning/buyers/ajax/', update_buyer_ajax, name='update_buyer_ajax'),

    # Knit Machine Entry
    path('hr-admin/knit-machine/', knit_machine_entry_view, name='knit_machine_entry'),
    path('hr-admin/knit-machine/ajax/', update_knit_machine_ajax, name='update_knit_machine_ajax'),

    # Order Management
    path('marketing/confirm-order/', confirm_order_entry_view, name='confirm_order_entry'),
    path('marketing/ajax/search-buyer/', search_buyer_ajax, name='search_buyer_ajax'),
    path('marketing/ajax/save-order/', save_confirm_order_ajax, name='save_confirm_order_ajax'),
    path('marketing/ajax/get-order/<str:job_no>/', get_order_details_ajax, name='get_order_details_ajax'),
    path('marketing/ajax/search-job/', search_old_job_ajax, name='search_old_job_ajax'),
    path('marketing/ajax/order-action/', order_action_ajax, name='order_action_ajax'),
    
    # Notifications
    path('ajax/notifications/', get_notifications_ajax, name='get_notifications_ajax'),
]