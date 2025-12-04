"""
Pytest configuration and shared fixtures for WMS tests.
"""

import pytest
from django.contrib.auth.models import Permission
from factory import Faker

from accounts.models import Company, Role, User, UserWarehouse
from inventory.models import InventoryItem, ProductCustomFieldValue
from masterdata.models import (
    Location,
    LocationType,
    Product,
    ProductCategory,
    Rack,
    Section,
    UnitOfMeasure,
    Warehouse,
    WarehouseZone,
)
from operations.models import (
    InboundOrder,
    InboundOrderLine,
    OutboundOrder,
    OutboundOrderLine,
)


@pytest.fixture
def company(db):
    """Create a test company."""
    return Company.objects.create(
        name="Test Company",
        email="test@example.com",
        is_active=True,
    )


@pytest.fixture
def company2(db):
    """Create a second test company."""
    return Company.objects.create(
        name="Test Company 2",
        email="test2@example.com",
        is_active=True,
    )


@pytest.fixture
def user(company):
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        email="testuser@example.com",
        password="testpass123",
        company=company,
        is_warehouse_operator=True,
    )


@pytest.fixture
def admin_user(company):
    """Create an admin user."""
    return User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="adminpass123",
        company=company,
        is_superuser=True,
        is_staff=True,
    )


@pytest.fixture
def warehouse(company):
    """Create a test warehouse."""
    return Warehouse.objects.create(
        company=company,
        name="Main Warehouse",
        code="WH-001",
        is_active=True,
    )


@pytest.fixture
def warehouse2(company):
    """Create a second test warehouse."""
    return Warehouse.objects.create(
        company=company,
        name="Secondary Warehouse",
        code="WH-002",
        is_active=True,
    )


@pytest.fixture
def location_type(company):
    """Create a location type."""
    return LocationType.objects.create(
        company=company,
        name="Standard Shelf",
        code="SHELF",
        is_active=True,
    )


@pytest.fixture
def zone(warehouse):
    """Create a warehouse zone."""
    return WarehouseZone.objects.create(
        warehouse=warehouse,
        name="Zone A",
    )


@pytest.fixture
def section(zone, warehouse):
    """Create a section."""
    return Section.objects.create(
        warehouse=warehouse,
        zone=zone,
        name="Section 1",
        code="SEC-001",
    )


@pytest.fixture
def rack(section, warehouse):
    """Create a rack."""
    return Rack.objects.create(
        warehouse=warehouse,
        section=section,
        code="RACK-001",
        description="Rack 1",
    )


@pytest.fixture
def location(rack, location_type, warehouse):
    """Create a location."""
    return Location.objects.create(
        warehouse=warehouse,
        rack=rack,
        location_type=location_type,
        code="LOC-001",
        description="Location 1",
        is_active=True,
    )


@pytest.fixture
def staging_location(warehouse, location_type):
    """Create a staging location."""
    return Location.objects.create(
        warehouse=warehouse,
        location_type=location_type,
        code="STAGING",
        description="Staging Area",
        is_active=True,
    )


@pytest.fixture
def uom(company):
    """Create a unit of measure."""
    return UnitOfMeasure.objects.create(
        company=company,
        name="Each",
        abbreviation="EA",
        base_unit="EA",
        conversion_factor=1.0,
    )


@pytest.fixture
def category(company):
    """Create a product category."""
    return ProductCategory.objects.create(
        company=company,
        name="Electronics",
    )


@pytest.fixture
def product(company, category, uom):
    """Create a test product."""
    return Product.objects.create(
        company=company,
        sku="PROD-001",
        name="Test Product",
        category=category,
        default_uom="EA",
        weight_kg=1.5,
        length_cm=10,
        width_cm=5,
        height_cm=3,
    )


@pytest.fixture
def product2(company, category, uom):
    """Create a second test product."""
    return Product.objects.create(
        company=company,
        sku="PROD-002",
        name="Test Product 2",
        category=category,
        default_uom="EA",
    )


@pytest.fixture
def inventory_item(warehouse, location, product):
    """Create an inventory item."""
    return InventoryItem.objects.create(
        warehouse=warehouse,
        location=location,
        product=product,
        quantity=100.0,
        reserved_quantity=0.0,
    )


@pytest.fixture
def role(company):
    """Create a test role."""
    return Role.objects.create(
        company=company,
        name="Operator",
        description="Warehouse operator role",
        is_active=True,
    )


@pytest.fixture
def role_with_permissions(company):
    """Create a role with pick_orders permission."""
    role = Role.objects.create(
        company=company,
        name="Picker",
        description="Can pick orders",
        is_active=True,
    )
    # Add pick_orders permission
    permission = Permission.objects.filter(
        codename="pick_orders",
        content_type__app_label="operations",
    ).first()
    if permission:
        role.permissions.add(permission)
    return role


@pytest.fixture
def user_warehouse_assignment(user, warehouse, role):
    """Assign user to warehouse with role."""
    return UserWarehouse.objects.create(
        user=user,
        warehouse=warehouse,
        role=role,
        is_active=True,
        is_primary=True,
    )


@pytest.fixture
def inbound_order(company, warehouse):
    """Create an inbound order."""
    return InboundOrder.objects.create(
        company=company,
        warehouse=warehouse,
        order_number="IN-001",
        order_type=InboundOrder.TYPE_PURCHASE,
        status=InboundOrder.STATUS_PLANNED,
    )


@pytest.fixture
def inbound_order_line(inbound_order, product):
    """Create an inbound order line."""
    return InboundOrderLine.objects.create(
        inbound_order=inbound_order,
        product=product,
        expected_quantity=50.0,
        uom="EA",
    )


@pytest.fixture
def outbound_order(company, warehouse):
    """Create an outbound order."""
    return OutboundOrder.objects.create(
        company=company,
        warehouse=warehouse,
        order_number="OUT-001",
        order_type=OutboundOrder.TYPE_SALES,
        status=OutboundOrder.STATUS_DRAFT,
    )


@pytest.fixture
def outbound_order_line(outbound_order, product):
    """Create an outbound order line."""
    return OutboundOrderLine.objects.create(
        outbound_order=outbound_order,
        product=product,
        ordered_quantity=10.0,
        uom="EA",
    )


@pytest.fixture
def receiving(company, warehouse, inbound_order, staging_location):
    """Create a receiving."""
    from operations.models import Receiving

    return Receiving.objects.create(
        company=company,
        warehouse=warehouse,
        inbound_order=inbound_order,
        reference="TRUCK-001",
        dock_location=staging_location,
    )


@pytest.fixture
def receiving_line(receiving, inbound_order_line, product, staging_location):
    """Create a receiving line."""
    from operations.models import ReceivingLine

    return ReceivingLine.objects.create(
        receiving=receiving,
        order_line=inbound_order_line,
        product=product,
        quantity=50.0,
        staging_location=staging_location,
    )
