from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .models import Property, PropertyPublication, PropertyType


def home(request):
    properties = Property.objects.filter(status='AVAILABLE', publication__status='PUBLISHED').select_related('property_type')[:24]
    return render(request, 'home.html', {'properties': properties})


def property_detail(request, property_id):
    prop = get_object_or_404(Property.objects.select_related('property_type'), property_id=property_id)
    return render(request, 'properties/detail.html', {'property': prop})

@login_required
def property_create(request):
    if not request.user.is_certified:
        messages.error(request, 'Votre compte doit être certifié avant de publier un logement.')
        return redirect('home')
    types = PropertyType.objects.filter(active=True)
    if request.method == 'POST':
        prop_type = get_object_or_404(PropertyType, pk=request.POST.get('property_type'))
        prop = Property.objects.create(
            owner=request.user,
            property_type=prop_type,
            furnished=request.POST.get('furnished') == 'yes',
            province=request.POST.get('province', '').strip(),
            city_or_territory=request.POST.get('city_or_territory', '').strip(),
            administrative_subdivision=request.POST.get('administrative_subdivision', '').strip(),
            neighborhood=request.POST.get('neighborhood', '').strip(),
            exact_address=request.POST.get('exact_address', '').strip(),
            google_maps_url=request.POST.get('google_maps_url', '').strip(),
            latitude=request.POST.get('latitude') or None,
            longitude=request.POST.get('longitude') or None,
            bedroom_count=max(0, int(request.POST.get('bedroom_count', 0))),
            living_room_count=max(0, int(request.POST.get('living_room_count', 0))),
            bathroom_count=max(0, int(request.POST.get('bathroom_count', 0))),
            toilet_count=max(0, int(request.POST.get('toilet_count', 0))),
            has_kitchen=request.POST.get('has_kitchen') == 'yes',
            floor=request.POST.get('floor', '').strip(),
            ceiling_type=request.POST.get('ceiling_type', '').strip(),
            floor_type=request.POST.get('floor_type', '').strip(),
            monthly_rent=request.POST.get('monthly_rent') or None,
            guarantee_amount=request.POST.get('guarantee_amount') or None,
            max_occupants=max(1, int(request.POST.get('max_occupants', 1))),
        )
        publication = PropertyPublication.objects.create(property=prop, status='DRAFT')
        messages.success(request, f'Brouillon {publication.publication_id} créé pour le logement {prop.property_id}.')
        return redirect('property_edit', property_id=prop.property_id)
    return render(request, 'properties/form.html', {'types': types, 'creating': True})

@login_required
def property_edit(request, property_id):
    prop = get_object_or_404(Property.objects.select_related('publication'), property_id=property_id, owner=request.user)
    if request.method == 'POST':
        prop.province = request.POST.get('province', '').strip()
        prop.city_or_territory = request.POST.get('city_or_territory', '').strip()
        prop.administrative_subdivision = request.POST.get('administrative_subdivision', '').strip()
        prop.neighborhood = request.POST.get('neighborhood', '').strip()
        prop.exact_address = request.POST.get('exact_address', '').strip()
        prop.google_maps_url = request.POST.get('google_maps_url', '').strip()
        prop.monthly_rent = request.POST.get('monthly_rent') or None
        prop.guarantee_amount = request.POST.get('guarantee_amount') or None
        prop.max_occupants = max(1, int(request.POST.get('max_occupants', prop.max_occupants)))
        prop.save(update_fields=['province','city_or_territory','administrative_subdivision','neighborhood','exact_address','google_maps_url','monthly_rent','guarantee_amount','max_occupants','updated_at'])
        if request.POST.get('submit') == '1':
            prop.publication.status = 'SUBMITTED'
            prop.publication.submitted_at = timezone.now()
            prop.publication.save(update_fields=['status','submitted_at','updated_at'])
            prop.status = 'UNDER_REVIEW'
            prop.save(update_fields=['status','updated_at'])
            messages.success(request, 'Publication soumise à Fasthome pour vérification.')
        else:
            messages.success(request, 'Brouillon enregistré.')
        return redirect('property_edit', property_id=prop.property_id)
    return render(request, 'properties/form.html', {'property': prop, 'types': PropertyType.objects.filter(active=True), 'creating': False})
