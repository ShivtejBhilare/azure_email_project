# email_app/admin.py
from django.contrib import admin
from .models import EmailMessage, DNSRecord

@admin.register(EmailMessage)
class EmailMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'sender', 'recipients_summary', 'sent_at', 'status', 'created_by')
    list_filter = ('status', 'sent_at', 'created_by')
    search_fields = ('subject', 'sender', 'recipients', 'body')
    readonly_fields = ('sent_at',)
    date_hierarchy = 'sent_at'
    
    def recipients_summary(self, obj):
        recipients = obj.recipients.split(',')
        if len(recipients) > 2:
            return f"{recipients[0]}, {recipients[1]} (+{len(recipients)-2} more)"
        return obj.recipients

@admin.register(DNSRecord)
class DNSRecordAdmin(admin.ModelAdmin):
    list_display = ('domain', 'record_type', 'created_at', 'verified', 'last_verified')
    list_filter = ('record_type', 'verified', 'domain')
    search_fields = ('domain', 'value')
    readonly_fields = ('created_at', 'last_verified')
    date_hierarchy = 'created_at'