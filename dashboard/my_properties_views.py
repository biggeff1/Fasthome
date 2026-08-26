from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from properties.models import Property

@login_required
def my_properties(request):
    properties = list(request.user.properties.select_related('property_type', 'publication').prefetch_related('photos').order_by('-updated_at', '-created_at'))
    counts = {
        'all': len(properties),
        'available': sum(p.status == 'AVAILABLE' for p in properties),
        'review': sum(p.status == 'UNDER_REVIEW' or (getattr(p, 'publication', None) and p.publication.status in {'SUBMITTED', 'UNDER_REVIEW'}) for p in properties),
        'draft': sum(p.status == 'DRAFT' or (getattr(p, 'publication', None) and p.publication.status in {'DRAFT', 'CORRECTION_REQUIRED'}) for p in properties),
        'rented': sum(p.status == 'RENTED' for p in properties),
    }
    return render(request, 'dashboard/my_properties.html', {'properties': properties, 'counts': counts})

@login_required
def property_manage(request, property_id):
    prop = get_object_or_404(Property.objects.select_related('property_type', 'publication').prefetch_related('photos'), property_id=property_id, owner=request.user)
    return render(request, 'dashboard/property_manage.html', {'property': prop, 'publication': getattr(prop, 'publication', None)})
