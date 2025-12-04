# Django Signals Plan for WMS Core Coherence

## Overview
Signals ensure data consistency across related models when operations occur. This document lists all signals needed for core WMS functionality.

---

## 1. INVENTORY COHERENCE SIGNALS

### 1.1 PutawayTask Completion → Inventory Updates
**Signal:** `post_save` on `PutawayTask` (when status changes to `completed`)
**Why:** When a putaway task completes, we must:
- Increase `InventoryItem.quantity` at target location
- Decrease `InventoryItem.quantity` at source location (if exists)
- Create `InventoryMovement` record (type=inbound, from staging to final location)
- Update `ReceivingLine` to track putaway progress

**Custom signal needed:** `putaway_task_completed` (optional, for future notifications)

---

### 1.2 PickingTask Completion → Inventory Updates
**Signal:** `post_save` on `PickingTask` (when status changes to `completed`)
**Why:** When picking completes:
- Decrease `InventoryItem.quantity` at source location
- Increase `InventoryItem.quantity` at destination (packing area) OR create new item there
- Decrease `InventoryItem.reserved_quantity` (release reservation)
- Update `OutboundOrderLine.allocated_quantity` (mark as picked)
- Create `InventoryMovement` record (type=outbound, from pick location to packing)

**Custom signal needed:** `picking_task_completed` (optional, for future notifications)

---

### 1.3 InternalMoveTask Completion → Inventory Updates
**Signal:** `post_save` on `InternalMoveTask` (when status changes to `completed`)
**Why:** When internal move completes:
- Decrease `InventoryItem.quantity` at source location
- Increase `InventoryItem.quantity` at target location (or create new item)
- Create `InventoryMovement` record (type=move, from→to)
- Update location references in `InventoryItem`

**Custom signal needed:** `internal_move_task_completed` (optional)

---

### 1.4 StockAdjustment Creation → Inventory Updates
**Signal:** `post_save` on `StockAdjustment` (on creation)
**Why:** When adjustment is created:
- Update `InventoryItem.quantity` by `quantity_difference` (increase or decrease)
- Create `InventoryMovement` record (type=adjustment, with reason)
- Ensure negative stock is prevented if warehouse doesn't allow it

**Built-in signal:** `post_save` (sufficient)

---

### 1.5 ReceivingLine Creation → Inventory Creation/Update
**Signal:** `post_save` on `ReceivingLine` (on creation)
**Why:** When goods are received:
- Create or update `InventoryItem` at staging location with received quantity
- Create `InventoryMovement` record (type=inbound, from external to staging)
- Update `InboundOrderLine.received_quantity`

**Built-in signal:** `post_save` (sufficient)

---

### 1.6 InventoryItem Quantity Changes → Movement History
**Signal:** `pre_save` / `post_save` on `InventoryItem` (when quantity changes)
**Why:** Track all quantity changes automatically:
- Compare old vs new quantity in `pre_save`
- In `post_save`, if quantity changed, create `InventoryMovement` if not already created by task signals
- This is a safety net to catch any direct quantity updates

**Built-in signal:** `pre_save` + `post_save` (sufficient, but be careful not to double-create movements)

---

## 2. ORDER STATUS COHERENCE SIGNALS

### 2.1 InboundOrderLine Received Quantity → Order Status
**Signal:** `post_save` on `InboundOrderLine` (when `received_quantity` changes)
**Why:** When all lines are fully received:
- Check if all `InboundOrderLine.received_quantity >= expected_quantity`
- If yes, update `InboundOrder.status` to `completed`
- Update `InboundOrder.completed_at`

**Built-in signal:** `post_save` (sufficient)

---

### 2.2 OutboundOrderLine Allocation → Reservation
**Signal:** `post_save` on `OutboundOrderLine` (when `allocated_quantity` changes)
**Why:** When allocation happens:
- Update `InventoryItem.reserved_quantity` (increase when allocated, decrease when deallocated)
- Ensure reserved qty doesn't exceed available qty
- Update order status if all lines are allocated

**Built-in signal:** `post_save` (sufficient)

---

### 2.3 OutboundOrderLine Shipped Quantity → Order Status
**Signal:** `post_save` on `OutboundOrderLine` (when `shipped_quantity` changes)
**Why:** When all lines are shipped:
- Check if all `OutboundOrderLine.shipped_quantity >= ordered_quantity`
- If yes, update `OutboundOrder.status` to `shipped`
- Update `OutboundOrder.shipped_at`

**Built-in signal:** `post_save` (sufficient)

---

