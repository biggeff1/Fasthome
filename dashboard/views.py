import calendar
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from properties.models import Favorite, Property
from visits.models import VisitRequest
from visits.views import (
    visit_fasthome_approved, visit_fasthome_refused, visit_confirmed, visit_completed,
)
from leasing.models import RentalCase, Lease, RenewalRequest, LeaseExit
from contracts.models import Contract
from inspections.models import InspectionReport
from payments.models import PaymentReceipt, LandlordPayout, RentInstallment
from notifications.models import Notification
from notifications.services import contract_created, contract_uploaded, contract_validated, inspection_validated, payment_recorded, payout_completed, lease_officialized, rental_case_accepted
from users.models import IdentityVerification, User
from .office_forms import ReceiptForm, PayoutForm


def staff_required(view):
    return user_passes_test(lambda u: u.is_authenticated and (u.is_staff or u.is_superuser))(view)


def admin_required(view):
    return user_passes_test(lambda u: u.is_authenticated and u.is_superuser)(view)


def _next_month(value):
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    return value.replace(year=year, month=month, day=min(value.day, calendar.monthrange(year, month)[1]))


def _ensure_next_installment(lease, from_installment=None):
    due_date = _next_month(from_installment.due_date) if from_installment is not None else (lease.start_date or timezone.localdate())
    installment, _ = RentInstallment.objects.get_or_create(lease=lease, due_date=due_date, defaults={'amount_due': lease.monthly_rent, 'status': 'UPCOMING'})
    return installment


@login_required
def favorites(request):
    items = (Favorite.objects.filter(user=request.user)
             .select_related('property', 'property__property_type', 'property__owner')
             .prefetch_related('property__photos')
             .order_by('-created_at'))
    return render(request, 'dashboard/favorites.html', {'items': items})


@login_required
@require_POST
def toggle_favorite(request, property_id):
    prop = get_object_or_404(Property.objects.only('pk', 'property_id'), property_id=property_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, property=prop)
    if not created:
        favorite.delete()
    liked = created
    wants_json = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')
    if wants_json:
        return JsonResponse({'success': True, 'liked': liked, 'property_id': prop.property_id})
    messages.success(request, 'Logement ajouté aux favoris.' if liked else 'Logement retiré des favoris.')
    return redirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or 'home')


@login_required
def notifications(request):
    qs = request.user.notifications.all().order_by('-created_at')
    unread_count = qs.filter(is_read=False).count()
    items = list(qs[:100])
    return render(request, 'dashboard/notifications.html', {'items': items, 'unread_count': unread_count})


@login_required
def notification_unread_count(request):
    return JsonResponse({'success': True, 'unread_count': request.user.notifications.filter(is_read=False).count()})


@login_required
def activity(request):
    visits = request.user.visit_requests.select_related('property', 'property__property_type').prefetch_related('property__photos').order_by('-created_at')[:20]
    landlord_visits = VisitRequest.objects.filter(property__owner=request.user, status='REQUESTED').select_related('property', 'property__property_type').order_by('-created_at')[:20]
    cases = request.user.rental_cases_as_tenant.select_related('property', 'property__property_type', 'visit').order_by('-created_at')[:20]
    leases = request.user.leases_as_tenant.select_related('property', 'property__property_type', 'landlord').order_by('-created_at')[:20]
    properties = request.user.properties.select_related('property_type', 'publication').prefetch_related('photos').order_by('-created_at')[:20]
    landlord_leases = request.user.leases_as_landlord.select_related('property', 'property__property_type', 'tenant').order_by('-created_at')[:20]
    return render(request, 'dashboard/activity.html', {
        'visits': visits, 'landlord_visit_requests': landlord_visits, 'cases': cases,
        'leases': leases, 'properties': properties, 'landlord_leases': landlord_leases,
    })


@login_required
def visits_page(request):
    visits = (request.user.visit_requests
              .select_related('property', 'property__property_type')
              .prefetch_related('property__photos')
              .order_by('-created_at')[:50])
    landlord_visits = (VisitRequest.objects.filter(property__owner=request.user)
                       .select_related('property', 'property__property_type')
                       .prefetch_related('property__photos')
                       .order_by('-created_at')[:50])
    return render(request, 'dashboard/visits.html', {
        'visits': visits,
        'landlord_visit_requests': landlord_visits,
    })


