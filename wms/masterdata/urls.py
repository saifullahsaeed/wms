"""
URL configuration for masterdata app - warehouse and product management.
"""

from django.urls import path
from .views import WarehouseListCreateView, WarehouseDetailView

app_name = "masterdata"

urlpatterns = [
    path(
        "warehouses/", WarehouseListCreateView.as_view(), name="warehouse-list-create"
    ),
    path(
        "warehouses/<int:pk>/", WarehouseDetailView.as_view(), name="warehouse-detail"
    ),
]
