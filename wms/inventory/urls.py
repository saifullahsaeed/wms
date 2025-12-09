"""
URL configuration for inventory app - stock management.
"""

from django.urls import path
from .views import (
    InventoryItemListView,
    InventoryItemDetailView,
    InventoryByProductView,
    InventoryByLocationView,
    low_stock_alerts,
    InventoryMovementListView,
    InventoryMovementDetailView,
    StockAdjustmentListCreateView,
    StockAdjustmentDetailView,
    StockCountSessionListCreateView,
    StockCountSessionDetailView,
    start_stock_count_session,
    complete_stock_count_session,
    cancel_stock_count_session,
    StockCountLineListCreateView,
    StockCountLineDetailView,
    CustomFieldDefinitionListCreateView,
    CustomFieldDefinitionDetailView,
    ProductCustomFieldValueListCreateView,
    ProductCustomFieldValueDetailView,
    InventoryItemCustomFieldValueListCreateView,
    InventoryItemCustomFieldValueDetailView,
)

app_name = "inventory"

urlpatterns = [
    # Inventory Items
    path("items/", InventoryItemListView.as_view(), name="inventory-item-list"),
    path("items/<int:pk>/", InventoryItemDetailView.as_view(), name="inventory-item-detail"),
    path("items/by-product/", InventoryByProductView.as_view(), name="inventory-by-product"),
    path("items/by-location/", InventoryByLocationView.as_view(), name="inventory-by-location"),
    path("items/low-stock/", low_stock_alerts, name="low-stock-alerts"),
    # Inventory Movements
    path("movements/", InventoryMovementListView.as_view(), name="inventory-movement-list"),
    path("movements/<int:pk>/", InventoryMovementDetailView.as_view(), name="inventory-movement-detail"),
    # Stock Adjustments
    path("adjustments/", StockAdjustmentListCreateView.as_view(), name="stock-adjustment-list-create"),
    path("adjustments/<int:pk>/", StockAdjustmentDetailView.as_view(), name="stock-adjustment-detail"),
    # Stock Count Sessions
    path("stock-counts/", StockCountSessionListCreateView.as_view(), name="stock-count-session-list-create"),
    path("stock-counts/<int:pk>/", StockCountSessionDetailView.as_view(), name="stock-count-session-detail"),
    path("stock-counts/<int:pk>/start/", start_stock_count_session, name="stock-count-session-start"),
    path("stock-counts/<int:pk>/complete/", complete_stock_count_session, name="stock-count-session-complete"),
    path("stock-counts/<int:pk>/cancel/", cancel_stock_count_session, name="stock-count-session-cancel"),
    # Stock Count Lines
    path("stock-counts/<int:session_id>/lines/", StockCountLineListCreateView.as_view(), name="stock-count-line-list-create"),
    path("stock-counts/<int:session_id>/lines/<int:pk>/", StockCountLineDetailView.as_view(), name="stock-count-line-detail"),
    # Custom Field Definitions
    path("custom-fields/", CustomFieldDefinitionListCreateView.as_view(), name="custom-field-definition-list-create"),
    path("custom-fields/<int:pk>/", CustomFieldDefinitionDetailView.as_view(), name="custom-field-definition-detail"),
    # Product Custom Field Values
    path("products/<int:product_id>/custom-fields/", ProductCustomFieldValueListCreateView.as_view(), name="product-custom-field-value-list-create"),
    path("products/<int:product_id>/custom-fields/<int:pk>/", ProductCustomFieldValueDetailView.as_view(), name="product-custom-field-value-detail"),
    # Inventory Item Custom Field Values
    path("items/<int:item_id>/custom-fields/", InventoryItemCustomFieldValueListCreateView.as_view(), name="inventory-item-custom-field-value-list-create"),
    path("items/<int:item_id>/custom-fields/<int:pk>/", InventoryItemCustomFieldValueDetailView.as_view(), name="inventory-item-custom-field-value-detail"),
]

