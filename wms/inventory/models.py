from django.db import models

from accounts.models import Company, User
from masterdata.models import Location, Product, Warehouse


class InventoryItem(models.Model):
    """
    Current on-hand stock at a specific warehouse/location for a product.
    Location/model relations to be wired once masterdata locations & products exist.
    """

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="inventory_items",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="inventory_items",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="inventory_items",
        null=True,
        blank=True,
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_items",
    )

    batch = models.CharField(
        max_length=100,
        blank=True,
        help_text="Batch / lot number if you need batch tracking.",
    )
    expiry_date = models.DateField(null=True, blank=True)

    quantity = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    reserved_quantity = models.DecimalField(
        max_digits=18, decimal_places=3, default=0, help_text="Qty reserved for orders."
    )

    is_locked = models.BooleanField(
        default=False,
        help_text="If true, stock cannot be moved (e.g. under investigation).",
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["company", "warehouse", "product", "location"],
            ),
        ]
        permissions = [
            ("view_inventory", "Can view inventory"),
            ("manage_inventory", "Can manage inventory (adjustments, counts)"),
        ]

    def __str__(self) -> str:
        location_code = self.location.code if self.location else "UNASSIGNED"
        product_sku = self.product.sku if self.product else "UNKNOWN"
        return f"{product_sku} @ {self.warehouse} ({location_code})"


class InventoryMovement(models.Model):
    """
    Immutable record of every stock movement (inbound, outbound, move, adjustment).
    """

    TYPE_INBOUND = "inbound"
    TYPE_OUTBOUND = "outbound"
    TYPE_MOVE = "move"
    TYPE_ADJUSTMENT = "adjustment"

    TYPE_CHOICES = (
        (TYPE_INBOUND, "Inbound"),
        (TYPE_OUTBOUND, "Outbound"),
        (TYPE_MOVE, "Move"),
        (TYPE_ADJUSTMENT, "Adjustment"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="inventory_movements",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="inventory_movements",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="inventory_movements",
        null=True,
        blank=True,
    )
    location_from = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movement_source",
    )
    location_to = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movement_destination",
    )

    batch = models.CharField(max_length=100, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    movement_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
    )
    quantity = models.DecimalField(max_digits=18, decimal_places=3)

    reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="External reference (order, PO, task id, etc.).",
    )
    reason = models.CharField(max_length=255, blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_inventory_movements",
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=[
                    "company",
                    "warehouse",
                    "product",
                    "movement_type",
                    "created_at",
                ]
            ),
        ]

    def __str__(self) -> str:
        product_sku = self.product.sku if self.product else "UNKNOWN"
        return f"{self.movement_type} {product_sku} {self.quantity} @ {self.warehouse}"


class StockAdjustment(models.Model):
    """
    Represents an adjustment event (e.g. damage, loss, count variance).
    Links to one or more InventoryMovement records logically via reference.
    """

    ADJUSTMENT_REASON_CHOICES = (
        ("damage", "Damage"),
        ("loss", "Loss / Missing"),
        ("count", "Stock count variance"),
        ("other", "Other"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="stock_adjustments",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="stock_adjustments",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="stock_adjustments",
        null=True,
        blank=True,
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_adjustments",
    )

    reason = models.CharField(
        max_length=20,
        choices=ADJUSTMENT_REASON_CHOICES,
        default="other",
    )
    description = models.TextField(blank=True)

    quantity_difference = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        help_text="Positive = increase stock, negative = decrease.",
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional link to count session / external document.",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_adjustments",
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self) -> str:
        product_sku = self.product.sku if self.product else "UNKNOWN"
        return f"Adjustment {product_sku} {self.quantity_difference} @ {self.warehouse}"


