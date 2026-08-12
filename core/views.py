from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import AppSetting

def is_superadmin(user):
    return user.is_superuser

@login_required(login_url='login')
@user_passes_test(is_superadmin, login_url='dashboard')
def system_settings_view(request):
    # এই ৪টি মূল সেটিং কখনো ডিলিট করা যাবে না
    core_keys = ['factory_name', 'app_version', 'copyright_text', 'developer_credit']
    
    # পেজ লোড হওয়ার সময় ডিফল্ট ডাটা চেক করা
    default_keys = [
        ('factory_name', 'Pandora Sweaters Ltd.', 'Name of the Factory/Company'),
        ('app_version', 'Version 1.0.0', 'Current software version'),
        ('copyright_text', '© 2026 Pandora Sweaters Ltd.', 'Footer copyright text'),
        ('developer_credit', 'Designed & Developed by Zearul', 'Developer info in footer')
    ]
    for k, v, d in default_keys:
        AppSetting.objects.get_or_create(key=k, defaults={'value': v, 'description': d})

    if request.method == 'POST':
        action = request.POST.get('action')
        
        # ১. নতুন সেটিং অ্যাড করা
        if action == 'add_new':
            raw_key = request.POST.get('key').strip().lower()
            key = raw_key.replace(' ', '_')
            value = request.POST.get('value')
            desc = request.POST.get('description')
            
            if not AppSetting.objects.filter(key=key).exists():
                AppSetting.objects.create(key=key, value=value, description=desc)
                messages.success(request, f"New setting '{key}' added successfully!")
            else:
                messages.error(request, f"Key '{key}' already exists!")
                
        # ২. সব সেটিং একসাথে আপডেট করা
        elif action == 'update_all':
            for key, value in request.POST.items():
                if key not in ['csrfmiddlewaretoken', 'action', 'delete_key']:
                    AppSetting.objects.filter(key=key).update(value=value)
            messages.success(request, "All settings updated successfully!")

        # ৩. নির্দিষ্ট সেটিং ডিলিট করা (নতুন ম্যাজিক)
        elif action == 'delete':
            delete_key = request.POST.get('delete_key')
            if delete_key and delete_key not in core_keys:
                AppSetting.objects.filter(key=delete_key).delete()
                messages.success(request, f"Setting '{delete_key}' deleted successfully!")
            elif delete_key in core_keys:
                messages.error(request, "System core settings cannot be deleted!")
            
        return redirect('system_settings')
        
    settings = AppSetting.objects.all().order_by('id')
    return render(request, 'system_settings.html', {'settings': settings, 'core_keys': core_keys})