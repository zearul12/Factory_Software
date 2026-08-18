from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from core.models import SystemNotification

@login_required
def get_notifications_ajax(request):
    notifs = SystemNotification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:10]
    notif_list = []
    for n in notifs:
        job_no = ""
        if "Order Approval:" in n.title or "Order Updated:" in n.title:
            job_no = n.title.split(': ')[1]
            
        notif_list.append({
            'id': n.id, 'title': n.title, 'message': n.message, 'link': n.link,
            'time': n.created_at.strftime('%d %b, %H:%M'), 'job_no': job_no
        })
    return JsonResponse({'status': 'success', 'count': notifs.count(), 'notifs': notif_list})