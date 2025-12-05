from django.db import models

from accounts.models import Company


class Warehouse(models.Model):
    """
    Physical warehouse belonging to a company.
    """

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="warehouses",
    )

    # Identity
    code = models.CharField(
        max_length=50,
        help_text="Short unique code for this warehouse (e.g. WH-01, KHI-01). Unique per company.",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Address / location info
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # Geo / time settings
    time_zone = models.CharField(max_length=50, blank=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    # Operational flags / types
    WAREHOUSE_TYPE_CHOICES = (
        ("main", "Main DC"),
        ("store", "Store / Outlet"),
        ("3pl", "3PL / External"),
        ("other", "Other"),
    )
    type = models.CharField(
        max_length=20,
        choices=WAREHOUSE_TYPE_CHOICES,
        default="main",
    )
    is_active = models.BooleanField(default=True)

    # Default operational settings (you can use them later in logic)
    allow_negative_stock = models.BooleanField(default=False)
    uses_bins = models.BooleanField(
        default=True,
        help_text="If false, you might store stock at warehouse level only.",
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ("company__name", "code")

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class WarehouseZone(models.Model):
    """
    Logical zone within a warehouse (e.g. Inbound, Outbound, Frozen, Mezzanine).
    """

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="zones",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(
        max_length=20,
        blank=True,
        help_text="For UI highlighting (hex code).",
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("warehouse", "name")
        ordering = ("warehouse__code", "name")

    def __str__(self) -> str:
        return f"{self.warehouse.code} - {self.name}"


class LocationType(models.Model):
    """
    Defines behavior/usage for locations (picking, reserve, staging, cold storage, etc.).
    """

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="location_types",
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    is_pickable = models.BooleanField(default=True)
    is_putaway_allowed = models.BooleanField(default=True)
    is_countable = models.BooleanField(default=True)

    temperature_zone = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g. ambient, chiller, freezer.",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ("company__name", "code")

    def __str__(self) -> str:
        return f"{self.company} - {self.name}"


class Section(models.Model):
    """
    Sections (or areas) belong to a warehouse (e.g. Aisle A, Bulk Area, Inbound Area).
    """

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="sections",
    )
    zone = models.ForeignKey(
        WarehouseZone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sections",
    )

    code = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("warehouse", "code")
        ordering = ("warehouse__code", "code")

    def __str__(self) -> str:
        return f"{self.warehouse.code} - {self.code}"


class Rack(models.Model):
    """
    Racks/shelves within a section.
    """

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="racks",
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="racks",
    )

    code = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    levels = models.PositiveIntegerField(default=1)
    positions_per_level = models.PositiveIntegerField(default=1)

    max_weight_kg = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    max_volume_cbm = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("section", "code")
        ordering = ("section__warehouse__code", "section__code", "code")

    def __str__(self) -> str:
        return f"{self.section.code}-{self.code}"


class Location(models.Model):
    """
    Bin/location within a warehouse (optionally linked to section/rack).
    """

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="locations",
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="locations",
    )
    rack = models.ForeignKey(
        Rack,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="locations",
    )

    location_type = models.ForeignKey(
        LocationType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="locations",
    )

    code = models.CharField(
        max_length=100,
        help_text="Human readable code (e.g. A1-R01-BIN05).",
    )
    barcode = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional barcode / QR for scanning.",
    )
    description = models.TextField(blank=True)

    pick_sequence = models.PositiveIntegerField(
        default=0,
        help_text="Used to optimize picking routes (lower = earlier).",
    )

    length_cm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    width_cm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    height_cm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    max_weight_kg = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("warehouse", "code")
        ordering = ("warehouse__code", "code")

    def __str__(self) -> str:
        return f"{self.warehouse.code}:{self.code}"


class UnitOfMeasure(models.Model):
    """
    Units of measure with conversion info per company (e.g. EA, BOX, PALLET).
    """

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="units_of_measure",
    )

    name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=20)
    description = models.TextField(blank=True)

    base_unit = models.CharField(
        max_length=20,
        help_text="Reference unit code used for conversions (e.g. EA).",
    )
    conversion_factor = models.DecimalField(
        max_digits=12,
        decimal_places=5,
        help_text="How many base units make one of this unit.",
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("company", "abbreviation")
        ordering = ("company__name", "name")

    def __str__(self) -> str:
        return f"{self.company} - {self.abbreviation}"


class ProductCategory(models.Model):
    """
    Category tree for products.
    """

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="product_categories",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("company", "name")
        ordering = ("company__name", "name")

    def __str__(self) -> str:
        return f"{self.company} - {self.name}"


class Product(models.Model):
    """
    Product / SKU master data.
    """

    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_DISCONTINUED = "discontinued"

    STATUS_CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
        (STATUS_DISCONTINUED, "Discontinued"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="products",
    )
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )

    sku = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
    )

    default_uom = models.CharField(
        max_length=20, help_text="Primary UOM code (e.g. EA)"
    )
    storage_uom = models.CharField(
        max_length=20,
        blank=True,
        help_text="Optional alternate UOM used in storage.",
    )

    weight_kg = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True
    )
    length_cm = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    width_cm = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    height_cm = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    volume_cbm = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )

    track_batch = models.BooleanField(default=False)
    track_serial = models.BooleanField(default=False)
    hazardous = models.BooleanField(default=False)
    requires_lot_expiry = models.BooleanField(default=False)

    storage_requirements = models.TextField(
        blank=True,
        help_text="Special instructions (temperature, stacking rules, etc.).",
    )

    image_url = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("company", "sku")
        ordering = ("company__name", "sku")

    def __str__(self) -> str:
        return f"{self.sku} - {self.name}"


class ProductBarcode(models.Model):
    """
    Multiple barcodes per product (EAN, UPC, internal codes, etc.).
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="barcodes",
    )
    barcode = models.CharField(max_length=100)
    is_primary = models.BooleanField(default=False)
    label = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. 'EAN13', 'Case barcode'.",
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("product", "barcode")

    def __str__(self) -> str:
        return f"{self.product.sku} - {self.barcode}"


class Supplier(models.Model):
    """
    Supplier / vendor master data.
    """

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="suppliers",
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)

    address = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ("company__name", "code")

    def __str__(self) -> str:
        return f"{self.company} - {self.code} ({self.name})"


class Customer(models.Model):
    """
    Customer master data for outbound orders and shipments.
    """

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="customers",
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)

    billing_address = models.TextField(blank=True)
    shipping_address = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ("company__name", "code")

    def __str__(self) -> str:
        return f"{self.company} - {self.code} ({self.name})"


class Carrier(models.Model):
    """
    Carrier / logistics provider for shipments.
    """

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="carriers",
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True)

    account_number = models.CharField(max_length=100, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("company", "name")
        ordering = ("company__name", "name")

    def __str__(self) -> str:
        return f"{self.company} - {self.name}"


class ReasonCode(models.Model):
    """
    Standard reason codes for adjustments, returns, etc.
    """

    CATEGORY_ADJUSTMENT = "adjustment"
    CATEGORY_RETURN = "return"
    CATEGORY_MOVE = "move"

    CATEGORY_CHOICES = (
        (CATEGORY_ADJUSTMENT, "Adjustment"),
        (CATEGORY_RETURN, "Return"),
        (CATEGORY_MOVE, "Move"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="reason_codes",
    )
    code = models.CharField(max_length=50)
    description = models.CharField(max_length=255)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_ADJUSTMENT,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("company", "code")
        ordering = ("company__name", "code")

    def __str__(self) -> str:
        return f"{self.company} - {self.code}"
