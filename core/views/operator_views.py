import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import ProtectedError, Count
from core.models import Operator, AppSetting

@login_required(login_url='login')
def operator_entry_view(request):
    sec_setting = AppSetting.objects.filter(key='operator_sections').first()
    sections = [s.strip() for s in sec_setting.value.split(',')] if sec_setting else ['Knitting']
    
    brand_setting = AppSetting.objects.filter(key='machine_brands').first()
    brands = [b.strip() for b in brand_setting.value.split(',')] if brand_setting else ['Shima']
    
    operators = Operator.objects.all().order_by('operator_id') # A-Z Sorting
    
    # Live Summary Logic
    summary = []
    for sec in sections:
        active = operators.filter(section=sec, is_active=True).count()
        inactive = operators.filter(section=sec, is_active=False).count()
        if active > 0 or inactive > 0:
            summary.append({'section': sec, 'active': active, 'inactive': inactive})

    context = {
        'operators': operators,
        'sections': sections,
        'sections_json': json.dumps(sections),
        'brands_json': json.dumps(brands),
        'summary': summary
    }
    return render(request, 'operator_entry.html', context)

@login_required
def save_operator_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            op_id = data.get('id')
            operator_id = data.get('operator_id', '').strip()
            name = data.get('name', '').strip()
            section = data.get('section', '').strip()
            category = data.get('category', 'Regular').strip()
            brand = data.get('machine_brand', '').strip()
            cell = data.get('cell_no', '').strip()
            machine = data.get('machine_no', '').strip()
            is_active = str(data.get('is_active')).lower() == 'true'

            if not operator_id or not name:
                return JsonResponse({'status': 'error', 'message': 'Operator ID and Name are required!'})

            if section.lower() == 'knitting' and category == 'Regular' and (not brand or not cell or not machine):
                return JsonResponse({'status': 'error', 'message': 'Machine Brand, Cell No and Machine No are mandatory for Regular Knitting operators.'})

            if op_id:
                operator = Operator.objects.get(id=op_id)
                if Operator.objects.filter(operator_id=operator_id).exclude(id=op_id).exists():
                    return JsonResponse({'status': 'error', 'message': 'This Operator ID already exists!'})
                operator.operator_id = operator_id
                operator.name = name
                operator.section = section
                operator.category = category
                operator.machine_brand = brand
                operator.cell_no = cell
                operator.machine_no = machine
                operator.is_active = is_active
                operator.save()
            else:
                if Operator.objects.filter(operator_id=operator_id).exists():
                    return JsonResponse({'status': 'error', 'message': 'This Operator ID already exists!'})
                Operator.objects.create(
                    operator_id=operator_id, name=name, section=section, 
                    category=category, machine_brand=brand, cell_no=cell, machine_no=machine, is_active=is_active
                )

            return JsonResponse({'status': 'success', 'message': 'Operator Saved Successfully!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@login_required
def delete_operator_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            operator = Operator.objects.get(id=data.get('id'))
            operator.delete()
            return JsonResponse({'status': 'success', 'message': 'Operator Deleted Successfully!'})
        except ProtectedError:
            return JsonResponse({'status': 'error', 'message': 'Cannot delete! Used in other records.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def bulk_delete_operator_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            deleted = 0
            err_msg = ""
            for op_id in ids:
                try:
                    Operator.objects.get(id=op_id).delete()
                    deleted += 1
                except ProtectedError:
                    err_msg = " Some operators are protected."
            return JsonResponse({'status': 'success', 'message': f'Deleted {deleted} Operators.{err_msg}'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def bulk_save_operator_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            operators = data.get('operators', [])
            count = 0
            for row in operators:
                op_id = str(row.get('operator_id', '')).strip()
                name = str(row.get('name', '')).strip()
                section = str(row.get('section', 'Knitting')).strip()
                category = str(row.get('category', 'Regular')).strip()
                brand = str(row.get('brand', '')).strip()
                cell = str(row.get('cell', '')).strip()
                machine = str(row.get('machine', '')).strip()
                
                status_raw = str(row.get('status', 'Active')).strip().lower()
                is_active = status_raw in ['active', 'true', '1', 'yes']

                if op_id and name:
                    Operator.objects.update_or_create(
                        operator_id=op_id, 
                        defaults={
                            'name': name, 'section': section, 'category': category,
                            'machine_brand': brand, 'cell_no': cell, 'machine_no': machine, 'is_active': is_active
                        }
                    )
                    count += 1
            return JsonResponse({'status': 'success', 'message': f'Successfully Imported {count} Operators!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})