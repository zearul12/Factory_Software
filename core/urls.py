from django.urls import path
from .views import (
    system_settings_view, 
    buyer_entry_view, update_buyer_ajax, 
    knit_machine_entry_view, update_knit_machine_ajax, 
    operator_entry_view, save_operator_ajax, delete_operator_ajax,
    get_notifications_ajax,
    knitting_order_entry_view, search_knitting_job_ajax, 
    save_knitting_order_ajax, get_knitting_order_details_ajax, knitting_order_action_ajax, bulk_delete_operator_ajax, bulk_save_operator_ajax,
    order_issue_entry_view, search_issue_job_ajax, get_issue_job_details_ajax,
    search_issue_operator_ajax, save_order_issue_ajax, search_tc_for_issue_ajax,
    get_single_issue_details_ajax, delete_order_issue_ajax,get_machine_line_ajax
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

    # Operator Entry (HR-Admin)
    path('hr-admin/operator-entry/', operator_entry_view, name='operator_entry'),
    path('hr-admin/operator-entry/ajax/save/', save_operator_ajax, name='save_operator_ajax'),
    path('hr-admin/operator-entry/ajax/delete/', delete_operator_ajax, name='delete_operator_ajax'),
    path('hr-admin/operator-entry/ajax/bulk-delete/', bulk_delete_operator_ajax, name='bulk_delete_operator_ajax'),
    path('hr-admin/operator-entry/ajax/bulk-save/', bulk_save_operator_ajax, name='bulk_save_operator_ajax'),

    # Notifications
    path('ajax/notifications/', get_notifications_ajax, name='get_notifications_ajax'),
    
    # Production Department -> Knitting Section Master Entry
    path('production/knitting/order-entry/', knitting_order_entry_view, name='knitting_order_entry'),
    path('production/knitting/ajax/search-job/', search_knitting_job_ajax, name='search_knitting_job_ajax'),
    path('production/knitting/ajax/save-order/', save_knitting_order_ajax, name='save_knitting_order_ajax'),
    path('production/knitting/ajax/get-order/<str:sys_id>/', get_knitting_order_details_ajax, name='get_knitting_order_details_ajax'),
    path('production/knitting/ajax/order-action/', knitting_order_action_ajax, name='knitting_order_action_ajax'),

    # Production Department -> Order Issue (Bundle)
    path('production/knitting/order-issue/', order_issue_entry_view, name='order_issue_entry'),
    path('production/knitting/order-issue/ajax/search-job/', search_issue_job_ajax, name='search_issue_job_ajax'),
    path('production/knitting/order-issue/ajax/get-job/<str:sys_id>/', get_issue_job_details_ajax, name='get_issue_job_details_ajax'),
    path('production/knitting/order-issue/ajax/search-operator/', search_issue_operator_ajax, name='search_issue_operator_ajax'),
    path('production/knitting/order-issue/ajax/search-tc/', search_tc_for_issue_ajax, name='search_tc_for_issue_ajax'),
    path('production/knitting/order-issue/ajax/get-tc/<str:tc_no>/', get_single_issue_details_ajax, name='get_single_issue_details_ajax'),
    path('production/knitting/order-issue/ajax/save/', save_order_issue_ajax, name='save_order_issue_ajax'),
    path('production/knitting/order-issue/ajax/delete/', delete_order_issue_ajax, name='delete_order_issue_ajax'),
    path('production/knitting/order-issue/ajax/get-machine-line/', get_machine_line_ajax, name='get_machine_line_ajax'),
]