from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication অ্যাপের ইউআরএলগুলো এখানে কানেক্ট করা হলো
    path('', include('authentication.urls')),
    
    # Core অ্যাপের ইউআরএলগুলো এখানে কানেক্ট করা হলো
    path('', include('core.urls')),
]