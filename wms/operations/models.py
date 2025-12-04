from django.db import models

from accounts.models import Company, User
from masterdata.models import (
    Carrier,
    Customer,
    Location,
    Product,
    ReasonCode,
    Supplier,
    Warehouse,
)


class InboundOrder(models.Model):
    """
    Generic inbound document (could be a PO, return, or transfer-in).
    Keeps it simple for now, without full purchasing logic.
    """

    TYPE_PURCHASE = "purchase"
    TYPE_RETURN = "return"
    TYPE_TRANSFER = "transfer"

    TYPE_CHOICES = (
        (TYPE_PURCHASE, "Purchase"),
        (TYPE_RETURN, "Return"),
        (TYPE_TRANSFER, "Transfer"),
    )

    STATUS_DRAFT = "draft"
    STATUS_PLANNED = "planned"
    STATUS_RECEIVING = "receiving"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELED = "canceled"

    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_PLANNED, "Planned"),
        (STATUS_RECEIVING, "Receiving"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELED, "Canceled"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="inbound_orders",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="inbound_orders",
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inbound_orders",
    )

    order_number = models.CharField(max_length=100)
    external_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Reference in the upstream system (ERP, marketplace, etc.).",
    )

    order_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_PURCHASE,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )

    expected_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_inbound_orders",
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("company", "order_number")
        ordering = ("-created_at",)
        permissions = [
            ("view_orders", "Can view orders"),
            ("manage_orders", "Can create and manage orders"),
            ("pick_orders", "Can pick orders"),
            ("putaway", "Can perform putaway"),
        ]

    def __str__(self) -> str:
        return f"{self.order_number} ({self.warehouse})"


class InboundOrderLine(models.Model):
    """
    Line for an inbound order (product + expected qty).
    """

    inbound_order = models.ForeignKey(
        InboundOrder,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="inbound_order_lines",
    )

    expected_quantity = models.DecimalField(max_digits=18, decimal_places=3)
    received_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
    )

    uom = models.CharField(
        max_length=20,
        blank=True,
        help_text="Unit of measure code, e.g. EA, BOX.",
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.inbound_order.order_number} - {self.product.sku}"


class Receiving(models.Model):
    """
    Actual receiving event against an inbound order (one truck / delivery).
    """

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="receivings",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="receivings",
    )
    inbound_order = models.ForeignKey(
        InboundOrder,
        on_delete=models.CASCADE,
        related_name="receivings",
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Truck or document reference (e.g. ASN number).",
    )

    dock_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receivings",
        help_text="Inbound dock / staging area location.",
    )

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    received_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receivings",
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self) -> str:
        return f"Receiving {self.id} for {self.inbound_order.order_number}"


class ReceivingLine(models.Model):
    """
    Per-product detail within a receiving event.
    """

    receiving = models.ForeignKey(
        Receiving,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    order_line = models.ForeignKey(
        InboundOrderLine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receiving_lines",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="receiving_lines",
    )

    quantity = models.DecimalField(max_digits=18, decimal_places=3)

    batch = models.CharField(max_length=100, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    staging_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receiving_lines",
        help_text="Where the goods are initially placed after unloading.",
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.product.sku} x {self.quantity} in receiving {self.receiving_id}"


class PutawayTask(models.Model):
    """
    Task to move received goods from staging to final storage locations.
    """

    STATUS_PENDING = "pending"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELED = "canceled"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELED, "Canceled"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="putaway_tasks",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="putaway_tasks",
    )

    receiving_line = models.ForeignKey(
        ReceivingLine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="putaway_tasks",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="putaway_tasks",
    )

    source_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="putaway_source_tasks",
    )
    target_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="putaway_target_tasks",
    )

    quantity = models.DecimalField(max_digits=18, decimal_places=3)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="putaway_tasks",
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("status", "created_at")

    def __str__(self) -> str:
        return f"Putaway {self.product.sku} x {self.quantity} in {self.warehouse}"


class InternalMoveTask(models.Model):
    """
    Generic internal move task (re-slotting, consolidation, etc.).
    """

    STATUS_PENDING = "pending"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELED = "canceled"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELED, "Canceled"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="internal_move_tasks",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="internal_move_tasks",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="internal_move_tasks",
    )

    source_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internal_move_source_tasks",
    )
    target_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internal_move_target_tasks",
    )

    quantity = models.DecimalField(max_digits=18, decimal_places=3)

    reason_code = models.ForeignKey(
        ReasonCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internal_move_tasks",
    )
    comment = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internal_move_tasks",
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("status", "created_at")

    def __str__(self) -> str:
        return f"Move {self.product.sku} x {self.quantity} in {self.warehouse}"


