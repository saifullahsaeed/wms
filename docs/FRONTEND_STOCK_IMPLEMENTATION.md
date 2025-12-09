# Frontend Stock Implementation Guide

## Overview & Dependencies

### Prerequisites
- User must be authenticated (JWT token required)
- User must be associated with a company
- Base URL: `/api/v1`

### Feature Dependencies
- **Warehouses**: Required - must have at least one warehouse
- **Products**: Required - products must exist before tracking inventory
- **Locations**: Optional but recommended for bin-level tracking

### Stock Tracking Concepts
- **Inventory Item**: Represents stock at a specific warehouse/location/product/batch combination
- **Quantity**: Total on-hand quantity
- **Reserved Quantity**: Quantity reserved for orders (not available)
- **Available Quantity**: Quantity - Reserved Quantity (available for new orders)
- **Movements**: Immutable history of all stock changes
- **Adjustments**: Manual corrections to stock levels
- **Stock Counts**: Physical inventory counting process

### Permissions
- `view_inventory`: Can view inventory levels
- `manage_inventory`: Can create adjustments and manage stock counts

---

## 1. Stock Levels View

### API Endpoint
**GET** `/api/v1/inventory/items/`

### Authentication
Required

### Query Parameters
- `warehouse_id` (optional): Filter by warehouse
- `product_id` (optional): Filter by product
- `location_id` (optional): Filter by location
- `batch` (optional): Filter by batch number
- `has_stock` (optional): `true` to show only items with quantity > 0
- `is_locked` (optional): `true` or `false` to filter locked items

### Request Example
```typescript
const response = await fetch(
  '/api/v1/inventory/items/?warehouse_id=1&has_stock=true',
  {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
  }
);
```

### Expected Response (200 OK)
```json
[
  {
    "id": 1,
    "product_sku": "LAPTOP-001",
    "location_code": "A1-R01-BIN05",
    "quantity": "10.000",
    "reserved_quantity": "2.000",
    "is_locked": false
  },
  {
    "id": 2,
    "product_sku": "LAPTOP-002",
    "location_code": "A1-R01-BIN06",
    "quantity": "5.000",
    "reserved_quantity": "0.000",
    "is_locked": false
  }
]
```

### Frontend Implementation

#### TypeScript Interfaces
```typescript
interface InventoryItem {
  id: number;
  company_id: number;
  warehouse_id: number;
  warehouse_code: string;
  product_id: number | null;
  product_sku: string | null;
  product_name: string | null;
  location_id: number | null;
  location_code: string | null;
  batch: string;
  expiry_date: string | null;
  quantity: string; // Decimal as string
  reserved_quantity: string; // Decimal as string
  available_quantity: string; // Calculated: quantity - reserved_quantity
  is_locked: boolean;
  created_at: string;
  updated_at: string;
}

interface InventoryItemListItem {
  id: number;
  product_sku: string | null;
  location_code: string | null;
  quantity: string;
  reserved_quantity: string;
  is_locked: boolean;
}
```

#### API Client Function
```typescript
interface InventoryItemFilters {
  warehouseId?: number;
  productId?: number;
  locationId?: number;
  batch?: string;
  hasStock?: boolean;
  isLocked?: boolean;
}

async function getInventoryItems(
  filters: InventoryItemFilters = {}
): Promise<InventoryItemListItem[]> {
  const queryParams = new URLSearchParams();
  if (filters.warehouseId) queryParams.append('warehouse_id', filters.warehouseId.toString());
  if (filters.productId) queryParams.append('product_id', filters.productId.toString());
  if (filters.locationId) queryParams.append('location_id', filters.locationId.toString());
  if (filters.batch) queryParams.append('batch', filters.batch);
  if (filters.hasStock !== undefined) queryParams.append('has_stock', filters.hasStock.toString());
  if (filters.isLocked !== undefined) queryParams.append('is_locked', filters.isLocked.toString());

  const response = await fetch(
    `/api/v1/inventory/items/?${queryParams.toString()}`,
    { method: 'GET', headers: getAuthHeaders() }
  );
  handleResponse(response);
  return response.json();
}
```

#### React Component Example
```typescript
function StockLevelsView({ warehouseId }: { warehouseId: number }) {
  const [items, setItems] = useState<InventoryItemListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<InventoryItemFilters>({
    warehouseId,
    hasStock: true,
  });

  useEffect(() => {
    loadItems();
  }, [filters]);

  const loadItems = async () => {
    try {
      setLoading(true);
      const data = await getInventoryItems(filters);
      setItems(data);
    } catch (err) {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <StockFilters filters={filters} onChange={setFilters} />
      {loading ? (
        <StockTableSkeleton />
      ) : (
        <StockTable
          items={items}
          columns={['product_sku', 'location_code', 'quantity', 'reserved_quantity', 'available']}
        />
      )}
    </div>
  );
}
```

#### UI/UX Considerations
- **Stock Dashboard**: Overview cards showing total stock, reserved, available
- **Filtering UI**: Warehouse, product, location filters
- **Stock Level Indicators**: Color-coded (green=good, yellow=low, red=out)
- **Locked Items**: Visual indicator for locked inventory
- **Batch/Expiry Display**: Show batch and expiry for tracked items
- **Quick Actions**: Lock/unlock, view details

---

## 2. Stock by Product Summary

### API Endpoint
**GET** `/api/v1/inventory/items/by-product/`

### Authentication
Required

### Query Parameters
- `warehouse_id` (required): Warehouse ID
- `product_id` (optional): Filter by specific product

### Request Example
```typescript
const response = await fetch(
  '/api/v1/inventory/items/by-product/?warehouse_id=1&product_id=5',
  {
    method: 'GET',
    headers: getAuthHeaders(),
  }
);
```

### Expected Response (200 OK)
```json
[
  {
    "product_sku": "LAPTOP-001",
    "product_name": "Gaming Laptop",
    "total_quantity": "15.000",
    "total_reserved": "2.000",
    "available": "13.000"
  },
  {
    "product_sku": "LAPTOP-002",
    "product_name": "Business Laptop",
    "total_quantity": "8.000",
    "total_reserved": "0.000",
    "available": "8.000"
  }
]
```

