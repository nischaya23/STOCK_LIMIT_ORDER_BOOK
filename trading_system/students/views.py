from django.shortcuts import render
# from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.shortcuts import redirect
from .forms import UserRegisterForm
# Create your views here.
def register(request):
    form = UserRegisterForm()
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()  
            username=form.cleaned_data.get('username')
            # messages.success(request, f'Account created for {username}!')/
            return redirect("login")

    else:
        form = UserRegisterForm()
    return render(request, 'trading/register.html', {'form': form})