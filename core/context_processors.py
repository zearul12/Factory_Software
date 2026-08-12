from .models import AppSetting

def global_settings(request):
    # ডাটাবেজ থেকে সমস্ত ডায়নামিক সেটিং টেনে আনবে
    settings = AppSetting.objects.all()
    context = {s.key: s.value for s in settings}
    
    # যদি ডাটাবেজ একদম খালি থাকে, তবে ডিফল্ট কিছু ডাটা ব্যাকআপ হিসেবে কাজ করবে
    defaults = {
        'factory_name': 'Smart Factory System',
        'app_version': 'Version 1.0.0',
        'copyright_text': '© 2026 Your Company',
        'developer_credit': 'Designed & Developed by Zearul'
    }
    
    for k, v in defaults.items():
        if k not in context:
            context[k] = v
            
    return context