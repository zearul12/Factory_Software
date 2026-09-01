import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Q
from django.apps import apps
from core.models import KnittingOrder, KnittingSize, Operator, KnittingIssue, AppSetting

@login_required(login_url='login')
def order_issue_entry_view(request):
    recent_issues = KnittingIssue.objects.filter(issued_by=request.user).order_by('-id')[:15]
    
    brand_setting = AppSetting.objects.filter(key='machine_brands').first()
    brands = [b.strip() for b in brand_setting.value.split(',')] if brand_setting else ['Shima', 'Stoll', 'Cixing']
    
    allowance_setting = AppSetting.objects.filter(key='issue_yarn_allowance_pct').first()
    yarn_allowance = float(allowance_setting.value) if allowance_setting and allowance_setting.value else 2.0
    
    context = {
        'recent_issues': recent_issues,
        'brands_json': json.dumps(brands),
        'yarn_allowance': yarn_allowance
    }
    return render(request, 'order_issue_entry.html', context)

@login_required
def search_issue_job_ajax(request):
    query = request.GET.get('q', '').strip()
    if len(query) >= 3:
        orders = KnittingOrder.objects.filter(
            Q(job_no__icontains=query) | Q(style_no__icontains=query)
        ).distinct().order_by('-id')[:15]
        
        results = [{
            'sys_id': o.system_id, 'job_no': o.job_no, 
            'buyer': o.buyer.buyer_name, 'style': o.style_no, 
            'pos': o.po_numbers
        } for o in orders]
    else:
        results = []
    return JsonResponse(results, safe=False)

