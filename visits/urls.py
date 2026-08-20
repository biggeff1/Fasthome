from django.urls import path
from . import views

urlpatterns = [
    path('request/<str:property_id>/', views.request_visit, name='request_visit'),
]
