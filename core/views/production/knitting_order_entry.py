import json
import datetime
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q
from core.models import AppSetting, Buyer, KnittingOrder, KnittingColor, KnittingSize, KnittingYarn, KnittingYarnLot, PageApprover, SystemNotification

@login_required(login_url='login')
def knitting_order_entry_view(request):
    size_settings = AppSetting.objects.filter(key__istartswith='Size_temp_')
    size_templates = {s.key: [sz.strip() for sz in s.value.split(',')] for s in size_settings}
    buyers = list(Buyer.objects.filter(is_active=True).values_list('buyer_name', flat=True))
    
    op_setting = AppSetting.objects.filter(key='quick_operations').first()
    quick_ops = [op.strip() for op in op_setting.value.split(',')] if op_setting else ['Body', 'Neck', 'Piping', 'Waistband']
    
    gauge_setting = AppSetting.objects.filter(key='machine_gauges').first()
    gauges = [g.strip() for g in gauge_setting.value.split(',')] if gauge_setting else ['3G', '5G', '7G', '12G', '14G']
    
    prefix_obj = AppSetting.objects.filter(key='job_prefix').first()
    job_prefix = prefix_obj.value.strip() if prefix_obj else 'PSL'
    current_year = datetime.date.today().strftime('%y')
    
    last_order = KnittingOrder.objects.filter(job_no__startswith=f"{job_prefix}-{current_year}-").order_by('-id').first()
    new_seq = int(last_order.job_no.split('-')[-1]) + 1 if last_order else 1
    new_job_sequence = f"{new_seq:05d}"

    context = {
        'size_templates_json': json.dumps(size_templates), 'buyers_json': json.dumps(buyers),
        'gauges_json': json.dumps(gauges), 'quick_ops': quick_ops,
        'job_prefix': job_prefix, 'current_year': current_year, 'new_job_sequence': new_job_sequence,
    }
    return render(request, 'knitting_order_entry.html', context)

@login_required
def search_knitting_job_ajax(request):
    query = request.GET.get('q', '').strip()
    if len(query) >= 2:
        orders = KnittingOrder.objects.filter(
            Q(job_no__icontains=query) | Q(buyer__buyer_name__icontains=query) | 
            Q(style_no__icontains=query) | Q(po_numbers__icontains=query) | Q(colors__color_name__icontains=query)
        ).distinct().order_by('-created_at')[:15]
        
        results = [{
            'sys_id': o.system_id, 'job_no': o.job_no, 'buyer': o.buyer.buyer_name, 'style': o.style_no, 'status': o.status,
            'pos': o.po_numbers, 'colors': ", ".join([c.color_name for c in o.colors.all()])
        } for o in orders]
    else:
        results = []
    return JsonResponse(results, safe=False)

def to_f(v):
    try: return float(v)
    except: return 0.0

def to_i(v):
    try: return int(v)
    except: return 0

