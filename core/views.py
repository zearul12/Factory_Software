import json
import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Case, When, Value, IntegerField, ProtectedError
from django.db.models import Q

from .models import AppSetting, Buyer, KnitMachine, OrderMaster, OrderPO, OrderColor, OrderSizeBreakdown, PageApprover, SystemNotification

def is_superadmin(user):
    return user.is_superuser

@login_required(login_url='login')
@user_passes_test(is_superadmin, login_url='dashboard')
def system_settings_view(request):
    core_keys = ['factory_name', 'app_version', 'copyright_text', 'developer_credit']
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
                
        elif action == 'update_all':
            for key, value in request.POST.items():
                if key not in ['csrfmiddlewaretoken', 'action', 'delete_key']:
                    AppSetting.objects.filter(key=key).update(value=value)
            messages.success(request, "All settings updated successfully!")

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

        if action == 'hold_toggle':
            buyer.is_active = not buyer.is_active
            buyer.save()
            return JsonResponse({'status': 'success'})
            
        elif action == 'save_edit':
            new_name = data.get('buyer_name').strip()
            if new_name and not Buyer.objects.filter(buyer_name__iexact=new_name).exclude(id=buyer_id).exists():
                buyer.buyer_name = new_name
                buyer.save()
                return JsonResponse({'status': 'success'})
            return JsonResponse({'status': 'error', 'msg': 'Name is invalid or already exists!'})

        elif action == 'delete':
            try:
                buyer.delete()
                return JsonResponse({'status': 'success'})
            except ProtectedError:
                return JsonResponse({'status': 'error', 'msg': 'Cannot delete! This buyer is already used.'})

