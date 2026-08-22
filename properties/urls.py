from django.urls import path
from . import views
from .location_views import location_children

urlpatterns = [
    path('', views.home, name='home'),
    path('properties/locations/children/', location_children, name='location_children'),
    # Keep the literal "create" route before the dynamic property_id route.
    path('properties/create/', views.property_create, name='property_create'),
    path('properties/<str:property_id>/edit/', views.property_edit, name='property_edit'),
    path('properties/<str:property_id>/', views.property_detail, name='property_detail'),
]
