from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from .forms import EmailLoginForm, IdentityVerificationForm, RegistrationForm
from .kyc_services import process_identity_verification
from .models import IdentityVerification, IdentityVerificationEvent, User


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
    rejected_kyc = bool(verification and verification.status in {'REJECTED', 'RETRY'})
    facial_retry = bool(verification and (verification.facial_status in {'REJECTED', 'RETRY'} or rejected_kyc))
    facial_only_retry = bool(verification and verification.status == 'VERIFIED' and verification.facial_status in {'REJECTED', 'RETRY'})
    fully_certified = bool(verification and verification.status == 'VERIFIED' and verification.facial_status == 'VERIFIED')

    if request.method == 'POST' and verification and not facial_retry:
        if fully_certified:
            messages.info(request, 'Votre identité est déjà certifiée. Aucun nouvel envoi n’est nécessaire.')
        elif verification.status in {'PENDING', 'IN_REVIEW'}:
            messages.info(request, 'Votre dossier est déjà en cours de traitement. Vous ne pouvez pas envoyer un second dossier pour le moment.')
        return redirect('certification')

    form = IdentityVerificationForm(request.POST or None, request.FILES or None, instance=verification)
    if facial_only_retry:
        form.fields['document_type'].required = False
        form.fields['document_file'].required = False
        form.fields['facial_photo'].required = True
    elif rejected_kyc:
        form.fields['document_type'].required = True
        form.fields['document_file'].required = True
        form.fields['facial_photo'].required = False

    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            locked = IdentityVerification.objects.select_for_update().filter(user=request.user).first()
            locked_facial_retry = bool(locked and locked.status == 'VERIFIED' and locked.facial_status in {'REJECTED', 'RETRY'})
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
            if locked_facial_retry:
                obj.document_file = locked.document_file
                obj.document_type = locked.document_type
                obj.status = 'VERIFIED'
                success_message = 'Votre nouvelle photo faciale a été transmise à Fasthome.'
            else:
                obj.status = 'PENDING'
                success_message = 'Votre demande de certification a été transmise. Les contrôles automatiques démarrent maintenant.'
            obj.facial_status = 'PENDING'
            obj.verified_at = None
            obj.rejection_reason = ''
            obj.save()
            IdentityVerificationEvent.objects.create(
                verification=obj,
                actor=request.user,
                event_type='SUBMITTED',
                from_status=locked.status if locked else '',
                to_status=obj.status,
                from_facial_status=locked.facial_status if locked else '',
                to_facial_status=obj.facial_status,
                reason='Dossier transmis par l’utilisateur.',
            )
            try:
                analysis = process_identity_verification(obj)
            except Exception as exc:
                # Fail-safe degraded mode: never certify when the pipeline crashes.
                obj.status = 'IN_REVIEW'
                obj.facial_status = 'IN_REVIEW'
                obj.rejection_reason = f'Contrôles automatiques temporairement indisponibles ({exc.__class__.__name__}). Vérification humaine requise.'
                obj.save()
                messages.warning(request, 'Les contrôles automatiques sont temporairement indisponibles. Votre dossier a été envoyé à un agent.')
            else:
                if analysis.decision == 'AUTO_VERIFIED':
                    success_message = 'Identité vérifiée automatiquement. Votre compte Fasthome est maintenant certifié.'
                elif analysis.decision == 'REJECTED':
                    success_message = 'La vérification automatique n’a pas été concluante. Consultez le motif et soumettez une nouvelle pièce si nécessaire.'
                else:
                    success_message = 'Votre dossier nécessite une vérification par un agent Fasthome.'

        messages.success(request, success_message)
        return redirect('certification')

    return render(request, 'users/certification.html', {
        'form': form,
        'verification': verification,
        'facial_retry': facial_retry,
        'facial_only_retry': facial_only_retry,
        'fully_certified': fully_certified,
    })
