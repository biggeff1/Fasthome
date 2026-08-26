from django.urls import path
from .my_properties_views import my_properties, property_manage

urlpatterns = [
    path('properties/', my_properties, name='my_properties'),
    path('properties/<str:property_id>/manage/', property_manage, name='property_manage'),
]