@login_required
@transaction.atomic
def save_knitting_order_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            buyer, _ = Buyer.objects.get_or_create(buyer_name=data.get('buyer_name'), defaults={'is_active': True})
            
            sys_id = data.get('system_id', '')
            order = KnittingOrder.objects.filter(system_id=sys_id).first() if sys_id else None
            is_new = False
            changed = []
            
            if order:
                old_status = order.status
                if str(order.job_no) != str(data['job_no']): changed.append('job_sequence')
                if str(order.buyer.buyer_name) != str(buyer.buyer_name): changed.append('m_buyer')
                if str(order.style_no) != str(data['style_no']): changed.append('m_style')
                if str(order.po_numbers) != str(data['po_list']): changed.append('m_po')
                if str(order.plan_pct) != str(data['plan_pct']): changed.append('m_planPct')
                if str(order.gauge) != str(data['gauge']): changed.append('m_gauge')
                if str(order.kcd_date) != str(data['kcd_date']): changed.append('m_kcdDate')
                if str(order.operations) != str(data['operations']): changed.append('opContainer')
                
                # Check Size & Yarn changes
                old_data_map = {}
                if order.colors.exists():
                    for c in order.colors.all():
                        c_safe = c.color_name.replace(' ', '_')
                        for s in c.sizes.all():
                            s_safe = s.size_name.replace(' ', '_')
                            old_data_map[f"qty_{c_safe}_{s_safe}"] = s.order_qty
                            old_data_map[f"wt_{c_safe}_{s_safe}"] = s.size_wt_gm
                            old_data_map[f"bndl_{c_safe}_{s_safe}"] = s.bundle_qty
                        
                        for y_idx, y in enumerate(c.yarns.all()):
                            old_data_map[f"y_name_{c_safe}_{y_idx}"] = y.yarn_name
                            old_data_map[f"y_cons_{c_safe}_{y_idx}"] = to_f(y.consumption_pct)
                            old_data_map[f"y_allow_{c_safe}_{y_idx}"] = to_f(y.allowance_pct)
                            old_data_map[f"y_req_{c_safe}_{y_idx}"] = y.req_weight_lbs
                            for l_idx, lot in enumerate(y.lots.all()):
                                old_data_map[f"l_name_{c_safe}_{y_idx}_{l_idx}"] = lot.lot_name
                                old_data_map[f"l_lbs_{c_safe}_{y_idx}_{l_idx}"] = to_f(lot.allocated_lbs)

                for c in data['colors']:
                    c_safe = c['name'].replace(' ', '_')
                    for s in c['sizes']:
                        s_safe = s['name'].replace(' ', '_')
                        if f"qty_{c_safe}_{s_safe}" not in old_data_map or str(old_data_map[f"qty_{c_safe}_{s_safe}"]) != str(s['oQty']): changed.append(f"qty_{c_safe}_{s_safe}")
                        if f"wt_{c_safe}_{s_safe}" not in old_data_map or str(old_data_map[f"wt_{c_safe}_{s_safe}"]) != str(s['sWeight']): changed.append(f"wt_{c_safe}_{s_safe}")
                    
                    for y_idx, y in enumerate(c.get('yarns', [])):
                        if f"y_name_{c_safe}_{y_idx}" not in old_data_map or old_data_map[f"y_name_{c_safe}_{y_idx}"] != y['name']: changed.append(f"y_name_{c_safe}_{y_idx}")
                        if f"y_cons_{c_safe}_{y_idx}" not in old_data_map or old_data_map[f"y_cons_{c_safe}_{y_idx}"] != to_f(y.get('consPct', 0)): changed.append(f"y_cons_{c_safe}_{y_idx}")
                        if f"y_allow_{c_safe}_{y_idx}" not in old_data_map or old_data_map[f"y_allow_{c_safe}_{y_idx}"] != to_f(y.get('allowPct', 0)): changed.append(f"y_allow_{c_safe}_{y_idx}")
                        if f"y_req_{c_safe}_{y_idx}" not in old_data_map or old_data_map[f"y_req_{c_safe}_{y_idx}"] != to_i(y.get('reqLbs', 0)): changed.append(f"y_req_{c_safe}_{y_idx}")
                        
                        for l_idx, lot in enumerate(y.get('lots', [])):
                            if f"l_name_{c_safe}_{y_idx}_{l_idx}" not in old_data_map or old_data_map[f"l_name_{c_safe}_{y_idx}_{l_idx}"] != lot['lotName']: changed.append(f"l_name_{c_safe}_{y_idx}_{l_idx}")
                            if f"l_lbs_{c_safe}_{y_idx}_{l_idx}" not in old_data_map or old_data_map[f"l_lbs_{c_safe}_{y_idx}_{l_idx}"] != to_f(lot.get('lbs', 0)): changed.append(f"l_lbs_{c_safe}_{y_idx}_{l_idx}")
                
                if len(changed) == 0:
                    return JsonResponse({'status': 'error', 'message': 'No changes detected! Please modify at least one field to update.'})
                
                order.changed_fields = ",".join(changed) if old_status == 'Approved' else ""
                order.colors.all().delete()
            else:
                is_new = True
                last_sys = KnittingOrder.objects.order_by('-id').first()
                new_sys_id = f"{(int(last_sys.system_id) + 1):08d}" if last_sys and last_sys.system_id.isdigit() else "00000001"
                order = KnittingOrder(system_id=new_sys_id, created_by=request.user)

            order.job_no = data['job_no']
            order.buyer = buyer
            order.style_no = data['style_no']
            order.po_numbers = data['po_list']
            order.plan_pct = data['plan_pct']
            order.gauge = data['gauge']
            order.kcd_date = data['kcd_date']
            order.operations = data['operations']
            order.total_color = data['total_color']
            order.total_size = data['total_size']
            order.total_order_qty = data['total_order_qty']
            order.total_plan_qty = data['total_plan_qty']
            order.total_weight_lbs = data['total_lbs']
            order.avg_weight_dz = data['avg_wt']
            order.status = 'Pending'
            order.save()

            for col_data in data['colors']:
                col_obj = KnittingColor.objects.create(order=order, color_name=col_data['name'])
                
                for sz_data in col_data['sizes']:
                    KnittingSize.objects.create(
                        color=col_obj, size_name=sz_data['name'], order_qty=sz_data['oQty'],
                        plan_qty=sz_data['pQty'], size_wt_gm=sz_data['sWeight'], total_lbs=sz_data['lbs'],
                        bundle_qty=int(sz_data.get('bundleQty') or 0), sort_order=sz_data['sort']
                    )
                
                for y_data in col_data.get('yarns', []):
                    y_obj = KnittingYarn.objects.create(
                        color=col_obj, yarn_name=y_data['name'], 
                        consumption_pct=to_f(y_data.get('consPct')), 
                        allowance_pct=to_f(y_data.get('allowPct')), 
                        req_weight_lbs=to_i(y_data.get('reqLbs'))
                    )
                    for l_data in y_data.get('lots', []):
                        KnittingYarnLot.objects.create(
                            yarn=y_obj, lot_name=l_data['lotName'], allocated_lbs=to_f(l_data.get('lbs'))
                        )

            approvers = list(PageApprover.objects.filter(page_name__icontains="Knitting").values_list('user_id', flat=True))
            superadmins = list(User.objects.filter(is_superuser=True).values_list('id', flat=True))
            notify_users = set(approvers + superadmins)
            
            notif_title = f"Order Updated: {order.job_no}" if not is_new and order.changed_fields else f"Order Approval: {order.job_no}"
            notif_msg = f"Buyer: {buyer.buyer_name} (Style: {order.style_no}) requires approval."
            
            for uid in notify_users:
                SystemNotification.objects.create(user_id=uid, title=notif_title, message=notif_msg, link=f"/production/knitting/order-entry/?load_sys_id={order.system_id}")

            return JsonResponse({'status': 'success', 'is_update': not is_new, 'sys_id': order.system_id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid Request'})

@login_required
def get_knitting_order_details_ajax(request, sys_id):
    try:
        order = KnittingOrder.objects.get(system_id=sys_id)
        
        colors_data = []
        for c in order.colors.all():
            sizes = [{'name': s.size_name, 'oQty': s.order_qty, 'pQty': s.plan_qty, 'sWeight': s.size_wt_gm, 'lbs': str(s.total_lbs), 'bundleQty': str(s.bundle_qty) if s.bundle_qty else ""} for s in c.sizes.all().order_by('sort_order')]
            
            yarns = []
            for y in c.yarns.all():
                lots = [{'lotName': l.lot_name, 'lbs': str(l.allocated_lbs).rstrip('0').rstrip('.')} for l in y.lots.all()]
                yarns.append({
                    'name': y.yarn_name, 
                    'consPct': str(y.consumption_pct).rstrip('0').rstrip('.') if y.consumption_pct else '', 
                    'allowPct': str(y.allowance_pct).rstrip('0').rstrip('.') if y.allowance_pct else '', 
                    'reqLbs': str(y.req_weight_lbs), 
                    'lots': lots
                })
                
            colors_data.append({'name': c.color_name, 'sizes': sizes, 'yarns': yarns})

        data = {
            'system_id': order.system_id, 'job_no': order.job_no, 'buyer_name': order.buyer.buyer_name,
            'style_no': order.style_no, 'po_numbers': order.po_numbers, 'plan_pct': order.plan_pct, 'gauge': order.gauge,
            'kcd_date': order.kcd_date.strftime('%Y-%m-%d') if order.kcd_date else '',
            'operations': order.operations, 'status': order.status, 'reject_reason': order.reject_reason,
            'changed_fields': order.changed_fields.split(',') if order.changed_fields else [],
            'colors': colors_data
        }
        return JsonResponse({'status': 'success', 'data': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
@transaction.atomic
def knitting_order_action_ajax(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        
        if action == 'approve_all':
            notifs = SystemNotification.objects.filter(user=request.user, is_read=False, title__startswith="Order ")
            for notif in notifs:
                try:
                    job_no = notif.title.split(': ')[1]
                    KnittingOrder.objects.filter(job_no=job_no).update(status='Approved', changed_fields='')
                    notif.is_read = True
                    notif.save()
                except: pass
            return JsonResponse({'status': 'success', 'msg': 'All pending orders approved!'})
            
        sys_id = data.get('system_id')
        try:
            order = KnittingOrder.objects.get(system_id=sys_id)
            if action == 'approve':
                order.status = 'Approved'
                order.changed_fields = ''
                order.save()
                SystemNotification.objects.filter(user=request.user, link__contains=sys_id).update(is_read=True)
                return JsonResponse({'status': 'success', 'msg': f'{order.job_no} Approved Successfully!'})
            
            elif action == 'reject':
                order.status = 'Rejected'
                order.reject_reason = data.get('reason', '')
                order.save()
                
                if order.created_by:
                    SystemNotification.objects.create(
                        user=order.created_by,
                        title=f"Order Rejected: {order.job_no}",
                        message=f"Reason: {order.reject_reason}",
                        link=f"/production/knitting/order-entry/?load_sys_id={order.system_id}"
                    )
                
                SystemNotification.objects.filter(user=request.user, link__contains=sys_id).update(is_read=True)
                return JsonResponse({'status': 'success', 'msg': f'{order.job_no} Rejected Successfully!'})
            
            elif action == 'hold':
                order.status = 'Hold'
                order.save()
                return JsonResponse({'status': 'success', 'msg': f'{order.job_no} placed on Hold!'})
        except KnittingOrder.DoesNotExist:
            return JsonResponse({'status': 'error', 'msg': 'Order not found!'})