from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from properties.models import Favorite, Property
from visits.models import VisitRequest
from leasing.models import RentalCase, Lease
from contracts.models import Contract
from inspections.models import InspectionReport
from payments.models import PaymentReceipt, LandlordPayout, RentInstallment
from notifications.models import Notification
from .office_forms import ReceiptForm, PayoutForm


def staff_required(view):
    return user_passes_test(lambda u: u.is_authenticated and (u.is_staff or u.is_superuser))(view)


@login_required
def favorites(request):
    return render(request, 'dashboard/favorites.html', {'items': Favorite.objects.filter(user=request.user).select_related('property', 'property__property_type').order_by('-created_at')})


@login_required
@require_POST
def toggle_favorite(request, property_id):
    prop = get_object_or_404(Property, property_id=property_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, property=prop)
    if not created:
        favorite.delete()
    messages.success(request, 'Logement ajouté aux favoris.' if created else 'Logement retiré des favoris.')
    return redirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or 'home')


@login_required
def notifications(request):
    items = request.user.notifications.order_by('-created_at')[:100]
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'dashboard/notifications.html', {'items': items})


@login_required
def activity(request):
    return render(request, 'dashboard/activity.html', {
        'visits': request.user.visit_requests.select_related('property', 'property__property_type').order_by('-created_at')[:20],
        'cases': request.user.rental_cases_as_tenant.select_related('property').order_by('-created_at')[:20],
        'leases': request.user.leases_as_tenant.select_related('property').order_by('-created_at')[:20],
        'properties': request.user.properties.select_related('property_type', 'publication').order_by('-created_at')[:20],
        'landlord_leases': request.user.leases_as_landlord.select_related('property').order_by('-created_at')[:20],
    })


@login_required
def lease_detail(request, lease_id):
    lease = get_object_or_404(Lease.objects.select_related('property', 'tenant', 'landlord'), lease_id=lease_id)
    if not (request.user.is_staff or request.user.is_superuser or request.user.pk in {lease.tenant_id, lease.landlord_id}):
        return redirect('activity')
    return render(request, 'dashboard/lease_detail.html', {'lease': lease, 'contracts': lease.contracts.all(), 'reports': lease.inspection_reports.all(), 'installments': lease.installments.order_by('due_date'), 'receipts': lease.payment_receipts.order_by('-received_at'), 'payouts': lease.landlord_payouts.order_by('-paid_at')})


@staff_required
def office_dashboard(request):
    return render(request, 'dashboard/office.html', {'pending_publications': Property.objects.filter(publication__status__in=['SUBMITTED', 'UNDER_REVIEW']).count(), 'pending_visits': VisitRequest.objects.filter(status='REQUESTED').count(), 'cases': RentalCase.objects.filter(status__in=['OPEN', 'UNDER_REVIEW']).count(), 'pending_contracts': Contract.objects.filter(status__in=['PENDING', 'UPLOADED']).count(), 'pending_reports': InspectionReport.objects.filter(status='DRAFT').count(), 'payments': PaymentReceipt.objects.count(), 'payouts': LandlordPayout.objects.count()})


@staff_required
@require_POST
def office_approve_visit(request, visit_id):
    with transaction.atomic():
        visit = get_object_or_404(VisitRequest.objects.select_for_update(), visit_id=visit_id)
        if visit.status != 'REQUESTED':
            messages.error(request, 'Cette demande de visite n’est plus en attente.')
            return redirect('office_visits')
        if request.POST.get('action') == 'approve':
            visit.fasthome_approved = True
            if visit.landlord_approved:
                visit.status = 'CONFIRMED'
            visit.save(update_fields=['fasthome_approved', 'status'])
        elif request.POST.get('action') == 'refuse':
            visit.status = 'REFUSED'
            visit.save(update_fields=['status'])
        else:
            messages.error(request, 'Action invalide.')
            return redirect('office_visits')
        Notification.objects.create(recipient=visit.requester, level='INFO', title='Mise à jour de votre demande de visite', message='Votre demande de visite a été mise à jour par Fasthome.', object_type='VisitRequest', object_id=visit.visit_id)
    return redirect('office_visits')


@staff_required
@require_POST
def office_complete_visit(request, visit_id):
    with transaction.atomic():
        visit = get_object_or_404(VisitRequest.objects.select_for_update(), visit_id=visit_id)
        if visit.status != 'CONFIRMED':
            messages.error(request, 'La visite n’est plus confirmée.')
            return redirect('office_visits')
        visit.status = 'COMPLETED'
        visit.completed_at = timezone.now()
        visit.completed_by = request.user
        visit.save(update_fields=['status', 'completed_at', 'completed_by'])
        Notification.objects.create(recipient=visit.requester, level='SUCCESS', title='Visite effectuée', message='La visite est enregistrée. Vous pouvez maintenant choisir de prendre ou non le logement.', object_type='VisitRequest', object_id=visit.visit_id)
    return redirect('office_visits')


