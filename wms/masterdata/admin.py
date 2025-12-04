from django.contrib import admin

from inventory.models import ProductCustomFieldValue

from .models import (
    Carrier,
    Customer,
    Location,
    LocationType,
    Product,
    ProductBarcode,
    ProductCategory,
    Rack,
    ReasonCode,
    Section,
    Supplier,
    UnitOfMeasure,
    Warehouse,
    WarehouseZone,
)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "company",
        "city",
        "country",
        "type",
        "is_active",
        "allow_negative_stock",
        "uses_bins",
        "created_at",
    )
    list_filter = (
        "company",
        "type",
        "is_active",
        "allow_negative_stock",
        "uses_bins",
        "country",
    )
    search_fields = (
        "code",
        "name",
        "company__name",
        "city",
        "state",
        "country",
    )
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "code",
                    "name",
                    "description",
                )
            },
        ),
        (
            "Company & type",
            {
                "fields": (
                    "company",
                    "type",
                    "is_active",
                )
            },
        ),
        (
            "Address",
            {
                "fields": (
                    "address_line1",
                    "address_line2",
                    "city",
                    "state",
                    "postal_code",
                    "country",
                )
            },
        ),
        (
            "Geo & time",
            {
                "fields": (
                    "time_zone",
                    "latitude",
                    "longitude",
                )
            },
        ),
        (
            "Operational settings",
            {
                "fields": (
                    "allow_negative_stock",
                    "uses_bins",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(WarehouseZone)
class WarehouseZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "warehouse", "is_active", "created_at")
    list_filter = ("warehouse", "is_active")
    search_fields = ("name", "warehouse__code", "warehouse__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(LocationType)
class LocationTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "company",
        "code",
        "is_pickable",
        "is_putaway_allowed",
        "temperature_zone",
        "is_active",
    )
    list_filter = (
        "company",
        "is_pickable",
        "is_putaway_allowed",
        "is_countable",
        "is_active",
    )
    search_fields = ("name", "code", "company__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "warehouse", "zone", "is_active")
    list_filter = ("warehouse", "zone", "is_active")
    search_fields = ("code", "name", "warehouse__code", "warehouse__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Rack)
class RackAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "warehouse",
        "section",
        "levels",
        "positions_per_level",
        "is_active",
    )
    list_filter = ("warehouse", "section", "is_active")
    search_fields = (
        "code",
        "section__code",
        "warehouse__code",
        "warehouse__name",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "warehouse",
        "section",
        "rack",
        "location_type",
        "is_active",
        "pick_sequence",
    )
    list_filter = (
        "warehouse",
        "location_type",
        "section",
        "rack",
        "is_active",
    )
    search_fields = (
        "code",
        "barcode",
        "warehouse__code",
        "warehouse__name",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = (
        "abbreviation",
        "name",
        "company",
        "base_unit",
        "conversion_factor",
        "is_active",
    )
    list_filter = ("company", "is_active")
    search_fields = (
        "abbreviation",
        "name",
        "company__name",
    )
    readonly_fields = ("created_at", "updated_at")


class ProductBarcodeInline(admin.TabularInline):
    model = ProductBarcode
    extra = 0
    fields = ("barcode", "label", "is_primary", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")


class ProductCustomFieldValueInline(admin.TabularInline):
    model = ProductCustomFieldValue
    extra = 0
    autocomplete_fields = ("field",)
    fields = ("field", "value_text", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "parent", "is_active")
    list_filter = ("company", "is_active")
    search_fields = ("name", "company__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductBarcodeInline, ProductCustomFieldValueInline]

    list_display = (
        "sku",
        "name",
        "company",
        "category",
        "status",
        "default_uom",
        "storage_uom",
        "track_batch",
        "track_serial",
        "created_at",
    )
    list_filter = (
        "company",
        "category",
        "status",
        "track_batch",
        "track_serial",
        "hazardous",
    )
    search_fields = (
        "sku",
        "name",
        "company__name",
    )
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "company",
                    "sku",
                    "name",
                    "description",
                    "category",
                    "status",
                )
            },
        ),
        (
            "Units",
            {
                "fields": (
                    "default_uom",
                    "storage_uom",
                )
            },
        ),
        (
            "Dimensions & weight",
            {
                "fields": (
                    "weight_kg",
                    "length_cm",
                    "width_cm",
                    "height_cm",
                    "volume_cbm",
                )
            },
        ),
        (
            "Tracking & safety",
            {
                "fields": (
                    "track_batch",
                    "track_serial",
                    "hazardous",
                    "requires_lot_expiry",
                )
            },
        ),
        (
            "Storage requirements",
            {
                "fields": (
                    "storage_requirements",
                    "image_url",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(ProductBarcode)
class ProductBarcodeAdmin(admin.ModelAdmin):
    list_display = ("product", "barcode", "label", "is_primary", "created_at")
    list_filter = ("product__company", "is_primary")
    search_fields = ("product__sku", "barcode", "label")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "company", "email", "phone", "is_active")
    list_filter = ("company", "is_active")
    search_fields = ("code", "name", "company__name", "email", "phone")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "company", "email", "phone", "is_active")
    list_filter = ("company", "is_active")
    search_fields = ("code", "name", "company__name", "email", "phone")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Carrier)
class CarrierAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "company",
        "code",
        "account_number",
        "contact_email",
        "is_active",
    )
    list_filter = ("company", "is_active")
    search_fields = ("name", "code", "company__name", "account_number")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ReasonCode)
class ReasonCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "description", "company", "category", "is_active")
    list_filter = ("company", "category", "is_active")
    search_fields = ("code", "description", "company__name")
    readonly_fields = ("created_at", "updated_at")
