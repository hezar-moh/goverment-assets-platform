from django.urls import path
from .views import ministry_list_view, ministry_create_view, ministry_detail_view, ministry_toggle_active_view

urlpatterns = [
    path('ministries/',                        ministry_list_view,          name='ministry_list'),
    path('ministries/create/',                 ministry_create_view,        name='ministry_create'),
    path('ministries/<int:ministry_id>/',      ministry_detail_view,        name='ministry_detail'),
    path('ministries/<int:ministry_id>/toggle/', ministry_toggle_active_view, name='ministry_toggle_active'),
]
