from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import AppSetting, Buyer, OrderMaster, KnitMachine
from django.db.models import Case, When, Value, IntegerField


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

import json
from django.http import JsonResponse
from django.db.models import ProtectedError
from .models import Buyer # Buyer মডেল ইম্পোর্ট করতে ভুলবেন না (উপরে AppSetting এর সাথে লিখে দিতে পারেন)

# ... (আগের system_settings_view এর কোড থাকবে) ...

@login_required(login_url='login')
def buyer_entry_view(request):
    if request.method == 'POST':
        b_name = request.POST.get('buyer_name').strip()
        if b_name:
            if not Buyer.objects.filter(buyer_name__iexact=b_name).exists():
                Buyer.objects.create(buyer_name=b_name)
                messages.success(request, f"Buyer '{b_name}' added successfully!")
            else:
                messages.error(request, "This Buyer already exists!")
        return redirect('buyer_entry')
        
    buyers = Buyer.objects.all().order_by('buyer_name')
    return render(request, 'buyer_entry.html', {'buyers': buyers})


@login_required(login_url='login')
def update_buyer_ajax(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        buyer_id = data.get('buyer_id')
        
        try:
            buyer = Buyer.objects.get(id=buyer_id)
        except Buyer.DoesNotExist:
            return JsonResponse({'status': 'error', 'msg': 'Buyer not found!'})

        # স্ট্যাটাস পরিবর্তন (Hold / Active)
        if action == 'hold_toggle':
            buyer.is_active = not buyer.is_active
            buyer.save()
            return JsonResponse({'status': 'success'})
            
        # ইন-লাইন এডিট সেভ
        elif action == 'save_edit':
            new_name = data.get('buyer_name').strip()
            if new_name and not Buyer.objects.filter(buyer_name__iexact=new_name).exclude(id=buyer_id).exists():
                buyer.buyer_name = new_name
                buyer.save()
                return JsonResponse({'status': 'success'})
            return JsonResponse({'status': 'error', 'msg': 'Name is invalid or already exists!'})

        # ডিলিট করার লজিক (ভবিষ্যতে ব্যবহৃত হলে অটো আটকে দিবে)
        elif action == 'delete':
            try:
                buyer.delete()
                return JsonResponse({'status': 'success'})
            except ProtectedError:
                return JsonResponse({'status': 'error', 'msg': 'Cannot delete! This buyer is already used in other modules. Please put it on "Hold" instead.'})

from django.db.models import Case, When, Value, IntegerField
from .models import KnitMachine

@login_required(login_url='login')
def knit_machine_entry_view(request):
    # সেটিং থেকে মেশিনের ব্র্যান্ডগুলো আনা
    setting_obj = AppSetting.objects.filter(key='machine_brands').first()
    brands_list = [b.strip() for b in setting_obj.value.split(',')] if setting_obj and setting_obj.value else []

    # সর্টিং ম্যাজিক (সেটিংয়ের সিরিয়াল অনুযায়ী)
    cases = [When(brand_name=brand, then=Value(i)) for i, brand in enumerate(brands_list)]
    order_case = Case(*cases, default=Value(999), output_field=IntegerField())
    
    machines = KnitMachine.objects.annotate(custom_order=order_case).order_by('custom_order', 'machine_no')

    # সামারি (Summary) ক্যালকুলেশন
    summary_data = []
    total_lines = 0
    total_mcs = 0
    for brand in brands_list:
        qs = KnitMachine.objects.filter(brand_name=brand)
        mc_qty = qs.count()
        if mc_qty > 0:
            # ইউনিক লাইনের সংখ্যা বের করা
            line_qty = qs.values('line_no').distinct().count() 
            summary_data.append({'brand': brand, 'lines': line_qty, 'mcs': mc_qty})
            total_lines += line_qty
            total_mcs += mc_qty

    context = {
        'brands': brands_list,
        'machines': machines,
        'summary': summary_data,
        'total_lines': total_lines,
        'total_mcs': total_mcs
    }
    return render(request, 'knit_machine_entry.html', context)


@login_required(login_url='login')
def update_knit_machine_ajax(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        
        brand = data.get('brand_name')
        gauge = data.get('gauge')
        line = data.get('line_no')
        mc = data.get('machine_no')
        line_mc = data.get('line_mc_no')
        
        if action == 'save_new':
            if KnitMachine.objects.filter(line_mc_no=line_mc).exists():
                return JsonResponse({'status': 'error', 'msg': f'Machine ID {line_mc} already exists!'})
            KnitMachine.objects.create(brand_name=brand, gauge=gauge, line_no=line, machine_no=mc, line_mc_no=line_mc)
            return JsonResponse({'status': 'success'})

        # --- ফিক্স: Bulk Delete লজিকটিকে আগে আনা হলো ---
        elif action == 'bulk_delete':
            machine_ids = data.get('machine_ids', [])
            if not machine_ids:
                return JsonResponse({'status': 'error', 'msg': 'No machines selected!'})
            try:
                KnitMachine.objects.filter(id__in=machine_ids).delete()
                return JsonResponse({'status': 'success'})
            except ProtectedError:
                return JsonResponse({'status': 'error', 'msg': 'Some selected machines are in use and cannot be deleted!'})

        # --- এখন সিগেল মেশিনের আইডি চেক করবে ---
        mc_id = data.get('machine_id')
        if not mc_id: return JsonResponse({'status': 'error', 'msg': 'Machine ID missing!'})
        
        try:
            machine = KnitMachine.objects.get(id=mc_id)
        except KnitMachine.DoesNotExist:
            return JsonResponse({'status': 'error', 'msg': 'Machine not found!'})

        if action == 'update':
            if KnitMachine.objects.filter(line_mc_no=line_mc).exclude(id=mc_id).exists():
                return JsonResponse({'status': 'error', 'msg': f'Machine ID {line_mc} already exists!'})
            machine.brand_name = brand
            machine.gauge = gauge
            machine.line_no = line
            machine.machine_no = mc
            machine.line_mc_no = line_mc
            machine.save()
            return JsonResponse({'status': 'success'})
            
        elif action == 'hold_toggle':
            machine.is_active = not machine.is_active
            machine.save()
            return JsonResponse({'status': 'success'})
            
        elif action == 'delete':
            try:
                machine.delete()
                return JsonResponse({'status': 'success'})
            except ProtectedError:
                return JsonResponse({'status': 'error', 'msg': 'Cannot delete! Machine is in use.'})

import datetime

@login_required(login_url='login')
def confirm_order_entry_view(request):
    # ১. Job Prefix এবং Year বের করা
    prefix_obj = AppSetting.objects.filter(key='job_prefix').first()
    job_prefix = prefix_obj.value.strip() if prefix_obj else 'PSL'
    current_year = datetime.date.today().strftime('%y')
    prefix_year = f"{job_prefix}-{current_year}-"
    
    # ২. Auto Generate Next Job Sequence (ডাটাবেজ চেক করে নতুন সিরিয়াল বের করা)
    last_order = OrderMaster.objects.filter(job_no__startswith=prefix_year).order_by('-job_no').first()
    if last_order:
        try:
            last_seq = int(last_order.job_no.split('-')[-1])
            new_seq = last_seq + 1
        except:
            new_seq = 1
    else:
        new_seq = 1
    new_job_no = f"{prefix_year}{new_seq:05d}"
    
    # ৩. Settings থেকে ড্রপডাউনের ডাটা আনা
    dept_obj = AppSetting.objects.filter(key='departments').first()
    departments = [d.strip() for d in dept_obj.value.split(',')] if dept_obj else []
    
    proc_obj = AppSetting.objects.filter(key='additional_processes').first()
    processes = [p.strip() for p in proc_obj.value.split(',')] if proc_obj else []
    
    mc_obj = AppSetting.objects.filter(key='machine_brands').first()
    machines = [m.strip() for m in mc_obj.value.split(',')] if mc_obj else []
    
    # ৪. Size Templates গুলো আনা (JSON হিসেবে পাঠানোর জন্য)
    size_settings = AppSetting.objects.filter(key__istartswith='Size_temp_')
    size_templates = {}
    for s in size_settings:
        size_templates[s.key] = [sz.strip() for sz in s.value.split(',')]
        
    context = {
        'new_job_no': new_job_no,
        'job_prefix': job_prefix,
        'current_year': current_year,
        'departments': departments,
        'processes': processes,
        'machines': machines,
        'size_templates_json': json.dumps(size_templates)
    }
    return render(request, 'confirm_order_entry.html', context)


# বায়ার সার্চ করার লাইভ AJAX ফাংশন (১ টা অক্ষর লিখলেই সাজেস্ট করবে)
@login_required(login_url='login')
def search_buyer_ajax(request):
    query = request.GET.get('q', '')
    if query:
        buyers = Buyer.objects.filter(buyer_name__icontains=query)[:10]
        results = [{'id': b.id, 'name': b.buyer_name} for b in buyers]
    else:
        results = []
    return JsonResponse(results, safe=False)