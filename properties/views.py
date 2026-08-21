from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import (
    Bathroom, Bedroom, CollaborationConsent, Kitchen, LivingRoom, Property,
    PropertyDeclaration, PropertyFeature, PropertyPublication, PropertyType, Toilet,
)

FEATURE_OPTIONS = [
    ('courtyard', 'Cour'), ('garden', 'Jardin'), ('terrace', 'Terrasse'),
    ('balcony', 'Balcon'), ('veranda', 'Véranda'), ('parking', 'Parking'), ('garage', 'Garage'),
    ('water_network', 'Réseau d’eau'), ('borehole', 'Forage'), ('cistern', 'Citerne'), ('well', 'Puits'),
    ('electric_network', 'Réseau électrique'), ('generator', 'Groupe électrogène'), ('solar', 'Solaire'),
    ('security_guard', 'Gardien'), ('fence', 'Clôture'), ('secure_door', 'Porte sécurisée'),
    ('cameras', 'Caméras'), ('alarm', 'Alarme'), ('secure_parking', 'Parking sécurisé'),
]


def home(request):
    properties = Property.objects.filter(status='AVAILABLE', publication__status='PUBLISHED').select_related('property_type').prefetch_related('photos')[:24]
    return render(request, 'home.html', {'properties': properties})


def property_detail(request, property_id):
    prop = get_object_or_404(Property.objects.select_related('property_type').prefetch_related('photos', 'features'), property_id=property_id)
    return render(request, 'properties/detail.html', {'property': prop})


def _positive(value, default=0):
    try:
        return max(0, int(value or default))
    except (TypeError, ValueError):
        return default


def _save_dynamic_details(prop, post):
    prop.bedrooms.all().delete()
    for number in range(1, _positive(post.get('bedroom_count')) + 1):
        Bedroom.objects.create(property=prop, number=number, bed_type=post.get(f'bed_{number}_type', ''), mattress=post.get(f'bed_{number}_mattress') == 'on', wardrobe=post.get(f'bed_{number}_wardrobe') == 'on', bedside_table=post.get(f'bed_{number}_bedside') == 'on', desk=post.get(f'bed_{number}_desk') == 'on', chair=post.get(f'bed_{number}_chair') == 'on', curtains=post.get(f'bed_{number}_curtains') == 'on', mosquito_net=post.get(f'bed_{number}_mosquito') == 'on', fan=post.get(f'bed_{number}_fan') == 'on', air_conditioning=post.get(f'bed_{number}_ac') == 'on')
    prop.living_rooms.all().delete()
    for number in range(1, _positive(post.get('living_room_count')) + 1):
        LivingRoom.objects.create(property=prop, number=number, sofa=post.get(f'living_{number}_sofa') == 'on', coffee_table=post.get(f'living_{number}_table') == 'on', television=post.get(f'living_{number}_tv') == 'on', curtains=post.get(f'living_{number}_curtains') == 'on', fan=post.get(f'living_{number}_fan') == 'on', air_conditioning=post.get(f'living_{number}_ac') == 'on')
    prop.bathrooms.all().delete()
    for number in range(1, _positive(post.get('bathroom_count')) + 1):
        Bathroom.objects.create(property=prop, number=number, location_type=post.get(f'bathroom_{number}_location', 'INTERIOR'), access_type=post.get(f'bathroom_{number}_access', ''), hot_water=post.get(f'bathroom_{number}_hot') == 'on', shower=post.get(f'bathroom_{number}_shower') == 'on', bathtub=post.get(f'bathroom_{number}_bathtub') == 'on', sink=post.get(f'bathroom_{number}_sink') == 'on', mirror=post.get(f'bathroom_{number}_mirror') == 'on', storage=post.get(f'bathroom_{number}_storage') == 'on')
    prop.toilets.all().delete()
    for number in range(1, _positive(post.get('toilet_count')) + 1):
        Toilet.objects.create(property=prop, number=number, location_type=post.get(f'toilet_{number}_location', 'INTERIOR'), access_type=post.get(f'toilet_{number}_access', ''), toilet_type=post.get(f'toilet_{number}_type', 'BOWL'))
    if prop.has_kitchen:
        kitchen, _ = Kitchen.objects.get_or_create(property=prop)
        kitchen.equipped = post.get('kitchen_equipped') == 'on'
        for field in ['stove', 'oven', 'refrigerator', 'freezer', 'microwave', 'hood', 'sink', 'cupboards', 'table', 'chairs']:
            setattr(kitchen, field, post.get(f'kitchen_{field}') == 'on')
        kitchen.save()
    else:
        Kitchen.objects.filter(property=prop).delete()
    prop.features.all().delete()
    exterior = {'courtyard', 'garden', 'terrace', 'balcony', 'veranda', 'parking', 'garage'}
    infrastructure = {'water_network', 'borehole', 'cistern', 'well', 'electric_network', 'generator', 'solar'}
    for key, _label in FEATURE_OPTIONS:
        if post.get(key) == 'on':
            category = 'EXTERIOR' if key in exterior else 'INFRASTRUCTURE' if key in infrastructure else 'SECURITY'
            PropertyFeature.objects.create(property=prop, key=key, category=category, value='true')