### 2.4 ShipmentLine Creation → OutboundOrderLine Update
**Signal:** `post_save` on `ShipmentLine` (on creation)
**Why:** When shipment line is created:
- Update `OutboundOrderLine.shipped_quantity` (add to existing)
- This triggers signal 2.3 above

**Built-in signal:** `post_save` (sufficient)

---

## 3. TASK STATUS COHERENCE SIGNALS

### 3.1 PickingTask Completion → Wave Status
**Signal:** `post_save` on `PickingTask` (when status changes to `completed`)
**Why:** When all tasks in a wave are complete:
- Check if all `PickingTask` in `PickingWave.tasks` are `completed`
- If yes, update `PickingWave.status` to `completed`
- Update `PickingWave.completed_at`

**Built-in signal:** `post_save` (sufficient)

---

### 3.2 Receiving Completion → InboundOrder Status
**Signal:** `post_save` on `Receiving` (when `completed_at` is set)
**Why:** When receiving is marked complete:
- Check if all `ReceivingLine` for this receiving are processed
- Update `InboundOrder.status` if all goods received

**Built-in signal:** `post_save` (sufficient)

---

## 4. DATA INTEGRITY SIGNALS

### 4.1 InventoryItem Quantity Validation
**Signal:** `pre_save` on `InventoryItem`
**Why:** Prevent invalid states:
- Ensure `quantity >= 0` (unless warehouse allows negative stock)
- Ensure `reserved_quantity <= quantity`
- Ensure `reserved_quantity >= 0`

**Built-in signal:** `pre_save` (sufficient)

---

### 4.2 Product Deletion Protection
**Signal:** `pre_delete` on `Product`
**Why:** Prevent deletion if:
- Product has `InventoryItem` records (active stock)
- Product has pending orders (`InboundOrderLine` or `OutboundOrderLine`)
- Raise `ProtectedError` or set status to inactive instead

**Built-in signal:** `pre_delete` (sufficient)

---

### 4.3 Location Deletion Protection
**Signal:** `pre_delete` on `Location`
**Why:** Prevent deletion if:
- Location has `InventoryItem` records (active stock)
- Location has pending tasks (`PutawayTask`, `PickingTask`, `InternalMoveTask`)

**Built-in signal:** `pre_delete` (sufficient)

---

## 5. AUDIT LOGGING SIGNALS

### 5.1 InventoryItem Changes → AuditLog
**Signal:** `post_save` on `InventoryItem` (when quantity or reserved_quantity changes)
**Why:** Track all inventory changes for audit:
- Create `AuditLog` entry with action="inventory_updated"
- Include old vs new values
- Include user context if available

**Built-in signal:** `post_save` (sufficient)

---

### 5.2 Order Status Changes → AuditLog
**Signal:** `post_save` on `InboundOrder` / `OutboundOrder` (when status changes)
**Why:** Track order lifecycle:
- Create `AuditLog` entry with action="order_status_changed"
- Include old vs new status
- Include user who made the change

**Built-in signal:** `post_save` (sufficient)

---

## SUMMARY: Signals Needed

### Built-in Django Signals (Use These):
1. `pre_save` - Validation before save
2. `post_save` - Actions after save (most common)
3. `pre_delete` - Validation before delete
4. `post_delete` - Cleanup after delete (if needed)

### Custom Signals (Optional, for Future Extensibility):
1. `putaway_task_completed` - Emit when putaway task completes
2. `picking_task_completed` - Emit when picking task completes
3. `internal_move_task_completed` - Emit when internal move completes
4. `order_status_changed` - Emit when order status changes
5. `inventory_low_stock` - Emit when stock falls below threshold (future feature)

### Priority Implementation Order:
1. **HIGH:** PutawayTask → InventoryItem updates (1.1)
2. **HIGH:** PickingTask → InventoryItem updates (1.2)
3. **HIGH:** StockAdjustment → InventoryItem updates (1.4)
4. **MEDIUM:** InternalMoveTask → InventoryItem updates (1.3)
5. **MEDIUM:** Order status coherence (2.1, 2.2, 2.3)
6. **MEDIUM:** Data integrity checks (4.1, 4.2, 4.3)
7. **LOW:** Audit logging (5.1, 5.2)
8. **LOW:** Custom signals (for future notifications)

---

## Implementation Notes:
- Use `@receiver` decorator or `Signal.connect()` in `signals.py` files per app
- Import signals in `apps.py` `ready()` method to ensure they're registered
- Use `update_fields` check in `post_save` to only act on relevant field changes
- Use `created` parameter in `post_save` to distinguish create vs update
- Store old values in `pre_save` if needed for comparison in `post_save`