### Frontend Implementation

#### TypeScript Interface
```typescript
interface InventoryByProduct {
  product_sku: string;
  product_name: string;
  total_quantity: string;
  total_reserved: string;
  available: string;
}
```

#### Component Example
```typescript
function ProductStockSummary({ warehouseId }: { warehouseId: number }) {
  const [summary, setSummary] = useState<InventoryByProduct[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSummary();
  }, [warehouseId]);

  const loadSummary = async () => {
    try {
      setLoading(true);
      const data = await getInventoryByProduct(warehouseId);
      setSummary(data);
    } catch (err) {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  return (
    <Table>
      <thead>
        <tr>
          <th>Product SKU</th>
          <th>Product Name</th>
          <th>Total Quantity</th>
          <th>Reserved</th>
          <th>Available</th>
        </tr>
      </thead>
      <tbody>
        {summary.map((item) => (
          <tr key={item.product_sku}>
            <td>{item.product_sku}</td>
            <td>{item.product_name}</td>
            <td>{item.total_quantity}</td>
            <td>{item.total_reserved}</td>
            <td>
              <span className={getAvailabilityClass(item.available)}>
                {item.available}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
```

#### UI/UX Considerations
- **Summary Table**: Aggregated view by product
- **Availability Highlighting**: Color-code available quantities
- **Warehouse Breakdown**: Show stock per warehouse if multiple
- **Drill-down**: Click product to see location details
- **Sort Options**: Sort by SKU, quantity, available

---

## 3. Stock by Location Summary

### API Endpoint
**GET** `/api/v1/inventory/items/by-location/`

### Authentication
Required

### Query Parameters
- `warehouse_id` (required): Warehouse ID
- `location_id` (optional): Filter by specific location

### Request Example
```typescript
const response = await fetch(
  '/api/v1/inventory/items/by-location/?warehouse_id=1&location_id=10',
  {
    method: 'GET',
    headers: getAuthHeaders(),
  }
);
```

### Expected Response (200 OK)
```json
[
  {
    "location_code": "A1-R01-BIN05",
    "product_sku": "LAPTOP-001",
    "product_name": "Gaming Laptop",
    "quantity": "10.000",
    "reserved_quantity": "2.000",
    "available": "8.000",
    "batch": "BATCH-001",
    "expiry_date": "2025-12-31"
  },
  {
    "location_code": "A1-R01-BIN06",
    "product_sku": "LAPTOP-002",
    "product_name": "Business Laptop",
    "quantity": "5.000",
    "reserved_quantity": "0.000",
    "available": "5.000",
    "batch": null,
    "expiry_date": null
  }
]
```

### Frontend Implementation

#### TypeScript Interface
```typescript
interface InventoryByLocation {
  location_code: string;
  product_sku: string;
  product_name: string;
  quantity: string;
  reserved_quantity: string;
  available: string;
  batch: string | null;
  expiry_date: string | null;
}
```

#### Location Map Visualization
```typescript
function LocationStockMap({ warehouseId }: { warehouseId: number }) {
  const [locationStock, setLocationStock] = useState<InventoryByLocation[]>([]);
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null);

  useEffect(() => {
    loadLocationStock();
  }, [warehouseId]);

  const loadLocationStock = async () => {
    const data = await getInventoryByLocation(warehouseId);
    setLocationStock(data);
  };

  // Group by location
  const stockByLocation = locationStock.reduce((acc, item) => {
    if (!acc[item.location_code]) {
      acc[item.location_code] = [];
    }
    acc[item.location_code].push(item);
    return acc;
  }, {} as Record<string, InventoryByLocation[]>);

  return (
    <div className="location-map">
      {Object.entries(stockByLocation).map(([locationCode, items]) => (
        <LocationCell
          key={locationCode}
          locationCode={locationCode}
          items={items}
          selected={selectedLocation === locationCode}
          onClick={() => setSelectedLocation(locationCode)}
        />
      ))}
    </div>
  );
}
```

#### UI/UX Considerations
- **Location Map**: Visual grid/map showing locations with stock
- **Location Details**: Click location to see all products at that location
- **Batch/Expiry Display**: Show batch and expiry dates
- **Color Coding**: Use colors to indicate stock levels
- **Empty Locations**: Show empty locations differently

---

## 4. Low Stock Alerts

### API Endpoint
**GET** `/api/v1/inventory/items/low-stock/`

### Authentication
Required

### Query Parameters
- `warehouse_id` (required): Warehouse ID
- `threshold` (optional): Threshold value (default: 0)

### Request Example
```typescript
const response = await fetch(
  '/api/v1/inventory/items/low-stock/?warehouse_id=1&threshold=5',
  {
    method: 'GET',
    headers: getAuthHeaders(),
  }
);
```

### Expected Response (200 OK)
```json
[
  {
    "product_sku": "LAPTOP-001",
    "product_name": "Gaming Laptop",
    "total_quantity": "3.000",
    "total_reserved": "2.000",
    "available": "1.000"
  }
]
```

### Frontend Implementation

#### Alert Dashboard Component
```typescript
function LowStockAlerts({ warehouseId }: { warehouseId: number }) {
  const [alerts, setAlerts] = useState<InventoryByProduct[]>([]);
  const [threshold, setThreshold] = useState(5);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAlerts();
  }, [warehouseId, threshold]);

  const loadAlerts = async () => {
    try {
      setLoading(true);
      const data = await getLowStockAlerts(warehouseId, threshold);
      setAlerts(data);
    } catch (err) {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="alert-header">
        <h2>Low Stock Alerts</h2>
        <ThresholdInput
          value={threshold}
          onChange={setThreshold}
          label="Alert Threshold"
        />
      </div>

      {alerts.length === 0 ? (
        <EmptyState message="No low stock alerts" />
      ) : (
        <AlertList
          alerts={alerts}
          threshold={threshold}
          onReorder={(product) => {
            // Navigate to reorder/create PO
          }}
        />
      )}
    </div>
  );
}
```