@login_required(login_url='login')
def knit_machine_entry_view(request):
    setting_obj = AppSetting.objects.filter(key='machine_brands').first()
    brands_list = [b.strip() for b in setting_obj.value.split(',')] if setting_obj and setting_obj.value else []

    cases = [When(brand_name=brand, then=Value(i)) for i, brand in enumerate(brands_list)]
    order_case = Case(*cases, default=Value(999), output_field=IntegerField())
    
    machines = KnitMachine.objects.annotate(custom_order=order_case).order_by('custom_order', 'machine_no')

    summary_data = []
    total_lines = 0
    total_mcs = 0
    for brand in brands_list:
        qs = KnitMachine.objects.filter(brand_name=brand)
        mc_qty = qs.count()
        if mc_qty > 0:
            line_qty = qs.values('line_no').distinct().count() 
            summary_data.append({'brand': brand, 'lines': line_qty, 'mcs': mc_qty})
            total_lines += line_qty
            total_mcs += mc_qty

    context = {
        'brands': brands_list, 'machines': machines, 'summary': summary_data,
        'total_lines': total_lines, 'total_mcs': total_mcs
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

        elif action == 'bulk_delete':
            machine_ids = data.get('machine_ids', [])
            if not machine_ids: return JsonResponse({'status': 'error', 'msg': 'No machines selected!'})
            try:
                KnitMachine.objects.filter(id__in=machine_ids).delete()
                return JsonResponse({'status': 'success'})
            except ProtectedError:
                return JsonResponse({'status': 'error', 'msg': 'Some selected machines are in use!'})

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

@login_required(login_url='login')
def confirm_order_entry_view(request):
    prefix_obj = AppSetting.objects.filter(key='job_prefix').first()
    job_prefix = prefix_obj.value.strip() if prefix_obj else 'PSL'
    current_year = datetime.date.today().strftime('%y')
    prefix_year = f"{job_prefix}-{current_year}-"
    
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
    
    dept_obj = AppSetting.objects.filter(key='departments').first()
    departments = [d.strip() for d in dept_obj.value.split(',')] if dept_obj else []
    
    proc_obj = AppSetting.objects.filter(key='additional_processes').first()
    processes = [p.strip() for p in proc_obj.value.split(',')] if proc_obj else []
    
    mc_obj = AppSetting.objects.filter(key='machine_brands').first()
    machines = [m.strip() for m in mc_obj.value.split(',')] if mc_obj else []
    
    size_settings = AppSetting.objects.filter(key__istartswith='Size_temp_')
    size_templates = {}
    for s in size_settings:
        size_templates[s.key] = [sz.strip() for sz in s.value.split(',')]
        
    recent_orders = OrderMaster.objects.filter(created_by=request.user).order_by('-created_at')[:5]
    
    context = {
        'new_job_no': new_job_no, 'job_prefix': job_prefix, 'current_year': current_year,
        'departments': departments, 'processes': processes, 'machines': machines,
        'size_templates_json': json.dumps(size_templates), 'recent_orders': recent_orders
    }
    return render(request, 'confirm_order_entry.html', context)

@login_required(login_url='login')
def search_buyer_ajax(request):
    query = request.GET.get('q', '')
    if query:
        buyers = Buyer.objects.filter(buyer_name__icontains=query)[:10]
        results = [{'id': b.id, 'name': b.buyer_name} for b in buyers]
    else:
        results = []
    return JsonResponse(results, safe=False)

@login_required(login_url='login')
@transaction.atomic
def save_confirm_order_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            job_no = data['job_no']
            buyer = Buyer.objects.get(id=data['buyer_id'])
            
            order = OrderMaster.objects.filter(job_no=job_no).first()
            is_new = False
            old_status = ''
            
            if order:
                old_status = order.status
                
                # --- Magic: Track Changed Fields if previously Approved ---
                changed = []
                if old_status == 'Approved':
                    if order.department != data['department']: changed.append('department')
                    if order.buyer.id != int(data['buyer_id']): changed.append('buyer_name')
                    if order.style_no != data['style_no']: changed.append('style_no')
                    if order.development_mc != data['dev_mc']: changed.append('dev_mc')
                    if order.style_description != data['style_desc']: changed.append('style_desc')
                    if str(order.total_order_qty) != str(data['order_qty']): changed.append('order_qty')
                    if str(order.shipment_date) != str(data['shipment_date']): changed.append('shipment_date')
                    if str(order.file_handover_date) != str(data['file_handover_date']): changed.append('file_handover_date')
                    if str(order.avg_fob) != str(data['avg_fob']): changed.append('avg_fob')
                    if str(order.discounted_fob) != str(data['discount_fob']): changed.append('discount_fob')
                    if order.additional_process != data['additional_process']: changed.append('additional_process')
                    if order.remarks != data.get('remarks', ''): changed.append('remarks')
                    
                    old_pos = list(order.pos.values_list('po_number', flat=True))
                    if set(old_pos) != set(data['po_list']): changed.append('po_input')
                    
                    old_colors = list(order.colors.values_list('color_name', flat=True))
                    if set(old_colors) != set(data['color_list']): changed.append('color_input')
                    
                    # --- NEW: DEEP MATRIX COMPARISON ---
                    # আগের ম্যাট্রিক্সের ডাটা ডিকশনারিতে নিয়ে আসা হচ্ছে
                    old_matrix = { f"matrix_{m.po.po_number}_{m.color.color_name}_{m.size_name}": m.qty for m in order.size_breakdowns.all() }
                    
                    # নতুন আসা ম্যাট্রিক্সের সাথে প্রতিটি লাইন মিলিয়ে দেখা হচ্ছে
                    for item in data['matrix_data']:
                        key = f"matrix_{item['po']}_{item['color']}_{item['size']}"
                        # যদি নতুন সাইজ হয় অথবা কোয়ান্টিটি না মেলে, তবেই হাইলাইট করবে!
                        if key not in old_matrix or str(old_matrix[key]) != str(item['qty']):
                            changed.append(key)

                    order.changed_fields = ",".join(changed)
                else:
                    order.changed_fields = "" # Pending থাকলে ট্র্যাকিং দরকার নেই
                
                # Update Existing Order
                order.department = data['department']
                order.buyer = buyer
                order.style_no = data['style_no']
                order.development_mc = data['dev_mc']
                order.style_description = data['style_desc']
                order.total_order_qty = data['order_qty']
                order.shipment_date = data['shipment_date']
                order.file_handover_date = data['file_handover_date']
                order.avg_fob = data['avg_fob']
                order.discounted_fob = data['discount_fob']
                order.additional_process = data['additional_process']
                order.remarks = data.get('remarks', '')
                order.status = 'Pending' # আপডেট হলে আবার Pending
                order.save()
                
                order.pos.all().delete()
                order.colors.all().delete()
                order.size_breakdowns.all().delete()
            else:
                is_new = True
                order = OrderMaster.objects.create(
                    job_no=job_no, department=data['department'], buyer=buyer,
                    style_no=data['style_no'], development_mc=data['dev_mc'], style_description=data['style_desc'],
                    total_order_qty=data['order_qty'], shipment_date=data['shipment_date'], file_handover_date=data['file_handover_date'],
                    avg_fob=data['avg_fob'], discounted_fob=data['discount_fob'], additional_process=data['additional_process'],
                    remarks=data.get('remarks', ''), status='Pending', created_by=request.user, changed_fields=""
                )

            po_dict = {po: OrderPO.objects.create(order=order, po_number=po) for po in data['po_list']}
            color_dict = {c: OrderColor.objects.create(order=order, color_name=c) for c in data['color_list']}

            for item in data['matrix_data']:
                OrderSizeBreakdown.objects.create(
                    order=order, po=po_dict[item['po']], color=color_dict[item['color']],
                    size_name=item['size'], qty=item['qty'], sort_order=item['sort']
                )

            approvers = list(PageApprover.objects.filter(page_name="Confirm Order Entry").values_list('user_id', flat=True))
            superadmins = list(User.objects.filter(is_superuser=True).values_list('id', flat=True))
            notify_users = set(approvers + superadmins) 
            
            # --- Magic Logic: Only send "Updated" if it was Approved before ---
            if is_new or old_status != 'Approved':
                notif_title = f"New Order Approval: {order.job_no}"
                notif_msg = f"Buyer: {buyer.buyer_name} (Style: {order.style_no}) requires approval."
            else:
                notif_title = f"Order Updated: {order.job_no}"
                notif_msg = f"User has modified Approved Order for Buyer: {buyer.buyer_name}. Please re-check highlighted fields."
            
            for uid in notify_users:
                SystemNotification.objects.create(
                    user_id=uid, title=notif_title, message=notif_msg,
                    link=f"/marketing/confirm-order/?load_job={order.job_no}"
                )

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid Request'})


# Advanced Search (Job, Buyer, or Style)
@login_required
def search_old_job_ajax(request):
    query = request.GET.get('q', '').strip()
    if len(query) >= 2:
        orders = OrderMaster.objects.filter(
            Q(job_no__icontains=query) | Q(buyer__buyer_name__icontains=query) | Q(style_no__icontains=query)
        ).order_by('-created_at')[:10]
        results = [{'job_no': o.job_no, 'buyer': o.buyer.buyer_name, 'style': o.style_no, 'status': o.status} for o in orders]
    else:
        results = []
    return JsonResponse(results, safe=False)

@login_required
def get_order_details_ajax(request, job_no):
    try:
        order = OrderMaster.objects.get(job_no=job_no)
        data = {
            'job_no': order.job_no, 'department': order.department, 'buyer_id': order.buyer.id,
            'buyer_name': order.buyer.buyer_name, 'style_no': order.style_no, 'dev_mc': order.development_mc,
            'style_desc': order.style_description, 'order_qty': order.total_order_qty,
            'shipment_date': order.shipment_date.strftime('%Y-%m-%d') if order.shipment_date else '',
            'file_handover_date': order.file_handover_date.strftime('%Y-%m-%d') if order.file_handover_date else '',
            'avg_fob': str(order.avg_fob), 'discount_fob': str(order.discounted_fob),
            'additional_process': order.additional_process, 'remarks': order.remarks,
            'status': order.status, 'reject_reason': order.reject_reason,
            'changed_fields': order.changed_fields.split(',') if order.changed_fields else [], # Changed fields পাঠানো হচ্ছে
            'pos': [po.po_number for po in order.pos.all()], 'colors': [col.color_name for col in order.colors.all()],
            'matrix': [{'po': m.po.po_number, 'color': m.color.color_name, 'size': m.size_name, 'qty': m.qty} for m in order.size_breakdowns.all().order_by('sort_order')]
        }
        return JsonResponse({'status': 'success', 'data': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
def get_notifications_ajax(request):
    notifs = SystemNotification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:10]
    notif_list = []
    for n in notifs:
        job_no = ""
        if "Order Approval:" in n.title:
            job_no = n.title.split(': ')[1]
            
        notif_list.append({
            'id': n.id, 'title': n.title, 'message': n.message, 'link': n.link,
            'time': n.created_at.strftime('%d %b, %H:%M'), 'job_no': job_no
        })
    return JsonResponse({'status': 'success', 'count': notifs.count(), 'notifs': notif_list})

# --- Quick Approve / Reject / Hold Logic ---
@login_required
@transaction.atomic
def order_action_ajax(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        
        if action == 'approve_all':
            notifs = SystemNotification.objects.filter(user=request.user, is_read=False, title__startswith="Order Approval:")
            for notif in notifs:
                job_no = notif.title.split(': ')[1]
                OrderMaster.objects.filter(job_no=job_no).update(status='Approved')
                notif.is_read = True
                notif.save()
            return JsonResponse({'status': 'success', 'msg': 'All pending orders approved!'})
            
        job_no = data.get('job_no')
        try:
            order = OrderMaster.objects.get(job_no=job_no)
            if action == 'approve':
                order.status = 'Approved'
                order.save()
                SystemNotification.objects.filter(user=request.user, title__contains=job_no).update(is_read=True)
                return JsonResponse({'status': 'success', 'msg': f'{job_no} Approved Successfully!'})
            elif action == 'reject':
                order.status = 'Rejected'
                order.reject_reason = data.get('reason', '')
                order.save()
                SystemNotification.objects.filter(user=request.user, title__contains=job_no).update(is_read=True)
                return JsonResponse({'status': 'success', 'msg': f'{job_no} Rejected Successfully!'})
            elif action == 'hold': # নতুন Hold লজিক
                order.status = 'Hold'
                order.save()
                return JsonResponse({'status': 'success', 'msg': f'{job_no} placed on Hold!'})
        except OrderMaster.DoesNotExist:
            return JsonResponse({'status': 'error', 'msg': 'Order not found!'})