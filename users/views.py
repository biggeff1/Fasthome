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
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)
        if user.is_superuser:
            return redirect('/admin/')
        if user.is_staff:
            return redirect('office_dashboard')
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
    facial_retry = bool(verification and verification.facial_status in {'REJECTED', 'RETRY'})
    fully_certified = bool(verification and verification.status == 'VERIFIED' and verification.facial_status == 'VERIFIED')

    if request.method == 'POST' and verification and not facial_retry:
        if fully_certified:
            messages.info(request, 'Votre identité est déjà certifiée. Aucun nouvel envoi n’est nécessaire.')
        elif verification.status in {'PENDING', 'IN_REVIEW'}:
            messages.info(request, 'Votre dossier est déjà en cours de traitement. Vous ne pouvez pas envoyer un second dossier pour le moment.')
        return redirect('certification')

    form = IdentityVerificationForm(request.POST or None, request.FILES or None, instance=verification)

    # If only the facial check was rejected/needs retry, the identity document
    # remains valid and only a fresh selfie is required.
    if facial_retry:
        form.fields['document_type'].required = False
        form.fields['document_file'].required = False
        form.fields['facial_photo'].required = True

    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            locked = IdentityVerification.objects.select_for_update().filter(user=request.user).first()
            locked_facial_retry = bool(locked and locked.facial_status in {'REJECTED', 'RETRY'})

            if locked:
                locked_fully_certified = locked.status == 'VERIFIED' and locked.facial_status == 'VERIFIED'
                if locked_fully_certified:
                    messages.info(request, 'Votre identité est déjà certifiée.')
                    return redirect('certification')
                if locked.status in {'PENDING', 'IN_REVIEW'} and not locked_facial_retry:
                    messages.info(request, 'Votre dossier est déjà en cours de traitement.')
                    return redirect('certification')

            obj = form.save(commit=False)
            obj.user = request.user

            if locked and locked_facial_retry and locked.status == 'VERIFIED':
                # The document was already approved. Keep it and restart only
                # the facial verification with the newly uploaded selfie.
                obj.document_file = locked.document_file
                obj.document_type = locked.document_type
                obj.status = 'VERIFIED'
            else:
                # A rejected/failed complete KYC starts a new document review.
                obj.status = 'PENDING'

            obj.facial_status = 'PENDING'
            obj.verified_at = None
            obj.rejection_reason = ''
            obj.save()

        messages.success(request, 'Votre nouvelle photo faciale a été transmise à Fasthome.')
        return redirect('certification')

    return render(
        request,
        'users/certification.html',
        {
            'form': form,
            'verification': verification,
            'facial_retry': facial_retry,
            'fully_certified': fully_certified,
        },
    )
