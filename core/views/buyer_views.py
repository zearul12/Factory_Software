import json
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import ProtectedError
from core.models import Buyer

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
def search_buyer_ajax(request):
    query = request.GET.get('q', '')
    if query:
        buyers = Buyer.objects.filter(buyer_name__icontains=query)[:10]
        results = [{'id': b.id, 'name': b.buyer_name} for b in buyers]
    else:
        results = []
    return JsonResponse(results, safe=False)