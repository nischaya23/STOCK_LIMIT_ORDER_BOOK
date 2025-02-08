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

import csv
from django.contrib.auth.models import User
from .forms import CSVUploadForm


def bulk_user_upload(request):
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            csv_reader = csv.reader(decoded_file)
            
            for row in csv_reader:
                if len(row) >= 2:  # Ensure at least two columns exist
                    username, email = row[:2]  # Get username and email
                    password = row[2] if len(row) > 2 else 'defaultpassword'  # Set password if given, else default
                    
                    if not User.objects.filter(username=username).exists():
                        User.objects.create_user(username=username, email=email, password=password)
            
            messages.success(request, "Users created successfully!")
            return redirect('home')

    else:
        form = CSVUploadForm()

    return render(request, 'trading/bulk_upload.html', {'form': form})
import csv
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from .forms import UserDeleteCSVForm
from django.contrib import messages

def bulk_user_delete(request):
    if request.method == 'POST':
        form = UserDeleteCSVForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            csv_reader = csv.reader(decoded_file)
            
            deleted_count = 0
            not_found_users = []

            for row in csv_reader:
                if len(row) >= 1:
                    username = row[0].strip()
                    try:
                        user = User.objects.get(username=username)
                        user.delete()
                        deleted_count += 1
                    except User.DoesNotExist:
                        not_found_users.append(username)
            
            if deleted_count > 0:
                messages.success(request, f"{deleted_count} users deleted successfully.")
            if not_found_users:
                messages.warning(request, f"Users not found: {', '.join(not_found_users)}")

            return redirect('home')

    else:
        form = UserDeleteCSVForm()

    return render(request, 'trading/bulk_delete.html', {'form': form})
