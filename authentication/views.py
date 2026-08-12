from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

def login_view(request):
    # যদি ইউজার আগে থেকেই লগইন করা থাকে, তবে সরাসরি ড্যাশবোর্ডে পাঠিয়ে দিবে
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        user_id = request.POST.get('username')
        pass_word = request.POST.get('password')
        
        user = authenticate(request, username=user_id, password=pass_word)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid User ID or Password!")
            return redirect('login')

    return render(request, 'login.html')
    return render(request, 'login.html', context)

# সিকিউরিটি গার্ড: লগইন ছাড়া কেউ এই পেজে আসতে পারবে না
@login_required(login_url='login')
def dashboard_view(request):
    return render(request, 'dashboard.html')

# লগআউট করার লজিক
def logout_view(request):
    logout(request)
    return redirect('login')