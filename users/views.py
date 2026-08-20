from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import EmailLoginForm, IdentityVerificationForm, RegistrationForm
from .models import IdentityVerification, User


def register(request):
    if request.user.is_authenticated:
        return redirect('profile')
    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        user.is_email_verified = True
        user.is_phone_verified = True
        user.save(update_fields=['is_email_verified', 'is_phone_verified', 'updated_at'])
        login(request, user)
        messages.success(request, f'Compte créé. Votre ID Fasthome est {user.fasthome_id}.')
        return redirect('profile')
    return render(request, 'users/register.html', {'form': form})


def login_view(request):
    form = EmailLoginForm(request, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect(request.GET.get('next') or 'home')
    return render(request, 'users/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def profile(request):
    return render(request, 'users/profile.html', {'profile_user': request.user})


@login_required
def certification(request):
    verification = getattr(request.user, 'identity_verification', None)
    form = IdentityVerificationForm(request.POST or None, request.FILES or None, instance=verification)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.user = request.user
        obj.status = 'PENDING'
        obj.facial_status = 'PENDING'
        obj.verified_at = None
        obj.save()
        messages.success(request, 'Votre dossier d’identité a été transmis à Fasthome.')
        return redirect('certification')
    return render(request, 'users/certification.html', {'form': form, 'verification': verification})
