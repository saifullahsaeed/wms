"""
Tests for inventory app - models, services, and signals.
"""

from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission

from accounts.models import Company, User
from inventory.models import (
    CustomFieldDefinition,
    InventoryItem,
    InventoryMovement,
    ProductCustomFieldValue,
    StockAdjustment,
)
from inventory.services import (
    check_stock_available,
    get_available_quantity,
    get_inventory_by_location,
    get_inventory_by_product,
    get_inventory_item,
    release_stock,
    reserve_stock,
)
from masterdata.models import Location, Product, Warehouse


class TestInventoryItemModel:
    """Test InventoryItem model."""

    def test_inventory_item_creation(self, company, warehouse, location, product):
        """Test creating an inventory item."""
        item = InventoryItem.objects.create(
            company=company,
            warehouse=warehouse,
            location=location,
            product=product,
            quantity=100.0,
            reserved_quantity=10.0,
        )
        assert item.quantity == Decimal("100.0")
        assert item.reserved_quantity == Decimal("10.0")
        assert item.available_quantity == Decimal("90.0")

    def test_inventory_item_available_quantity(
        self, company, warehouse, location, product
    ):
        """Test available_quantity property."""
        item = InventoryItem.objects.create(
            company=company,
            warehouse=warehouse,
            location=location,
            product=product,
            quantity=100.0,
            reserved_quantity=25.0,
        )
        assert item.available_quantity == Decimal("75.0")

    def test_inventory_item_negative_available(
        self, company, warehouse, location, product
    ):
        """Test available_quantity doesn't go negative."""
        item = InventoryItem.objects.create(
            company=company,
            warehouse=warehouse,
            location=location,
            product=product,
            quantity=50.0,
            reserved_quantity=100.0,  # More reserved than available
        )
        # Property should return 0, not negative
        assert item.available_quantity >= Decimal("0")


class TestInventoryServices:
    """Test inventory service functions."""

    def test_get_inventory_item(self, company, warehouse, location, product):
        """Test getting inventory item."""
        InventoryItem.objects.create(
            company=company,
            warehouse=warehouse,
            location=location,
            product=product,
            quantity=100.0,
        )

        item = get_inventory_item(
            company=company,
            warehouse=warehouse,
            product=product,
            location=location,
        )
        assert item is not None
        assert item.quantity == Decimal("100.0")

    def test_get_inventory_item_not_found(self, company, warehouse, location, product):
        """Test getting non-existent inventory item."""
        item = get_inventory_item(
            company=company,
            warehouse=warehouse,
            product=product,
            location=location,
        )
        assert item is None

    def test_get_available_quantity(self, company, warehouse, location, product):
        """Test getting available quantity."""
        InventoryItem.objects.create(
            company=company,
            warehouse=warehouse,
            location=location,
            product=product,
            quantity=100.0,
            reserved_quantity=20.0,
        )

        available = get_available_quantity(
            company=company,
            warehouse=warehouse,
            product=product,
            location=location,
        )
        assert available == Decimal("80.0")

    def test_get_available_quantity_multiple_locations(
        self, company, warehouse, location, product, staging_location
    ):
        """Test getting available quantity across multiple locations."""
        InventoryItem.objects.create(
            company=company,
            warehouse=warehouse,
            location=location,
            product=product,
            quantity=50.0,
            reserved_quantity=10.0,
        )
        InventoryItem.objects.create(
            company=company,
            warehouse=warehouse,
            location=staging_location,
            product=product,
            quantity=30.0,
            reserved_quantity=5.0,
        )

        available = get_available_quantity(
            company=company,
            warehouse=warehouse,
            product=product,
            location=None,  # All locations
        )
        assert available == Decimal("65.0")  # (50-10) + (30-5)

    def test_check_stock_available(self, company, warehouse, location, product):
        """Test checking stock availability."""
        InventoryItem.objects.create(
            company=company,
            warehouse=warehouse,
            location=location,
            product=product,
            quantity=100.0,
            reserved_quantity=20.0,
        )

        # Check for available quantity
        available, qty = check_stock_available(
            company=company,
            warehouse=warehouse,
            product=product,
            quantity=Decimal("50.0"),
            location=location,
        )
        assert available is True
        assert qty == Decimal("50.0")

        # Check for more than available
        available, qty = check_stock_available(
            company=company,
            warehouse=warehouse,
            product=product,
            quantity=Decimal("100.0"),
            location=location,
        )
        assert available is False
        assert qty == Decimal("80.0")  # Available quantity

    def test_reserve_stock(self, company, warehouse, location, product):
        """Test reserving stock."""
        item = InventoryItem.objects.create(
            company=company,
            warehouse=warehouse,
            location=location,
            product=product,
            quantity=100.0,
            reserved_quantity=0.0,
        )

        success = reserve_stock(
            company=company,
            warehouse=warehouse,
            product=product,
            quantity=Decimal("30.0"),
            location=location,
        )

        assert success is True
        item.refresh_from_db()
        assert item.reserved_quantity == Decimal("30.0")

    def test_reserve_stock_insufficient(self, company, warehouse, location, product):
        """Test reserving more stock than available."""
        InventoryItem.objects.create(
            company=company,
            warehouse=warehouse,
            location=location,
            product=product,
            quantity=50.0,
            reserved_quantity=0.0,
        )

        success = reserve_stock(
            company=company,
            warehouse=warehouse,
            product=product,
            quantity=Decimal("100.0"),
            location=location,
        )

        assert success is False

    def test_release_stock(self, company, warehouse, location, product):
        """Test releasing reserved stock."""
        item = InventoryItem.objects.create(
            company=company,
            warehouse=warehouse,
            location=location,
            product=product,
            quantity=100.0,
            reserved_quantity=50.0,
        )

        success = release_stock(
            company=company,
            warehouse=warehouse,
            product=product,
            quantity=Decimal("20.0"),
            location=location,
        )

        assert success is True
        item.refresh_from_db()
        assert item.reserved_quantity == Decimal("30.0")

    def test_release_stock_more_than_reserved(
        self, company, warehouse, location, product
    ):
        """Test releasing more stock than reserved."""
        item = InventoryItem.objects.create(
            company=company,
            warehouse=warehouse,
            location=location,
            product=product,
            quantity=100.0,
            reserved_quantity=30.0,
        )

        success = release_stock(
            company=company,
            warehouse=warehouse,
            product=product,
            quantity=Decimal("50.0"),
            location=location,
        )

        # Should release only what's reserved
        assert success is True
        item.refresh_from_db()
        assert item.reserved_quantity == Decimal("0.0")

    def test_get_inventory_by_product(
        self, company, warehouse, location, staging_location, product
    ):
        """Test getting inventory by product."""
        InventoryItem.objects.create(
            company=company,
            warehouse=warehouse,
            location=location,
            product=product,
            quantity=50.0,
        )
        InventoryItem.objects.create(
            company=company,
            warehouse=warehouse,
            location=staging_location,
            product=product,
            quantity=30.0,
        )

        items = get_inventory_by_product(
            company=company,
            warehouse=warehouse,
            product=product,
        )
        assert len(items) == 2
        total_qty = sum(item.quantity for item in items)
        assert total_qty == Decimal("80.0")

    def test_get_inventory_by_location(
        self, company, warehouse, location, product, product2
    ):
        """Test getting inventory by location."""
        InventoryItem.objects.create(
            company=company,
            warehouse=warehouse,
            location=location,
            product=product,
            quantity=50.0,
        )
        InventoryItem.objects.create(
            company=company,
            warehouse=warehouse,
            location=location,
            product=product2,
            quantity=30.0,
        )

        items = get_inventory_by_location(
            company=company,
            warehouse=warehouse,
            location=location,
        )
        assert len(items) == 2
        total_qty = sum(item.quantity for item in items)
        assert total_qty == Decimal("80.0")


