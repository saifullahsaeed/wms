from django.contrib import admin

from .models import (
    CustomFieldDefinition,
    InventoryItem,
    InventoryItemCustomFieldValue,
    InventoryMovement,
    ProductCustomFieldValue,
    StockAdjustment,
    StockCountLine,
    StockCountSession,
)


class InventoryItemCustomFieldValueInline(admin.TabularInline):
    model = InventoryItemCustomFieldValue
    extra = 0
    autocomplete_fields = ("field",)
    fields = ("field", "value_text", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "company",
        "warehouse",
        "location",
        "quantity",
        "reserved_quantity",
        "is_locked",
        "updated_at",
    )
    list_filter = (
        "company",
        "warehouse",
        "is_locked",
    )
    search_fields = (
        "product__sku",
        "product__name",
        "location__code",
        "warehouse__code",
        "warehouse__name",
    )
    readonly_fields = ("created_at", "updated_at")
    inlines = [InventoryItemCustomFieldValueInline]

    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "company",
                    "warehouse",
                    "product",
                    "location",
                )
            },
        ),
        (
            "Batch & expiry",
            {
                "fields": (
                    "batch",
                    "expiry_date",
                )
            },
        ),
        (
            "Quantities",
            {
                "fields": (
                    "quantity",
                    "reserved_quantity",
                    "is_locked",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "company",
        "warehouse",
        "product",
        "movement_type",
        "quantity",
        "location_from",
        "location_to",
        "reference",
        "created_by",
    )
    list_filter = (
        "company",
        "warehouse",
        "movement_type",
        "created_at",
    )
    search_fields = (
        "product__sku",
        "product__name",
        "location_from__code",
        "location_to__code",
        "reference",
        "reason",
        "created_by__username",
    )
    readonly_fields = (
        "company",
        "warehouse",
        "product",
        "location_from",
        "location_to",
        "batch",
        "expiry_date",
        "movement_type",
        "quantity",
        "reference",
        "reason",
        "created_by",
        "created_at",
    )

    def has_add_permission(self, request):
        # Movement records should be created via business logic, not manually.
        return False


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "warehouse",
        "product",
        "location",
        "reason",
        "quantity_difference",
        "reference",
        "created_by",
        "created_at",
    )
    list_filter = (
        "company",
        "warehouse",
        "reason",
        "created_at",
    )
    search_fields = (
        "product__sku",
        "product__name",
        "location__code",
        "reference",
        "description",
        "created_by__username",
    )
    readonly_fields = ("created_at",)

    fieldsets = (
        (
            "Context",
            {
                "fields": (
                    "company",
                    "warehouse",
                    "product",
                    "location",
                )
            },
        ),
        (
            "Adjustment",
            {
                "fields": (
                    "reason",
                    "description",
                    "quantity_difference",
                    "reference",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "created_by",
                    "created_at",
                )
            },
        ),
    )


class StockCountLineInline(admin.TabularInline):
    model = StockCountLine
    extra = 0
    autocomplete_fields = ("product", "location", "counted_by")
    fields = (
        "product",
        "location",
        "system_quantity",
        "counted_quantity",
        "difference",
        "counted_by",
        "created_at",
    )
    readonly_fields = ("created_at",)


@admin.register(StockCountSession)
class StockCountSessionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "company",
        "warehouse",
        "count_type",
        "status",
        "started_at",
        "completed_at",
        "created_by",
        "created_at",
    )
    list_filter = (
        "company",
        "warehouse",
        "count_type",
        "status",
        "created_at",
    )
    search_fields = (
        "name",
        "scope_description",
        "warehouse__code",
        "warehouse__name",
    )
    readonly_fields = ("created_at", "updated_at")
    inlines = [StockCountLineInline]

    fieldsets = (
        (
            "Context",
            {
                "fields": (
                    "company",
                    "warehouse",
                    "name",
                    "count_type",
                    "status",
                )
            },
        ),
        (
            "Scope",
            {
                "fields": ("scope_description",),
            },
        ),
        (
            "Timing & audit",
            {
                "fields": (
                    "started_at",
                    "completed_at",
                    "created_by",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(CustomFieldDefinition)
class CustomFieldDefinitionAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "scope",
        "name",
        "label",
        "field_type",
        "is_required",
        "is_active",
        "order",
    )
    list_filter = (
        "company",
        "scope",
        "field_type",
        "is_required",
        "is_active",
    )
    search_fields = (
        "name",
        "label",
        "company__name",
    )
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Context",
            {
                "fields": (
                    "company",
                    "scope",
                )
            },
        ),
        (
            "Field definition",
            {
                "fields": (
                    "name",
                    "label",
                    "field_type",
                    "is_required",
                    "is_active",
                    "order",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(InventoryItemCustomFieldValue)
class InventoryItemCustomFieldValueAdmin(admin.ModelAdmin):
    list_display = (
        "item",
        "field",
        "value_text",
        "created_at",
        "updated_at",
    )
    list_filter = ("field__company", "field", "created_at")
    search_fields = (
        "item__product__sku",
        "item__product__name",
        "item__location__code",
        "field__name",
        "field__label",
        "value_text",
    )
    autocomplete_fields = ("item", "field")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ProductCustomFieldValue)
class ProductCustomFieldValueAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "field",
        "value_text",
        "created_at",
        "updated_at",
    )
    list_filter = ("field__company", "field__scope", "field", "created_at")
    search_fields = (
        "product__sku",
        "product__name",
        "field__name",
        "field__label",
        "value_text",
    )
    autocomplete_fields = ("product", "field")
    readonly_fields = ("created_at", "updated_at")
