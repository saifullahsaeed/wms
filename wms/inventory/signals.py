from django.db.models.signals import post_save
from django.dispatch import receiver

from inventory.models import InventoryItem, InventoryMovement, StockAdjustment
from operations.models import ReceivingLine


@receiver(post_save, sender=ReceivingLine)
def receiving_line_created(sender, instance, created, **kwargs):
    """
    When ReceivingLine is created:
    - Create or update InventoryItem at staging_location
    - Create InventoryMovement record (type=inbound)
    - Update InboundOrderLine.received_quantity
    """
    if not created:
        return

    if not instance.product or not instance.staging_location:
        return

    company = instance.receiving.company
    warehouse = instance.receiving.warehouse
    product = instance.product
    quantity = instance.quantity

    # Create or update InventoryItem at staging location
    inventory_item, item_created = InventoryItem.objects.get_or_create(
        company=company,
        warehouse=warehouse,
        product=product,
        location=instance.staging_location,
        batch=instance.batch or "",
        expiry_date=instance.expiry_date,
        defaults={"quantity": 0},
    )
    inventory_item.quantity += quantity
    inventory_item.save()

    # Create InventoryMovement record
    InventoryMovement.objects.create(
        company=company,
        warehouse=warehouse,
        product=product,
        location_from=None,  # External source
        location_to=instance.staging_location,
        batch=instance.batch or "",
        expiry_date=instance.expiry_date,
        movement_type=InventoryMovement.TYPE_INBOUND,
        quantity=quantity,
        reference=f"ReceivingLine-{instance.pk}",
        reason="Goods received",
        created_by=instance.receiving.received_by,
    )

    # Update InboundOrderLine.received_quantity
    if instance.order_line:
        instance.order_line.received_quantity += quantity
        instance.order_line.save()


@receiver(post_save, sender=StockAdjustment)
def stock_adjustment_created(sender, instance, created, **kwargs):
    """
    When StockAdjustment is created:
    - Update InventoryItem.quantity by quantity_difference
    - Create InventoryMovement record (type=adjustment)
    - Prevent negative stock if warehouse doesn't allow it
    """
    if not created:
        return

    if not instance.product:
        return

    company = instance.company
    warehouse = instance.warehouse
    product = instance.product
    quantity_difference = instance.quantity_difference

    # Get or create InventoryItem at location (if specified)
    if instance.location:
        inventory_item, _ = InventoryItem.objects.get_or_create(
            company=company,
            warehouse=warehouse,
            product=product,
            location=instance.location,
            defaults={"quantity": 0},
        )
    else:
        # If no location, find any inventory item for this product in warehouse
        inventory_item = InventoryItem.objects.filter(
            company=company,
            warehouse=warehouse,
            product=product,
        ).first()

        if not inventory_item:
            # Create a default item if none exists (location will be None)
            inventory_item = InventoryItem.objects.create(
                company=company,
                warehouse=warehouse,
                product=product,
                location=None,
                quantity=0,
            )

    # Update quantity
    inventory_item.quantity += quantity_difference

    # Prevent negative stock if warehouse doesn't allow it
    if inventory_item.quantity < 0 and not warehouse.allow_negative_stock:
        inventory_item.quantity = 0

    inventory_item.save()

    # Create InventoryMovement record
    reason_text = (
        instance.get_reason_display()
        if hasattr(instance, "get_reason_display")
        else instance.reason
    )
    if instance.description:
        reason_text = (
            f"{reason_text}: {instance.description}"
            if reason_text
            else instance.description
        )

    InventoryMovement.objects.create(
        company=company,
        warehouse=warehouse,
        product=product,
        location_from=instance.location,
        location_to=instance.location,  # Same location for adjustments
        movement_type=InventoryMovement.TYPE_ADJUSTMENT,
        quantity=abs(quantity_difference),
        reference=f"StockAdjustment-{instance.pk}",
        reason=reason_text or "Stock adjustment",
        created_by=instance.created_by,
    )
