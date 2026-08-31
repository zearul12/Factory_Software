import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q
from django.core.mail import send_mail
from django.contrib.auth.models import User
from core.models import KnittingOrder, YarnReceive, YarnReceiveHistory, PageApprover, SystemNotification

@login_required(login_url='login')
def yarn_receive_entry_view(request):
    return render(request, 'yarn_receive_entry.html')

@login_required
def search_yarn_receive_job_ajax(request):
    query = request.GET.get('q', '').strip()
    if len(query) >= 2:
        orders = KnittingOrder.objects.filter(
            Q(job_no__icontains=query) | Q(buyer__buyer_name__icontains=query) | 
            Q(style_no__icontains=query) | Q(po_numbers__icontains=query) | Q(colors__color_name__icontains=query)
        ).distinct().order_by('-created_at')[:15]
        
        results = [{
            'sys_id': o.system_id, 'job_no': o.job_no, 'buyer': o.buyer.buyer_name, 
            'style': o.style_no, 'pos': o.po_numbers, 
            'status': o.status, 
            'colors': ", ".join([c.color_name for c in o.colors.all()])
        } for o in orders]
    else:
        results = []
    return JsonResponse(results, safe=False)

@login_required
def get_yarn_receive_details_ajax(request, sys_id):
    try:
        order = KnittingOrder.objects.get(system_id=sys_id)
        
        if order.status != 'Approved':
            return JsonResponse({
                'status': 'unapproved', 
                'sys_id': order.system_id,
                'job_no': order.job_no,
                'message': f"Job {order.job_no} is currently '{order.status}' and waiting for approval. You cannot receive yarn until it is approved."
            })
        
        colors_data = []
        for c in order.colors.all():
            sizes_data = []
            for s in c.sizes.all().order_by('sort_order'):
                sizes_data.append({
                    'id': s.id, 'name': s.size_name, 'pQty': s.plan_qty
                })

            yarns_data = []
            for y in c.yarns.all():
                lots_data = []
                for lot in y.lots.all():
                    rcv_record = YarnReceive.objects.filter(
                        job_no=order.job_no, color=c.color_name, 
                        yarn_name=y.yarn_name, lot_name=lot.lot_name
                    ).first()
                    
                    history = []
                    before_rcv = 0
                    if rcv_record:
                        before_rcv = float(rcv_record.total_received_lbs)
                        for h in rcv_record.history.all().order_by('id'):
                            user_name = h.received_by.first_name if h.received_by and h.received_by.first_name else (h.received_by.username if h.received_by else 'Unknown')
                            history.append({
                                'id': h.id,
                                'date': h.received_date.strftime('%d %b %Y, %I:%M %p'),
                                'lbs': float(h.received_lbs),
                                'user': user_name
                            })

                    lots_data.append({
                        'id': lot.id,
                        'record_id': rcv_record.id if rcv_record else '',
                        'lot_name': lot.lot_name,
                        'lot_alloc_lbs': float(lot.allocated_lbs),
                        'before_rcv': before_rcv,
                        'history': history
                    })
                
                yarns_data.append({
                    'id': y.id,
                    'yarn_name': y.yarn_name,
                    'type': y.yarn_type,
                    'parentId': y.parent_yarn_id,
                    'allow_pct': float(y.allowance_pct),
                    'req_lbs': y.req_weight_lbs,
                    'lots': lots_data
                })
            
            colors_data.append({
                'id': c.id,
                'color_name': c.color_name,
                'pack_type': c.pack_type,
                'sizes': sizes_data,
                'yarns': yarns_data
            })

        data = {
            'system_id': order.system_id, 'job_no': order.job_no, 'buyer_name': order.buyer.buyer_name,
            'style_no': order.style_no, 'po_numbers': order.po_numbers, 'plan_pct': order.plan_pct,
            'order_qty': order.total_order_qty, 'plan_qty': order.total_plan_qty,
            'colors': colors_data
        }
        return JsonResponse({'status': 'success', 'data': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def send_approval_knock_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            sys_id = data.get('sys_id')
            job_no = data.get('job_no')
            
            approvers = PageApprover.objects.filter(page_name__icontains="Knitting")
            if not approvers.exists():
                approver_users = User.objects.filter(is_superuser=True)
            else:
                approver_users = [a.user for a in approvers]
                
            emails = [u.email for u in approver_users if u.email]
            
            notif_title = f"URGENT: Approval Needed for {job_no}"
            req_user = request.user.first_name if request.user.first_name else request.user.username
            notif_msg = f"User '{req_user}' is waiting to receive yarn for Job '{job_no}'. Please review and approve the order ASAP."
            link = f"/production/knitting/order-entry/?load_sys_id={sys_id}"
            
            for u in set(approver_users):
                SystemNotification.objects.create(user=u, title=notif_title, message=notif_msg, link=link)
            
            if emails:
                try:
                    send_mail(
                        subject=notif_title,
                        message=notif_msg + f"\n\nDirect Link: https://pandora-khdr.onrender.com{link}",
                        from_email=None,
                        recipient_list=emails,
                        fail_silently=True,
                    )
                except: pass
                
            return JsonResponse({'status': 'success', 'message': 'Knock sent successfully! The approvers have been notified via App & Email.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error'})

@login_required
@transaction.atomic
def save_yarn_receive_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            job_no = data.get('job_no')
            
            saved_count = 0
            for row in data.get('lots', []):
                curr_rcv_raw = row.get('current_rcv')
                if curr_rcv_raw == '' or curr_rcv_raw is None:
                    continue
                    
                curr_rcv = float(curr_rcv_raw)
                hist_id = row.get('history_id')
                
                if hist_id:
                    hist_obj = YarnReceiveHistory.objects.get(id=hist_id)
                    rcv_obj = hist_obj.receive_record
                    old_rcv = float(hist_obj.received_lbs)
                    diff = curr_rcv - old_rcv
                    
                    if diff != 0:
                        hist_obj.received_lbs = curr_rcv
                        hist_obj.received_by = request.user
                        hist_obj.save()
                        
                        rcv_obj.total_received_lbs = float(rcv_obj.total_received_lbs) + diff
                        rcv_obj.balance_lbs = float(rcv_obj.total_received_lbs) - float(rcv_obj.req_weight_lbs)
                        rcv_obj.save()
                        saved_count += 1
                else:
                    if curr_rcv > 0:
                        record_id = row.get('record_id')
                        if record_id:
                            rcv_obj = YarnReceive.objects.get(id=record_id)
                            rcv_obj.before_received_lbs = rcv_obj.total_received_lbs
                            rcv_obj.current_received_lbs = curr_rcv
                            rcv_obj.total_received_lbs = float(rcv_obj.total_received_lbs) + curr_rcv
                            rcv_obj.balance_lbs = float(rcv_obj.total_received_lbs) - float(rcv_obj.req_weight_lbs)
                            rcv_obj.received_by = request.user
                            rcv_obj.save()
                        else:
                            last_sys = YarnReceive.objects.order_by('-id').first()
                            sys_id = f"YR-{(int(last_sys.system_id.split('-')[1]) + 1):06d}" if last_sys and '-' in last_sys.system_id else "YR-000001"
                            
                            rcv_obj = YarnReceive.objects.create(
                                system_id=sys_id,
                                job_no=job_no, buyer_name=data.get('buyer_name'),
                                style_no=data.get('style_no'), po_no=data.get('po_no'),
                                plan_pct=data.get('plan_pct'), color=row.get('color'),
                                yarn_name=row.get('yarn_name'), allowance_pct=row.get('allow_pct'),
                                lot_name=row.get('lot_name'), req_weight_lbs=row.get('lot_alloc_lbs'),
                                before_received_lbs=0, current_received_lbs=curr_rcv,
                                total_received_lbs=curr_rcv, 
                                balance_lbs=curr_rcv - float(row.get('lot_alloc_lbs')),
                                received_by=request.user
                            )
                        
                        YarnReceiveHistory.objects.create(
                            receive_record=rcv_obj,
                            received_lbs=curr_rcv,
                            received_by=request.user
                        )
                        saved_count += 1
            
            if saved_count > 0:
                return JsonResponse({'status': 'success', 'message': f'Successfully saved/updated {saved_count} records!'})
            else:
                return JsonResponse({'status': 'error', 'message': 'No changes were made.'})
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid Request'})