def _save_consents(publication, post):
    declaration, _ = PropertyDeclaration.objects.get_or_create(publication=publication, defaults={'relationship_to_property': ''})
    declaration.relationship_to_property = post.get('relationship_to_property', '').strip()
    declaration.right_to_offer_confirmed = post.get('right_to_offer_confirmed') == 'on'
    declaration.accuracy_confirmed = post.get('accuracy_confirmed') == 'on'
    declaration.photos_authentic_confirmed = post.get('photos_authentic_confirmed') == 'on'
    declaration.authorization_confirmed = post.get('authorization_confirmed') == 'on'
    declaration.acknowledged_responsibility = post.get('acknowledged_responsibility') == 'on'
    declaration.accepted_at = timezone.now() if all([declaration.right_to_offer_confirmed, declaration.accuracy_confirmed, declaration.photos_authentic_confirmed, declaration.authorization_confirmed, declaration.acknowledged_responsibility]) else None
    declaration.save()
    consent, _ = CollaborationConsent.objects.get_or_create(publication=publication, defaults={'terms_version': 'v1'})
    consent.verification_accepted = post.get('verification_accepted') == 'on'
    consent.presentation_accepted = post.get('presentation_accepted') == 'on'
    consent.visits_accepted = post.get('visits_accepted') == 'on'
    consent.management_accepted = post.get('management_accepted') == 'on'
    consent.collaboration_accepted = post.get('collaboration_accepted') == 'on'
    consent.accepted_at = timezone.now() if all([consent.verification_accepted, consent.presentation_accepted, consent.visits_accepted, consent.management_accepted, consent.collaboration_accepted]) else None
    consent.save()
    return declaration, consent


def _context(**extra):
    return {'features': FEATURE_OPTIONS, **extra}


def _validate_publication_ready(publication):
    if not publication.declaration.accepted_at:
        raise ValidationError('Toutes les déclarations obligatoires doivent être acceptées.')
    if not publication.collaboration_consent.accepted_at:
        raise ValidationError('Toutes les conditions de collaboration avec Fasthome doivent être acceptées.')
    prop = publication.property
    if not all([prop.province, prop.city_or_territory, prop.neighborhood]):
        raise ValidationError('La localisation du logement est incomplète.')
    if not prop.monthly_rent or prop.monthly_rent <= 0:
        raise ValidationError('Le loyer mensuel doit être renseigné et supérieur à zéro.')
    if not prop.max_occupants or prop.max_occupants < 1:
        raise ValidationError('La capacité maximale d’occupants doit être supérieure à zéro.')


