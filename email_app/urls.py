from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('send-email/', views.send_email, name='send_email'),
    path('dns-management/', views.dns_management, name='dns_management'),
]


# Now let's create the project settings
# azure_email_project/settings.py (partial, add these to Django default settings)

# Azure Communication Services settings
AZURE_COMMUNICATION_CONNECTION_STRING = 'your-connection-string-here'
# Alternative to connection string:
# AZURE_COMMUNICATION_API_KEY = 'your-api-key-here'
# AZURE_COMMUNICATION_ENDPOINT = 'your-endpoint-here'

# Email settings
EMAIL_HOST = 'smtp.azurecomm.net'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'your-azure-comm-username'
EMAIL_HOST_PASSWORD = 'your-azure-comm-password'
EMAIL_USE_TLS = True
EMAIL_DOMAIN = 'example.com'


# Main project urls.py
# azure_email_project/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('email_app.urls')),
    # Add this if you're using Django's auth system
    path('accounts/', include('django.contrib.auth.urls')),
]
