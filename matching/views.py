from decimal import Decimal
from django.shortcuts import render
from properties.models import Property
from .models import SearchRequest, MatchingResult

WEIGHTS = {'budget':25,'province':10,'city':15,'subdivision':10,'neighborhood':10,'bedrooms':10,'living_rooms':5,'furnished':5,'occupants':10}


def score_property(prop, search):
    checks = {}
    if search.maximum_budget is not None: checks['budget'] = prop.monthly_rent is not None and prop.monthly_rent <= search.maximum_budget
    if search.province: checks['province'] = prop.province.strip().casefold() == search.province.strip().casefold()
    if search.city_or_territory: checks['city'] = prop.city_or_territory.strip().casefold() == search.city_or_territory.strip().casefold()
    if search.administrative_subdivision: checks['subdivision'] = prop.administrative_subdivision.strip().casefold() == search.administrative_subdivision.strip().casefold()
    if search.neighborhood: checks['neighborhood'] = prop.neighborhood.strip().casefold() == search.neighborhood.strip().casefold()
    if search.minimum_bedrooms: checks['bedrooms'] = prop.bedroom_count >= search.minimum_bedrooms
    if search.minimum_living_rooms: checks['living_rooms'] = prop.living_room_count >= search.minimum_living_rooms
    if search.furnished_preference != 'ANY': checks['furnished'] = ((search.furnished_preference == 'YES') == prop.furnished)
    if search.requested_occupants: checks['occupants'] = prop.max_occupants >= search.requested_occupants
    active_weight = sum(WEIGHTS[k] for k in checks) or 1
    score = sum(WEIGHTS[k] for k, ok in checks.items() if ok) * Decimal(100) / Decimal(active_weight)
    return min(score, Decimal('100')), {k: (100 if ok else 0) for k, ok in checks.items()}


def matching(request):
    results=[]; values=None
    if request.method == 'POST':
        values=request.POST
        search=SearchRequest.objects.create(user=request.user if request.user.is_authenticated else None, furnished_preference=values.get('furnished_preference','ANY'), province=values.get('province','').strip(), city_or_territory=values.get('city_or_territory','').strip(), administrative_subdivision=values.get('administrative_subdivision','').strip(), neighborhood=values.get('neighborhood','').strip(), minimum_living_rooms=int(values.get('minimum_living_rooms') or 0), minimum_bedrooms=int(values.get('minimum_bedrooms') or 0), maximum_budget=values.get('maximum_budget') or None, requested_occupants=max(1,int(values.get('requested_occupants') or 1)))
        qs=Property.objects.filter(status='AVAILABLE', publication__status='PUBLISHED').select_related('property_type').prefetch_related('photos')
        for prop in qs:
            score, breakdown=score_property(prop,search)
            if score >= 60:
                results.append(MatchingResult.objects.create(search=search,property=prop,score=score,criteria_breakdown=breakdown))
    return render(request,'matching/index.html',{'results':results,'values':values})
