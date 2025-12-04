from django.contrib.auth.models import AbstractUser, Permission
from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)

    # Basic contact / identity
    legal_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)

    # Address info (optional but useful)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # Business details
    tax_id = models.CharField(max_length=100, blank=True)
    registration_number = models.CharField(max_length=100, blank=True)

    # Status / timestamps
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self) -> str:
        return self.name


class User(AbstractUser):
    """
    Custom user model that keeps Django's auth/permission system
    and adds company + warehouse assignment.
    """

    # Company this employee belongs to
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
    )

    warehouses = models.ManyToManyField(
        "masterdata.Warehouse",
        through="UserWarehouse",
        related_name="users",
        blank=True,
    )

    # Preferred / default warehouse for this user
    default_warehouse = models.ForeignKey(
        "masterdata.Warehouse",
        on_delete=models.SET_NULL,
        related_name="default_users",
        null=True,
        blank=True,
    )

    # Extra HR / profile fields
    employee_code = models.CharField(max_length=100, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    mobile = models.CharField(max_length=50, blank=True)

    # Preferences
    language = models.CharField(max_length=10, blank=True, help_text="e.g. en, en-US")
    time_zone = models.CharField(max_length=50, blank=True)

    # Flags
    is_warehouse_operator = models.BooleanField(
        default=False,
        help_text="Can operate on warehouse tasks (picking, putaway, etc.).",
    )

    def __str__(self) -> str:
        return f"{self.username} ({self.company})"


class Role(models.Model):
    """
    Company-defined roles with Django permissions.
    Companies can create custom roles and assign specific permissions to them.
    """

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="roles",
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Link to Django's built-in Permission model
    permissions = models.ManyToManyField(
        Permission,
        related_name="roles",
        blank=True,
        help_text="Django permissions assigned to this role.",
    )

    is_system_role = models.BooleanField(
        default=False,
        help_text="System roles (admin, manager, etc.) cannot be deleted.",
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("company", "name")
        ordering = ("company__name", "name")

    def __str__(self) -> str:
        return f"{self.company.name} - {self.name}"


class UserWarehouse(models.Model):
    """
    Links user to warehouse with a role.
    Uses Role FK for flexibility, but keeps legacy role field for backward compatibility.
    """

    # Legacy role choices (kept for backward compatibility during migration)
    ROLE_CHOICES = (
        ("admin", "Admin"),
        ("manager", "Manager"),
        ("operator", "Operator"),
        ("viewer", "Viewer"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="warehouse_assignments",
    )
    warehouse = models.ForeignKey(
        "masterdata.Warehouse",
        on_delete=models.CASCADE,
        related_name="user_assignments",
    )

    # New flexible role system (preferred)
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_warehouse_assignments",
        help_text="Custom role with specific permissions. Takes precedence over legacy_role.",
    )

    # Legacy role field (for backward compatibility, will be removed in future)
    legacy_role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        blank=True,
        help_text="Legacy role field. Use 'role' FK instead.",
    )

    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False)

    assigned_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("user", "warehouse")

    def __str__(self) -> str:
        return f"{self.user} @ {self.warehouse}"


class CompanySetting(models.Model):
    """
    Per-company configuration flags and defaults.
    Keep it generic so you can grow without changing the core Company model a lot.
    """

    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="settings",
    )

    default_language = models.CharField(max_length=10, blank=True)
    default_time_zone = models.CharField(max_length=50, blank=True)

    # Inventory / operations preferences
    allow_negative_stock_global = models.BooleanField(default=False)
    require_strict_location_scanning = models.BooleanField(
        default=True,
        help_text="If true, force scanning/validating bin locations during operations.",
    )

    # Place for extra JSON-style config (per integrations, UI flags, etc.)
    extra = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self) -> str:
        return f"Settings for {self.company}"


class Invitation(models.Model):
    """
    Invitation flow for adding employees to a company,
    optionally pre-assigning warehouses and a role.
    """

    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_EXPIRED = "expired"
    STATUS_CANCELED = "canceled"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_CANCELED, "Canceled"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="invitations",
    )

    email = models.EmailField()
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_invitations",
    )

    # You will generate this token in services when sending the invite email
    token = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    # Optional: pre-assign warehouses and a role
    warehouses = models.ManyToManyField(
        "masterdata.Warehouse",
        related_name="invitations",
        blank=True,
    )
    role = models.CharField(
        max_length=20,
        choices=UserWarehouse.ROLE_CHOICES,
        default="operator",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["company", "email"]),
            models.Index(fields=["token"]),
        ]

    def __str__(self) -> str:
        return f"Invitation {self.email} to {self.company} ({self.status})"


class AuditLog(models.Model):
    """
    Simple audit trail of important actions, scoped by company.
    You can call this from services when key things happen (e.g. stock adjustment).
    """

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    action = models.CharField(max_length=255)
    object_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Model or entity type, e.g. 'Warehouse', 'Product', 'InventoryItem'.",
    )
    object_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Identifier of the affected object (pk or external id).",
    )
    description = models.TextField(blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["company", "created_at"]),
            models.Index(fields=["object_type", "object_id"]),
        ]

    def __str__(self) -> str:
        return f"[{self.company}] {self.action} by {self.user or 'system'}"
