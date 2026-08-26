from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from properties.models import Property, PropertyPublication
from visits.models import VisitRequest


@login_required
def my_properties(request):
    properties = (
        Property.objects.filter(owner=request.user)
        .select_related('property_type', 'publication')
        .prefetch_related('photos')
        .order_by('-updated_at', '-created_at')
    )

    counts = {
        'all': properties.count(),
        'available': properties.filter(status='AVAILABLE').count(),
        'review': properties.filter(Q(status='UNDER_REVIEW') | Q(publication__status__in=['SUBMITTED', 'UNDER_REVIEW'])).distinct().count(),
        'draft': properties.filter(Q(publication__isnull=True) | Q(publication__status__in=['DRAFT', 'CORRECTION_REQUIRED'])).distinct().count(),
        'rented': properties.filter(Q(status='RENTED') | Q(publication__status='RENTED')).distinct().count(),
    }

    return render(request, 'dashboard/my_properties.html', {
        'properties': properties,
        'counts': counts,
    })


@login_required
def property_manage(request, property_id):
    property_obj = get_object_or_404(
        Property.objects.filter(owner=request.user)
        .select_related('property_type', 'publication')
        .prefetch_related('photos', 'features'),
        property_id=property_id,
    )

    publication = getattr(property_obj, 'publication', None)
    visit_requests = (
        VisitRequest.objects.filter(property=property_obj)
        .order_by('-created_at')[:10]
    )

    return render(request, 'dashboard/property_manage.html', {
        'property': property_obj,
        'publication': publication,
        'photos': property_obj.photos.all().order_by('order', 'id'),
        'visit_requests': visit_requests,
    })
