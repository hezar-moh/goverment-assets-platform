from django.urls import path
from .views import login_view, logout_view
from .user_views import (user_list_view, user_create_view, user_edit_view,
                         user_toggle_active_view, user_reset_password_view,
                         user_sync_from_keycloak_view)
from .pending_access_views import (pending_access_list_view,
                                   pending_access_review_view,
                                   pending_access_clear_view)
from .unlock_views import account_unlock_view

urlpatterns = [
    path('login/',                    login_view,                   name='login'),
    path('logout/',                   logout_view,                  name='logout'),
    path('users/',                    user_list_view,               name='user_list'),
    path('users/create/',             user_create_view,             name='user_create'),
    path('users/<int:user_id>/edit/', user_edit_view,               name='user_edit'),
    path('users/<int:user_id>/toggle-active/', user_toggle_active_view, name='user_toggle_active'),
    path('users/<int:user_id>/sync-from-keycloak/', user_sync_from_keycloak_view, name='user_sync_from_keycloak'),
    path('users/<int:user_id>/reset-password/', user_reset_password_view, name='user_reset_password'),
    path('pending-access/',                       pending_access_list_view,   name='pending_access_list'),
    path('pending-access/<int:request_id>/review/', pending_access_review_view, name='pending_access_review'),
    path('pending-access/clear/',                 pending_access_clear_view,  name='pending_access_clear'),
    path('unlock-account/<uuid:token>/', account_unlock_view,      name='account_unlock'),
]