@login_required
def property_create(request):
    if not request.user.is_certified:
        messages.error(request, 'Votre compte doit être certifié avant de publier un logement.')
        return redirect('certification')
    types = PropertyType.objects.filter(active=True)
    if request.method == 'POST':
        prop_type = get_object_or_404(PropertyType, pk=request.POST.get('property_type'))
        with transaction.atomic():
            prop = Property.objects.create(owner=request.user, property_type=prop_type, furnished=request.POST.get('furnished') == 'yes', province=request.POST.get('province', '').strip(), city_or_territory=request.POST.get('city_or_territory', '').strip(), administrative_subdivision=request.POST.get('administrative_subdivision', '').strip(), neighborhood=request.POST.get('neighborhood', '').strip(), exact_address=request.POST.get('exact_address', '').strip(), google_maps_url=request.POST.get('google_maps_url', '').strip(), latitude=request.POST.get('latitude') or None, longitude=request.POST.get('longitude') or None, bedroom_count=_positive(request.POST.get('bedroom_count')), living_room_count=_positive(request.POST.get('living_room_count')), bathroom_count=_positive(request.POST.get('bathroom_count')), toilet_count=_positive(request.POST.get('toilet_count')), has_kitchen=request.POST.get('has_kitchen') == 'yes', floor=request.POST.get('floor', '').strip(), ceiling_type=request.POST.get('ceiling_type', '').strip(), floor_type=request.POST.get('floor_type', '').strip(), monthly_rent=request.POST.get('monthly_rent') or None, guarantee_amount=request.POST.get('guarantee_amount') or None, max_occupants=max(1, _positive(request.POST.get('max_occupants'), 1)))
            publication = PropertyPublication.objects.create(property=prop, status='DRAFT')
            _save_dynamic_details(prop, request.POST)
            _save_consents(publication, request.POST)
        messages.success(request, f'Brouillon {publication.publication_id} créé pour le logement {prop.property_id}.')
        return redirect('property_edit', property_id=prop.property_id)
    return render(request, 'properties/form.html', _context(types=types, creating=True))


@login_required
def property_edit(request, property_id):
    prop = get_object_or_404(Property.objects.select_related('publication', 'property_type'), property_id=property_id, owner=request.user)
    if request.method == 'POST':
        with transaction.atomic():
            prop.furnished = request.POST.get('furnished') == 'yes'
            prop.bedroom_count = _positive(request.POST.get('bedroom_count'), prop.bedroom_count)
            prop.living_room_count = _positive(request.POST.get('living_room_count'), prop.living_room_count)
            prop.bathroom_count = _positive(request.POST.get('bathroom_count'), prop.bathroom_count)
            prop.toilet_count = _positive(request.POST.get('toilet_count'), prop.toilet_count)
            prop.has_kitchen = request.POST.get('has_kitchen') == 'yes'
            prop.floor = request.POST.get('floor', '').strip()
            prop.ceiling_type = request.POST.get('ceiling_type', '').strip()
            prop.floor_type = request.POST.get('floor_type', '').strip()
            prop.province = request.POST.get('province', '').strip()
            prop.city_or_territory = request.POST.get('city_or_territory', '').strip()
            prop.administrative_subdivision = request.POST.get('administrative_subdivision', '').strip()
            prop.neighborhood = request.POST.get('neighborhood', '').strip()
            prop.exact_address = request.POST.get('exact_address', '').strip()
            prop.google_maps_url = request.POST.get('google_maps_url', '').strip()
            prop.latitude = request.POST.get('latitude') or None
            prop.longitude = request.POST.get('longitude') or None
            prop.monthly_rent = request.POST.get('monthly_rent') or None
            prop.guarantee_amount = request.POST.get('guarantee_amount') or None
            prop.max_occupants = max(1, _positive(request.POST.get('max_occupants'), prop.max_occupants))
            prop.save()
            _save_dynamic_details(prop, request.POST)
            _save_consents(prop.publication, request.POST)
            if request.POST.get('submit') == '1':
                try:
                    _validate_publication_ready(prop.publication)
                except ValidationError as exc:
                    messages.error(request, str(exc))
                    return redirect('property_edit', property_id=prop.property_id)
                prop.publication.status = 'SUBMITTED'
                prop.publication.submitted_at = timezone.now()
                prop.publication.save(update_fields=['status', 'submitted_at', 'updated_at'])
                prop.status = 'UNDER_REVIEW'
                prop.save(update_fields=['status', 'updated_at'])
                messages.success(request, 'Publication soumise à Fasthome pour vérification.')
            else:
                messages.success(request, 'Brouillon enregistré.')
        return redirect('property_edit', property_id=prop.property_id)
    return render(request, 'properties/form.html', _context(property=prop, types=PropertyType.objects.filter(active=True), creating=False))
