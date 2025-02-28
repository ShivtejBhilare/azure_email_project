from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import EmailForm, MXRecordForm, SPFRecordForm, DKIMRecordForm
from .models import EmailMessage, DNSRecord
from .services import AzureEmailService, DNSManager
from django.utils import timezone

@login_required
def index(request):
    recent_emails = EmailMessage.objects.filter(created_by=request.user).order_by('-sent_at')[:10]
    return render(request, 'email_app/index.html', {
        'recent_emails': recent_emails
    })

@login_required
def send_email(request):
    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            email = form.save(commit=False)
            email.created_by = request.user
            
            # Process recipients
            recipients = email.recipients.split(',')
            
            # Send email
            email_service = AzureEmailService()
            
            # Choose between SMTP and direct API
            use_direct_api = request.POST.get('use_direct_api', False)
            
            if use_direct_api:
                success, message = email_service.send_email_direct_api(
                    email.sender,
                    recipients,
                    email.subject,
                    email.body,
                    email.html_body
                )
            else:
                success, message = email_service.send_email(
                    email.sender,
                    recipients,
                    email.subject,
                    email.body,
                    email.html_body
                )
            
            # Update and save email record
            email.status = 'SENT' if success else 'FAILED'
            email.error_message = None if success else message
            email.save()
            
            if success:
                messages.success(request, 'Email sent successfully!')
            else:
                messages.error(request, f'Failed to send email: {message}')
            
            return redirect('index')
    else:
        form = EmailForm()
    
    return render(request, 'email_app/send_email.html', {
        'form': form
    })

@login_required
def dns_management(request):
    dns_manager = DNSManager()
    
    # Handle MX Record creation
    if request.method == 'POST' and 'create_mx' in request.POST:
        mx_form = MXRecordForm(request.POST)
        if mx_form.is_valid():
            mail_server = mx_form.cleaned_data['mail_server']
            priority = mx_form.cleaned_data['priority']
            
            success, message = dns_manager.create_mx_record(mail_server, priority)
            
            if success:
                DNSRecord.objects.create(
                    domain=dns_manager.domain,
                    record_type='MX',
                    value=f'Priority: {priority}, Server: {mail_server}'
                )
                messages.success(request, message)
            else:
                messages.error(request, message)
            
            return redirect('dns_management')
    else:
        mx_form = MXRecordForm()
    
    # Handle SPF Record creation
    if request.method == 'POST' and 'create_spf' in request.POST:
        spf_form = SPFRecordForm(request.POST)
        if spf_form.is_valid():
            allowed_servers = spf_form.cleaned_data['allowed_servers']
            
            success, message = dns_manager.create_spf_record(allowed_servers)
            
            if success:
                DNSRecord.objects.create(
                    domain=dns_manager.domain,
                    record_type='SPF',
                    value=f"v=spf1 {' '.join(allowed_servers)} -all"
                )
                messages.success(request, message)
            else:
                messages.error(request, message)
            
            return redirect('dns_management')
    else:
        spf_form = SPFRecordForm()
    
    # Handle DKIM Record creation
    if request.method == 'POST' and 'create_dkim' in request.POST:
        dkim_form = DKIMRecordForm(request.POST)
        if dkim_form.is_valid():
            selector = dkim_form.cleaned_data['selector']
            dkim_value = dkim_form.cleaned_data['dkim_value']
            
            success, message = dns_manager.create_dkim_record(selector, dkim_value)
            
            if success:
                DNSRecord.objects.create(
                    domain=dns_manager.domain,
                    record_type='DKIM',
                    value=f"Selector: {selector}, Value: {dkim_value[:30]}..."
                )
                messages.success(request, message)
            else:
                messages.error(request, message)
            
            return redirect('dns_management')
    else:
        dkim_form = DKIMRecordForm()
    
    # Handle DNS verification
    if request.method == 'POST' and 'verify_dns' in request.POST:
        success, results = dns_manager.verify_dns_records()
        
        if success:
            # Update verification status of records
            dns_records = DNSRecord.objects.filter(domain=dns_manager.domain)
            for record in dns_records:
                record.verified = True
                record.last_verified = timezone.now()
                record.save()
            
            messages.success(request, 'DNS verification completed')
        else:
            messages.error(request, 'DNS verification failed')
        
        return render(request, 'email_app/dns_management.html', {
            'mx_form': mx_form,
            'spf_form': spf_form,
            'dkim_form': dkim_form,
            'verification_results': results,
            'dns_records': DNSRecord.objects.filter(domain=dns_manager.domain).order_by('-created_at')
        })
    
    return render(request, 'email_app/dns_management.html', {
        'mx_form': mx_form,
        'spf_form': spf_form,
        'dkim_form': dkim_form,
        'dns_records': DNSRecord.objects.filter(domain=dns_manager.domain).order_by('-created_at')
    })

