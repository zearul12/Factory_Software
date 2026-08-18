import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Case, When, Value, IntegerField, ProtectedError
from core.models import AppSetting, KnitMachine

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