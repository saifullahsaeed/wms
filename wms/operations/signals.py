from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from inventory.models import InventoryItem, InventoryMovement
from operations.models import PickingTask, PutawayTask


@receiver(pre_save, sender=PutawayTask)
def putaway_task_pre_save(sender, instance, **kwargs):
    """Store old status before save to detect status changes."""
    if instance.pk:
        try:
            old_instance = PutawayTask.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except PutawayTask.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=PutawayTask)
def putaway_task_completed(sender, instance, created, **kwargs):
    """
    When PutawayTask is completed:
    - Decrease InventoryItem quantity at source_location (if exists)
    - Increase InventoryItem quantity at target_location
    - Create InventoryMovement record
    """
    # Only process if status changed to completed
    old_status = getattr(instance, "_old_status", None)
    if instance.status != "completed" or (old_status == "completed" and not created):
        return

    if not instance.product or not instance.target_location:
        return

    # Set completed_at if not set
    if not instance.completed_at:
        instance.completed_at = timezone.now()
        PutawayTask.objects.filter(pk=instance.pk).update(completed_at=instance.completed_at)

    company = instance.company
    warehouse = instance.warehouse
    product = instance.product
    quantity = instance.quantity

    # Decrease from source location (if exists)
    if instance.source_location:
        source_item, _ = InventoryItem.objects.get_or_create(
            company=company,
            warehouse=warehouse,
            product=product,
            location=instance.source_location,
            batch=instance.receiving_line.batch if instance.receiving_line else "",
            expiry_date=instance.receiving_line.expiry_date if instance.receiving_line else None,
            defaults={"quantity": 0},
        )
        source_item.quantity -= quantity
        if source_item.quantity < 0 and not warehouse.allow_negative_stock:
            source_item.quantity = 0
        source_item.save()

    # Increase at target location
    target_item, created_item = InventoryItem.objects.get_or_create(
        company=company,
        warehouse=warehouse,
        product=product,
        location=instance.target_location,
        batch=instance.receiving_line.batch if instance.receiving_line else "",
        expiry_date=instance.receiving_line.expiry_date if instance.receiving_line else None,
        defaults={"quantity": 0},
    )
    target_item.quantity += quantity
    target_item.save()

    # Create InventoryMovement record
    InventoryMovement.objects.create(
        company=company,
        warehouse=warehouse,
        product=product,
        location_from=instance.source_location,
        location_to=instance.target_location,
        batch=instance.receiving_line.batch if instance.receiving_line else "",
        expiry_date=instance.receiving_line.expiry_date if instance.receiving_line else None,
        movement_type=InventoryMovement.TYPE_INBOUND,
        quantity=quantity,
        reference=f"PutawayTask-{instance.pk}",
        reason="Putaway from staging to storage",
        created_by=instance.assigned_to,
    )


@receiver(pre_save, sender=PickingTask)
def picking_task_pre_save(sender, instance, **kwargs):
    """Store old status before save to detect status changes."""
    if instance.pk:
        try:
            old_instance = PickingTask.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except PickingTask.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=PickingTask)
def picking_task_completed(sender, instance, created, **kwargs):
    """
    When PickingTask is completed:
    - Decrease InventoryItem quantity at source_location
    - Increase InventoryItem quantity at destination_location (packing area)
    - Decrease InventoryItem.reserved_quantity
    - Update OutboundOrderLine.allocated_quantity
    - Create InventoryMovement record
    """
    # Only process if status changed to completed
    old_status = getattr(instance, "_old_status", None)
    if instance.status != "completed" or (old_status == "completed" and not created):
        return

    if not instance.product or not instance.source_location:
        return

    # Set completed_at if not set
    if not instance.completed_at:
        instance.completed_at = timezone.now()
        PickingTask.objects.filter(pk=instance.pk).update(completed_at=instance.completed_at)

    company = instance.company
    warehouse = instance.warehouse
    product = instance.product
    quantity = instance.quantity

    # Decrease from source location
    source_item = InventoryItem.objects.filter(
        company=company,
        warehouse=warehouse,
        product=product,
        location=instance.source_location,
    ).first()

    if source_item:
        source_item.quantity -= quantity
        if source_item.quantity < 0 and not warehouse.allow_negative_stock:
            source_item.quantity = 0
        # Decrease reserved quantity if it exists
        if source_item.reserved_quantity > 0:
            source_item.reserved_quantity = max(0, source_item.reserved_quantity - quantity)
        source_item.save()

    # Increase at destination location (packing area)
    if instance.destination_location:
        dest_item, _ = InventoryItem.objects.get_or_create(
            company=company,
            warehouse=warehouse,
            product=product,
            location=instance.destination_location,
            defaults={"quantity": 0},
        )
        dest_item.quantity += quantity
        dest_item.save()

    # Update OutboundOrderLine allocated quantity
    if instance.outbound_line:
        instance.outbound_line.allocated_quantity += quantity
        instance.outbound_line.save()

    # Create InventoryMovement record
    InventoryMovement.objects.create(
        company=company,
        warehouse=warehouse,
        product=product,
        location_from=instance.source_location,
        location_to=instance.destination_location,
        movement_type=InventoryMovement.TYPE_OUTBOUND,
        quantity=quantity,
        reference=f"PickingTask-{instance.pk}",
        reason="Picked for outbound order",
        created_by=instance.assigned_to,
    )

