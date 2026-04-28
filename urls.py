from django.urls import path, include
from django.contrib import admin
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('index', views.index, name='index'),
    path('about', views.about, name='about'),
    path('contact', views.contact, name='contact'),
    path('check-username/', views.check_username, name='check_username'),
    
    # ADMIN URLs - With trailing slashes
    path('admin_login/', views.admin_login, name='admin_login'),
    path('admin_changepassword/', views.admin_changepassword, name='admin_changepassword'),
    path('admin_logout/', views.admin_logout, name='admin_logout'),
    path('admin_home/', views.admin_home, name='admin_home'),
    path('admin_user_view/', views.admin_user_view, name='admin_user_view'),
    path('admin_user_delete/', views.admin_user_delete, name='admin_user_delete'),
    path('admin_user_feedback_view/', views.admin_user_feedback_view, name='admin_user_feedback_view'),
    path('admin_support_tickets/', views.admin_support_tickets_view, name='admin_support_tickets'),
    path('admin_ticket_update/', views.admin_ticket_update, name='admin_ticket_update'),
    
    # USER URLs - With trailing slashes
    path('user_login/', views.user_login_check, name='user_login'),
    path('user_logout/', views.user_logout, name='user_logout'),
    path('user_home/', views.user_home, name='user_home'),
    path('user_details_add/', views.user_details_add, name='user_details_add'),
    path('user_details_update/', views.user_details_update, name='user_details_update'),
    path('user_changepassword/', views.user_changepassword, name='user_changepassword'),
    path('user_file_store_add/', views.user_file_store_add, name='user_file_store_add'),
    path('user_file_store_view/', views.user_file_store_view, name='user_file_store_view'),
    path('user_file_store_delete/', views.user_file_store_delete, name='user_file_store_delete'),
    path('user_file_store_download/', views.user_file_store_download, name='user_file_store_download'),
    path('user_file_search/', views.user_file_search, name='user_file_search'),
    path('user_storage_view/', views.user_storage_view, name='user_storage_view'),
    path('user_feedback_add/', views.user_feedback_add, name='user_feedback_add'),
    path('user_feedback_view/', views.user_feedback_view, name='user_feedback_view'),
    path('user_feedback_delete/', views.user_feedback_delete, name='user_feedback_delete'),
    path('user_notifications/', views.user_notifications, name='user_notifications'),
    path('user_notification_count/', views.user_notification_count_api, name='user_notification_count'),
    
    # AJAX endpoints
    path('get-ticket-count/', views.get_ticket_count, name='get_ticket_count'),
    path('get-dashboard-stats/', views.get_dashboard_stats, name='get_dashboard_stats'),
    path('user_storage_stats/', views.user_storage_stats, name='user_storage_stats'),
    path('mark-notification-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    
    # Ticket URLs
    path('user_tickets/', views.user_tickets, name='user_tickets'),
    path('user_ticket_detail/<int:ticket_id>/', views.user_ticket_detail, name='user_ticket_detail'),
    path('user_create_ticket/', views.user_create_ticket, name='user_create_ticket'),
    
    # Profile and Search AJAX endpoints
    path('user_profile_data/', views.user_profile_data, name='user_profile_data'),
    path('user_file_search_ajax/', views.user_file_search_ajax, name='user_file_search_ajax'),

  # ===== FILE SHARING URLs =====
    path('my_shared_links/', views.my_shared_links, name='my_shared_links'),
    path('generate_share_link/<int:file_id>/', views.generate_share_link, name='generate_share_link'),
    path('revoke_share_link/<int:link_id>/', views.revoke_share_link, name='revoke_share_link'),
    path('share/<str:token>/', views.view_shared_file, name='view_shared_file'),
    path('share/download/<str:token>/', views.download_shared_file, name='download_shared_file'),
]