class TestStockAdjustment:
    """Test StockAdjustment model and signals."""

    def test_stock_adjustment_creates_movement(
        self, company, warehouse, location, product, user
    ):
        """Test that stock adjustment creates inventory movement."""
        item = InventoryItem.objects.create(
            company=company,
            warehouse=warehouse,
            location=location,
            product=product,
            quantity=100.0,
        )

        adjustment = StockAdjustment.objects.create(
            company=company,
            warehouse=warehouse,
            location=location,
            product=product,
            quantity_adjusted=Decimal("20.0"),
            reason="Cycle count correction",
            created_by=user,
        )

        # Check inventory item was updated
        item.refresh_from_db()
        assert item.quantity == Decimal("120.0")

        # Check movement was created
        movement = InventoryMovement.objects.filter(
            inventory_item=item,
            movement_type=InventoryMovement.TYPE_ADJUSTMENT,
        ).first()
        assert movement is not None
        assert movement.quantity == Decimal("20.0")

    def test_stock_adjustment_negative(
        self, company, warehouse, location, product, user
    ):
        """Test negative stock adjustment."""
        item = InventoryItem.objects.create(
            company=company,
            warehouse=warehouse,
            location=location,
            product=product,
            quantity=100.0,
        )

        adjustment = StockAdjustment.objects.create(
            company=company,
            warehouse=warehouse,
            location=location,
            product=product,
            quantity_adjusted=Decimal("-30.0"),
            reason="Damage",
            created_by=user,
        )

        item.refresh_from_db()
        assert item.quantity == Decimal("70.0")


class TestCustomFields:
    """Test custom fields functionality."""

    def test_custom_field_definition(self, company):
        """Test creating custom field definition."""
        field = CustomFieldDefinition.objects.create(
            company=company,
            name="color",
            label="Color",
            field_type=CustomFieldDefinition.FIELD_TYPE_TEXT,
            scope=CustomFieldDefinition.SCOPE_PRODUCT,
            is_required=False,
        )
        assert field.name == "color"
        assert field.scope == CustomFieldDefinition.SCOPE_PRODUCT

    def test_product_custom_field_value(self, company, product):
        """Test creating product custom field value."""
        field_def = CustomFieldDefinition.objects.create(
            company=company,
            name="color",
            label="Color",
            field_type=CustomFieldDefinition.FIELD_TYPE_TEXT,
            scope=CustomFieldDefinition.SCOPE_PRODUCT,
        )

        value = ProductCustomFieldValue.objects.create(
            product=product,
            field=field_def,
            value_text="Red",
        )
        assert value.value_text == "Red"
        assert value.product == product
        assert value.field == field_def
