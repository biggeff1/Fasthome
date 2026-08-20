from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from properties.models import Property
from notifications.models import Notification
from leasing.models import RentalCase
from .models import VisitRequest


@login_required
def request_visit(request, property_id):
    if not request.user.is_certified:
        messages.error(request, 'Un compte certifié est nécessaire pour demander une visite.')
        return redirect('property_detail', property_id=property_id)
    prop = get_object_or_404(Property, property_id=property_id, status='AVAILABLE')
    if request.method == 'POST':
        visit = VisitRequest.objects.create(
            property=prop,
            requester=request.user,
            requested_date=request.POST.get('requested_date'),
            requested_time_slot=request.POST.get('requested_time_slot', ''),
        )
        Notification.objects.create(recipient=prop.owner, level='ACTION', title='Demande de visite à valider', message='Une demande de visite pour votre logement nécessite votre validation. L’identité du demandeur reste masquée à cette étape.', object_type='VisitRequest', object_id=visit.visit_id)
        messages.success(request, f'Demande {visit.visit_id} envoyée à Fasthome et au bailleur.')
        return redirect('property_detail', property_id=prop.property_id)
    return render(request, 'visits/request.html', {'property': prop})


@login_required
def landlord_visit_decision(request, visit_id):
    visit = get_object_or_404(VisitRequest.objects.select_related('property'), visit_id=visit_id, property__owner=request.user)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            visit.landlord_approved = True
            visit.refresh_confirmation_status()
            visit.save(update_fields=['landlord_approved', 'status'])
            if visit.fasthome_approved and visit.landlord_approved:
                Notification.objects.create(recipient=visit.requester, level='SUCCESS', title='Visite confirmée', message='Fasthome et le bailleur ont validé votre demande de visite.', object_type='VisitRequest', object_id=visit.visit_id)
        elif action == 'refuse':
            visit.status = 'REFUSED'
            visit.save(update_fields=['status'])
            Notification.objects.create(recipient=visit.requester, level='INFO', title='Demande de visite non confirmée', message='Votre demande de visite n’a pas été confirmée.', object_type='VisitRequest', object_id=visit.visit_id)
    return redirect('activity')


@login_required
def tenant_decision(request, visit_id):
    visit = get_object_or_404(VisitRequest, visit_id=visit_id, requester=request.user, status='COMPLETED')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'take':
            case, created = RentalCase.objects.get_or_create(
                visit=visit,
                defaults={'property': visit.property, 'tenant': request.user, 'status': 'OPEN'},
            )
            visit.property.status = 'UNDER_REVIEW'
            visit.property.save(update_fields=['status', 'updated_at'])
            Notification.objects.create(recipient=request.user, level='SUCCESS', title='Dossier de location créé', message=f'Votre dossier {case.case_id} est maintenant en traitement.', object_type='RentalCase', object_id=case.case_id)
            messages.success(request, 'Votre choix a été enregistré. Fasthome traite maintenant votre dossier.')
            return redirect('activity')
        if action == 'decline':
            messages.success(request, 'Votre décision de ne pas prendre le logement a été enregistrée.')
            return redirect('activity')
    return render(request, 'visits/decision.html', {'visit': visit})
