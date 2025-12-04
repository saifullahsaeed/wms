"""
Tests for accounts models.
"""

import pytest
from django.contrib.auth.models import Permission

from accounts.models import Company, Role, User, UserWarehouse
from masterdata.models import Warehouse


class TestCompanyModel:
    """Test Company model."""

    def test_company_creation(self, db):
        """Test creating a company."""
        company = Company.objects.create(
            name="Test Company",
            email="test@example.com",
        )
        assert company.name == "Test Company"
        assert company.is_active is True
        assert str(company) == "Test Company"

    def test_company_unique_name(self, db):
        """Test company name must be unique."""
        Company.objects.create(name="Unique Company")
        with pytest.raises(Exception):  # IntegrityError
            Company.objects.create(name="Unique Company")


class TestUserModel:
    """Test User model."""

    def test_user_creation(self, company):
        """Test creating a user."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass",
            company=company,
        )
        assert user.username == "testuser"
        assert user.company == company
        assert user.check_password("testpass")

    def test_user_without_company(self, db):
        """Test user can be created without company (for superuser)."""
        user = User.objects.create_user(
            username="superuser",
            email="super@example.com",
            password="testpass",
        )
        assert user.company is None

    def test_user_warehouse_operator_flag(self, company):
        """Test is_warehouse_operator flag."""
        user = User.objects.create_user(
            username="operator",
            email="op@example.com",
            password="testpass",
            company=company,
            is_warehouse_operator=True,
        )
        assert user.is_warehouse_operator is True


class TestRoleModel:
    """Test Role model."""

    def test_role_creation(self, company):
        """Test creating a role."""
        role = Role.objects.create(
            company=company,
            name="Manager",
            description="Warehouse manager",
        )
        assert role.company == company
        assert role.name == "Manager"
        assert role.is_active is True
        assert str(role) == f"{company.name} - Manager"

    def test_role_unique_per_company(self, company):
        """Test role name must be unique per company."""
        Role.objects.create(company=company, name="Operator")
        with pytest.raises(Exception):  # IntegrityError
            Role.objects.create(company=company, name="Operator")

    def test_role_with_permissions(self, company):
        """Test role can have permissions."""
        role = Role.objects.create(company=company, name="Picker")
        permission = Permission.objects.filter(
            codename="pick_orders",
            content_type__app_label="operations",
        ).first()
        if permission:
            role.permissions.add(permission)
            assert permission in role.permissions.all()


class TestUserWarehouseModel:
    """Test UserWarehouse model."""

    def test_user_warehouse_assignment(self, user, warehouse, role):
        """Test assigning user to warehouse."""
        assignment = UserWarehouse.objects.create(
            user=user,
            warehouse=warehouse,
            role=role,
            is_active=True,
        )
        assert assignment.user == user
        assert assignment.warehouse == warehouse
        assert assignment.role == role
        assert assignment.is_active is True

    def test_user_multiple_warehouses(self, user, warehouse, warehouse2, role):
        """Test user can be assigned to multiple warehouses."""
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
        assert UserWarehouse.objects.filter(user=user).count() == 2