class OutboundOrder(models.Model):
    """
    Generic outbound document (customer order, transfer-out, etc.).
    """

    TYPE_SALES = "sales"
    TYPE_TRANSFER = "transfer"
    TYPE_RETURN = "return"

    TYPE_CHOICES = (
        (TYPE_SALES, "Sales"),
        (TYPE_TRANSFER, "Transfer"),
        (TYPE_RETURN, "Return"),
    )

    STATUS_DRAFT = "draft"
    STATUS_PLANNED = "planned"
    STATUS_PICKING = "picking"
    STATUS_SHIPPED = "shipped"
    STATUS_CANCELED = "canceled"

    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_PLANNED, "Planned"),
        (STATUS_PICKING, "Picking"),
        (STATUS_SHIPPED, "Shipped"),
        (STATUS_CANCELED, "Canceled"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="outbound_orders",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="outbound_orders",
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outbound_orders",
    )

    order_number = models.CharField(max_length=100)
    external_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Reference from upstream order system.",
    )

    order_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_SALES,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )

    requested_ship_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_outbound_orders",
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("company", "order_number")
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.order_number} ({self.warehouse})"


class OutboundOrderLine(models.Model):
    """
    Line for an outbound order (product + ordered qty).
    """

    outbound_order = models.ForeignKey(
        OutboundOrder,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="outbound_order_lines",
    )

    ordered_quantity = models.DecimalField(max_digits=18, decimal_places=3)
    allocated_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
        help_text="Quantity reserved/allocated in inventory.",
    )
    shipped_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        default=0,
    )

    uom = models.CharField(
        max_length=20,
        blank=True,
        help_text="Unit of measure code, e.g. EA, BOX.",
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.outbound_order.order_number} - {self.product.sku}"


class PickingTask(models.Model):
    """
    Task to pick product from locations for outbound orders.
    """

    STATUS_PENDING = "pending"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELED = "canceled"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELED, "Canceled"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="picking_tasks",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="picking_tasks",
    )

    wave = models.ForeignKey(
        "PickingWave",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )

    outbound_line = models.ForeignKey(
        OutboundOrderLine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="picking_tasks",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="picking_tasks",
    )

    source_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="picking_source_tasks",
    )
    destination_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="picking_destination_tasks",
        help_text="Usually a packing/staging location.",
    )

    quantity = models.DecimalField(max_digits=18, decimal_places=3)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="picking_tasks",
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("status", "created_at")

    def __str__(self) -> str:
        return f"Pick {self.product.sku} x {self.quantity} in {self.warehouse}"


class PickingWave(models.Model):
    """
    Groups picking tasks into waves/batches for efficiency.
    """

    STATUS_PLANNED = "planned"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELED = "canceled"

    STATUS_CHOICES = (
        (STATUS_PLANNED, "Planned"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELED, "Canceled"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="picking_waves",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="picking_waves",
    )

    wave_number = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PLANNED,
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_picking_waves",
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("company", "wave_number")
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Wave {self.wave_number} ({self.warehouse})"


class Shipment(models.Model):
    """
    Represents a shipment (one or more outbound orders combined).
    """

    STATUS_DRAFT = "draft"
    STATUS_PACKING = "packing"
    STATUS_SHIPPED = "shipped"
    STATUS_CANCELED = "canceled"

    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_PACKING, "Packing"),
        (STATUS_SHIPPED, "Shipped"),
        (STATUS_CANCELED, "Canceled"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="shipments",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="shipments",
    )

    shipment_number = models.CharField(max_length=100)
    carrier = models.ForeignKey(
        Carrier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shipments",
    )
    carrier_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Free text carrier name if no master record.",
    )
    tracking_number = models.CharField(max_length=100, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )

    ship_to_name = models.CharField(max_length=255, blank=True)
    ship_to_address = models.TextField(blank=True)

    packed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_shipments",
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("company", "shipment_number")
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Shipment {self.shipment_number} ({self.warehouse})"


class ShipmentLine(models.Model):
    """
    Product-level detail within a shipment.
    """

    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    outbound_line = models.ForeignKey(
        OutboundOrderLine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shipment_lines",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="shipment_lines",
    )

    quantity = models.DecimalField(max_digits=18, decimal_places=3)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.shipment.shipment_number} - {self.product.sku} x {self.quantity}"