class StockCountSession(models.Model):
    """
    A stock count (cycle count or full count) session for a warehouse.
    """

    TYPE_CYCLE = "cycle"
    TYPE_FULL = "full"

    TYPE_CHOICES = (
        (TYPE_CYCLE, "Cycle count"),
        (TYPE_FULL, "Full count"),
    )

    STATUS_DRAFT = "draft"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELED = "canceled"

    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELED, "Canceled"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="stock_count_sessions",
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="stock_count_sessions",
    )

    name = models.CharField(max_length=255)
    count_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_CYCLE,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )

    # Optional scope fields (e.g., which locations or products are included)
    scope_description = models.TextField(
        blank=True,
        help_text="Free-text description of what is being counted.",
    )

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_stock_count_sessions",
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.name} ({self.warehouse})"


class StockCountLine(models.Model):
    """
    Individual counted line within a stock count session.
    """

    session = models.ForeignKey(
        StockCountSession,
        on_delete=models.CASCADE,
        related_name="lines",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="stock_count_lines",
        null=True,
        blank=True,
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_count_lines",
    )

    system_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        help_text="Quantity according to system at the time of counting.",
    )
    counted_quantity = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        help_text="Quantity physically counted.",
    )

    difference = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        help_text="counted - system",
    )

    counted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_count_lines",
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "session",
                    "product",
                    "location",
                ]
            ),
        ]

    def __str__(self) -> str:
        product_sku = self.product.sku if self.product else "UNKNOWN"
        location_code = self.location.code if self.location else "UNASSIGNED"
        return f"{product_sku} @ {location_code} ({self.session})"


class CustomFieldDefinition(models.Model):
    """
    Per-company configurable custom fields, scoped to products or inventory items.
    Same field definition can be reused across scopes (e.g., "color" for both products and inventory).
    """

    SCOPE_PRODUCT = "product"
    SCOPE_INVENTORY_ITEM = "inventory_item"

    SCOPE_CHOICES = (
        (SCOPE_PRODUCT, "Product"),
        (SCOPE_INVENTORY_ITEM, "Inventory item"),
    )

    FIELD_TYPE_TEXT = "text"
    FIELD_TYPE_NUMBER = "number"
    FIELD_TYPE_BOOLEAN = "boolean"
    FIELD_TYPE_DATE = "date"

    FIELD_TYPE_CHOICES = (
        (FIELD_TYPE_TEXT, "Text"),
        (FIELD_TYPE_NUMBER, "Number"),
        (FIELD_TYPE_BOOLEAN, "Boolean"),
        (FIELD_TYPE_DATE, "Date"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="custom_field_definitions",
    )

    scope = models.CharField(
        max_length=50,
        choices=SCOPE_CHOICES,
        default=SCOPE_INVENTORY_ITEM,
    )

    name = models.CharField(
        max_length=100,
        help_text="Internal key, e.g. 'color' or 'qc_status'.",
    )
    label = models.CharField(
        max_length=100,
        help_text="User-facing label, e.g. 'Color' or 'QC Status'.",
    )

    field_type = models.CharField(
        max_length=20,
        choices=FIELD_TYPE_CHOICES,
        default=FIELD_TYPE_TEXT,
    )

    is_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("company", "scope", "name")
        ordering = ("company__name", "scope", "order", "name")

    def __str__(self) -> str:
        return f"{self.company} - {self.scope} - {self.label}"


class InventoryItemCustomFieldValue(models.Model):
    """
    Value of a custom field for a specific inventory item.
    Stored as text; your services/UI can cast based on field_type.
    """

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name="custom_field_values",
    )
    field = models.ForeignKey(
        CustomFieldDefinition,
        on_delete=models.CASCADE,
        related_name="inventory_values",
    )

    value_text = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("item", "field")

    def __str__(self) -> str:
        return f"{self.item} - {self.field.label}: {self.value_text}"


class ProductCustomFieldValue(models.Model):
    """
    Value of a custom field for a specific product.
    Stored as text; your services/UI can cast based on field_type.
    """

    product = models.ForeignKey(
        "masterdata.Product",
        on_delete=models.CASCADE,
        related_name="custom_field_values",
    )
    field = models.ForeignKey(
        CustomFieldDefinition,
        on_delete=models.CASCADE,
        related_name="product_values",
    )

    value_text = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("product", "field")

    def __str__(self) -> str:
        return f"{self.product.sku} - {self.field.label}: {self.value_text}"
