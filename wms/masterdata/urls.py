"""
URL configuration for masterdata app - warehouse and product management.
"""

from django.urls import path
from .views import (
    WarehouseListCreateView,
    WarehouseDetailView,
    check_warehouse_code,
)

app_name = "masterdata"

urlpatterns = [
    path(
        "warehouses/", WarehouseListCreateView.as_view(), name="warehouse-list-create"
    ),
    path(
        "warehouses/<int:pk>/", WarehouseDetailView.as_view(), name="warehouse-detail"
    ),
    path(
        "warehouses/check-code/",
        check_warehouse_code,
        name="warehouse-check-code",
    ),
]