#### Notification System
```typescript
function useLowStockNotifications(warehouseId: number, threshold: number) {
  useEffect(() => {
    const checkAlerts = async () => {
      try {
        const alerts = await getLowStockAlerts(warehouseId, threshold);
        if (alerts.length > 0) {
          showNotification({
            title: 'Low Stock Alert',
            message: `${alerts.length} products are below threshold`,
            type: 'warning',
          });
        }
      } catch (err) {
        // Handle error
      }
    };

    // Check every 5 minutes
    const interval = setInterval(checkAlerts, 5 * 60 * 1000);
    checkAlerts(); // Initial check

    return () => clearInterval(interval);
  }, [warehouseId, threshold]);
}
```

#### UI/UX Considerations
- **Alert Dashboard**: Dedicated page for low stock alerts
- **Threshold Configuration**: Allow users to set custom thresholds
- **Notification System**: Browser notifications or in-app alerts
- **Reorder Suggestions**: Quick action to create purchase orders
- **Alert Severity**: Color-code by how low stock is (critical/warning/info)

---

## 5. Stock Adjustments

### API Endpoint
**POST** `/api/v1/inventory/adjustments/`

### Authentication
Required

### Request Body
```json
{
  "warehouse": 1,                    // Required
  "product": 5,                      // Optional
  "location": 10,                    // Optional
  "reason": "damage",                // Required, choices: "damage", "loss", "count", "other"
  "description": "Damaged during handling", // Optional
  "quantity_difference": "-2.000",   // Required, positive = increase, negative = decrease
  "reference": "ADJ-2024-001"        // Optional, external reference
}
```

### Reason Code Choices
- `damage`: Product damaged
- `loss`: Product lost/missing
- `count`: Stock count variance
- `other`: Other reason

### Request Example
```typescript
async function createStockAdjustment(
  data: StockAdjustmentCreate
): Promise<StockAdjustment> {
  const response = await fetch('/api/v1/inventory/adjustments/', {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });

  handleResponse(response);
  return response.json();
}
```

### Expected Success Response (201 Created)
```json
{
  "id": 1,
  "company_id": 1,
  "warehouse": 1,
  "warehouse_code": "WH-001",
  "product": 5,
  "product_sku": "LAPTOP-001",
  "location": 10,
  "location_code": "A1-R01-BIN05",
  "reason": "damage",
  "description": "Damaged during handling",
  "quantity_difference": "-2.000",
  "reference": "ADJ-2024-001",
  "created_by": 1,
  "created_by_email": "user@example.com",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Note**: Creating an adjustment automatically:
1. Creates an inventory movement record
2. Updates the inventory item quantity
3. Validates negative stock (if warehouse doesn't allow it)

### Error Responses

**400 Bad Request** - Validation Error
```json
{
  "warehouse": ["Warehouse does not belong to your company."],
  "quantity_difference": ["This field is required."]
}
```

**400 Bad Request** - Negative Stock Not Allowed
```json
{
  "detail": "Negative stock not allowed for this warehouse."
}
```

### Frontend Implementation

#### Adjustment Form Component
```typescript
interface StockAdjustmentCreate {
  warehouse: number;
  product?: number;
  location?: number;
  reason: 'damage' | 'loss' | 'count' | 'other';
  description?: string;
  quantity_difference: string; // Decimal as string, positive or negative
  reference?: string;
}

