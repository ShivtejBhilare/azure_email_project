# email_app/tests.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock

from .models import EmailMessage, DNSRecord
from .services import AzureEmailService, DNSManager

class AzureEmailServiceTests(TestCase):
    def setUp(self):
        # Setup test environment
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
    
    @patch('email_app.services.EmailClient')
    @patch('email_app.services.smtplib.SMTP')
    def test_send_email_smtp(self, mock_smtp, mock_email_client):
        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Create service
        service = AzureEmailService()
        
        # Override settings for testing
        service.smtp_server = 'test-smtp.example.com'
        service.smtp_port = 587
        service.smtp_username = 'test-user'
        service.smtp_password = 'test-password'
        
        # Test sending an email
        success, message = service.send_email(
            sender='noreply@example.com',
            recipients='recipient@example.com',
            subject='Test Email',
            body='This is a test email.',
            html_body='<p>This is a test email.</p>'
        )
        
        # Assert SMTP was called correctly
        mock_smtp.assert_called_once_with('test-smtp.example.com', 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with('test-user', 'test-password')
        mock_server.send_message.assert_called_once()
        
        # Assert success
        self.assertTrue(success)
    
    @patch('email_app.services.EmailClient')
    def test_send_email_direct_api(self, mock_email_client):
        # Mock EmailClient
        mock_client = MagicMock()
        mock_email_client.from_connection_string.return_value = mock_client
        
        # Mock poller
        mock_poller = MagicMock()
        mock_result = MagicMock()
        mock_result.message_id = 'test-message-id'
        mock_poller.result.return_value = mock_result
        mock_client.begin_send.return_value = mock_poller
        
        # Create service
        service = AzureEmailService()
        service.email_client = mock_client
        
        # Test sending an email
        success, message = service.send_email_direct_api(
            sender='noreply@example.com',
            recipients='recipient@example.com',
            subject='Test Email',
            body='This is a test email.',
            html_body='<p>This is a test email.</p>'
        )
        
        # Assert API was called correctly
        mock_client.begin_send.assert_called_once()
        mock_poller.result.assert_called_once()
        
        # Assert success
        self.assertTrue(success)


class DNSManagerTests(TestCase):
    @patch('email_app.services.dns.resolver.resolve')
    def test_verify_dns_records(self, mock_resolve):
        # Mock DNS resolver
        mock_mx_records = [MagicMock()]
        mock_mx_records[0].preference = 10
        mock_mx_records[0].exchange = 'mail.example.com'
        
        mock_txt_records = [MagicMock()]
        mock_txt_string = b'v=spf1 include:communication.azure.com -all'
        mock_txt_records[0].strings = [mock_txt_string]
        
        # Configure mock to return different values for different calls
        mock_resolve.side_effect = lambda domain, record_type: (
            mock_mx_records if record_type == 'MX' else mock_txt_records
        )
        
        # Create DNS manager
        manager = DNSManager()
        manager.domain = 'example.com'
        
        # Test verifying DNS records
        success, results = manager.verify_dns_records()
        
        # Assert resolver was called correctly
        self.assertEqual(mock_resolve.call_count, 2)
        
        # Assert success
        self.assertTrue(success)
        self.assertTrue(any('MX records' in result for result in results))
        self.assertTrue(any('SPF record' in result for result in results))


class ViewTests(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create test client
        self.client = Client()
        self.client.login(username='testuser', password='testpassword')
    
    def test_index_view(self):
        # Test index view
        response = self.client.get(reverse('index'))
        
        # Assert response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'email_app/index.html')
    
    @patch('email_app.views.AzureEmailService')
    def test_send_email_view(self, mock_email_service):
        # Mock email service
        mock_service = MagicMock()
        mock_service.send_email.return_value = (True, 'Email sent successfully')
        mock_email_service.return_value = mock_service
        
        # Test sending an email
        response = self.client.post(reverse('send_email'), {
            'sender': 'noreply@example.com',
            'recipients': 'recipient@example.com',
            'subject': 'Test Email',
            'body': 'This is a test email.',
            'html_body': '<p>This is a test email.</p>'
        })
        
        # Assert redirect
        self.assertEqual(response.status_code, 302)
        
        # Assert email was created
        self.assertEqual(EmailMessage.objects.count(), 1)
        email = EmailMessage.objects.first()
        self.assertEqual(email.subject, 'Test Email')
        self.assertEqual(email.sender, 'noreply@example.com')
        self.assertEqual(email.status, 'SENT')
    
    @patch('email_app.views.DNSManager')
    def test_dns_management_view(self, mock_dns_manager):
        # Mock DNS manager
        mock_manager = MagicMock()
        mock_manager.create_mx_record.return_value = (True, 'MX record created successfully')
        mock_dns_manager.return_value = mock_manager
        
        # Test creating an MX record
        response = self.client.post(reverse('dns_management'), {
            'create_mx': True,
            'mail_server': 'mail.example.com',
            'priority': '10'
        })
        
        # Assert redirect
        self.assertEqual(response.status_code, 302)
        
        # Check if DNS record was created
        mock_manager.create_mx_record.assert_called_once_with('mail.example.com', 10)


class ModelTests(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
    
    def test_email_message_model(self):
        # Create test email message
        email = EmailMessage.objects.create(
            sender='noreply@example.com',
            recipients='recipient@example.com',
            subject='Test Email',
            body='This is a test email.',
            html_body='<p>This is a test email.</p>',
            status='SENT',
            created_by=self.user
        )
        
        # Assert fields
        self.assertEqual(email.sender, 'noreply@example.com')
        self.assertEqual(email.recipients, 'recipient@example.com')
        self.assertEqual(email.subject, 'Test Email')
        self.assertEqual(email.body, 'This is a test email.')
        self.assertEqual(email.html_body, '<p>This is a test email.</p>')
        self.assertEqual(email.status, 'SENT')
        self.assertEqual(email.created_by, self.user)
    
    def test_dns_record_model(self):
        # Create test DNS record
        dns_record = DNSRecord.objects.create(
            domain='example.com',
            record_type='MX',
            value='Priority: 10, Server: mail.example.com'
        )
        
        # Assert fields
        self.assertEqual(dns_record.domain, 'example.com')
        self.assertEqual(dns_record.record_type, 'MX')
        self.assertEqual(dns_record.value, 'Priority: 10, Server: mail.example.com')
        self.assertFalse(dns_record.verified)
        self.assertIsNone(dns_record.last_verified)