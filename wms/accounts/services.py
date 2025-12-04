"""
Accounts service layer - Permission checks and user-warehouse management.
Combines Django's built-in permissions with warehouse-scoped roles.
"""

from accounts.models import Company, Role, User, UserWarehouse
from masterdata.models import Warehouse


def get_user_warehouses(user: User, active_only: bool = True) -> list[Warehouse]:
    """
    Get all warehouses a user has access to.
    Returns list of Warehouse objects.
    """
    filters = {"user": user, "is_active": True} if active_only else {"user": user}
    assignments = UserWarehouse.objects.filter(**filters).select_related("warehouse")
    return [assignment.warehouse for assignment in assignments]


def can_user_access_warehouse(user: User, warehouse: Warehouse) -> bool:
    """
    Check if user can access a warehouse (has active assignment).
    Superusers can access all warehouses.
    """
    if user.is_superuser:
        return True

    if not user.company or warehouse.company != user.company:
        return False

    return UserWarehouse.objects.filter(
        user=user,
        warehouse=warehouse,
        is_active=True,
    ).exists()


def get_user_warehouse_role(user: User, warehouse: Warehouse) -> Role | str | None:
    """
    Get user's role in a specific warehouse.
    Returns Role object (if using new system) or legacy role string, or None.
    """
    if user.is_superuser:
        # Superuser has admin-like access
        return "admin"

    assignment = (
        UserWarehouse.objects.filter(
            user=user,
            warehouse=warehouse,
            is_active=True,
        )
        .select_related("role")
        .first()
    )

    if not assignment:
        return None

    # Prefer new role FK over legacy role
    if assignment.role:
        return assignment.role
    return assignment.legacy_role or None


def can_user_manage_warehouse(user: User, warehouse: Warehouse) -> bool:
    """
    Check if user can manage a warehouse (admin or manager role).
    Also checks Django permission 'accounts.manage_warehouse' if set.
    """
    if user.is_superuser:
        return True

    if not can_user_access_warehouse(user, warehouse):
        return False

    # Check Django permission (direct or via role)
    if user.has_perm("accounts.manage_warehouse"):
        return True

    # Check warehouse role
    role = get_user_warehouse_role(user, warehouse)
    if isinstance(role, Role):
        # New role system - check if role has the permission
        return role.permissions.filter(codename="manage_warehouse").exists()
    # Legacy role system
    return role in ["admin", "manager"]


def can_user_pick_orders(user: User, warehouse: Warehouse) -> bool:
    """
    Check if user can pick orders in a warehouse.
    Requires operator, manager, or admin role, plus is_warehouse_operator flag.
    """
    if user.is_superuser:
        return True

    if not can_user_access_warehouse(user, warehouse):
        return False

    if not user.is_warehouse_operator:
        return False

    # Check Django permission (direct or via role)
    if user.has_perm("operations.pick_orders"):
        return True

    # Check warehouse role
    role = get_user_warehouse_role(user, warehouse)
    if isinstance(role, Role):
        # New role system - check if role has the permission
        return role.permissions.filter(
            codename="pick_orders", content_type__app_label="operations"
        ).exists()
    # Legacy role system
    return role in ["admin", "manager", "operator"]


def can_user_putaway(user: User, warehouse: Warehouse) -> bool:
    """
    Check if user can perform putaway operations.
    Requires operator, manager, or admin role, plus is_warehouse_operator flag.
    """
    if user.is_superuser:
        return True

    if not can_user_access_warehouse(user, warehouse):
        return False

    if not user.is_warehouse_operator:
        return False

    # Check Django permission (direct or via role)
    if user.has_perm("operations.putaway"):
        return True

    # Check warehouse role
    role = get_user_warehouse_role(user, warehouse)
    if isinstance(role, Role):
        # New role system - check if role has the permission
        return role.permissions.filter(
            codename="putaway", content_type__app_label="operations"
        ).exists()
    # Legacy role system
    return role in ["admin", "manager", "operator"]


def can_user_view_inventory(user: User, warehouse: Warehouse) -> bool:
    """
    Check if user can view inventory.
    All roles can view, but must have warehouse access.
    """
    if user.is_superuser:
        return True

    if not can_user_access_warehouse(user, warehouse):
        return False

    # Check Django permission
    if user.has_perm("inventory.view_inventory"):
        return True

    # All warehouse roles can view
    return True


