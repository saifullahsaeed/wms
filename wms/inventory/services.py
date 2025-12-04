"""
Inventory service layer - Core business logic for inventory operations.
"""

from decimal import Decimal

from django.db.models import Q, Sum

from accounts.models import Company, User
from inventory.models import InventoryItem
from masterdata.models import Location, Product, Warehouse


def get_inventory_item(
    company: Company,
    warehouse: Warehouse,
    product: Product,
    location: Location = None,
    batch: str = "",
    expiry_date=None,
) -> InventoryItem | None:
    """
    Get an inventory item for a specific product/location/batch combination.
    Returns None if not found.
    """
    filters = {
        "company": company,
        "warehouse": warehouse,
        "product": product,
        "batch": batch or "",
    }
    if location:
        filters["location"] = location
    else:
        filters["location__isnull"] = True

    if expiry_date:
        filters["expiry_date"] = expiry_date
    else:
        filters["expiry_date__isnull"] = True

    return InventoryItem.objects.filter(**filters).first()


def get_available_quantity(
    company: Company,
    warehouse: Warehouse,
    product: Product,
    location: Location = None,
) -> Decimal:
    """
    Get available quantity (quantity - reserved_quantity) for a product at a location.
    If location is None, sums across all locations in the warehouse.
    """
    filters = {
        "company": company,
        "warehouse": warehouse,
        "product": product,
        "is_locked": False,
    }
    if location:
        filters["location"] = location

    items = InventoryItem.objects.filter(**filters)
    total_quantity = items.aggregate(Sum("quantity"))["quantity__sum"] or Decimal("0")
    total_reserved = items.aggregate(Sum("reserved_quantity"))[
        "reserved_quantity__sum"
    ] or Decimal("0")

    return max(Decimal("0"), total_quantity - total_reserved)


def check_stock_available(
    company: Company,
    warehouse: Warehouse,
    product: Product,
    quantity: Decimal,
    location: Location = None,
) -> tuple[bool, Decimal]:
    """
    Check if sufficient stock is available for a product.
    Returns (is_available, available_quantity).
    """
    available = get_available_quantity(company, warehouse, product, location)
    return (available >= quantity, available)


def reserve_stock(
    company: Company,
    warehouse: Warehouse,
    product: Product,
    quantity: Decimal,
    location: Location = None,
    user: User = None,
) -> list[InventoryItem]:
    """
    Reserve stock for an order. Uses FIFO (first in, first out) by default.
    Returns list of InventoryItems that were reserved.
    """
    if not check_stock_available(company, warehouse, product, quantity, location)[0]:
        raise ValueError(f"Insufficient stock. Requested: {quantity}")

    filters = {
        "company": company,
        "warehouse": warehouse,
        "product": product,
        "is_locked": False,
    }
    if location:
        filters["location"] = location

    # Get items with available stock, ordered by created_at (FIFO)
    items = InventoryItem.objects.filter(**filters).order_by(
        "created_at", "expiry_date"
    )

    reserved_items = []
    remaining_to_reserve = quantity

    for item in items:
        if remaining_to_reserve <= 0:
            break

        available = item.quantity - item.reserved_quantity
        if available <= 0:
            continue

        reserve_amount = min(available, remaining_to_reserve)
        item.reserved_quantity += reserve_amount
        item.save()
        reserved_items.append(item)
        remaining_to_reserve -= reserve_amount

    if remaining_to_reserve > 0:
        # Release what we reserved if we couldn't get enough
        release_stock(reserved_items, quantity - remaining_to_reserve)
        raise ValueError(
            f"Could not reserve full quantity. Only reserved: {quantity - remaining_to_reserve}"
        )

    return reserved_items


def release_stock(
    inventory_items: list[InventoryItem] | InventoryItem,
    quantity: Decimal = None,
) -> None:
    """
    Release reserved stock. If quantity is None, releases all reserved quantity.
    """
    if isinstance(inventory_items, InventoryItem):
        inventory_items = [inventory_items]

    for item in inventory_items:
        if quantity is None:
            item.reserved_quantity = Decimal("0")
        else:
            item.reserved_quantity = max(
                Decimal("0"), item.reserved_quantity - quantity
            )
        item.save()


def get_inventory_by_product(
    company: Company,
    warehouse: Warehouse,
    product: Product = None,
) -> dict:
    """
    Get inventory summary by product.
    Returns dict with product_sku, total_quantity, total_reserved, available.
    """
    filters = {
        "company": company,
        "warehouse": warehouse,
        "is_locked": False,
    }
    if product:
        filters["product"] = product

    items = (
        InventoryItem.objects.filter(**filters)
        .values("product__sku", "product__name")
        .annotate(
            total_quantity=Sum("quantity"),
            total_reserved=Sum("reserved_quantity"),
        )
    )

    result = []
    for item in items:
        available = max(
            Decimal("0"),
            (item["total_quantity"] or Decimal("0"))
            - (item["total_reserved"] or Decimal("0")),
        )
        result.append(
            {
                "product_sku": item["product__sku"],
                "product_name": item["product__name"],
                "total_quantity": item["total_quantity"] or Decimal("0"),
                "total_reserved": item["total_reserved"] or Decimal("0"),
                "available": available,
            }
        )

    return result


def get_inventory_by_location(
    company: Company,
    warehouse: Warehouse,
    location: Location = None,
) -> list[dict]:
    """
    Get inventory summary by location.
    Returns list of dicts with location_code, product_sku, quantity, reserved_quantity, available.
    """
    filters = {
        "company": company,
        "warehouse": warehouse,
        "is_locked": False,
    }
    if location:
        filters["location"] = location

    items = InventoryItem.objects.filter(**filters).select_related(
        "product", "location"
    )

    result = []
    for item in items:
        available = max(Decimal("0"), item.quantity - item.reserved_quantity)
        result.append(
            {
                "location_code": item.location.code if item.location else "UNASSIGNED",
                "product_sku": item.product.sku if item.product else "UNKNOWN",
                "product_name": item.product.name if item.product else "",
                "quantity": item.quantity,
                "reserved_quantity": item.reserved_quantity,
                "available": available,
                "batch": item.batch,
                "expiry_date": item.expiry_date,
            }
        )

    return result
