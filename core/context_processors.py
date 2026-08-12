from .models import FactorySetting

def global_settings(request):
    # ডাটাবেজ থেকে ফ্যাক্টরির নাম টেনে আনবে, না পেলে ডিফল্ট নাম দেখাবে
    setting = FactorySetting.objects.first()
    
    if setting and setting.factory_name:
        factory_name = setting.factory_name
    else:
        factory_name = "Smart Factory System"
        
    return {
        'factory_name': factory_name
    }