def can_user_manage_inventory(user: User, warehouse: Warehouse) -> bool:
    """
    Check if user can manage inventory (adjustments, counts).
    Requires manager or admin role.
    """
    if user.is_superuser:
        return True

    if not can_user_access_warehouse(user, warehouse):
        return False

    # Check Django permission (direct or via role)
    if user.has_perm("inventory.manage_inventory"):
        return True

    # Check warehouse role
    role = get_user_warehouse_role(user, warehouse)
    if isinstance(role, Role):
        # New role system - check if role has the permission
        return role.permissions.filter(
            codename="manage_inventory", content_type__app_label="inventory"
        ).exists()
    # Legacy role system
    return role in ["admin", "manager"]


def can_user_view_orders(user: User, warehouse: Warehouse) -> bool:
    """
    Check if user can view orders.
    All roles can view, but must have warehouse access.
    """
    if user.is_superuser:
        return True

    if not can_user_access_warehouse(user, warehouse):
        return False

    # Check Django permission
    if user.has_perm("operations.view_orders"):
        return True

    # All warehouse roles can view
    return True


def can_user_manage_orders(user: User, warehouse: Warehouse) -> bool:
    """
    Check if user can create/manage orders.
    Requires manager or admin role.
    """
    if user.is_superuser:
        return True

    if not can_user_access_warehouse(user, warehouse):
        return False

    # Check Django permission (direct or via role)
    if user.has_perm("operations.manage_orders"):
        return True

    # Check warehouse role
    role = get_user_warehouse_role(user, warehouse)
    if isinstance(role, Role):
        # New role system - check if role has the permission
        return role.permissions.filter(
            codename="manage_orders", content_type__app_label="operations"
        ).exists()
    # Legacy role system
    return role in ["admin", "manager"]


def assign_user_to_warehouse(
    user: User,
    warehouse: Warehouse,
    role: Role | str = None,
    is_primary: bool = False,
) -> UserWarehouse:
    """
    Assign a user to a warehouse with a specific role.
    Creates or updates UserWarehouse assignment.

    Args:
        role: Can be a Role object (new system) or role string (legacy: 'admin', 'manager', 'operator', 'viewer')
    """
    if warehouse.company != user.company:
        raise ValueError("User and warehouse must belong to the same company")

    defaults = {
        "is_active": True,
        "is_primary": is_primary,
    }

    if isinstance(role, Role):
        # New role system
        if role.company != user.company:
            raise ValueError("Role must belong to the same company as user")
        defaults["role"] = role
        defaults["legacy_role"] = ""  # Clear legacy role
    elif isinstance(role, str):
        # Legacy role system
        if role not in [choice[0] for choice in UserWarehouse.ROLE_CHOICES]:
            raise ValueError(
                f"Invalid legacy role. Must be one of: {[c[0] for c in UserWarehouse.ROLE_CHOICES]}"
            )
        defaults["legacy_role"] = role
        defaults["role"] = None  # Clear new role
    else:
        # Default to operator if no role provided
        defaults["legacy_role"] = "operator"

    assignment, created = UserWarehouse.objects.update_or_create(
        user=user,
        warehouse=warehouse,
        defaults=defaults,
    )

    # If this is set as primary, unset other primary assignments
    if is_primary:
        UserWarehouse.objects.filter(
            user=user,
            is_primary=True,
        ).exclude(
            pk=assignment.pk
        ).update(is_primary=False)

    return assignment


def get_warehouse_users(
    warehouse: Warehouse,
    role: str = None,
    active_only: bool = True,
) -> list[User]:
    """
    Get all users assigned to a warehouse, optionally filtered by role.
    """
    filters = (
        {"warehouse": warehouse, "is_active": True}
        if active_only
        else {"warehouse": warehouse}
    )
    if role:
        filters["role"] = role

    assignments = UserWarehouse.objects.filter(**filters).select_related("user")
    return [assignment.user for assignment in assignments]


def get_user_default_warehouse(user: User) -> Warehouse | None:
    """
    Get user's default warehouse (primary assignment or default_warehouse field).
    """
    if user.default_warehouse:
        return user.default_warehouse

    primary = UserWarehouse.objects.filter(
        user=user,
        is_primary=True,
        is_active=True,
    ).first()

    return primary.warehouse if primary else None


def require_warehouse_access(user: User, warehouse: Warehouse) -> None:
    """
    Raise PermissionError if user cannot access warehouse.
    Use in API views/services for access control.
    """
    if not can_user_access_warehouse(user, warehouse):
        raise PermissionError(
            f"User {user.username} does not have access to warehouse {warehouse.code}"
        )


def require_warehouse_permission(
    user: User,
    warehouse: Warehouse,
    permission_func,
) -> None:
    """
    Raise PermissionError if user doesn't have required permission.
    permission_func should be one of the can_user_* functions above.
    """
    if not permission_func(user, warehouse):
        raise PermissionError(
            f"User {user.username} does not have required permission for warehouse {warehouse.code}"
        )