@login_required
def lease_detail(request, lease_id):
    lease = get_object_or_404(Lease.objects.select_related('property', 'property__property_type', 'tenant', 'landlord'), lease_id=lease_id)
    if not (request.user.is_staff or request.user.is_superuser or request.user.pk in {lease.tenant_id, lease.landlord_id}):
        return redirect('activity')
    contracts = lease.contracts.all().select_related('lease')
    reports = lease.inspection_reports.all().select_related('property')
    installments = lease.installments.all().order_by('due_date')
    receipts = lease.payment_receipts.all().order_by('-received_at')
    payouts = lease.landlord_payouts.all().order_by('-paid_at')
    return render(request, 'dashboard/lease_detail.html', {'lease': lease, 'contracts': contracts, 'reports': reports, 'installments': installments, 'receipts': receipts, 'payouts': payouts})


@staff_required
def office_dashboard(request):
    return render(request, 'dashboard/office.html', {
        'pending_publications': Property.objects.filter(publication__status__in=['SUBMITTED', 'UNDER_REVIEW', 'CORRECTION_REQUIRED']).count(),
        'pending_verifications': IdentityVerification.objects.filter(status__in=['PENDING', 'IN_REVIEW', 'RETRY']).count(),
        'pending_visits': VisitRequest.objects.filter(status='REQUESTED').count(),
        'cases': RentalCase.objects.filter(status__in=['OPEN', 'UNDER_REVIEW']).count(),
        'pending_contracts': Contract.objects.filter(status__in=['PENDING', 'UPLOADED']).count(),
        'pending_reports': InspectionReport.objects.filter(status='DRAFT').count(),
        'lifecycle_requests': RenewalRequest.objects.filter(status='REQUESTED').count() + LeaseExit.objects.filter(status='REQUESTED').count(),
        'payments': PaymentReceipt.objects.count(), 'payouts': LandlordPayout.objects.count(),
        'is_admin': request.user.is_superuser,
    })


@admin_required
def office_users(request):
    users = User.objects.order_by('-created_at')[:250]
    return render(request, 'dashboard/office_users.html', {'users': users})


@staff_required
@require_POST
def office_approve_visit(request, visit_id):
    with transaction.atomic():
        visit = get_object_or_404(VisitRequest.objects.select_for_update().select_related('property', 'requester'), visit_id=visit_id)
        if visit.status != 'REQUESTED': messages.error(request, 'Cette demande de visite n’est plus en attente.'); return redirect('office_visits')
        if request.POST.get('action') == 'approve':
            visit.fasthome_approved = True
            if visit.landlord_approved: visit.status = 'CONFIRMED'
            visit.save(update_fields=['fasthome_approved', 'status'])
            if visit.status == 'CONFIRMED':
                visit_confirmed(visit)
            else:
                visit_fasthome_approved(visit)
        elif request.POST.get('action') == 'refuse':
            visit.status = 'REFUSED'; visit.save(update_fields=['status'])
            visit_fasthome_refused(visit)
        else: messages.error(request, 'Action invalide.'); return redirect('office_visits')
    return redirect('office_visits')


@staff_required
@require_POST
def office_complete_visit(request, visit_id):
    with transaction.atomic():
        visit = get_object_or_404(VisitRequest.objects.select_for_update().select_related('property', 'requester'), visit_id=visit_id)
        if visit.status != 'CONFIRMED': messages.error(request, 'La visite n’est plus confirmée.'); return redirect('office_visits')
        visit.status = 'COMPLETED'; visit.completed_at = timezone.now(); visit.completed_by = request.user; visit.save(update_fields=['status', 'completed_at', 'completed_by'])
        visit_completed(visit)
    return redirect('office_visits')


@staff_required
def office_visits(request):
    visits = VisitRequest.objects.select_related('property', 'property__property_type', 'requester').prefetch_related('property__photos').order_by('-created_at')
    return render(request, 'dashboard/office_visits.html', {'visits': visits})


@staff_required
@require_POST
def office_approve_visit(request, visit_id):
    return redirect('office_visits')


@staff_required
@require_POST
def office_complete_visit(request, visit_id):
    return redirect('office_visits')


@staff_required
@require_POST
def office_approve_visit(request, visit_id):
    return redirect('office_visits')


@staff_required
@require_POST
def office_complete_visit(request, visit_id):
    return redirect('office_visits')