@staff_required
def office_visits(request):
    return render(request, 'dashboard/office_visits.html', {'visits': VisitRequest.objects.select_related('property').order_by('-created_at')})


@staff_required
def office_cases(request):
    return render(request, 'dashboard/office_cases.html', {'cases': RentalCase.objects.select_related('property', 'tenant', 'visit').order_by('-created_at')})


@staff_required
@require_POST
def office_accept_case(request, case_id):
    with transaction.atomic():
        case = get_object_or_404(RentalCase.objects.select_for_update().select_related('property', 'tenant', 'visit'), case_id=case_id)
        if case.status not in {'OPEN', 'UNDER_REVIEW'} or case.visit.status != 'COMPLETED':
            messages.error(request, 'Ce dossier n’est pas éligible à la contractualisation.')
            return redirect('office_cases')
        lease, _ = Lease.objects.select_for_update().get_or_create(rental_case=case, defaults={'property': case.property, 'tenant': case.tenant, 'landlord': case.property.owner, 'monthly_rent': case.property.monthly_rent or Decimal('0'), 'guarantee_amount': case.property.guarantee_amount, 'status': 'PENDING'})
        Contract.objects.get_or_create(lease=lease, contract_type='TENANT')
        Contract.objects.get_or_create(lease=lease, contract_type='LANDLORD')
        InspectionReport.objects.get_or_create(lease=lease, property=lease.property, report_type='ENTRY', defaults={'status': 'DRAFT'})
        case.status = 'CONTRACTING'
        case.save(update_fields=['status'])
        Notification.objects.create(recipient=case.tenant, level='ACTION', title='Contrats en préparation', message=f'Les contrats de la location {lease.lease_id} sont en préparation.', object_type='Lease', object_id=lease.lease_id)
        Notification.objects.create(recipient=lease.landlord, level='ACTION', title='Contrat bailleur en préparation', message=f'Le contrat du logement {lease.property.property_id} est en préparation.', object_type='Lease', object_id=lease.lease_id)
        messages.success(request, f'Location {lease.lease_id} prête pour la contractualisation.')
    return redirect('office_cases')


@staff_required
def office_contracts(request):
    return render(request, 'dashboard/office_contracts.html', {'contracts': Contract.objects.select_related('lease', 'lease__property').order_by('-contract_id')})


@staff_required
@require_POST
def office_contract_upload(request, contract_id):
    contract = get_object_or_404(Contract, contract_id=contract_id)
    if not request.FILES.get('signed_document'):
        messages.error(request, 'Aucun document signé fourni.')
        return redirect('office_contracts')
    with transaction.atomic():
        contract = Contract.objects.select_for_update().get(pk=contract.pk)
        if contract.status not in {'PENDING', 'REJECTED'}:
            messages.error(request, 'Ce contrat ne peut plus être téléversé dans son état actuel.')
            return redirect('office_contracts')
        contract.signed_document = request.FILES['signed_document']
        contract.status = 'UPLOADED'
        contract.uploaded_at = timezone.now()
        contract.uploaded_by = request.user
        contract.save()
    messages.success(request, 'Contrat signé téléversé.')
    return redirect('office_contracts')


@staff_required
@require_POST
def office_contract_validate(request, contract_id):
    with transaction.atomic():
        contract = get_object_or_404(Contract.objects.select_for_update(), contract_id=contract_id)
        if contract.status != 'UPLOADED' or not contract.signed_document or not contract.uploaded_by_id:
            messages.error(request, 'Ce contrat ne peut pas être validé dans son état actuel.')
            return redirect('office_contracts')
        contract.status = 'VALIDATED'
        contract.signed_at = timezone.now()
        contract.save(update_fields=['status', 'signed_at'])
        messages.success(request, 'Contrat validé.')
    return redirect('office_contracts')


@staff_required
def office_reports(request):
    return render(request, 'dashboard/office_reports.html', {'reports': InspectionReport.objects.select_related('lease', 'property').order_by('-created_at')})


@staff_required
@require_POST
def office_report_validate(request, report_id):
    with transaction.atomic():
        report = get_object_or_404(InspectionReport.objects.select_for_update(), report_id=report_id)
        if report.status != 'DRAFT':
            messages.error(request, 'Ce PV n’est plus en brouillon.')
            return redirect('office_reports')
        report.status = 'VALIDATED'
        report.save(update_fields=['status'])
        messages.success(request, 'PV validé.')
    return redirect('office_reports')


