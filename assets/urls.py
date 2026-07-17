from django.urls import path
from .views import asset_list_view, asset_create_view, asset_detail_view, asset_edit_view, asset_delete_view
from .category_views import asset_category_list_view, asset_category_create_view, asset_category_edit_view, asset_category_delete_view

urlpatterns = [
    path('assets/',                    asset_list_view,             name='asset_list'),
    path('assets/create/',             asset_create_view,           name='asset_create'),
    path('assets/<int:asset_id>/',     asset_detail_view,           name='asset_detail'),
    path('assets/<int:asset_id>/edit/',   asset_edit_view,          name='asset_edit'),
    path('assets/<int:asset_id>/delete/', asset_delete_view,        name='asset_delete'),
    path('assets/categories/',          asset_category_list_view,   name='asset_category_list'),
    path('assets/categories/create/',   asset_category_create_view, name='asset_category_create'),
    path('assets/categories/<int:category_id>/edit/',  asset_category_edit_view,  name='asset_category_edit'),
    path('assets/categories/<int:category_id>/delete/', asset_category_delete_view, name='asset_category_delete'),
]
