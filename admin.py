from django.contrib import admin

# Register your models here.
from .models import user_login, user_details
from .models import storage_details, file_index, user_file_map, feedback
from .models import support_ticket, notification

admin.site.register(user_login)
admin.site.register(user_details)
admin.site.register(storage_details)
admin.site.register(file_index)
admin.site.register(user_file_map)
admin.site.register(feedback)

class support_ticket_admin(admin.ModelAdmin):
    list_display = ('id', 'user_name', 'issue_type', 'priority', 'status', 'created_at')
    list_filter = ('priority', 'status', 'issue_type')
    search_fields = ('subject', 'message', 'user_name', 'user_email')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('User Information', {
            'fields': ('user_id', 'user_name', 'user_email')
        }),
        ('Ticket Details', {
            'fields': ('issue_type', 'subject', 'message', 'priority')
        }),
        ('Status', {
            'fields': ('status', 'created_at')
        }),
    )

admin.site.register(support_ticket, support_ticket_admin)

class notification_admin(admin.ModelAdmin):
    list_display = ('id', 'user_id', 'ticket_id', 'message', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('message',)

admin.site.register(notification, notification_admin)