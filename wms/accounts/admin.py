from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    AuditLog,
    Company,
    CompanySetting,
    Invitation,
    Role,
    User,
    UserWarehouse,
)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "legal_name",
        "email",
        "phone",
        "country",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "country", "created_at")
    search_fields = (
        "name",
        "legal_name",
        "email",
        "phone",
        "tax_id",
        "registration_number",
    )
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Basic info",
            {
                "fields": (
                    "name",
                    "legal_name",
                    "is_active",
                )
            },
        ),
        (
            "Contact",
            {
                "fields": (
                    "email",
                    "phone",
                    "website",
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
            "Business details",
            {
                "fields": (
                    "tax_id",
                    "registration_number",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


class UserWarehouseInline(admin.TabularInline):
    model = UserWarehouse
    extra = 0
    autocomplete_fields = ("warehouse",)
    fields = ("warehouse", "role", "is_active", "is_primary", "assigned_at")
    readonly_fields = ("assigned_at",)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    inlines = [UserWarehouseInline]

    list_display = (
        "username",
        "email",
        "company",
        "default_warehouse",
        "is_staff",
        "is_active",
        "is_warehouse_operator",
    )
    list_filter = (
        "company",
        "is_staff",
        "is_superuser",
        "is_active",
        "is_warehouse_operator",
        "groups",
    )
    search_fields = ("username", "email", "first_name", "last_name", "employee_code")

    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "Company & Warehouse",
            {
                "fields": (
                    "company",
                    "default_warehouse",
                    "is_warehouse_operator",
                )
            },
        ),
        (
            "Profile",
            {
                "fields": (
                    "employee_code",
                    "job_title",
                    "phone",
                    "mobile",
                    "language",
                    "time_zone",
                )
            },
        ),
    )

    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (
            "Company & Warehouse",
            {
                "classes": ("wide",),
                "fields": (
                    "company",
                    "default_warehouse",
                    "is_warehouse_operator",
                ),
            },
        ),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "company",
        "is_system_role",
        "is_active",
        "permission_count",
        "created_at",
    )
    list_filter = ("company", "is_system_role", "is_active", "created_at")
    search_fields = ("name", "description", "company__name")
    filter_horizontal = ("permissions",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Basic info",
            {
                "fields": (
                    "company",
                    "name",
                    "description",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": ("permissions",),
                "description": "Select Django permissions for this role.",
            },
        ),
        (
            "Settings",
            {
                "fields": (
                    "is_system_role",
                    "is_active",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def permission_count(self, obj):
        return obj.permissions.count()

    permission_count.short_description = "Permissions"


@admin.register(UserWarehouse)
class UserWarehouseAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "warehouse",
        "role_display",
        "is_active",
        "is_primary",
        "assigned_at",
    )
    list_filter = ("role", "legacy_role", "is_active", "is_primary", "warehouse__company")
    search_fields = ("user__username", "user__email", "warehouse__name", "warehouse__code", "role__name")
    autocomplete_fields = ("user", "warehouse", "role")
    readonly_fields = ("assigned_at", "updated_at")

    fieldsets = (
        (
            "Assignment",
            {
                "fields": (
                    "user",
                    "warehouse",
                )
            },
        ),
        (
            "Role",
            {
                "fields": (
                    "role",
                    "legacy_role",
                ),
                "description": "Use 'role' (new system) or 'legacy_role' (old system).",
            },
        ),
        (
            "Settings",
            {
                "fields": (
                    "is_active",
                    "is_primary",
                )
            },
        ),
        ("Timestamps", {"fields": ("assigned_at", "updated_at")}),
    )

    def role_display(self, obj):
        if obj.role:
            return f"{obj.role.name} (Custom)"
        return obj.get_legacy_role_display() if obj.legacy_role else "None"

    role_display.short_description = "Role"


@admin.register(CompanySetting)
class CompanySettingAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "default_language",
        "default_time_zone",
        "allow_negative_stock_global",
        "require_strict_location_scanning",
    )
    list_filter = (
        "allow_negative_stock_global",
        "require_strict_location_scanning",
    )
    search_fields = ("company__name", "company__legal_name")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Company",
            {
                "fields": ("company",),
            },
        ),
        (
            "Defaults",
            {
                "fields": (
                    "default_language",
                    "default_time_zone",
                )
            },
        ),
        (
            "Inventory & operations",
            {
                "fields": (
                    "allow_negative_stock_global",
                    "require_strict_location_scanning",
                )
            },
        ),
        ("Extra config", {"fields": ("extra",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "company",
        "role",
        "status",
        "invited_by",
        "expires_at",
        "accepted_at",
        "created_at",
    )
    list_filter = ("status", "role", "company", "created_at")
    search_fields = ("email", "company__name", "invited_by__username")
    autocomplete_fields = ("company", "invited_by", "warehouses")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Invitation details",
            {
                "fields": (
                    "company",
                    "email",
                    "invited_by",
                    "role",
                    "warehouses",
                )
            },
        ),
        (
            "Status & timing",
            {
                "fields": (
                    "status",
                    "token",
                    "expires_at",
                    "accepted_at",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "company",
        "user",
        "action",
        "object_type",
        "object_id",
    )
    list_filter = ("company", "object_type", "created_at")
    search_fields = (
        "action",
        "object_type",
        "object_id",
        "description",
        "user__username",
        "company__name",
    )
    readonly_fields = (
        "company",
        "user",
        "action",
        "object_type",
        "object_id",
        "description",
        "ip_address",
        "user_agent",
        "created_at",
    )

    def has_add_permission(self, request):
        # Audit logs should be created by the system, not by hand.
        return False
