from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from properties.models import Favorite, Property
from visits.models import VisitRequest
from leasing.models import RentalCase, Lease
from contracts.models import Contract
from inspections.models import InspectionReport
from payments.models import PaymentReceipt, LandlordPayout
from notifications.models import Notification


def staff_required(view):
    return user_passes_test(lambda u: u.is_authenticated and (u.is_staff or u.is_superuser))(view)


@login_required
def favorites(request):
    items = Favorite.objects.filter(user=request.user).select_related('property', 'property__property_type').order_by('-created_at')
    return render(request, 'dashboard/favorites.html', {'items': items})


@login_required
def toggle_favorite(request, property_id):
    prop = get_object_or_404(Property, property_id=property_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, property=prop)
    if not created:
        favorite.delete()
        messages.success(request, 'Logement retiré des favoris.')
    else:
        messages.success(request, 'Logement ajouté aux favoris.')
    return redirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or 'home')


@login_required
def notifications(request):
    items = request.user.notifications.order_by('-created_at')[:100]
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'dashboard/notifications.html', {'items': items})


@login_required
def activity(request):
    visits = request.user.visit_requests.select_related('property', 'property__property_type').order_by('-created_at')[:20]
    cases = request.user.rental_cases_as_tenant.select_related('property').order_by('-created_at')[:20]
    leases = request.user.leases_as_tenant.select_related('property').order_by('-created_at')[:20]
    properties = request.user.properties.select_related('property_type', 'publication').order_by('-created_at')[:20]
    landlord_leases = request.user.leases_as_landlord.select_related('property').order_by('-created_at')[:20]
    return render(request, 'dashboard/activity.html', {
        'visits': visits, 'cases': cases, 'leases': leases,
        'properties': properties, 'landlord_leases': landlord_leases,
    })


@login_required
def lease_detail(request, lease_id):
    lease = get_object_or_404(Lease.objects.select_related('property', 'tenant', 'landlord'), lease_id=lease_id)
    if request.user not in (lease.tenant, lease.landlord) and not request.user.is_staff:
        return redirect('activity')
    return render(request, 'dashboard/lease_detail.html', {
        'lease': lease,
        'contracts': lease.contracts.all(),
        'reports': lease.inspection_reports.all(),
        'installments': lease.installments.order_by('due_date'),
        'receipts': lease.payment_receipts.order_by('-received_at'),
        'payouts': lease.landlord_payouts.order_by('-paid_at'),
    })


@staff_required
def office_dashboard(request):
    return render(request, 'dashboard/office.html', {
        'pending_publications': Property.objects.filter(publication__status__in=['SUBMITTED', 'UNDER_REVIEW']).count(),
        'pending_visits': VisitRequest.objects.filter(status='REQUESTED').count(),
        'cases': RentalCase.objects.filter(status__in=['OPEN', 'UNDER_REVIEW']).count(),
        'pending_contracts': Contract.objects.filter(status__in=['PENDING', 'UPLOADED']).count(),
        'pending_reports': InspectionReport.objects.filter(status='DRAFT').count(),
        'payments': PaymentReceipt.objects.count(),
        'payouts': LandlordPayout.objects.count(),
    })


@staff_required
def office_visits(request):
    visits = VisitRequest.objects.select_related('property', 'requester').order_by('-created_at')
    return render(request, 'dashboard/office_visits.html', {'visits': visits})


@staff_required
def office_approve_visit(request, visit_id):
    visit = get_object_or_404(VisitRequest, visit_id=visit_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        visit.fasthome_approved = action == 'approve'
        if action == 'refuse':
            visit.status = 'REFUSED'
        visit.refresh_confirmation_status()
        if action == 'approve' and visit.fasthome_approved and visit.landlord_approved:
            visit.status = 'CONFIRMED'
        visit.save(update_fields=['fasthome_approved', 'landlord_approved', 'status'])
        Notification.objects.create(recipient=visit.requester, level='INFO', title='Mise à jour de votre demande de visite', message='Votre demande de visite a été mise à jour par Fasthome.', object_type='VisitRequest', object_id=visit.visit_id)
    return redirect('office_visits')


@staff_required
def office_complete_visit(request, visit_id):
    visit = get_object_or_404(VisitRequest, visit_id=visit_id, status='CONFIRMED')
    if request.method == 'POST':
        visit.status = 'COMPLETED'
        visit.completed_at = timezone.now()
        visit.completed_by = request.user
        visit.save(update_fields=['status', 'completed_at', 'completed_by'])
        Notification.objects.create(recipient=visit.requester, level='SUCCESS', title='Visite effectuée', message='La visite est maintenant enregistrée comme effectuée. Vous pouvez choisir de prendre ou non le logement.', object_type='VisitRequest', object_id=visit.visit_id)
    return redirect('office_visits')
