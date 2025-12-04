from django.contrib import admin

from .models import (
    InboundOrder,
    InboundOrderLine,
    InternalMoveTask,
    OutboundOrder,
    OutboundOrderLine,
    PickingTask,
    PickingWave,
    PutawayTask,
    Receiving,
    ReceivingLine,
    Shipment,
    ShipmentLine,
)


class InboundOrderLineInline(admin.TabularInline):
    model = InboundOrderLine
    extra = 0
    autocomplete_fields = ("product",)
    fields = ("product", "expected_quantity", "received_quantity", "uom")


@admin.register(InboundOrderLine)
class InboundOrderLineAdmin(admin.ModelAdmin):
    list_display = (
        "inbound_order",
        "product",
        "expected_quantity",
        "received_quantity",
        "uom",
        "created_at",
    )
    list_filter = ("inbound_order__company", "inbound_order__warehouse")
    search_fields = (
        "inbound_order__order_number",
        "product__sku",
        "product__name",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(InboundOrder)
class InboundOrderAdmin(admin.ModelAdmin):
    inlines = [InboundOrderLineInline]

    list_display = (
        "order_number",
        "company",
        "warehouse",
        "supplier",
        "order_type",
        "status",
        "expected_at",
        "completed_at",
        "created_at",
    )
    list_filter = (
        "company",
        "warehouse",
        "supplier",
        "order_type",
        "status",
        "expected_at",
    )
    search_fields = (
        "order_number",
        "external_reference",
        "company__name",
        "warehouse__code",
        "warehouse__name",
        "supplier__code",
        "supplier__name",
    )
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "company",
                    "warehouse",
                    "supplier",
                    "order_number",
                    "external_reference",
                    "order_type",
                    "status",
                )
            },
        ),
        (
            "Timing",
            {
                "fields": (
                    "expected_at",
                    "completed_at",
                )
            },
        ),
        ("Audit", {"fields": ("created_by", "created_at", "updated_at")}),
    )


class ReceivingLineInline(admin.TabularInline):
    model = ReceivingLine
    extra = 0
    autocomplete_fields = ("order_line", "product", "staging_location")
    fields = (
        "order_line",
        "product",
        "quantity",
        "batch",
        "expiry_date",
        "staging_location",
        "created_at",
    )
    readonly_fields = ("created_at",)


@admin.register(Receiving)
class ReceivingAdmin(admin.ModelAdmin):
    inlines = [ReceivingLineInline]

    list_display = (
        "id",
        "company",
        "warehouse",
        "inbound_order",
        "reference",
        "dock_location",
        "started_at",
        "completed_at",
        "received_by",
        "created_at",
    )
    list_filter = (
        "company",
        "warehouse",
        "inbound_order",
        "started_at",
        "completed_at",
    )
    search_fields = (
        "id",
        "reference",
        "inbound_order__order_number",
        "warehouse__code",
        "warehouse__name",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(PutawayTask)
class PutawayTaskAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "warehouse",
        "product",
        "quantity",
        "source_location",
        "target_location",
        "status",
        "assigned_to",
        "created_at",
    )
    list_filter = (
        "company",
        "warehouse",
        "status",
        "assigned_to",
    )
    search_fields = (
        "product__sku",
        "product__name",
        "source_location__code",
        "target_location__code",
    )
    readonly_fields = ("created_at",)


@admin.register(OutboundOrder)
class OutboundOrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "company",
        "warehouse",
        "customer",
        "order_type",
        "status",
        "requested_ship_at",
        "shipped_at",
        "created_at",
    )
    list_filter = (
        "company",
        "warehouse",
        "customer",
        "order_type",
        "status",
        "requested_ship_at",
    )
    search_fields = (
        "order_number",
        "external_reference",
        "company__name",
        "warehouse__code",
        "warehouse__name",
        "customer__code",
        "customer__name",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(OutboundOrderLine)
class OutboundOrderLineAdmin(admin.ModelAdmin):
    list_display = (
        "outbound_order",
        "product",
        "ordered_quantity",
        "allocated_quantity",
        "shipped_quantity",
        "uom",
    )
    list_filter = ("outbound_order__company", "outbound_order__warehouse")
    search_fields = (
        "outbound_order__order_number",
        "product__sku",
        "product__name",
    )


@admin.register(PickingWave)
class PickingWaveAdmin(admin.ModelAdmin):
    list_display = (
        "wave_number",
        "company",
        "warehouse",
        "status",
        "created_by",
        "created_at",
        "started_at",
        "completed_at",
    )
    list_filter = ("company", "warehouse", "status", "created_at")
    search_fields = ("wave_number", "company__name", "warehouse__code", "warehouse__name")
    readonly_fields = ("created_at", "started_at", "completed_at")


@admin.register(PickingTask)
class PickingTaskAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "warehouse",
        "product",
        "quantity",
        "source_location",
        "destination_location",
        "status",
        "assigned_to",
        "wave",
        "created_at",
    )
    list_filter = (
        "company",
        "warehouse",
        "status",
        "assigned_to",
        "wave",
    )
    search_fields = (
        "product__sku",
        "product__name",
        "source_location__code",
        "destination_location__code",
        "wave__wave_number",
    )
    readonly_fields = ("created_at",)


@admin.register(InternalMoveTask)
class InternalMoveTaskAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "warehouse",
        "product",
        "quantity",
        "source_location",
        "target_location",
        "reason_code",
        "status",
        "assigned_to",
        "created_at",
    )
    list_filter = (
        "company",
        "warehouse",
        "status",
        "reason_code",
        "assigned_to",
    )
    search_fields = (
        "product__sku",
        "product__name",
        "source_location__code",
        "target_location__code",
        "reason_code__code",
    )
    readonly_fields = ("created_at",)


class ShipmentLineInline(admin.TabularInline):
    model = ShipmentLine
    extra = 0
    autocomplete_fields = ("outbound_line", "product")
    fields = ("outbound_line", "product", "quantity", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    inlines = [ShipmentLineInline]

    list_display = (
        "shipment_number",
        "company",
        "warehouse",
        "carrier",
        "status",
        "tracking_number",
        "packed_at",
        "shipped_at",
        "created_at",
    )
    list_filter = (
        "company",
        "warehouse",
        "carrier",
        "status",
        "shipped_at",
    )
    search_fields = (
        "shipment_number",
        "tracking_number",
        "company__name",
        "warehouse__code",
        "warehouse__name",
        "carrier__name",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(ShipmentLine)
class ShipmentLineAdmin(admin.ModelAdmin):
    list_display = (
        "shipment",
        "product",
        "quantity",
        "created_at",
    )
    list_filter = ("shipment__company", "shipment__warehouse")
    search_fields = (
        "shipment__shipment_number",
        "product__sku",
        "product__name",
    )
    readonly_fields = ("created_at", "updated_at")

from django.contrib import admin

# Register your models here.
