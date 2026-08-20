from decimal import Decimal
from django.shortcuts import render
from properties.models import Property
from .models import SearchRequest, MatchingResult


def score_property(prop, search):
    weights = {
        'budget': Decimal('25'), 'province': Decimal('10'), 'city': Decimal('15'),
        'subdivision': Decimal('10'), 'neighborhood': Decimal('10'), 'bedrooms': Decimal('10'),
        'living_rooms': Decimal('5'), 'furnished': Decimal('5'), 'occupants': Decimal('10'),
    }
    breakdown = {}
    score = Decimal('0')
    if search.maximum_budget is not None:
        ok = prop.monthly_rent is not None and prop.monthly_rent <= search.maximum_budget
        breakdown['budget'] = 100 if ok else 0
        score += weights['budget'] if ok else Decimal('0')
    if search.province:
        ok = prop.province.strip().lower() == search.province.strip().lower()
        breakdown['province'] = 100 if ok else 0
        score += weights['province'] if ok else Decimal('0')
    if search.city_or_territory:
        ok = prop.city_or_territory.strip().lower() == search.city_or_territory.strip().lower()
        breakdown['city'] = 100 if ok else 0
        score += weights['city'] if ok else Decimal('0')
    if search.administrative_subdivision:
        ok = prop.administrative_subdivision.strip().lower() == search.administrative_subdivision.strip().lower()
        breakdown['subdivision'] = 100 if ok else 0
        score += weights['subdivision'] if ok else Decimal('0')
    if search.neighborhood:
        ok = prop.neighborhood.strip().lower() == search.neighborhood.strip().lower()
        breakdown['neighborhood'] = 100 if ok else 0
        score += weights['neighborhood'] if ok else Decimal('0')
    ok = prop.bedroom_count >= search.minimum_bedrooms
    breakdown['bedrooms'] = 100 if ok else 0
    score += weights['bedrooms'] if ok else Decimal('0')
    ok = prop.living_room_count >= search.minimum_living_rooms
    breakdown['living_rooms'] = 100 if ok else 0
    score += weights['living_rooms'] if ok else Decimal('0')
    if search.furnished_preference == 'ANY':
        furnished_score = 100
    else:
        furnished_score = 100 if ((search.furnished_preference == 'YES') == prop.furnished) else 0
    breakdown['furnished'] = furnished_score
    score += weights['furnished'] * Decimal(furnished_score) / Decimal('100')
    ok = prop.max_occupants >= search.requested_occupants
    breakdown['occupants'] = 100 if ok else 0
    score += weights['occupants'] if ok else Decimal('0')
    return min(score, Decimal('100')), breakdown


def matching(request):
    results = []
    values = None
    if request.method == 'POST':
        values = request.POST
        search = SearchRequest.objects.create(
            user=request.user if request.user.is_authenticated else None,
            furnished_preference=values.get('furnished_preference', 'ANY'),
            province=values.get('province','').strip(),
            city_or_territory=values.get('city_or_territory','').strip(),
            administrative_subdivision=values.get('administrative_subdivision','').strip(),
            neighborhood=values.get('neighborhood','').strip(),
            minimum_living_rooms=int(values.get('minimum_living_rooms') or 0),
            minimum_bedrooms=int(values.get('minimum_bedrooms') or 0),
            maximum_budget=values.get('maximum_budget') or None,
            requested_occupants=max(1, int(values.get('requested_occupants') or 1)),
        )
        qs = Property.objects.filter(status='AVAILABLE', publication__status='PUBLISHED').select_related('property_type')
        for prop in qs:
            score, breakdown = score_property(prop, search)
            if score >= 60:
                result = MatchingResult.objects.create(search=search, property=prop, score=score, criteria_breakdown=breakdown)
                results.append(result)
    return render(request, 'matching/index.html', {'results': results, 'values': values})
