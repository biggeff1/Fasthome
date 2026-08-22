from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .location_models import LocationNode


@login_required
@require_GET
def location_children(request):
    parent_id = request.GET.get('parent')
    kind = request.GET.get('kind')
    queryset = LocationNode.objects.filter(active=True)
    if parent_id:
        queryset = queryset.filter(parent_id=parent_id)
    else:
        queryset = queryset.filter(parent__isnull=True)
    if kind:
        queryset = queryset.filter(kind=kind)
    data = [{'id': node.id, 'name': node.name, 'kind': node.kind} for node in queryset.order_by('order', 'name')]
    return JsonResponse({'results': data})
