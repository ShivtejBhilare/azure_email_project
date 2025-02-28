import os
import smtplib
import dns.resolver
import dns.zone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from azure.communication.email import EmailClient
from azure.core.credentials import AzureKeyCredential
from django.conf import settings

class AzureEmailService:
    def __init__(self):
        """Initialize Azure Email Service using settings from Django"""
        connection_string = settings.AZURE_COMMUNICATION_CONNECTION_STRING
        api_key = getattr(settings, 'AZURE_COMMUNICATION_API_KEY', None)
        endpoint = getattr(settings, 'AZURE_COMMUNICATION_ENDPOINT', None)
        
        if connection_string:
            self.email_client = EmailClient.from_connection_string(connection_string)
        elif api_key and endpoint:
            self.email_client = EmailClient(endpoint, AzureKeyCredential(api_key))
        else:
            raise ValueError("Azure Communication Service credentials not properly configured in settings")
        
        # SMTP settings from Django settings
        self.smtp_server = settings.EMAIL_HOST
        self.smtp_port = settings.EMAIL_PORT
        self.smtp_username = settings.EMAIL_HOST_USER
        self.smtp_password = settings.EMAIL_HOST_PASSWORD
    
    def send_email(self, sender, recipients, subject, body, html_body=None, attachments=None):
        """Send email using Azure Communication Services SMTP"""
        try:
            # Create the email message
            message = MIMEMultipart('alternative')
            message['From'] = sender
            message['To'] = ", ".join(recipients) if isinstance(recipients, list) else recipients
            message['Subject'] = subject
            
            # Attach text body
            message.attach(MIMEText(body, 'plain'))
            
            # Attach HTML body if provided
            if html_body:
                message.attach(MIMEText(html_body, 'html'))
            
            # Send using Azure Communication Services SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Secure the connection
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(message)
            
            return True, "Email sent successfully"
        except Exception as e:
            return False, f"Failed to send email: {str(e)}"
    
    def send_email_direct_api(self, sender, recipients, subject, body, html_body=None):
        """Send email using Azure Communication Services direct API"""
        try:
            if isinstance(recipients, str):
                recipients = [recipients]
                
            # Create recipient list in the format expected by Azure
            to_recipients = [{"address": r} for r in recipients]
            
            # Create the email content
            content = {
                "subject": subject,
                "plainText": body,
            }
            
            if html_body:
                content["html"] = html_body
                
            # Send using direct API
            poller = self.email_client.begin_send(
                sender=sender,
                recipients={"to": to_recipients},
                content=content
            )
            
            result = poller.result()
            return True, f"Email sent successfully. Message ID: {result.message_id}"
        except Exception as e:
            return False, f"Failed to send email via direct API: {str(e)}"


class DNSManager:
    def __init__(self):
        """Initialize DNS Manager"""
        self.domain = settings.EMAIL_DOMAIN
    
    def create_mx_record(self, mail_server, priority=10):
        """Create MX record for the domain"""
        try:
            # In a real implementation, you would call your DNS provider's API here
            # For demonstration, we're just returning success
            return True, f"Created MX record for {self.domain} pointing to {mail_server} with priority {priority}"
        except Exception as e:
            return False, f"Failed to create MX record: {str(e)}"
    
    def create_spf_record(self, allowed_servers):
        """Create SPF record for domain authentication"""
        try:
            spf_record = f"v=spf1 {' '.join(allowed_servers)} -all"
            # In a real implementation, you would call your DNS provider's API here
            return True, f"Created SPF record for {self.domain}: {spf_record}"
        except Exception as e:
            return False, f"Failed to create SPF record: {str(e)}"
    
    def create_dkim_record(self, selector, dkim_value):
        """Create DKIM record for domain authentication"""
        try:
            # In a real implementation, you would call your DNS provider's API here
            return True, f"Created DKIM record for {selector}._domainkey.{self.domain}"
        except Exception as e:
            return False, f"Failed to create DKIM record: {str(e)}"
    
    def verify_dns_records(self):
        """Verify that DNS records exist and are properly configured"""
        try:
            results = []
            
            # Check MX records
            try:
                mx_records = dns.resolver.resolve(self.domain, 'MX')
                mx_results = []
                for mx in mx_records:
                    mx_results.append(f"Priority: {mx.preference}, Server: {mx.exchange}")
                results.append(f"Found {len(mx_records)} MX records for {self.domain}")
                results.extend(mx_results)
            except Exception as e:
                results.append(f"Error checking MX records: {str(e)}")
            
            # Check SPF records
            try:
                txt_records = dns.resolver.resolve(self.domain, 'TXT')
                spf_found = False
                for txt in txt_records:
                    for string in txt.strings:
                        if string.startswith(b'v=spf1'):
                            spf_found = True
                            results.append(f"Found SPF record: {string.decode('utf-8')}")
                
                if not spf_found:
                    results.append("No SPF record found")
            except Exception as e:
                results.append(f"Error checking SPF records: {str(e)}")
            
            return True, results
        except Exception as e:
            return False, [f"Error verifying DNS records: {str(e)}"]


# Now let's create models.py to store email and DNS record information
# email_app/models.py

from django.db import models
from django.contrib.auth.models import User

class EmailMessage(models.Model):
    sender = models.EmailField()
    recipients = models.TextField()  # Store as comma-separated emails
    subject = models.CharField(max_length=255)
    body = models.TextField()
    html_body = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50)
    error_message = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.subject} - {self.sent_at}"

class DNSRecord(models.Model):
    RECORD_TYPES = (
        ('MX', 'MX Record'),
        ('SPF', 'SPF Record'),
        ('DKIM', 'DKIM Record'),
    )
    
    domain = models.CharField(max_length=255)
    record_type = models.CharField(max_length=10, choices=RECORD_TYPES)
    value = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
    last_verified = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.record_type} for {self.domain} - {self.created_at}"