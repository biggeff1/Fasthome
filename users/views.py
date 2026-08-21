from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
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
        user = form.get_user()
        login(request, user)

        # Respect a protected destination first, otherwise route the user
        # according to their Fasthome role.
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)

        if user.is_superuser:
            return redirect('/admin/')

        if user.is_staff:
            return redirect('dashboard:office')

        return redirect('home')

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

    # A pending/in-review/verified dossier must never be overwritten by a
    # second POST. A new document is allowed only after rejection/retry.
    if request.method == 'POST' and verification and verification.status in {'PENDING', 'IN_REVIEW', 'VERIFIED'}:
        if verification.status == 'VERIFIED':
            messages.info(request, 'Votre identité est déjà certifiée. Aucun nouveau document n’est nécessaire.')
        else:
            messages.info(request, 'Votre dossier est déjà en cours de traitement. Vous ne pouvez pas envoyer un second document pour le moment.')
        return redirect('certification')

    form = IdentityVerificationForm(request.POST or None, request.FILES or None, instance=verification)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            locked = IdentityVerification.objects.select_for_update().filter(user=request.user).first()
            if locked and locked.status in {'PENDING', 'IN_REVIEW', 'VERIFIED'}:
                if locked.status == 'VERIFIED':
                    messages.info(request, 'Votre identité est déjà certifiée. Aucun nouveau document n’est nécessaire.')
                else:
                    messages.info(request, 'Votre dossier est déjà en cours de traitement. Vous ne pouvez pas envoyer un second document pour le moment.')
                return redirect('certification')

            obj = form.save(commit=False)
            obj.user = request.user
            obj.status = 'PENDING'
            obj.facial_status = 'PENDING'
            obj.verified_at = None
            obj.rejection_reason = ''
            obj.save()

        messages.success(request, 'Votre dossier d’identité a été transmis à Fasthome.')
        return redirect('certification')
    return render(request, 'users/certification.html', {'form': form, 'verification': verification})
