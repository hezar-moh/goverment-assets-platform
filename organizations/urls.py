from django.urls import path
from .views import (org_unit_list_view, org_unit_create_view,
                    org_unit_edit_view, org_unit_delete_view,
                    audit_log_view, audit_log_detail_view)
from .master_data_views import (master_data_list_view, master_data_create_view,
                                master_data_edit_view, master_data_delete_view,
                                master_data_seed_view)

urlpatterns = [
    path('organisation/',                      org_unit_list_view,     name='org_unit_list'),
    path('organisation/create/',               org_unit_create_view,   name='org_unit_create'),
    path('organisation/<int:unit_id>/edit/',   org_unit_edit_view,     name='org_unit_edit'),
    path('organisation/<int:unit_id>/delete/', org_unit_delete_view,   name='org_unit_delete'),
    path('master-data/',                        master_data_list_view,   name='master_data_list'),
    path('master-data/create/',                 master_data_create_view, name='master_data_create'),
    path('master-data/<int:item_id>/edit/',     master_data_edit_view,   name='master_data_edit'),
    path('master-data/<int:item_id>/delete/',   master_data_delete_view, name='master_data_delete'),
    path('master-data/seed/',                   master_data_seed_view,   name='master_data_seed'),
    path('audit-logs/',                  audit_log_view,          name='audit_log'),
    path('audit-log/<int:log_id>/',     audit_log_detail_view,   name='audit_log_detail'),
]
