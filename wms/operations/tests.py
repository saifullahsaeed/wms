"""
Tests for operations app - models, services, and signals.
"""

from decimal import Decimal

import pytest

from accounts.models import Company, User
from inventory.models import InventoryItem, InventoryMovement
from inventory.services import get_available_quantity
from masterdata.models import Location, Product, Warehouse
from operations.models import (
    InboundOrder,
    InboundOrderLine,
    OutboundOrder,
    OutboundOrderLine,
    PickingTask,
    PutawayTask,
    Receiving,
    ReceivingLine,
)
from operations.services import (
    assign_task_to_user,
    complete_task,
    create_picking_tasks_from_outbound_line,
    create_putaway_tasks_from_receiving,
    get_user_pending_tasks,
)


class TestInboundOrderModel:
    """Test InboundOrder model."""

    def test_inbound_order_creation(self, company, warehouse):
        """Test creating an inbound order."""
        order = InboundOrder.objects.create(
            company=company,
            warehouse=warehouse,
            order_number="IN-001",
            order_type=InboundOrder.TYPE_PURCHASE,
            status=InboundOrder.STATUS_DRAFT,
        )
        assert order.order_number == "IN-001"
        assert order.status == InboundOrder.STATUS_DRAFT
        assert str(order) == f"IN-001 ({warehouse})"

    def test_inbound_order_line(self, inbound_order, product):
        """Test creating inbound order line."""
        line = InboundOrderLine.objects.create(
            inbound_order=inbound_order,
            product=product,
            expected_quantity=50.0,
            uom="EA",
        )
        assert line.expected_quantity == Decimal("50.0")
        assert line.received_quantity == Decimal("0.0")


class TestOutboundOrderModel:
    """Test OutboundOrder model."""

    def test_outbound_order_creation(self, company, warehouse):
        """Test creating an outbound order."""
        order = OutboundOrder.objects.create(
            company=company,
            warehouse=warehouse,
            order_number="OUT-001",
            order_type=OutboundOrder.TYPE_SALES,
            status=OutboundOrder.STATUS_DRAFT,
        )
        assert order.order_number == "OUT-001"
        assert order.status == OutboundOrder.STATUS_DRAFT

    def test_outbound_order_line(self, outbound_order, product):
        """Test creating outbound order line."""
        line = OutboundOrderLine.objects.create(
            outbound_order=outbound_order,
            product=product,
            ordered_quantity=10.0,
            uom="EA",
        )
        assert line.ordered_quantity == Decimal("10.0")
        assert line.allocated_quantity == Decimal("0.0")


class TestReceiving:
    """Test Receiving and ReceivingLine models."""

    def test_receiving_creation(
        self, company, warehouse, inbound_order, staging_location
    ):
        """Test creating a receiving."""
        receiving = Receiving.objects.create(
            company=company,
            warehouse=warehouse,
            inbound_order=inbound_order,
            reference="TRUCK-001",
            dock_location=staging_location,
        )
        assert receiving.reference == "TRUCK-001"
        assert receiving.inbound_order == inbound_order

    def test_receiving_line_creates_inventory(
        self, company, warehouse, inbound_order, product, staging_location, user
    ):
        """Test that receiving line creates inventory at staging location."""
        receiving = Receiving.objects.create(
            company=company,
            warehouse=warehouse,
            inbound_order=inbound_order,
            dock_location=staging_location,
        )

        receiving_line = ReceivingLine.objects.create(
            receiving=receiving,
            inbound_order_line=inbound_order.lines.first(),
            product=product,
            quantity=50.0,
            staging_location=staging_location,
            received_by=user,
        )

        # Check inventory item was created
        item = InventoryItem.objects.filter(
            company=company,
            warehouse=warehouse,
            location=staging_location,
            product=product,
        ).first()
        assert item is not None
        assert item.quantity == Decimal("50.0")

        # Check movement was created
        movement = InventoryMovement.objects.filter(
            inventory_item=item,
            movement_type=InventoryMovement.TYPE_RECEIVING,
        ).first()
        assert movement is not None


class TestPutawayTask:
    """Test PutawayTask model and signals."""

    def test_putaway_task_creation(
        self, company, warehouse, receiving_line, staging_location, location
    ):
        """Test creating a putaway task."""
        task = PutawayTask.objects.create(
            company=company,
            warehouse=warehouse,
            receiving_line=receiving_line,
            product=receiving_line.product,
            source_location=staging_location,
            target_location=location,
            quantity=50.0,
            status=PutawayTask.STATUS_PENDING,
        )
        assert task.status == PutawayTask.STATUS_PENDING
        assert task.quantity == Decimal("50.0")

    def test_putaway_task_completion_updates_inventory(
        self,
        company,
        warehouse,
        receiving_line,
        staging_location,
        location,
        product,
        user,
    ):
        """Test that completing putaway task updates inventory."""
        # Create inventory at staging
        staging_item = InventoryItem.objects.create(
            company=company,
            warehouse=warehouse,
            location=staging_location,
            product=product,
            quantity=50.0,
        )

        task = PutawayTask.objects.create(
            company=company,
            warehouse=warehouse,
            receiving_line=receiving_line,
            product=product,
            source_location=staging_location,
            target_location=location,
            quantity=50.0,
            status=PutawayTask.STATUS_PENDING,
        )

        # Complete the task
        task.status = PutawayTask.STATUS_COMPLETED
        task.completed_by = user
        task.save()

        # Check staging inventory decreased
        staging_item.refresh_from_db()
        assert staging_item.quantity == Decimal("0.0")

        # Check target location inventory increased
        target_item = InventoryItem.objects.filter(
            company=company,
            warehouse=warehouse,
            location=location,
            product=product,
        ).first()
        assert target_item is not None
        assert target_item.quantity == Decimal("50.0")

        # Check movement was created
        movement = InventoryMovement.objects.filter(
            inventory_item=target_item,
            movement_type=InventoryMovement.TYPE_PUTAWAY,
        ).first()
        assert movement is not None


