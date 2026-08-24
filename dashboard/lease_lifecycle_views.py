from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from leasing.models import Lease, RenewalRequest, LeaseExit
from notifications.models import Notification


def staff_required(view):
    return user_passes_test(lambda u: u.is_authenticated and (u.is_staff or u.is_superuser))(view)


def _can_access(user, lease):
    return user.is_staff or user.is_superuser or user.pk in {lease.tenant_id, lease.landlord_id}


@login_required
@require_POST
def request_renewal(request, lease_id):
    with transaction.atomic():
        lease = get_object_or_404(Lease.objects.select_for_update(), lease_id=lease_id)
        if request.user.pk != lease.tenant_id or lease.status != 'ACTIVE':
            return redirect('lease_detail', lease_id=lease.lease_id)
        if RenewalRequest.objects.filter(lease=lease, status='REQUESTED').exists():
            messages.error(request, 'Une demande de renouvellement est déjà en cours.')
            return redirect('lease_detail', lease_id=lease.lease_id)
        requested_end_date = request.POST.get('requested_end_date')
        proposed_rent = request.POST.get('proposed_monthly_rent') or None
        reason = request.POST.get('reason', '').strip()
        if not requested_end_date:
            messages.error(request, 'Indiquez la nouvelle date de fin.')
            return redirect('lease_detail', lease_id=lease.lease_id)
        RenewalRequest.objects.create(lease=lease, requested_by=request.user, requested_end_date=requested_end_date, proposed_monthly_rent=proposed_rent, reason=reason)
        Notification.objects.create(recipient=lease.landlord, level='ACTION', title='Demande de renouvellement', message=f'Une demande de renouvellement a été déposée pour {lease.lease_id}.', object_type='Lease', object_id=lease.lease_id)
    messages.success(request, 'Demande de renouvellement envoyée.')
    return redirect('lease_detail', lease_id=lease.lease_id)


@login_required
@require_POST
def request_exit(request, lease_id):
    with transaction.atomic():
        lease = get_object_or_404(Lease.objects.select_for_update(), lease_id=lease_id)
        if request.user.pk != lease.tenant_id or lease.status != 'ACTIVE':
            return redirect('lease_detail', lease_id=lease.lease_id)
        if LeaseExit.objects.filter(lease=lease, status='REQUESTED').exists():
            messages.error(request, 'Une demande de sortie est déjà en cours.')
            return redirect('lease_detail', lease_id=lease.lease_id)
        requested_date = request.POST.get('requested_date')
        if not requested_date:
            messages.error(request, 'Indiquez la date de sortie souhaitée.')
            return redirect('lease_detail', lease_id=lease.lease_id)
        LeaseExit.objects.create(lease=lease, requested_by=request.user, requested_date=requested_date, reason=request.POST.get('reason', '').strip())
        Notification.objects.create(recipient=lease.landlord, level='ACTION', title='Demande de sortie', message=f'Une demande de sortie a été déposée pour {lease.lease_id}.', object_type='Lease', object_id=lease.lease_id)
    messages.success(request, 'Demande de sortie envoyée.')
    return redirect('lease_detail', lease_id=lease.lease_id)


@login_required
def lease_requests(request, lease_id):
    lease = get_object_or_404(Lease, lease_id=lease_id)
    if not _can_access(request.user, lease):
        return redirect('activity')
    return render(request, 'dashboard/lease_requests.html', {'lease': lease, 'renewals': lease.renewal_requests.order_by('-created_at'), 'exits': lease.exit_requests.order_by('-created_at')})


@staff_required
def office_lifecycle_requests(request):
    renewals = RenewalRequest.objects.filter(status='REQUESTED').select_related('lease', 'lease__property', 'lease__tenant', 'lease__landlord').order_by('created_at')
    exits = LeaseExit.objects.filter(status='REQUESTED').select_related('lease', 'lease__property', 'lease__tenant', 'lease__landlord').order_by('created_at')
    return render(request, 'dashboard/office_lifecycle.html', {'renewals': renewals, 'exits': exits})


@staff_required
@require_POST
def decide_renewal(request, request_id):
    with transaction.atomic():
        renewal = get_object_or_404(RenewalRequest.objects.select_for_update().select_related('lease', 'lease__property'), request_id=request_id)
        if renewal.status != 'REQUESTED' or renewal.lease.status != 'ACTIVE':
            messages.error(request, 'Cette demande n’est plus traitable.')
            return redirect('office_lifecycle_requests')
        action = request.POST.get('action')
        renewal.decided_by = request.user
        renewal.decided_at = timezone.now()
        if action == 'approve':
            lease = Lease.objects.select_for_update().get(pk=renewal.lease_id)
            lease.end_date = renewal.requested_end_date
            if renewal.proposed_monthly_rent is not None:
                lease.monthly_rent = renewal.proposed_monthly_rent
            lease.status = 'RENEWAL'
            lease.save(update_fields=['end_date', 'monthly_rent', 'status'])
            renewal.status = 'APPROVED'
            Notification.objects.create(recipient=lease.tenant, level='SUCCESS', title='Renouvellement accepté', message=f'Le renouvellement de {lease.lease_id} a été accepté.', object_type='Lease', object_id=lease.lease_id)
        elif action == 'refuse':
            renewal.status = 'REFUSED'
            Notification.objects.create(recipient=renewal.lease.tenant, level='INFO', title='Renouvellement refusé', message=f'La demande de renouvellement {renewal.request_id} a été refusée.', object_type='Lease', object_id=renewal.lease.lease_id)
        else:
            messages.error(request, 'Action invalide.')
            return redirect('office_lifecycle_requests')
        renewal.save(update_fields=['status', 'decided_at', 'decided_by'])
    messages.success(request, 'Demande de renouvellement traitée.')
    return redirect('office_lifecycle_requests')


@staff_required
@require_POST
def decide_exit(request, exit_id):
    with transaction.atomic():
        exit_request = get_object_or_404(LeaseExit.objects.select_for_update().select_related('lease', 'lease__property'), exit_id=exit_id)
        if exit_request.status != 'REQUESTED' or exit_request.lease.status != 'ACTIVE':
            messages.error(request, 'Cette demande n’est plus traitable.')
            return redirect('office_lifecycle_requests')
        action = request.POST.get('action')
        exit_request.decided_by = request.user
        exit_request.decided_at = timezone.now()
        if action == 'approve':
            lease = Lease.objects.select_for_update().get(pk=exit_request.lease_id)
            lease.status = 'TERMINATION'
            lease.end_date = exit_request.requested_date
            lease.save(update_fields=['status', 'end_date'])
            exit_request.status = 'APPROVED'
            Notification.objects.create(recipient=lease.tenant, level='SUCCESS', title='Sortie acceptée', message=f'La demande de sortie de {lease.lease_id} a été acceptée. Un PV de sortie doit être réalisé.', object_type='Lease', object_id=lease.lease_id)
        elif action == 'refuse':
            exit_request.status = 'REFUSED'
            Notification.objects.create(recipient=exit_request.lease.tenant, level='INFO', title='Sortie refusée', message=f'La demande de sortie {exit_request.exit_id} a été refusée.', object_type='Lease', object_id=exit_request.lease_id)
        else:
            messages.error(request, 'Action invalide.')
            return redirect('office_lifecycle_requests')
        exit_request.save(update_fields=['status', 'decided_at', 'decided_by'])
    messages.success(request, 'Demande de sortie traitée.')
    return redirect('office_lifecycle_requests')
