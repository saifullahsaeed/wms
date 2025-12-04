"""
Masterdata service layer - Helper functions for locations, products, and warehouse structure.
"""

from decimal import Decimal

from django.db.models import Q, Sum

from accounts.models import Company
from inventory.models import InventoryItem
from masterdata.models import Location, LocationType, Product, Warehouse


def find_best_putaway_location(
    warehouse: Warehouse,
    product: Product,
    quantity: Decimal = None,
) -> Location | None:
    """
    Find the best location for putaway based on:
    - Location type allows putaway
    - Location is active
    - Location has capacity (if product dimensions/weight provided)
    - Prefer locations with same product (consolidation)
    - Prefer locations with available space

    Returns Location or None if no suitable location found.
    """
    # Get locations that allow putaway
    location_types = LocationType.objects.filter(
        company=warehouse.company,
        is_putaway_allowed=True,
        is_active=True,
    )

    locations = Location.objects.filter(
        warehouse=warehouse,
        location_type__in=location_types,
        is_active=True,
    )

    if not locations.exists():
        return None

    # If product has same product at a location, prefer that (consolidation)
    existing_items = InventoryItem.objects.filter(
        company=warehouse.company,
        warehouse=warehouse,
        product=product,
        location__in=locations,
        is_locked=False,
    ).select_related("location")

    if existing_items.exists():
        # Prefer location with same product that has space
        for item in existing_items:
            location = item.location
            if _check_location_capacity(location, product, quantity, existing_quantity=item.quantity):
                return location

    # Otherwise, find empty or low-occupancy location
    for location in locations.order_by("code"):
        if _check_location_capacity(location, product, quantity):
            # Check if location is empty or has minimal stock
            existing = InventoryItem.objects.filter(
                company=warehouse.company,
                warehouse=warehouse,
                location=location,
            ).aggregate(total=Sum("quantity"))["total"] or Decimal("0")

            if existing == Decimal("0"):
                return location

    # Return first available location if no perfect match
    return locations.first()


def find_best_picking_location(
    warehouse: Warehouse,
    product: Product,
    quantity: Decimal,
    strategy: str = "fifo",
) -> Location | None:
    """
    Find the best location to pick from based on strategy:
    - 'fifo': First in, first out (by created_at, expiry_date)
    - 'closest': By pick_sequence (lower = earlier in route)
    - 'lifo': Last in, first out

    Returns Location with sufficient available stock or None.
    """
    from inventory.services import get_available_quantity

    # Get locations that allow picking
    location_types = LocationType.objects.filter(
        company=warehouse.company,
        is_pickable=True,
        is_active=True,
    )

    locations = Location.objects.filter(
        warehouse=warehouse,
        location_type__in=location_types,
        is_active=True,
    )

    # Get items with available stock
    items = InventoryItem.objects.filter(
        company=warehouse.company,
        warehouse=warehouse,
        product=product,
        location__in=locations,
        is_locked=False,
    ).select_related("location")

    # Filter by available quantity
    valid_items = []
    for item in items:
        available = get_available_quantity(
            warehouse.company,
            warehouse,
            product,
            item.location,
        )
        if available >= quantity:
            valid_items.append(item)

    if not valid_items:
        return None

    # Apply strategy
    if strategy == "fifo":
        # First in, first out - prioritize by created_at and expiry_date
        valid_items.sort(key=lambda x: (x.created_at or x.product.created_at, x.expiry_date or ""))
    elif strategy == "lifo":
        # Last in, first out - reverse order
        valid_items.sort(key=lambda x: (x.created_at or x.product.created_at, x.expiry_date or ""), reverse=True)
    elif strategy == "closest":
        # By pick_sequence (lower = earlier in route)
        valid_items.sort(key=lambda x: x.location.pick_sequence if x.location else 9999)
    else:
        # Default to FIFO
        valid_items.sort(key=lambda x: (x.created_at or x.product.created_at, x.expiry_date or ""))

    return valid_items[0].location if valid_items else None


def _check_location_capacity(
    location: Location,
    product: Product,
    quantity: Decimal = None,
    existing_quantity: Decimal = Decimal("0"),
) -> bool:
    """
    Check if location has capacity for the product.
    Checks weight and volume if provided.
    """
    if not location.is_active:
        return False

    # Check weight capacity
    if location.max_weight_kg and product.weight_kg:
        current_weight = existing_quantity * product.weight_kg
        if quantity:
            new_weight = quantity * product.weight_kg
            if current_weight + new_weight > location.max_weight_kg:
                return False

    # Check volume capacity (simplified - assumes products stack)
    if location.length_cm and location.width_cm and location.height_cm:
        if product.length_cm and product.width_cm and product.height_cm:
            location_volume = (
                location.length_cm * location.width_cm * location.height_cm
            )
            product_volume = product.length_cm * product.width_cm * product.height_cm
            if product_volume > 0:
                max_products = location_volume / product_volume
                if quantity and (existing_quantity + quantity) > max_products:
                    return False

    return True


def get_location_utilization(
    warehouse: Warehouse,
    location: Location = None,
) -> dict:
    """
    Get utilization stats for a location or all locations in warehouse.
    Returns dict with location_code, used_weight, max_weight, used_volume, max_volume, utilization_percent.
    """
    filters = {
        "warehouse": warehouse,
    }
    if location:
        filters["location"] = location

    items = InventoryItem.objects.filter(**filters).select_related("product", "location")

    result = {}
    for item in items:
        loc_code = item.location.code if item.location else "UNASSIGNED"
        if loc_code not in result:
            result[loc_code] = {
                "location_code": loc_code,
                "used_weight_kg": Decimal("0"),
                "max_weight_kg": item.location.max_weight_kg if item.location else None,
                "used_volume_cbm": Decimal("0"),
                "max_volume_cbm": None,
                "utilization_percent": 0,
            }

        # Calculate used weight
        if item.product.weight_kg:
            result[loc_code]["used_weight_kg"] += item.quantity * item.product.weight_kg

        # Calculate used volume
        if item.location and item.product.volume_cbm:
            result[loc_code]["used_volume_cbm"] += item.quantity * item.product.volume_cbm
        elif item.location and all([
            item.location.length_cm,
            item.location.width_cm,
            item.location.height_cm,
            item.product.length_cm,
            item.product.width_cm,
            item.product.height_cm,
        ]):
            # Calculate volume from dimensions
            location_volume = (
                item.location.length_cm * item.location.width_cm * item.location.height_cm
            ) / 1000000  # Convert to m³
            product_volume = (
                item.product.length_cm * item.product.width_cm * item.product.height_cm
            ) / 1000000
            result[loc_code]["used_volume_cbm"] += item.quantity * product_volume

    # Calculate utilization percentages
    for loc_code, data in result.items():
        if data["max_weight_kg"]:
            data["utilization_percent"] = float(
                (data["used_weight_kg"] / data["max_weight_kg"]) * 100
            )
        elif data["max_volume_cbm"]:
            data["utilization_percent"] = float(
                (data["used_volume_cbm"] / data["max_volume_cbm"]) * 100
            )

    return list(result.values())

