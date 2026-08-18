import json
import datetime
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q
from core.models import AppSetting, Buyer, OrderMaster, OrderPO, OrderColor, OrderSizeBreakdown, PageApprover, SystemNotification

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
                changed = set(order.changed_fields.split(',')) if order.changed_fields else set()
                
                if old_status == 'Approved':
                    if str(order.department) != str(data['department']): changed.add('department')
                    if str(order.buyer.id) != str(data['buyer_id']): changed.add('buyer_name')
                    if str(order.style_no) != str(data['style_no']): changed.add('style_no')
                    if str(order.development_mc) != str(data['dev_mc']): changed.add('dev_mc')
                    if str(order.style_description) != str(data['style_desc']): changed.add('style_desc')
                    if str(order.total_order_qty) != str(data['order_qty']): changed.add('order_qty')
                    if str(order.shipment_date) != str(data['shipment_date']): changed.add('shipment_date')
                    if str(order.file_handover_date) != str(data['file_handover_date']): changed.add('file_handover_date')
                    if str(order.avg_fob) != str(data['avg_fob']): changed.add('avg_fob')
                    if str(order.discounted_fob) != str(data['discount_fob']): changed.add('discount_fob')
                    if str(order.additional_process) != str(data['additional_process']): changed.add('additional_process')
                    if str(order.remarks) != str(data.get('remarks', '')): changed.add('remarks')
                    
                    old_pos = list(order.pos.values_list('po_number', flat=True))
                    if set(old_pos) != set(data['po_list']): changed.add('po_input')
                    
                    old_colors = list(order.colors.values_list('color_name', flat=True))
                    if set(old_colors) != set(data['color_list']): changed.add('color_input')
                    
                    old_matrix = { f"matrix_{m.po.po_number.strip()}_{m.color.color_name.strip()}_{m.size_name.strip()}": m.qty for m in order.size_breakdowns.all() }
                    
                    for item in data['matrix_data']:
                        po_val = str(item['po']).strip()
                        col_val = str(item['color']).strip()
                        sz_val = str(item['size']).strip()
                        key = f"matrix_{po_val}_{col_val}_{sz_val}"
                        
                        if key not in old_matrix or str(old_matrix[key]) != str(item['qty']):
                            changed.add(key)

                    changed.discard('')
                    order.changed_fields = ",".join(changed)
                else:
                    order.changed_fields = "" 
                
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
                order.status = 'Pending'
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
            
            if is_new or old_status != 'Approved':
                notif_title = f"New Order Approval: {order.job_no}"
                notif_msg = f"Buyer: {buyer.buyer_name} (Style: {order.style_no}) requires approval."
            else:
                notif_title = f"Order Updated: {order.job_no}"
                notif_msg = f"User has modified Approved Order for Buyer: {buyer.buyer_name}. Please re-check highlighted fields."
            
            for uid in notify_users:
                if uid != request.user.id:
                    SystemNotification.objects.create(
                        user_id=uid, title=notif_title,
                        message=notif_msg,
                        link=f"/marketing/confirm-order/?load_job={order.job_no}"
                    )

            return JsonResponse({'status': 'success', 'is_update': not is_new})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid Request'})

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
            'changed_fields': order.changed_fields.split(',') if order.changed_fields else [],
            'pos': [po.po_number for po in order.pos.all()], 'colors': [col.color_name for col in order.colors.all()],
            'matrix': [{'po': m.po.po_number, 'color': m.color.color_name, 'size': m.size_name, 'qty': m.qty} for m in order.size_breakdowns.all().order_by('sort_order')]
        }
        return JsonResponse({'status': 'success', 'data': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

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
                OrderMaster.objects.filter(job_no=job_no).update(status='Approved', changed_fields='') 
                notif.is_read = True
                notif.save()
            return JsonResponse({'status': 'success', 'msg': 'All pending orders approved!'})
            
        job_no = data.get('job_no')
        try:
            order = OrderMaster.objects.get(job_no=job_no)
            if action == 'approve':
                order.status = 'Approved'
                order.changed_fields = ''
                order.save()
                SystemNotification.objects.filter(user=request.user, title__contains=job_no).update(is_read=True)
                return JsonResponse({'status': 'success', 'msg': f'{job_no} Approved Successfully!'})
            elif action == 'reject':
                order.status = 'Rejected'
                order.reject_reason = data.get('reason', '')
                order.save()
                SystemNotification.objects.filter(user=request.user, title__contains=job_no).update(is_read=True)
                return JsonResponse({'status': 'success', 'msg': f'{job_no} Rejected Successfully!'})
            elif action == 'hold':
                order.status = 'Hold'
                order.save()
                return JsonResponse({'status': 'success', 'msg': f'{job_no} placed on Hold!'})
        except OrderMaster.DoesNotExist:
            return JsonResponse({'status': 'error', 'msg': 'Order not found!'})