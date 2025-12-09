"""
URL configuration for masterdata app - warehouse and product management.
"""

from django.urls import path
from .views import (
    WarehouseListCreateView,
    WarehouseDetailView,
    check_warehouse_code,
    ProductListCreateView,
    ProductDetailView,
    check_product_sku,
    ProductBarcodeListCreateView,
    ProductBarcodeDetailView,
    lookup_product_by_barcode,
    ProductCategoryListCreateView,
    ProductCategoryDetailView,
    LocationTypeListCreateView,
    LocationTypeDetailView,
    WarehouseZoneListCreateView,
    WarehouseZoneDetailView,
    SectionListCreateView,
    SectionDetailView,
    RackListCreateView,
    RackDetailView,
    LocationListCreateView,
    LocationDetailView,
    check_location_code,
    UnitOfMeasureListCreateView,
    UnitOfMeasureDetailView,
    SupplierListCreateView,
    SupplierDetailView,
    CustomerListCreateView,
    CustomerDetailView,
    CarrierListCreateView,
    CarrierDetailView,
    ReasonCodeListCreateView,
    ReasonCodeDetailView,
)

app_name = "masterdata"

urlpatterns = [
    # Warehouses
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
    # Products
    path("products/", ProductListCreateView.as_view(), name="product-list-create"),
    path("products/<int:pk>/", ProductDetailView.as_view(), name="product-detail"),
    path("products/check-sku/", check_product_sku, name="product-check-sku"),
    path(
        "products/<int:product_id>/barcodes/",
        ProductBarcodeListCreateView.as_view(),
        name="product-barcode-list-create",
    ),
    path(
        "products/<int:product_id>/barcodes/<int:pk>/",
        ProductBarcodeDetailView.as_view(),
        name="product-barcode-detail",
    ),
    path(
        "products/lookup-by-barcode/",
        lookup_product_by_barcode,
        name="product-lookup-by-barcode",
    ),
    # Product Categories
    path(
        "product-categories/",
        ProductCategoryListCreateView.as_view(),
        name="product-category-list-create",
    ),
    path(
        "product-categories/<int:pk>/",
        ProductCategoryDetailView.as_view(),
        name="product-category-detail",
    ),
    # Location Types
    path(
        "location-types/",
        LocationTypeListCreateView.as_view(),
        name="location-type-list-create",
    ),
    path(
        "location-types/<int:pk>/",
        LocationTypeDetailView.as_view(),
        name="location-type-detail",
    ),
    # Warehouse Zones (nested under warehouse)
    path(
        "warehouses/<int:warehouse_id>/zones/",
        WarehouseZoneListCreateView.as_view(),
        name="warehouse-zone-list-create",
    ),
    path(
        "warehouses/<int:warehouse_id>/zones/<int:pk>/",
        WarehouseZoneDetailView.as_view(),
        name="warehouse-zone-detail",
    ),
    # Sections (nested under warehouse)
    path(
        "warehouses/<int:warehouse_id>/sections/",
        SectionListCreateView.as_view(),
        name="section-list-create",
    ),
    path(
        "warehouses/<int:warehouse_id>/sections/<int:pk>/",
        SectionDetailView.as_view(),
        name="section-detail",
    ),
    # Racks (nested under warehouse)
    path(
        "warehouses/<int:warehouse_id>/racks/",
        RackListCreateView.as_view(),
        name="rack-list-create",
    ),
    path(
        "warehouses/<int:warehouse_id>/racks/<int:pk>/",
        RackDetailView.as_view(),
        name="rack-detail",
    ),
    # Locations (nested under warehouse)
    path(
        "warehouses/<int:warehouse_id>/locations/",
        LocationListCreateView.as_view(),
        name="location-list-create",
    ),
    path(
        "warehouses/<int:warehouse_id>/locations/<int:pk>/",
        LocationDetailView.as_view(),
        name="location-detail",
    ),
    path(
        "warehouses/<int:warehouse_id>/locations/check-code/",
        check_location_code,
        name="location-check-code",
    ),
    # Units of Measure
    path(
        "units-of-measure/",
        UnitOfMeasureListCreateView.as_view(),
        name="unit-of-measure-list-create",
    ),
    path(
        "units-of-measure/<int:pk>/",
        UnitOfMeasureDetailView.as_view(),
        name="unit-of-measure-detail",
    ),
    # Suppliers
    path("suppliers/", SupplierListCreateView.as_view(), name="supplier-list-create"),
    path("suppliers/<int:pk>/", SupplierDetailView.as_view(), name="supplier-detail"),
    # Customers
    path("customers/", CustomerListCreateView.as_view(), name="customer-list-create"),
    path("customers/<int:pk>/", CustomerDetailView.as_view(), name="customer-detail"),
    # Carriers
    path("carriers/", CarrierListCreateView.as_view(), name="carrier-list-create"),
    path("carriers/<int:pk>/", CarrierDetailView.as_view(), name="carrier-detail"),
    # Reason Codes
    path(
        "reason-codes/",
        ReasonCodeListCreateView.as_view(),
        name="reason-code-list-create",
    ),
    path(
        "reason-codes/<int:pk>/",
        ReasonCodeDetailView.as_view(),
        name="reason-code-detail",
    ),
]