@login_required
def get_issue_job_details_ajax(request, sys_id):
    try:
        order = KnittingOrder.objects.get(system_id=sys_id)
        colors = list(order.colors.values_list('color_name', flat=True).distinct())
        operations = [op.strip() for op in order.operations.split(',')] if order.operations else []
        
        matrix_data = []
        allocations_data = [] # Rules: Which Lot for Which Size?
        
        for c in order.colors.all():
            # Map frontend lot IDs to actual Lot Names
            lot_map = {}
            for y in c.yarns.all():
                for l in y.lots.all():
                    if l.frontend_id:
                        lot_map[str(l.frontend_id)] = l.lot_name
            
            # Parse allocation matrix safely
            if c.lot_allocation_json:
                try:
                    alloc_dict = json.loads(c.lot_allocation_json)
                    for alloc_key, sizes_dict in alloc_dict.items():
                        parts = alloc_key.split('_')
                        if len(parts) >= 3:
                            m_lot_name = lot_map.get(parts[1], 'Unknown')
                            s_lot_name = lot_map.get(parts[2], '')
                            
                            # Combine Main and Support lot names for display
                            display_lot = m_lot_name
                            if s_lot_name and s_lot_name != 'No support yarn':
                                display_lot = f"{m_lot_name} + {s_lot_name}"
                            
                            for sz_name, qty in sizes_dict.items():
                                if int(qty) > 0:
                                    allocations_data.append({
                                        'color': c.color_name,
                                        'size': sz_name,
                                        'lot': display_lot,
                                        'alloc_qty': int(qty)
                                    })
                except Exception as e:
                    print("Error parsing allocation:", e)

            for s in c.sizes.all():
                matrix_data.append({
                    'color': c.color_name, 'size': s.size_name,
                    'plan_qty': s.plan_qty, 'bundle_qty': s.bundle_qty or 0, 'size_wt': s.size_wt_gm or 0
                })
        
        issues = KnittingIssue.objects.filter(job_no=order.job_no).exclude(status='Deleted')
        issue_list = [{'color': i.color, 'size': i.size, 'lot': i.lot, 'op': i.operation, 'qty': i.issue_qty, 'recv': 0} for i in issues]
        
        data = {
            'job_no': order.job_no, 'buyer_name': order.buyer.buyer_name,
            'style_no': order.style_no, 'po_numbers': order.po_numbers,
            'colors': colors, 'operations': operations,
            'matrix': matrix_data, 
            'alloc_rules': allocations_data, # <--- Sending Strict Matrix Rules to Frontend
            'issues': issue_list
        }
        return JsonResponse({'status': 'success', 'data': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def search_issue_operator_ajax(request):
    query = request.GET.get('q', '').strip()
    if len(query) >= 3:
        operators = Operator.objects.filter(
            operator_id__icontains=query, is_active=True, section__icontains='Knitting'
        ).order_by('operator_id')[:10]
        
        results = []
        for op in operators:
            pend_issues = KnittingIssue.objects.filter(operator=op, status='Pending')
            results.append({
                'id': op.id, 'operator_id': op.operator_id, 'name': op.name,
                'category': op.category, 'brand': op.machine_brand,
                'cell': op.cell_no, 'machine_no': op.machine_no,
                'pend_count': pend_issues.count(), 
                'pend_qty': pend_issues.aggregate(Sum('issue_qty'))['issue_qty__sum'] or 0
            })
    else:
        results = []
    return JsonResponse(results, safe=False)

@login_required
def get_machine_line_ajax(request):
    mac_no = request.GET.get('m', '').strip()
    brand = request.GET.get('b', '').strip()
    
    # 01 and 1 handling logic
    mac_no_1 = str(int(mac_no)) if mac_no.isdigit() else mac_no
    mac_no_2 = mac_no.zfill(2) if mac_no.isdigit() else mac_no
    
    line_val = ''
    cell_val = ''
    
    try:
        # 1. Get Line from KnitMachine (Machine DB)
        KnitMachine = apps.get_model('core', 'KnitMachine')
        macs = KnitMachine.objects.filter(machine_no__in=[mac_no_1, mac_no_2])
        for mac in macs:
            db_brand = getattr(mac, 'brand_name', getattr(mac, 'machine_brand', '')).strip()
            if brand and brand.lower() in db_brand.lower():
                line_val = getattr(mac, 'line_no', getattr(mac, 'line', ''))
                break
                
        # 2. Get Cell from Operator (Operator DB)
        op_query = Q(category='Regular')
        if brand:
            op_query &= Q(machine_brand__icontains=brand)
            
        reg_ops = Operator.objects.filter(op_query)
        for op in reg_ops:
            if op.machine_no:
                machines = [m.strip() for m in op.machine_no.split(',')]
                # Strict exact match in comma separated list
                if mac_no_1 in machines or mac_no_2 in machines:
                    cell_val = op.cell_no
                    break
                    
        return JsonResponse({'status': 'success', 'line': str(line_val), 'cell': str(cell_val)})
    except Exception as e:
        print(e)
        pass
    return JsonResponse({'status': 'error', 'line': '', 'cell': ''})

@login_required
def save_order_issue_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            operator = Operator.objects.get(id=data['operator_id']) if data.get('operator_id') else None
            
            job_no = data['job_no']
            job_last_3 = job_no.split('-')[-1][-3:] if '-' in job_no else job_no[-3:]
            
            last_issue = KnittingIssue.objects.filter(tc_no__startswith=f"TC-{job_last_3}-").order_by('-id').first()
            new_seq = int(last_issue.tc_no.split('-')[-1]) + 1 if last_issue else 1
            tc_no = f"TC-{job_last_3}-{new_seq:03d}"
            
            last_sys = KnittingIssue.objects.order_by('-id').first()
            sys_id = f"{(int(last_sys.system_id) + 1):08d}" if last_sys and last_sys.system_id.isdigit() else "00000001"
            
            issue = KnittingIssue.objects.create(
                system_id=sys_id, tc_no=tc_no, job_no=job_no, buyer_name=data['buyer'],
                style_no=data['style'], po_no=data['po'], color=data['color'], size=data['size'],
                lot=data['lot'], operation=data['operation'], operator=operator,
                machine_no=data.get('machine_no', ''), line=data.get('line', ''), shift=data.get('shift', 'Day'),
                issue_qty=data['issue_qty'], issue_weight_lbs=data['issue_wt'],
                issued_by=request.user, status='Pending', print_count=1
            )
            
            return JsonResponse({'status': 'success', 'tc_no': issue.tc_no, 'sys_id': issue.system_id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def search_tc_for_issue_ajax(request):
    query = request.GET.get('q', '').strip()
    if len(query) >= 6:
        issues = KnittingIssue.objects.filter(tc_no__icontains=query).order_by('-id')[:10]
        results = [{
            'tc_no': i.tc_no, 'job_no': i.job_no, 'style': i.style_no,
            'color': i.color, 'size': i.size, 'qty': i.issue_qty, 'status': i.status
        } for i in issues]
    else:
        results = []
    return JsonResponse(results, safe=False)

@login_required
def get_single_issue_details_ajax(request, tc_no):
    try:
        i = KnittingIssue.objects.get(tc_no=tc_no)
        order = KnittingOrder.objects.get(job_no=i.job_no)
        data = {
            'tc_no': i.tc_no, 'job_sys_id': order.system_id,
            'op_id': i.operator.operator_id if i.operator else '', 
            'op_name': i.operator.name if i.operator else '',
            'op_db_id': i.operator.id if i.operator else '',
            'op_cat': i.operator.category if i.operator else 'Regular',
            'brand': i.operator.machine_brand if i.operator else '',
            'cell': i.operator.cell_no if i.operator else '',
            'machine_no': i.machine_no, 'line': i.line, 'shift': i.shift,
            'color': i.color, 'size': i.size, 'lot': i.lot, 'operation': i.operation,
            'issue_qty': i.issue_qty, 'issue_wt': str(i.issue_weight_lbs), 'status': i.status
        }
        return JsonResponse({'status': 'success', 'data': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def delete_order_issue_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            issue = KnittingIssue.objects.get(tc_no=data['tc_no'])
            if issue.status == 'Received': return JsonResponse({'status': 'error', 'message': 'Cannot delete! This issue has already been received.'})
            issue.status = 'Deleted'
            issue.delete_reason = data.get('reason', 'No reason provided')
            issue.save()
            return JsonResponse({'status': 'success', 'message': f'{issue.tc_no} marked as Deleted.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error'})