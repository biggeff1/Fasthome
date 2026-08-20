from django.urls import path
from . import views

urlpatterns = [
    path('request/<str:property_id>/', views.request_visit, name='request_visit'),
    path('<str:visit_id>/landlord-decision/', views.landlord_visit_decision, name='landlord_visit_decision'),
    path('<str:visit_id>/decision/', views.tenant_decision, name='tenant_decision'),
]