@staff_required
@require_POST
def office_officialize_lease(request, lease_id):
    with transaction.atomic():
        lease = get_object_or_404(Lease.objects.select_for_update().select_related('rental_case'), lease_id=lease_id)
        if lease.status != 'PENDING':
            messages.error(request, 'Cette location n’est plus en attente d’officialisation.')
            return redirect('office_dashboard')
        if lease.rental_case.status != 'CONTRACTING' or lease.rental_case.visit.status != 'COMPLETED':
            messages.error(request, 'Le dossier ou la visite ne permet pas encore l’officialisation.')
            return redirect('office_dashboard')
        contracts = list(lease.contracts.all())
        reports = list(lease.inspection_reports.filter(report_type='ENTRY'))
        if len([c for c in contracts if c.status == 'VALIDATED']) != 2 or len([c for c in contracts if c.contract_type == 'TENANT']) != 1 or len([c for c in contracts if c.contract_type == 'LANDLORD']) != 1 or not any(r.status == 'VALIDATED' for r in reports):
            messages.error(request, 'Impossible d’officialiser : les deux contrats et le PV d’entrée doivent être validés.')
            return redirect('office_dashboard')
        property_obj = Property.objects.select_for_update().get(pk=lease.property_id)
        if property_obj.status != 'UNDER_REVIEW':
            messages.error(request, 'Le logement n’est pas dans l’état attendu pour l’officialisation.')
            return redirect('office_dashboard')
        lease.status = 'ACTIVE'
        lease.save(update_fields=['status'])
        property_obj.status = 'RENTED'
        property_obj.save(update_fields=['status', 'updated_at'])
        publication = getattr(property_obj, 'publication', None)
        if publication:
            publication.status = 'RENTED'
            publication.save(update_fields=['status', 'updated_at'])
        Notification.objects.create(recipient=lease.tenant, level='SUCCESS', title='Location officielle', message=f'Votre location {lease.lease_id} est maintenant officielle.', object_type='Lease', object_id=lease.lease_id)
        Notification.objects.create(recipient=lease.landlord, level='SUCCESS', title='Logement officiellement loué', message=f'Votre logement {lease.property.property_id} est maintenant officiellement loué.', object_type='Lease', object_id=lease.lease_id)
        messages.success(request, 'Location officialisée et logement retiré du Matching.')
    return redirect('office_dashboard')


@staff_required
@require_POST
def office_receipt(request):
    form = ReceiptForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            installment = RentInstallment.objects.select_for_update().get(pk=form.cleaned_data['installment'].pk)
            received = sum((p.amount for p in installment.payments.all()), Decimal('0'))
            amount = form.cleaned_data['amount']
            if received + amount > installment.amount_due:
                form.add_error('amount', 'Le solde de cette échéance a changé. Réessayez avec le montant restant.')
            else:
                data = {k: v for k, v in form.cleaned_data.items() if k in {'lease', 'installment', 'amount', 'received_at', 'reference', 'notes'}}
                obj = PaymentReceipt.objects.create(recorded_by=request.user, **data)
                total = received + obj.amount
                installment.status = 'PAID' if total == installment.amount_due else 'PARTIAL'
                installment.save(update_fields=['status'])
                Notification.objects.create(recipient=obj.lease.tenant, level='SUCCESS', title='Paiement enregistré', message=f'{obj.amount} FC ont été enregistrés par Fasthome.', object_type='PaymentReceipt', object_id=obj.payment_id)
                messages.success(request, f'Paiement {obj.payment_id} enregistré.')
                return redirect('office_dashboard')
    return render(request, 'dashboard/payment_form.html', {'form': form, 'title': 'Enregistrer un loyer reçu'})


@staff_required
@require_POST
def office_payout(request):
    form = PayoutForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            installment = RentInstallment.objects.select_for_update().get(pk=form.cleaned_data['installment'].pk)
            received = sum((p.amount for p in installment.payments.all()), Decimal('0'))
            already_paid = sum((p.amount for p in installment.payouts.all()), Decimal('0'))
            amount = form.cleaned_data['amount']
            if already_paid + amount > received:
                form.add_error('amount', 'Le montant disponible à verser a changé. Réessayez avec le solde réellement reçu.')
            else:
                data = {k: v for k, v in form.cleaned_data.items() if k in {'lease', 'installment', 'amount', 'paid_at', 'reference'}}
                obj = LandlordPayout.objects.create(recorded_by=request.user, **data)
                Notification.objects.create(recipient=obj.lease.landlord, level='SUCCESS', title='Versement au bailleur enregistré', message=f'{obj.amount} FC ont été enregistrés comme versés.', object_type='LandlordPayout', object_id=obj.payout_id)
                messages.success(request, f'Versement {obj.payout_id} enregistré.')
                return redirect('office_dashboard')
    return render(request, 'dashboard/payment_form.html', {'form': form, 'title': 'Enregistrer un versement au bailleur'})