class TestPickingTask:
    """Test PickingTask model and signals."""

    def test_picking_task_creation(
        self, company, warehouse, outbound_order_line, location, user
    ):
        """Test creating a picking task."""
        task = PickingTask.objects.create(
            company=company,
            warehouse=warehouse,
            outbound_order_line=outbound_order_line,
            product=outbound_order_line.product,
            source_location=location,
            destination_location=None,  # Packing area
            quantity=10.0,
            status=PickingTask.STATUS_PENDING,
            assigned_to=user,
        )
        assert task.status == PickingTask.STATUS_PENDING
        assert task.quantity == Decimal("10.0")

    def test_picking_task_completion_updates_inventory(
        self,
        company,
        warehouse,
        outbound_order_line,
        location,
        product,
        user,
    ):
        """Test that completing picking task updates inventory."""
        # Create inventory with reserved quantity
        source_item = InventoryItem.objects.create(
            company=company,
            warehouse=warehouse,
            location=location,
            product=product,
            quantity=100.0,
            reserved_quantity=10.0,
        )

        task = PickingTask.objects.create(
            company=company,
            warehouse=warehouse,
            outbound_order_line=outbound_order_line,
            product=product,
            source_location=location,
            quantity=10.0,
            status=PickingTask.STATUS_PENDING,
            assigned_to=user,
        )

        # Complete the task
        task.status = PickingTask.STATUS_COMPLETED
        task.completed_by = user
        task.save()

        # Check source inventory decreased
        source_item.refresh_from_db()
        assert source_item.quantity == Decimal("90.0")
        assert source_item.reserved_quantity == Decimal("0.0")

        # Check order line allocated quantity updated
        outbound_order_line.refresh_from_db()
        assert outbound_order_line.allocated_quantity == Decimal("10.0")

        # Check movement was created
        movement = InventoryMovement.objects.filter(
            inventory_item=source_item,
            movement_type=InventoryMovement.TYPE_PICKING,
        ).first()
        assert movement is not None


class TestOperationsServices:
    """Test operations service functions."""

    def test_create_putaway_tasks_from_receiving(
        self, company, warehouse, receiving_line, location
    ):
        """Test creating putaway tasks from receiving."""
        tasks = create_putaway_tasks_from_receiving(
            receiving_line=receiving_line,
            target_location=location,
        )

        assert len(tasks) == 1
        assert tasks[0].source_location == receiving_line.staging_location
        assert tasks[0].target_location == location
        assert tasks[0].status == PutawayTask.STATUS_PENDING

    def test_create_picking_tasks_from_outbound_line(
        self, company, warehouse, outbound_order_line, location, product
    ):
        """Test creating picking tasks from outbound order line."""
        # Create inventory
        InventoryItem.objects.create(
            company=company,
            warehouse=warehouse,
            location=location,
            product=product,
            quantity=100.0,
            reserved_quantity=0.0,
        )

        tasks = create_picking_tasks_from_outbound_line(
            outbound_line=outbound_order_line,
            strategy="fifo",
        )

        assert len(tasks) > 0
        assert tasks[0].product == product
        assert tasks[0].status == PickingTask.STATUS_PENDING

    def test_assign_task_to_user(
        self, user, warehouse, outbound_order_line, location, product
    ):
        """Test assigning task to user."""
        task = PickingTask.objects.create(
            company=user.company,
            warehouse=warehouse,
            outbound_order_line=outbound_order_line,
            product=product,
            source_location=location,
            quantity=10.0,
            status=PickingTask.STATUS_PENDING,
        )

        assign_task_to_user(task, user)
        task.refresh_from_db()

        assert task.assigned_to == user
        assert task.status == PickingTask.STATUS_ASSIGNED

    def test_complete_task(
        self, user, warehouse, outbound_order_line, location, product
    ):
        """Test completing a task."""
        task = PickingTask.objects.create(
            company=user.company,
            warehouse=warehouse,
            outbound_order_line=outbound_order_line,
            product=product,
            source_location=location,
            quantity=10.0,
            status=PickingTask.STATUS_ASSIGNED,
            assigned_to=user,
        )

        complete_task(task, user)
        task.refresh_from_db()

        assert task.status == PickingTask.STATUS_COMPLETED
        assert task.completed_by == user

    def test_get_user_pending_tasks(
        self, user, warehouse, outbound_order_line, location, product
    ):
        """Test getting user's pending tasks."""
        # Create tasks
        task1 = PickingTask.objects.create(
            company=user.company,
            warehouse=warehouse,
            outbound_order_line=outbound_order_line,
            product=product,
            source_location=location,
            quantity=10.0,
            status=PickingTask.STATUS_PENDING,
            assigned_to=user,
        )
        task2 = PickingTask.objects.create(
            company=user.company,
            warehouse=warehouse,
            outbound_order_line=outbound_order_line,
            product=product,
            source_location=location,
            quantity=5.0,
            status=PickingTask.STATUS_ASSIGNED,
            assigned_to=user,
        )
        # Task for different user
        other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="test",
            company=user.company,
        )
        PickingTask.objects.create(
            company=user.company,
            warehouse=warehouse,
            outbound_order_line=outbound_order_line,
            product=product,
            source_location=location,
            quantity=5.0,
            status=PickingTask.STATUS_PENDING,
            assigned_to=other_user,
        )

        tasks = get_user_pending_tasks(user, warehouse)
        assert len(tasks) == 2
        assert task1 in tasks
        assert task2 in tasks
