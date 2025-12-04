"""
Tests for accounts service functions.
"""

import pytest
from django.contrib.auth.models import Permission

from accounts.models import Role, UserWarehouse
from accounts.services import (
    assign_user_to_warehouse,
    can_user_access_warehouse,
    can_user_manage_inventory,
    can_user_manage_orders,
    can_user_manage_warehouse,
    can_user_pick_orders,
    can_user_putaway,
    can_user_view_inventory,
    get_user_default_warehouse,
    get_user_warehouse_role,
    get_user_warehouses,
    get_warehouse_users,
)
from masterdata.models import Warehouse


class TestAccountsServices:
    """Test accounts service functions."""

    def test_get_user_warehouses(self, user, warehouse, warehouse2, role):
        """Test getting user's warehouses."""
        UserWarehouse.objects.create(
            user=user,
            warehouse=warehouse,
            role=role,
            is_active=True,
        )
        UserWarehouse.objects.create(
            user=user,
            warehouse=warehouse2,
            role=role,
            is_active=True,
        )

        warehouses = get_user_warehouses(user)
        assert len(warehouses) == 2
        assert warehouse in warehouses
        assert warehouse2 in warehouses

    def test_get_user_warehouses_active_only(self, user, warehouse, warehouse2, role):
        """Test getting only active warehouse assignments."""
        UserWarehouse.objects.create(
            user=user,
            warehouse=warehouse,
            role=role,
            is_active=True,
        )
        UserWarehouse.objects.create(
            user=user,
            warehouse=warehouse2,
            role=role,
            is_active=False,
        )

        warehouses = get_user_warehouses(user, active_only=True)
        assert len(warehouses) == 1
        assert warehouse in warehouses

        warehouses_all = get_user_warehouses(user, active_only=False)
        assert len(warehouses_all) == 2

    def test_can_user_access_warehouse(self, user, warehouse, role):
        """Test warehouse access check."""
        # User has no assignment
        assert can_user_access_warehouse(user, warehouse) is False

        # Assign user to warehouse
        UserWarehouse.objects.create(
            user=user,
            warehouse=warehouse,
            role=role,
            is_active=True,
        )
        assert can_user_access_warehouse(user, warehouse) is True

    def test_can_user_access_warehouse_superuser(self, admin_user, warehouse):
        """Test superuser can access any warehouse."""
        assert can_user_access_warehouse(admin_user, warehouse) is True

    def test_can_user_access_warehouse_different_company(
        self, user, company2, warehouse
    ):
        """Test user cannot access warehouse from different company."""
        warehouse2 = Warehouse.objects.create(
            company=company2,
            name="Other Warehouse",
            code="WH-OTHER",
        )
        assert can_user_access_warehouse(user, warehouse2) is False

    def test_get_user_warehouse_role(self, user, warehouse, role):
        """Test getting user's role in warehouse."""
        UserWarehouse.objects.create(
            user=user,
            warehouse=warehouse,
            role=role,
            is_active=True,
        )

        retrieved_role = get_user_warehouse_role(user, warehouse)
        assert isinstance(retrieved_role, Role)
        assert retrieved_role == role

    def test_get_user_warehouse_role_superuser(self, admin_user, warehouse):
        """Test superuser role returns 'admin'."""
        role = get_user_warehouse_role(admin_user, warehouse)
        assert role == "admin"

    def test_get_user_warehouse_role_no_assignment(self, user, warehouse):
        """Test getting role when user has no assignment."""
        role = get_user_warehouse_role(user, warehouse)
        assert role is None

    def test_can_user_manage_warehouse(self, user, warehouse, role):
        """Test warehouse management permission."""
        # No assignment
        assert can_user_manage_warehouse(user, warehouse) is False

        # With assignment but no permission
        UserWarehouse.objects.create(
            user=user,
            warehouse=warehouse,
            role=role,
            is_active=True,
        )
        assert can_user_manage_warehouse(user, warehouse) is False

    def test_can_user_manage_warehouse_superuser(self, admin_user, warehouse):
        """Test superuser can manage warehouse."""
        assert can_user_manage_warehouse(admin_user, warehouse) is True

    def test_can_user_pick_orders(self, user, warehouse, role_with_permissions):
        """Test pick orders permission."""
        # User not assigned
        assert can_user_pick_orders(user, warehouse) is False

        # User assigned but not operator
        user.is_warehouse_operator = False
        user.save()
        UserWarehouse.objects.create(
            user=user,
            warehouse=warehouse,
            role=role_with_permissions,
            is_active=True,
        )
        assert can_user_pick_orders(user, warehouse) is False

        # User assigned and is operator
        user.is_warehouse_operator = True
        user.save()
        assert can_user_pick_orders(user, warehouse) is True

    def test_can_user_putaway(self, user, warehouse, role_with_permissions):
        """Test putaway permission."""
        user.is_warehouse_operator = True
        user.save()

        # Add putaway permission to role
        permission = Permission.objects.filter(
            codename="putaway",
            content_type__app_label="operations",
        ).first()
        if permission:
            role_with_permissions.permissions.add(permission)

        UserWarehouse.objects.create(
            user=user,
            warehouse=warehouse,
            role=role_with_permissions,
            is_active=True,
        )

        assert can_user_putaway(user, warehouse) is True

    def test_can_user_view_inventory(self, user, warehouse, role):
        """Test view inventory permission."""
        # No assignment
        assert can_user_view_inventory(user, warehouse) is False

        # With assignment (all roles can view)
        UserWarehouse.objects.create(
            user=user,
            warehouse=warehouse,
            role=role,
            is_active=True,
        )
        assert can_user_view_inventory(user, warehouse) is True

    def test_can_user_manage_inventory(self, user, warehouse, role):
        """Test manage inventory permission."""
        # No assignment
        assert can_user_manage_inventory(user, warehouse) is False

        # Add manage_inventory permission
        permission = Permission.objects.filter(
            codename="manage_inventory",
            content_type__app_label="inventory",
        ).first()
        if permission:
            role.permissions.add(permission)

        UserWarehouse.objects.create(
            user=user,
            warehouse=warehouse,
            role=role,
            is_active=True,
        )

        assert can_user_manage_inventory(user, warehouse) is True

    def test_can_user_manage_orders(self, user, warehouse, role):
        """Test manage orders permission."""
        # No assignment
        assert can_user_manage_orders(user, warehouse) is False

        # Add manage_orders permission
        permission = Permission.objects.filter(
            codename="manage_orders",
            content_type__app_label="operations",
        ).first()
        if permission:
            role.permissions.add(permission)

        UserWarehouse.objects.create(
            user=user,
            warehouse=warehouse,
            role=role,
            is_active=True,
        )

        assert can_user_manage_orders(user, warehouse) is True

    def test_assign_user_to_warehouse(self, user, warehouse, role):
        """Test assigning user to warehouse."""
        assignment = assign_user_to_warehouse(
            user=user,
            warehouse=warehouse,
            role=role,
            is_primary=True,
        )

        assert assignment.user == user
        assert assignment.warehouse == warehouse
        assert assignment.role == role
        assert assignment.is_active is True  # Always True by default
        assert assignment.is_primary is True

    def test_assign_user_to_warehouse_legacy_role(self, user, warehouse):
        """Test assigning user with legacy role string."""
        assignment = assign_user_to_warehouse(
            user=user,
            warehouse=warehouse,
            role="admin",  # Legacy role string
        )

        assert assignment.user == user
        assert assignment.warehouse == warehouse
        assert assignment.legacy_role == "admin"
        assert assignment.is_active is True  # Always True by default

    def test_get_warehouse_users(self, user, warehouse, role):
        """Test getting users assigned to warehouse."""
        UserWarehouse.objects.create(
            user=user,
            warehouse=warehouse,
            role=role,
            is_active=True,
        )

        users = get_warehouse_users(warehouse)
        assert len(users) == 1
        assert user in users

    def test_get_user_default_warehouse(self, user, warehouse, warehouse2, role):
        """Test getting user's primary warehouse."""
        UserWarehouse.objects.create(
            user=user,
            warehouse=warehouse,
            role=role,
            is_active=True,
            is_primary=True,
        )
        UserWarehouse.objects.create(
            user=user,
            warehouse=warehouse2,
            role=role,
            is_active=True,
            is_primary=False,
        )

        default = get_user_default_warehouse(user)
        assert default == warehouse

    def test_get_user_default_warehouse_no_primary(self, user, warehouse, role):
        """Test getting default warehouse when no primary set."""
        UserWarehouse.objects.create(
            user=user,
            warehouse=warehouse,
            role=role,
            is_active=True,
            is_primary=False,
        )

        default = get_user_default_warehouse(user)
        # Returns None if no primary warehouse is set
        assert default is None