function StockAdjustmentForm({ onSuccess }: { onSuccess: () => void }) {
  const [formData, setFormData] = useState<StockAdjustmentCreate>({
    warehouse: 0,
    reason: 'other',
    quantity_difference: '0',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [reasonCodes, setReasonCodes] = useState<ReasonCode[]>([]);

  useEffect(() => {
    loadReasonCodes();
  }, []);

  const loadReasonCodes = async () => {
    const data = await getReasonCodes({ category: 'adjustment' });
    setReasonCodes(data);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrors({});

    try {
      await createStockAdjustment(formData);
      onSuccess();
      // Reset form or navigate
    } catch (err: any) {
      if (err.response?.data) {
        setErrors(err.response.data);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <WarehousePicker
        value={formData.warehouse}
        onChange={(id) => setFormData(prev => ({ ...prev, warehouse: id }))}
        error={errors.warehouse}
      />

      <ProductPicker
        value={formData.product}
        onChange={(id) => setFormData(prev => ({ ...prev, product: id }))}
      />

      <LocationPicker
        warehouseId={formData.warehouse}
        value={formData.location}
        onChange={(id) => setFormData(prev => ({ ...prev, location: id }))}
      />

      <ReasonCodeSelect
        value={formData.reason}
        onChange={(reason) => setFormData(prev => ({ ...prev, reason }))}
        options={reasonCodes}
      />

      <QuantityInput
        label="Quantity Difference"
        value={formData.quantity_difference}
        onChange={(value) => setFormData(prev => ({ ...prev, quantity_difference: value }))}
        helpText="Positive = increase stock, Negative = decrease stock"
        error={errors.quantity_difference}
      />

      <TextArea
        label="Description"
        value={formData.description}
        onChange={(value) => setFormData(prev => ({ ...prev, description: value }))}
      />

      <button type="submit" disabled={submitting}>
        {submitting ? 'Creating Adjustment...' : 'Create Adjustment'}
      </button>
    </form>
  );
}
```

#### Quantity Input with Sign Indicator
```typescript
function QuantityDifferenceInput({
  value,
  onChange,
  error,
}: {
  value: string;
  onChange: (value: string) => void;
  error?: string;
}) {
  const [isPositive, setIsPositive] = useState(
    parseFloat(value) >= 0 || value === ''
  );

  const handleChange = (newValue: string) => {
    const num = parseFloat(newValue);
    if (!isNaN(num)) {
      onChange(isPositive ? newValue : `-${newValue}`);
    } else {
      onChange(newValue);
    }
  };

  return (
    <div>
      <div className="quantity-input-group">
        <button
          type="button"
          onClick={() => {
            setIsPositive(!isPositive);
            const num = Math.abs(parseFloat(value));
            onChange(isPositive ? `-${num}` : `${num}`);
          }}
        >
          {isPositive ? '+' : '-'}
        </button>
        <input
          type="number"
          step="0.001"
          value={Math.abs(parseFloat(value) || 0)}
          onChange={(e) => handleChange(e.target.value)}
        />
      </div>
      <span className="help-text">
        {isPositive ? 'Increase stock' : 'Decrease stock'}
      </span>
      {error && <span className="error">{error}</span>}
    </div>
  );
}
```

#### Adjustment History
```typescript
function AdjustmentHistory({ warehouseId }: { warehouseId: number }) {
  const [adjustments, setAdjustments] = useState<StockAdjustment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAdjustments();
  }, [warehouseId]);

  const loadAdjustments = async () => {
    try {
      setLoading(true);
      const data = await getStockAdjustments({ warehouseId });
      setAdjustments(data);
    } catch (err) {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  return (
    <Table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Product</th>
          <th>Location</th>
          <th>Reason</th>
          <th>Quantity</th>
          <th>Reference</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {adjustments.map((adj) => (
          <tr key={adj.id}>
            <td>{formatDate(adj.created_at)}</td>
            <td>{adj.product_sku}</td>
            <td>{adj.location_code || '—'}</td>
            <td>{adj.reason}</td>
            <td>
              <span className={adj.quantity_difference.startsWith('-') ? 'negative' : 'positive'}>
                {adj.quantity_difference}
              </span>
            </td>
            <td>{adj.reference || '—'}</td>
            <td>
              <button onClick={() => handleCancel(adj.id)}>Cancel</button>
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
```

#### UI/UX Considerations
- **Adjustment Form**: Clear form with warehouse/product/location selection
- **Quantity Input**: Visual indicator for increase/decrease
- **Reason Codes**: Dropdown with predefined reasons
- **Confirmation**: Confirm before creating adjustment
- **Adjustment History**: Table showing all adjustments
- **Cancel Adjustment**: Ability to reverse adjustments
- **Validation**: Prevent negative stock if warehouse doesn't allow

---

## 6. Stock Movements History

### API Endpoint
**GET** `/api/v1/inventory/movements/`

### Authentication
Required

### Query Parameters
- `warehouse_id` (optional): Filter by warehouse
- `product_id` (optional): Filter by product
- `movement_type` (optional): Filter by type (`inbound`, `outbound`, `move`, `adjustment`)
- `reference` (optional): Search by reference
- `date_from` (optional): Start date (ISO format)
- `date_to` (optional): End date (ISO format)

### Request Example
```typescript
const response = await fetch(
  '/api/v1/inventory/movements/?warehouse_id=1&movement_type=adjustment&date_from=2024-01-01',
  {
    method: 'GET',
    headers: getAuthHeaders(),
  }
);
```

### Expected Response (200 OK)
```json
[
  {
    "id": 1,
    "product_sku": "LAPTOP-001",
    "movement_type": "adjustment",
    "quantity": "2.000",
    "reference": "ADJ-2024-001",
    "created_at": "2024-01-01T10:00:00Z"
  },
  {
    "id": 2,
    "product_sku": "LAPTOP-001",
    "movement_type": "inbound",
    "quantity": "10.000",
    "reference": "PO-2024-001",
    "created_at": "2024-01-02T14:30:00Z"
  }
]
```

### Movement Types
- `inbound`: Stock coming into warehouse
- `outbound`: Stock leaving warehouse
- `move`: Stock moving between locations
- `adjustment`: Manual adjustment

### Frontend Implementation

#### Movement Log Component
```typescript
interface InventoryMovement {
  id: number;
  company_id: number;
  warehouse: number;
  warehouse_code: string;
  product: number | null;
  product_sku: string | null;
  location_from: number | null;
  location_from_code: string | null;
  location_to: number | null;
  location_to_code: string | null;
  batch: string;
  expiry_date: string | null;
  movement_type: 'inbound' | 'outbound' | 'move' | 'adjustment';
  quantity: string;
  reference: string;
  reason: string;
  created_by: number | null;
  created_by_email: string | null;
  created_at: string;
}

function MovementLog({ filters }: { filters: MovementFilters }) {
  const [movements, setMovements] = useState<InventoryMovement[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMovements();
  }, [filters]);

  const loadMovements = async () => {
    try {
      setLoading(true);
      const data = await getInventoryMovements(filters);
      setMovements(data);
    } catch (err) {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <MovementFilters filters={filters} onChange={setFilters} />
      <MovementTable movements={movements} />
    </div>
  );
}
```

#### Movement Details View
```typescript
function MovementDetail({ movementId }: { movementId: number }) {
  const [movement, setMovement] = useState<InventoryMovement | null>(null);

  useEffect(() => {
    loadMovement();
  }, [movementId]);

  const loadMovement = async () => {
    const data = await getInventoryMovement(movementId);
    setMovement(data);
  };

  if (!movement) return <Loading />;

  return (
    <div className="movement-detail">
      <header>
        <h1>Movement #{movement.id}</h1>
        <MovementTypeBadge type={movement.movement_type} />
      </header>

      <section>
        <InfoRow label="Product" value={movement.product_sku} />
        <InfoRow label="Warehouse" value={movement.warehouse_code} />
        <InfoRow label="Quantity" value={movement.quantity} />
        <InfoRow label="From Location" value={movement.location_from_code || '—'} />
        <InfoRow label="To Location" value={movement.location_to_code || '—'} />
        <InfoRow label="Reference" value={movement.reference || '—'} />
        <InfoRow label="Reason" value={movement.reason || '—'} />
        <InfoRow label="Created By" value={movement.created_by_email} />
        <InfoRow label="Date" value={formatDateTime(movement.created_at)} />
      </section>
    </div>
  );
}
```

#### UI/UX Considerations
- **Movement Table**: Sortable table with all movements
- **Type Badges**: Color-coded badges for movement types
- **Date Range Filter**: Calendar picker for date range
- **Export Functionality**: Export movements to CSV/Excel
- **Drill-down**: Click movement to see full details
- **Reference Links**: Link to related orders/documents

---

## 7. Stock Counts (Physical Inventory)

Stock counts follow a workflow: **Draft → In Progress → Completed**

### API Endpoints

#### List Count Sessions
**GET** `/api/v1/inventory/stock-counts/`

**Query Parameters:**
- `warehouse_id` (optional): Filter by warehouse
- `status` (optional): Filter by status (`draft`, `in_progress`, `completed`, `canceled`)
- `count_type` (optional): Filter by type (`cycle`, `full`)

#### Create Count Session
**POST** `/api/v1/inventory/stock-counts/`

**Request Body:**
```json
{
  "warehouse": 1,                    // Required
  "name": "Cycle Count - Zone A",    // Required
  "count_type": "cycle",             // Required: "cycle" or "full"
  "scope_description": "Counting all items in Zone A" // Optional
}
```

#### Get Count Session
**GET** `/api/v1/inventory/stock-counts/{id}/`

#### Start Count Session
**POST** `/api/v1/inventory/stock-counts/{id}/start/`

#### Complete Count Session
**POST** `/api/v1/inventory/stock-counts/{id}/complete/`

**Note**: Completing a count automatically creates adjustments for all variances.

#### Cancel Count Session
**POST** `/api/v1/inventory/stock-counts/{id}/cancel/`

### Count Session Response Structure
```json
{
  "id": 1,
  "company_id": 1,
  "warehouse": 1,
  "warehouse_code": "WH-001",
  "name": "Cycle Count - Zone A",
  "count_type": "cycle",
  "status": "in_progress",
  "scope_description": "Counting all items in Zone A",
  "started_at": "2024-01-01T10:00:00Z",
  "completed_at": null,
  "created_by": 1,
  "created_by_email": "user@example.com",
  "lines_count": 25,
  "created_at": "2024-01-01T09:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

### Count Line Response Structure
```json
{
  "id": 1,
  "session": 1,
  "product": 5,
  "product_sku": "LAPTOP-001",
  "location": 10,
  "location_code": "A1-R01-BIN05",
  "system_quantity": "10.000",
  "counted_quantity": "8.000",
  "difference": "-2.000",
  "counted_by": 1,
  "counted_by_email": "user@example.com",
  "created_at": "2024-01-01T10:15:00Z",
  "updated_at": "2024-01-01T10:15:00Z"
}
```

### Frontend Implementation

#### Count Session Workflow Component
```typescript
interface StockCountSession {
  id: number;
  company_id: number;
  warehouse: number;
  warehouse_code: string;
  name: string;
  count_type: 'cycle' | 'full';
  status: 'draft' | 'in_progress' | 'completed' | 'canceled';
  scope_description: string;
  started_at: string | null;
  completed_at: string | null;
  created_by: number | null;
  created_by_email: string | null;
  lines_count: number;
  created_at: string;
  updated_at: string;
}

function StockCountWorkflow({ sessionId }: { sessionId: number }) {
  const [session, setSession] = useState<StockCountSession | null>(null);
  const [lines, setLines] = useState<StockCountLine[]>([]);

  useEffect(() => {
    loadSession();
    loadLines();
  }, [sessionId]);

  const loadSession = async () => {
    const data = await getStockCountSession(sessionId);
    setSession(data);
  };

  const loadLines = async () => {
    const data = await getStockCountLines(sessionId);
    setLines(data);
  };

  if (!session) return <Loading />;

  return (
    <div className="stock-count-workflow">
      <CountSessionHeader session={session} />

      {session.status === 'draft' && (
        <DraftPhase
          session={session}
          onStart={() => startCountSession(sessionId)}
        />
      )}

      {session.status === 'in_progress' && (
        <InProgressPhase
          session={session}
          lines={lines}
          onAddLine={handleAddLine}
          onComplete={() => completeCountSession(sessionId)}
        />
      )}

      {session.status === 'completed' && (
        <CompletedPhase
          session={session}
          lines={lines}
        />
      )}
    </div>
  );
}
```

#### Count Line Entry Component
```typescript
interface StockCountLine {
  id: number;
  session: number;
  product: number | null;
  product_sku: string | null;
  location: number | null;
  location_code: string | null;
  system_quantity: string;
  counted_quantity: string;
  difference: string; // Calculated: counted - system
  counted_by: number | null;
  counted_by_email: string | null;
  created_at: string;
  updated_at: string;
}

function CountLineEntry({ sessionId }: { sessionId: number }) {
  const [formData, setFormData] = useState({
    product: null as number | null,
    location: null as number | null,
    counted_quantity: '0',
  });
  const [systemQuantity, setSystemQuantity] = useState<string>('0');

  const handleProductLocationChange = async () => {
    if (formData.product && formData.location) {
      // Get system quantity from inventory
      const inventory = await getInventoryItems({
        productId: formData.product,
        locationId: formData.location,
      });
      if (inventory.length > 0) {
        setSystemQuantity(inventory[0].quantity]);
      } else {
        setSystemQuantity('0');
      }
    }
  };

  useEffect(() => {
    handleProductLocationChange();
  }, [formData.product, formData.location]);

  const difference = (
    parseFloat(formData.counted_quantity) - parseFloat(systemQuantity)
  ).toFixed(3);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await createStockCountLine(sessionId, {
      product: formData.product!,
      location: formData.location!,
      counted_quantity: formData.counted_quantity,
    });
    // Refresh lines
  };

  return (
    <form onSubmit={handleSubmit}>
      <ProductPicker
        value={formData.product}
        onChange={(id) => setFormData(prev => ({ ...prev, product: id }))}
      />
      <LocationPicker
        warehouseId={session.warehouse}
        value={formData.location}
        onChange={(id) => setFormData(prev => ({ ...prev, location: id }))}
      />
      <div>
        <label>System Quantity</label>
        <input type="text" value={systemQuantity} readOnly />
      </div>
      <div>
        <label>Counted Quantity *</label>
        <input
          type="number"
          step="0.001"
          value={formData.counted_quantity}
          onChange={(e) => setFormData(prev => ({ ...prev, counted_quantity: e.target.value }))}
          required
        />
      </div>
      <div>
        <label>Difference</label>
        <input
          type="text"
          value={difference}
          readOnly
          className={parseFloat(difference) !== 0 ? 'variance' : ''}
        />
      </div>
      <button type="submit">Add Count Line</button>
    </form>
  );
}
```

#### Count Lines Table with Variances
```typescript
function CountLinesTable({ lines }: { lines: StockCountLine[] }) {
  const variances = lines.filter(line => parseFloat(line.difference) !== 0);

  return (
    <div>
      <SummaryCard
        total={lines.length}
        withVariance={variances.length}
        varianceAmount={variances.reduce((sum, line) => sum + parseFloat(line.difference), 0)}
      />

      <Table>
        <thead>
          <tr>
            <th>Product</th>
            <th>Location</th>
            <th>System Qty</th>
            <th>Counted Qty</th>
            <th>Difference</th>
            <th>Counted By</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line) => (
            <tr
              key={line.id}
              className={parseFloat(line.difference) !== 0 ? 'has-variance' : ''}
            >
              <td>{line.product_sku}</td>
              <td>{line.location_code || '—'}</td>
              <td>{line.system_quantity}</td>
              <td>{line.counted_quantity}</td>
              <td>
                <span className={getVarianceClass(line.difference)}>
                  {line.difference}
                </span>
              </td>
              <td>{line.counted_by_email}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
}
```

#### Completion Workflow
```typescript
async function completeCountSession(sessionId: number) {
  const confirmed = await showConfirmDialog({
    title: 'Complete Stock Count',
    message: 'This will create adjustments for all variances. Continue?',
  });

  if (!confirmed) return;

  try {
    const result = await fetch(
      `/api/v1/inventory/stock-counts/${sessionId}/complete/`,
      {
        method: 'POST',
        headers: getAuthHeaders(),
      }
    );

    handleResponse(result);
    const data = await result.json();

    showSuccessMessage(
      `Count completed. ${data.adjustments_created} adjustments created.`
    );

    // Refresh session
    loadSession();
  } catch (err) {
    // Handle error
  }
}
```

#### UI/UX Considerations
- **Status Workflow**: Clear visual indication of current phase
- **Count Entry**: Easy product/location selection and quantity entry
- **System vs Counted**: Side-by-side comparison
- **Variance Highlighting**: Color-code variances (red=negative, green=positive)
- **Bulk Entry**: Support for scanning/importing multiple lines
- **Completion Confirmation**: Warn before completing (creates adjustments)
- **Progress Tracking**: Show count progress

---

## 8. Stock Reservations

Stock reservations are tracked via the `reserved_quantity` field on inventory items. The reservation logic is handled by the operations app (orders), but you can view and manage reservations through the inventory items API.

### Viewing Reservations

Reserved quantity is included in inventory item responses:

```typescript
interface InventoryItem {
  // ... other fields
  quantity: string;           // Total on-hand
  reserved_quantity: string;   // Reserved for orders
  available_quantity: string;  // Available = quantity - reserved_quantity
}
```

### Frontend Implementation

#### Reservation Display
```typescript
function StockReservationView({ productId, warehouseId }: Props) {
  const [items, setItems] = useState<InventoryItem[]>([]);

  useEffect(() => {
    loadReservations();
  }, [productId, warehouseId]);

  const loadReservations = async () => {
    const data = await getInventoryItems({
      productId,
      warehouseId,
      hasStock: true,
    });
    // Filter items with reservations
    const withReservations = data.filter(
      item => parseFloat(item.reserved_quantity) > 0
    );
    setItems(withReservations);
  };

  return (
    <Table>
      <thead>
        <tr>
          <th>Location</th>
          <th>Total Quantity</th>
          <th>Reserved</th>
          <th>Available</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.id}>
            <td>{item.location_code || 'Unassigned'}</td>
            <td>{item.quantity}</td>
            <td className="reserved">{item.reserved_quantity}</td>
            <td className="available">{item.available_quantity}</td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
```

#### Available Quantity Calculation
```typescript
function useAvailableStock(productId: number, warehouseId: number) {
  const { data: items } = useQuery({
    queryKey: ['inventory-items', productId, warehouseId],
    queryFn: () => getInventoryItems({ productId, warehouseId }),
  });

  const totalAvailable = useMemo(() => {
    if (!items) return 0;
    return items.reduce((sum, item) => {
      const available = parseFloat(item.available_quantity);
      return sum + available;
    }, 0);
  }, [items]);

  return { items, totalAvailable };
}
```

#### UI/UX Considerations
- **Reservation Display**: Show reserved vs available clearly
- **Visual Indicators**: Color-code reserved quantities
- **Reservation Details**: Link to orders that reserved the stock
- **Available Stock**: Always show available = total - reserved

---

## 9. Real-time Stock Updates

### Polling Strategy
```typescript
function useStockPolling(warehouseId: number, interval: number = 30000) {
  const queryClient = useQueryClient();

  useEffect(() => {
    const poll = setInterval(() => {
      queryClient.invalidateQueries(['inventory-items', warehouseId]);
    }, interval);

    return () => clearInterval(poll);
  }, [warehouseId, interval, queryClient]);
}
```

### WebSocket Considerations
```typescript
// If WebSocket support is added in the future
function useStockWebSocket(warehouseId: number) {
  useEffect(() => {
    const ws = new WebSocket(`ws://api.example.com/stock/${warehouseId}`);

    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      // Update cache with new stock levels
      queryClient.setQueryData(
        ['inventory-items', warehouseId],
        (old: InventoryItem[]) => {
          return old.map(item =>
            item.id === update.item_id
              ? { ...item, ...update }
              : item
          );
        }
      );
    };

    return () => ws.close();
  }, [warehouseId]);
}
```

### Auto-refresh Patterns
```typescript
function StockDashboard({ warehouseId }: { warehouseId: number }) {
  // Auto-refresh every 30 seconds
  useStockPolling(warehouseId, 30000);

  const { data: stock, isLoading } = useQuery({
    queryKey: ['inventory-items', warehouseId],
    queryFn: () => getInventoryItems({ warehouseId }),
    refetchInterval: 30000, // React Query auto-refetch
  });

  return (
    <div>
      <StockSummary stock={stock} />
      <LastUpdated timestamp={new Date()} />
    </div>
  );
}
```

#### UI/UX Considerations
- **Auto-refresh Indicator**: Show when data was last updated
- **Manual Refresh**: Button to force refresh
- **Update Notifications**: Toast notifications for significant changes
- **Optimistic Updates**: Update UI immediately, sync with server

---

## 10. Code Examples

### Complete TypeScript Types
```typescript
// types/inventory.ts
export interface InventoryItem {
  id: number;
  company_id: number;
  warehouse_id: number;
  warehouse_code: string;
  product_id: number | null;
  product_sku: string | null;
  product_name: string | null;
  location_id: number | null;
  location_code: string | null;
  batch: string;
  expiry_date: string | null;
  quantity: string;
  reserved_quantity: string;
  available_quantity: string;
  is_locked: boolean;
  created_at: string;
  updated_at: string;
}

export interface InventoryMovement {
  id: number;
  company_id: number;
  warehouse: number;
  warehouse_code: string;
  product: number | null;
  product_sku: string | null;
  location_from: number | null;
  location_from_code: string | null;
  location_to: number | null;
  location_to_code: string | null;
  batch: string;
  expiry_date: string | null;
  movement_type: 'inbound' | 'outbound' | 'move' | 'adjustment';
  quantity: string;
  reference: string;
  reason: string;
  created_by: number | null;
  created_by_email: string | null;
  created_at: string;
}

export interface StockAdjustment {
  id: number;
  company_id: number;
  warehouse: number;
  warehouse_code: string;
  product: number | null;
  product_sku: string | null;
  location: number | null;
  location_code: string | null;
  reason: 'damage' | 'loss' | 'count' | 'other';
  description: string;
  quantity_difference: string;
  reference: string;
  created_by: number | null;
  created_by_email: string | null;
  created_at: string;
}

export interface StockCountSession {
  id: number;
  company_id: number;
  warehouse: number;
  warehouse_code: string;
  name: string;
  count_type: 'cycle' | 'full';
  status: 'draft' | 'in_progress' | 'completed' | 'canceled';
  scope_description: string;
  started_at: string | null;
  completed_at: string | null;
  created_by: number | null;
  created_by_email: string | null;
  lines_count: number;
  created_at: string;
  updated_at: string;
}

export interface StockCountLine {
  id: number;
  session: number;
  product: number | null;
  product_sku: string | null;
  location: number | null;
  location_code: string | null;
  system_quantity: string;
  counted_quantity: string;
  difference: string;
  counted_by: number | null;
  counted_by_email: string | null;
  created_at: string;
  updated_at: string;
}
```

### API Client Functions
```typescript
// api/inventory.ts
export async function getInventoryItems(
  filters: InventoryItemFilters = {}
): Promise<InventoryItemListItem[]> {
  const queryParams = new URLSearchParams();
  if (filters.warehouseId) queryParams.append('warehouse_id', filters.warehouseId.toString());
  if (filters.productId) queryParams.append('product_id', filters.productId.toString());
  if (filters.locationId) queryParams.append('location_id', filters.locationId.toString());
  if (filters.batch) queryParams.append('batch', filters.batch);
  if (filters.hasStock !== undefined) queryParams.append('has_stock', filters.hasStock.toString());
  if (filters.isLocked !== undefined) queryParams.append('is_locked', filters.isLocked.toString());

  const response = await fetch(
    `${API_BASE}/inventory/items/?${queryParams.toString()}`,
    { method: 'GET', headers: getAuthHeaders() }
  );
  handleResponse(response);
  return response.json();
}

export async function getInventoryItem(id: number): Promise<InventoryItem> {
  const response = await fetch(`${API_BASE}/inventory/items/${id}/`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });
  handleResponse(response);
  return response.json();
}

export async function updateInventoryItem(
  id: number,
  data: { is_locked: boolean }
): Promise<InventoryItem> {
  const response = await fetch(`${API_BASE}/inventory/items/${id}/`, {
    method: 'PATCH',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  handleResponse(response);
  return response.json();
}

export async function getInventoryByProduct(
  warehouseId: number,
  productId?: number
): Promise<InventoryByProduct[]> {
  const queryParams = new URLSearchParams();
  queryParams.append('warehouse_id', warehouseId.toString());
  if (productId) queryParams.append('product_id', productId.toString());

  const response = await fetch(
    `${API_BASE}/inventory/items/by-product/?${queryParams.toString()}`,
    { method: 'GET', headers: getAuthHeaders() }
  );
  handleResponse(response);
  return response.json();
}

export async function getInventoryByLocation(
  warehouseId: number,
  locationId?: number
): Promise<InventoryByLocation[]> {
  const queryParams = new URLSearchParams();
  queryParams.append('warehouse_id', warehouseId.toString());
  if (locationId) queryParams.append('location_id', locationId.toString());

  const response = await fetch(
    `${API_BASE}/inventory/items/by-location/?${queryParams.toString()}`,
    { method: 'GET', headers: getAuthHeaders() }
  );
  handleResponse(response);
  return response.json();
}

export async function getLowStockAlerts(
  warehouseId: number,
  threshold: number = 0
): Promise<InventoryByProduct[]> {
  const response = await fetch(
    `${API_BASE}/inventory/items/low-stock/?warehouse_id=${warehouseId}&threshold=${threshold}`,
    { method: 'GET', headers: getAuthHeaders() }
  );
  handleResponse(response);
  return response.json();
}

// Stock Adjustments
export async function createStockAdjustment(
  data: StockAdjustmentCreate
): Promise<StockAdjustment> {
  const response = await fetch(`${API_BASE}/inventory/adjustments/`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  handleResponse(response);
  return response.json();
}

export async function getStockAdjustments(
  filters: AdjustmentFilters = {}
): Promise<StockAdjustment[]> {
  const queryParams = new URLSearchParams();
  if (filters.warehouseId) queryParams.append('warehouse_id', filters.warehouseId.toString());
  if (filters.productId) queryParams.append('product_id', filters.productId.toString());
  if (filters.reason) queryParams.append('reason', filters.reason);
  if (filters.dateFrom) queryParams.append('date_from', filters.dateFrom);
  if (filters.dateTo) queryParams.append('date_to', filters.dateTo);

  const response = await fetch(
    `${API_BASE}/inventory/adjustments/?${queryParams.toString()}`,
    { method: 'GET', headers: getAuthHeaders() }
  );
  handleResponse(response);
  return response.json();
}

export async function cancelStockAdjustment(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/inventory/adjustments/${id}/`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  handleResponse(response);
}

// Inventory Movements
export async function getInventoryMovements(
  filters: MovementFilters = {}
): Promise<InventoryMovement[]> {
  const queryParams = new URLSearchParams();
  if (filters.warehouseId) queryParams.append('warehouse_id', filters.warehouseId.toString());
  if (filters.productId) queryParams.append('product_id', filters.productId.toString());
  if (filters.movementType) queryParams.append('movement_type', filters.movementType);
  if (filters.reference) queryParams.append('reference', filters.reference);
  if (filters.dateFrom) queryParams.append('date_from', filters.dateFrom);
  if (filters.dateTo) queryParams.append('date_to', filters.dateTo);

  const response = await fetch(
    `${API_BASE}/inventory/movements/?${queryParams.toString()}`,
    { method: 'GET', headers: getAuthHeaders() }
  );
  handleResponse(response);
  return response.json();
}

export async function getInventoryMovement(id: number): Promise<InventoryMovement> {
  const response = await fetch(`${API_BASE}/inventory/movements/${id}/`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });
  handleResponse(response);
  return response.json();
}

// Stock Counts
export async function getStockCountSessions(
  filters: CountSessionFilters = {}
): Promise<StockCountSession[]> {
  const queryParams = new URLSearchParams();
  if (filters.warehouseId) queryParams.append('warehouse_id', filters.warehouseId.toString());
  if (filters.status) queryParams.append('status', filters.status);
  if (filters.countType) queryParams.append('count_type', filters.countType);

  const response = await fetch(
    `${API_BASE}/inventory/stock-counts/?${queryParams.toString()}`,
    { method: 'GET', headers: getAuthHeaders() }
  );
  handleResponse(response);
  return response.json();
}

export async function createStockCountSession(
  data: StockCountSessionCreate
): Promise<StockCountSession> {
  const response = await fetch(`${API_BASE}/inventory/stock-counts/`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  handleResponse(response);
  return response.json();
}

export async function startStockCountSession(id: number): Promise<StockCountSession> {
  const response = await fetch(`${API_BASE}/inventory/stock-counts/${id}/start/`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  handleResponse(response);
  return response.json();
}

export async function completeStockCountSession(
  id: number
): Promise<{ session: StockCountSession; adjustments_created: number; message: string }> {
  const response = await fetch(`${API_BASE}/inventory/stock-counts/${id}/complete/`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  handleResponse(response);
  return response.json();
}

export async function cancelStockCountSession(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/inventory/stock-counts/${id}/cancel/`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  handleResponse(response);
}

export async function getStockCountLines(sessionId: number): Promise<StockCountLine[]> {
  const response = await fetch(
    `${API_BASE}/inventory/stock-counts/${sessionId}/lines/`,
    { method: 'GET', headers: getAuthHeaders() }
  );
  handleResponse(response);
  return response.json();
}

export async function createStockCountLine(
  sessionId: number,
  data: StockCountLineCreate
): Promise<StockCountLine> {
  const response = await fetch(
    `${API_BASE}/inventory/stock-counts/${sessionId}/lines/`,
    {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    }
  );
  handleResponse(response);
  return response.json();
}

export async function updateStockCountLine(
  sessionId: number,
  lineId: number,
  data: Partial<StockCountLine>
): Promise<StockCountLine> {
  const response = await fetch(
    `${API_BASE}/inventory/stock-counts/${sessionId}/lines/${lineId}/`,
    {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    }
  );
  handleResponse(response);
  return response.json();
}

export async function deleteStockCountLine(
  sessionId: number,
  lineId: number
): Promise<void> {
  const response = await fetch(
    `${API_BASE}/inventory/stock-counts/${sessionId}/lines/${lineId}/`,
    {
      method: 'DELETE',
      headers: getAuthHeaders(),
    }
  );
  handleResponse(response);
}
```

### Custom Hooks
```typescript
// hooks/useInventory.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as inventoryAPI from '../api/inventory';

export function useInventoryItems(filters: InventoryItemFilters = {}) {
  return useQuery({
    queryKey: ['inventory-items', filters],
    queryFn: () => inventoryAPI.getInventoryItems(filters),
    staleTime: 1 * 60 * 1000, // 1 minute (stock changes frequently)
  });
}

export function useInventoryByProduct(warehouseId: number, productId?: number) {
  return useQuery({
    queryKey: ['inventory-by-product', warehouseId, productId],
    queryFn: () => inventoryAPI.getInventoryByProduct(warehouseId, productId),
    enabled: !!warehouseId,
  });
}

export function useLowStockAlerts(warehouseId: number, threshold: number) {
  return useQuery({
    queryKey: ['low-stock-alerts', warehouseId, threshold],
    queryFn: () => inventoryAPI.getLowStockAlerts(warehouseId, threshold),
    enabled: !!warehouseId,
    refetchInterval: 5 * 60 * 1000, // Refresh every 5 minutes
  });
}

export function useCreateStockAdjustment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: inventoryAPI.createStockAdjustment,
    onSuccess: (_, variables) => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: ['inventory-items'] });
      queryClient.invalidateQueries({ queryKey: ['inventory-movements'] });
      queryClient.invalidateQueries({ queryKey: ['stock-adjustments'] });
    },
  });
}

export function useStockCountSession(sessionId: number) {
  return useQuery({
    queryKey: ['stock-count-session', sessionId],
    queryFn: () => inventoryAPI.getStockCountSession(sessionId),
    enabled: !!sessionId,
  });
}

export function useStockCountLines(sessionId: number) {
  return useQuery({
    queryKey: ['stock-count-lines', sessionId],
    queryFn: () => inventoryAPI.getStockCountLines(sessionId),
    enabled: !!sessionId,
  });
}
```

---

## Summary

This guide covers all inventory/stock management APIs including:
- Stock levels and inventory items
- Stock summaries by product and location
- Low stock alerts
- Stock adjustments with automatic movement creation
- Inventory movement history
- Stock count workflow (draft → in progress → completed)
- Stock reservations tracking

All features are interconnected and depend on warehouses and products being set up first.

