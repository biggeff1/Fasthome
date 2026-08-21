from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from notifications.models import Notification
from users.models import IdentityVerification


def staff_required(view):
    return user_passes_test(lambda u: u.is_authenticated and (u.is_staff or u.is_superuser))(view)


@staff_required
def office_verifications(request):
    verifications = IdentityVerification.objects.select_related('user').filter(status__in=['PENDING', 'IN_REVIEW', 'RETRY']).order_by('submitted_at')
    return render(request, 'dashboard/office_verifications.html', {'verifications': verifications})


@staff_required
@require_POST
def office_verification_decision(request, verification_id):
    action = request.POST.get('action')
    reason = request.POST.get('reason', '').strip()
    with transaction.atomic():
        verification = get_object_or_404(
            IdentityVerification.objects.select_for_update().select_related('user'),
            pk=verification_id,
        )

        if action == 'verify_document':
            verification.status = 'VERIFIED'
            if verification.facial_status == 'RETRY':
                verification.facial_status = 'PENDING'
            verification.verified_at = timezone.now() if verification.facial_status == 'VERIFIED' else None

        elif action == 'verify_face':
            if verification.status != 'VERIFIED':
                messages.error(request, 'Le document d’identité doit être validé avant la vérification faciale finale.')
                return redirect('office_verifications')
            if not verification.facial_photo:
                messages.error(request, 'Aucune photo faciale n’est enregistrée. Le visage ne peut pas être validé.')
                return redirect('office_verifications')
            verification.facial_status = 'VERIFIED'
            verification.verified_at = timezone.now()

        elif action == 'reject':
            if not reason:
                messages.error(request, 'Indiquez le motif du refus.')
                return redirect('office_verifications')
            verification.status = 'RETRY'
            verification.facial_status = 'RETRY'
            verification.rejection_reason = reason
            verification.verified_at = None

        else:
            messages.error(request, 'Action de certification invalide.')
            return redirect('office_verifications')

        verification.save()
        Notification.objects.create(
            recipient=verification.user,
            level='SUCCESS' if verification.user.is_certified else 'ACTION',
            title='Mise à jour de votre certification',
            message=(
                'Votre identité est maintenant certifiée.'
                if verification.user.is_certified
                else 'Votre dossier de certification a été mis à jour. Consultez votre espace pour connaître la prochaine étape.'
            ),
            object_type='IdentityVerification',
            object_id=str(verification.pk),
        )
    messages.success(request, 'Dossier de certification mis à jour.')
    return redirect('office_verifications')
