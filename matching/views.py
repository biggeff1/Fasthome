from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import render

from properties.models import Property
from .models import MatchingResult, SearchRequest


WEIGHTS = {
    'budget': 25, 'province': 10, 'city': 15, 'subdivision': 10,
    'neighborhood': 10, 'bedrooms': 10, 'living_rooms': 5,
    'furnished': 5, 'occupants': 10,
}


def score_property(prop, search):
    """Compute a deterministic score only from criteria supplied by the user."""
    checks = {}
    if search.maximum_budget is not None:
        checks['budget'] = prop.monthly_rent is not None and prop.monthly_rent <= search.maximum_budget
    if search.province:
        checks['province'] = prop.province.strip().casefold() == search.province.strip().casefold()
    if search.city_or_territory:
        checks['city'] = prop.city_or_territory.strip().casefold() == search.city_or_territory.strip().casefold()
    if search.administrative_subdivision:
        checks['subdivision'] = prop.administrative_subdivision.strip().casefold() == search.administrative_subdivision.strip().casefold()
    if search.neighborhood:
        checks['neighborhood'] = prop.neighborhood.strip().casefold() == search.neighborhood.strip().casefold()
    if search.minimum_bedrooms:
        checks['bedrooms'] = prop.bedroom_count >= search.minimum_bedrooms
    if search.minimum_living_rooms:
        checks['living_rooms'] = prop.living_room_count >= search.minimum_living_rooms
    if search.furnished_preference != 'ANY':
        checks['furnished'] = ((search.furnished_preference == 'YES') == prop.furnished)
    if search.requested_occupants:
        checks['occupants'] = prop.max_occupants >= search.requested_occupants

    if not checks:
        return Decimal('0'), {}

    active_weight = sum(WEIGHTS[key] for key in checks)
    matched_weight = sum(WEIGHTS[key] for key, ok in checks.items() if ok)
    score = Decimal(matched_weight * 100) / Decimal(active_weight)
    return min(score, Decimal('100')), {key: (100 if ok else 0) for key, ok in checks.items()}


def _post_int(request, name, default=0, minimum=0):
    raw = (request.POST.get(name) or '').strip()
    try:
        value = int(raw) if raw else default
    except ValueError as exc:
        raise ValidationError(f'Valeur invalide pour {name}.') from exc
    if value < minimum:
        raise ValidationError(f'Valeur invalide pour {name}.')
    return value


def matching(request):
    results = []
    values = None
    if request.method == 'POST':
        values = request.POST
        try:
            requested_occupants = _post_int(request, 'requested_occupants', 1, minimum=1)
            minimum_living_rooms = _post_int(request, 'minimum_living_rooms', 0)
            minimum_bedrooms = _post_int(request, 'minimum_bedrooms', 0)
            budget_raw = (request.POST.get('maximum_budget') or '').strip()
            maximum_budget = Decimal(budget_raw) if budget_raw else None
            if maximum_budget is not None and maximum_budget < 0:
                raise ValidationError('Le budget maximum ne peut pas être négatif.')

            search = SearchRequest.objects.create(
                user=request.user if request.user.is_authenticated else None,
                furnished_preference=request.POST.get('furnished_preference', 'ANY'),
                province=request.POST.get('province', '').strip(),
                city_or_territory=request.POST.get('city_or_territory', '').strip(),
                administrative_subdivision=request.POST.get('administrative_subdivision', '').strip(),
                neighborhood=request.POST.get('neighborhood', '').strip(),
                minimum_living_rooms=minimum_living_rooms,
                minimum_bedrooms=minimum_bedrooms,
                maximum_budget=maximum_budget,
                requested_occupants=requested_occupants,
            )
            queryset = Property.objects.filter(
                status='AVAILABLE', publication__status='PUBLISHED'
            ).select_related('property_type').prefetch_related('photos')
            for prop in queryset:
                score, breakdown = score_property(prop, search)
                if score >= 60:
                    results.append(MatchingResult.objects.create(
                        search=search, property=prop, score=score,
                        criteria_breakdown=breakdown,
                    ))
        except (ValidationError, ArithmeticError) as exc:
            messages.error(request, str(exc))

    return render(request, 'matching/index.html', {'results': results, 'values': values})
