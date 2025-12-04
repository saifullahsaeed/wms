"""
Operations service layer - Business logic for warehouse operations and task management.
"""

from decimal import Decimal

from django.utils import timezone

from accounts.models import User
from inventory.services import check_stock_available, reserve_stock
from masterdata.models import Location, Product, Warehouse
from masterdata.services import find_best_picking_location, find_best_putaway_location
from operations.models import (
    InboundOrderLine,
    InternalMoveTask,
    OutboundOrderLine,
    PickingTask,
    PutawayTask,
    ReceivingLine,
)


def create_putaway_tasks_from_receiving(
    receiving_line: ReceivingLine,
    target_location: Location = None,
    assigned_to: User = None,
) -> list[PutawayTask]:
    """
    Create putaway tasks from a receiving line.
    If target_location is not provided, finds best location automatically.
    """
    if not receiving_line.staging_location:
        raise ValueError("Receiving line must have a staging location")

    if not target_location:
        target_location = find_best_putaway_location(
            receiving_line.receiving.warehouse,
            receiving_line.product,
            receiving_line.quantity,
        )
        if not target_location:
            raise ValueError("No suitable putaway location found")

    task = PutawayTask.objects.create(
        company=receiving_line.receiving.company,
        warehouse=receiving_line.receiving.warehouse,
        receiving_line=receiving_line,
        product=receiving_line.product,
        source_location=receiving_line.staging_location,
        target_location=target_location,
        quantity=receiving_line.quantity,
        status=PutawayTask.STATUS_PENDING,
        assigned_to=assigned_to,
    )

    return [task]


def create_picking_tasks_from_outbound_line(
    outbound_line: OutboundOrderLine,
    strategy: str = "fifo",
    assigned_to: User = None,
) -> list[PickingTask]:
    """
    Create picking tasks from an outbound order line.
    Automatically finds best picking locations and allocates stock.
    """
    order = outbound_line.outbound_order
    product = outbound_line.product
    quantity_needed = outbound_line.ordered_quantity - outbound_line.allocated_quantity

    if quantity_needed <= 0:
        return []

    # Check stock availability
    is_available, available_qty = check_stock_available(
        order.company,
        order.warehouse,
        product,
        quantity_needed,
    )

    if not is_available:
        raise ValueError(
            f"Insufficient stock. Available: {available_qty}, Needed: {quantity_needed}"
        )

    # Reserve stock
    reserved_items = reserve_stock(
        order.company,
        order.warehouse,
        product,
        quantity_needed,
    )

    # Update allocated quantity
    outbound_line.allocated_quantity += quantity_needed
    outbound_line.save()

    # Create picking tasks
    tasks = []
    remaining_qty = quantity_needed

    for item in reserved_items:
        if remaining_qty <= 0:
            break

        pick_qty = min(item.reserved_quantity, remaining_qty)
        if pick_qty <= 0:
            continue

        # Find destination (packing area) - could be configurable
        destination = Location.objects.filter(
            warehouse=order.warehouse,
            location_type__is_pickable=False,  # Packing areas are usually not pickable
            is_active=True,
        ).first()

        task = PickingTask.objects.create(
            company=order.company,
            warehouse=order.warehouse,
            outbound_line=outbound_line,
            product=product,
            source_location=item.location,
            destination_location=destination,
            quantity=pick_qty,
            status=PickingTask.STATUS_PENDING,
            assigned_to=assigned_to,
        )
        tasks.append(task)
        remaining_qty -= pick_qty

    return tasks


def assign_task_to_user(
    task: PutawayTask | PickingTask | InternalMoveTask,
    user: User,
) -> None:
    """
    Assign a task to a user and update status to in_progress if not already.
    """
    task.assigned_to = user
    if task.status == task.STATUS_PENDING:
        task.status = task.STATUS_IN_PROGRESS
        task.started_at = timezone.now()
    task.save()


def complete_task(
    task: PutawayTask | PickingTask | InternalMoveTask,
    user: User = None,
) -> None:
    """
    Mark a task as completed. Signals will handle inventory updates.
    """
    if task.status == task.STATUS_COMPLETED:
        return  # Already completed

    task.status = task.STATUS_COMPLETED
    task.completed_at = timezone.now()
    if user:
        task.assigned_to = user
    task.save()


def create_internal_move_task(
    company,
    warehouse: Warehouse,
    product: Product,
    source_location: Location,
    target_location: Location,
    quantity: Decimal,
    reason_code=None,
    comment: str = "",
    assigned_to: User = None,
) -> InternalMoveTask:
    """
    Create an internal move task (re-slotting, consolidation, etc.).
    """
    # Validate source has enough stock
    from inventory.services import check_stock_available

    is_available, available = check_stock_available(
        company,
        warehouse,
        product,
        quantity,
        source_location,
    )

    if not is_available:
        raise ValueError(
            f"Insufficient stock at source location. Available: {available}, Needed: {quantity}"
        )

    task = InternalMoveTask.objects.create(
        company=company,
        warehouse=warehouse,
        product=product,
        source_location=source_location,
        target_location=target_location,
        quantity=quantity,
        reason_code=reason_code,
        comment=comment,
        status=InternalMoveTask.STATUS_PENDING,
        assigned_to=assigned_to,
    )

    return task


def get_user_pending_tasks(
    user: User,
    warehouse: Warehouse = None,
    task_type: str = None,
) -> dict:
    """
    Get pending tasks for a user, optionally filtered by warehouse and task type.
    Returns dict with putaway_tasks, picking_tasks, internal_move_tasks.
    """
    filters = {
        "assigned_to": user,
        "status__in": [PutawayTask.STATUS_PENDING, PutawayTask.STATUS_IN_PROGRESS],
    }
    if warehouse:
        filters["warehouse"] = warehouse

    putaway_tasks = PutawayTask.objects.filter(**filters)

    picking_tasks = PickingTask.objects.filter(
        assigned_to=user,
        status__in=[PickingTask.STATUS_PENDING, PickingTask.STATUS_IN_PROGRESS],
        **({"warehouse": warehouse} if warehouse else {}),
    )

    internal_move_tasks = InternalMoveTask.objects.filter(
        assigned_to=user,
        status__in=[InternalMoveTask.STATUS_PENDING, InternalMoveTask.STATUS_IN_PROGRESS],
        **({"warehouse": warehouse} if warehouse else {}),
    )

    return {
        "putaway_tasks": list(putaway_tasks),
        "picking_tasks": list(picking_tasks),
        "internal_move_tasks": list(internal_move_tasks),
    }

