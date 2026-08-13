import json
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.db import IntegrityError
from .models import UserProfile, PagePermission
from core.models import AppSetting # মাস্টার সেটিং থেকে ডাটা টানার জন্য
from core.models import PageApprover # Approver মডেল ইম্পোর্ট করা হলো

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, "Invalid User ID or Password!")
        return redirect('login')
    return render(request, 'login.html')

@login_required(login_url='login')
def dashboard_view(request):
    return render(request, 'dashboard.html')

def logout_view(request):
    logout(request)
    return redirect('login')


AVAILABLE_PAGES = ['Inventory', 'Production', 'Reports'] 

@login_required(login_url='login')
@user_passes_test(lambda u: u.is_superuser, login_url='dashboard')
def user_management(request):
    if request.method == 'POST':
        try:
            # ইউজার তৈরি
            user = User.objects.create_user(
                username=request.POST.get('user_id'), 
                password=request.POST.get('password'), 
                first_name=request.POST.get('full_name')
            )
            # প্রোফাইল তৈরি (নতুন Emp ID সহ)
            UserProfile.objects.create(
                user=user, 
                employee_id=request.POST.get('employee_id'),
                company_name=request.POST.get('company_name'), 
                designation=request.POST.get('designation'), 
                department=request.POST.get('department')
            )
            
            # --- New Logic: Save Approver Pages (For New User) ---
            approver_pages = request.POST.getlist('approver_pages')
            if approver_pages:
                for page in approver_pages:
                    PageApprover.objects.create(user=user, page_name=page)

            for page in AVAILABLE_PAGES:
                PagePermission.objects.create(user=user, page_name=page, access_level='Not')
            messages.success(request, "User created successfully!")
        except IntegrityError:
            messages.error(request, "User ID already exists! Please choose a different ID.")
        return redirect('user_management')

    users = User.objects.all().order_by('-date_joined')
    user_data_list = []
    for u in users:
        profile, _ = UserProfile.objects.get_or_create(user=u)
        permissions = {p.page_name: p.access_level for p in PagePermission.objects.filter(user=u)}
        for page in AVAILABLE_PAGES:
            if page not in permissions:
                PagePermission.objects.create(user=u, page_name=page, access_level='Not')
                permissions[page] = 'Not'
        user_data_list.append({'user': u, 'profile': profile, 'permissions': permissions})

    company_setting = AppSetting.objects.filter(key='factory_name').first()
    company_name = company_setting.value if company_setting else "Smart Factory System"

    context = {
        'user_data_list': user_data_list,
        'pages': AVAILABLE_PAGES,
        'companies': [{'factory_name': company_name}]
    }
    return render(request, 'user_management.html', context)


@login_required(login_url='login')
def update_user_ajax(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_obj = User.objects.get(id=data['user_id'])
        profile, _ = UserProfile.objects.get_or_create(user=user_obj)
        action = data.get('action')
        
        if action == 'hold_toggle':
            profile.is_active_user = not profile.is_active_user
            profile.save()
            return JsonResponse({'status': 'success'})
            
        elif action == 'save_edit':
            user_obj.first_name = data.get('full_name', user_obj.first_name)
            
            # যদি নতুন পাসওয়ার্ড দেয়, তবে সেটি আপডেট হবে
            new_password = data.get('password')
            if new_password:
                user_obj.set_password(new_password)
            user_obj.save()
            
            profile.employee_id = data.get('employee_id', profile.employee_id)
            profile.company_name = data.get('company_name', profile.company_name)
            profile.designation = data.get('designation', profile.designation)
            profile.department = data.get('department', profile.department)
            profile.save()
            
            for page, access in data.get('permissions', {}).items():
                p_obj, _ = PagePermission.objects.get_or_create(user=user_obj, page_name=page)
                p_obj.access_level = access
                p_obj.save()
                
            # --- New Logic: Update Approver Pages (For Existing User) ---
            approver_pages = data.get('approver_pages', [])
            
            # Delete old permissions first
            PageApprover.objects.filter(user=user_obj).delete()
            
            # Save new permissions
            for page in approver_pages:
                PageApprover.objects.create(user=user_obj, page_name=page)
                
            return JsonResponse({'status': 'success'})