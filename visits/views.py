from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from properties.models import Property
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
        messages.success(request, f'Demande {visit.visit_id} envoyée à Fasthome.')
        return redirect('property_detail', property_id=prop.property_id)
    return render(request, 'visits/request.html', {'property': prop})
