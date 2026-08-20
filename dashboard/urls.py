from django.urls import path
from . import views

urlpatterns = [
    path('', views.activity, name='activity'),
    path('favorites/', views.favorites, name='favorites'),
    path('favorites/<str:property_id>/toggle/', views.toggle_favorite, name='toggle_favorite'),
    path('notifications/', views.notifications, name='notifications'),
    path('leases/<str:lease_id>/', views.lease_detail, name='lease_detail'),
    path('office/', views.office_dashboard, name='office_dashboard'),
    path('office/visits/', views.office_visits, name='office_visits'),
    path('office/visits/<str:visit_id>/approve/', views.office_approve_visit, name='office_approve_visit'),
    path('office/visits/<str:visit_id>/complete/', views.office_complete_visit, name='office_complete_visit'),
]
