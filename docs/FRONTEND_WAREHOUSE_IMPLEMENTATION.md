# Frontend Warehouse Implementation Guide

## Overview & Dependencies

### Prerequisites
- User must be authenticated (JWT token required)
- User must be associated with a company
- Base URL: `/api/v1`

### Feature Dependencies
- **Authentication**: User must complete login flow
- **Company Setup**: User's company must exist (created during registration)
- **Permissions**: No special permissions required for basic warehouse operations (all authenticated users can manage warehouses for their company)

### User Permissions
- All authenticated users can create, view, update, and delete warehouses for their company
- Warehouse creator is automatically assigned as admin for that warehouse

---

## 1. Warehouse List View

### API Endpoint
**GET** `/api/v1/masterdata/warehouses/`

### Authentication
Required - Include JWT token in Authorization header:
```
Authorization: Bearer <access_token>
```

### Query Parameters
- `page` (optional): Page number for pagination (default: 1)
- `page_size` (optional): Number of results per page (default: 50, max: 100)

### Request Example
```typescript
const response = await fetch('/api/v1/masterdata/warehouses/?page=1&page_size=20', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json',
  },
});
```

### Expected Response (200 OK)
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "code": "WH-001",
      "name": "Main Warehouse",
      "description": "Primary distribution center",
      "company_id": 1,
      "address_line1": "123 Warehouse St",
      "address_line2": "",
      "city": "New York",
      "state": "NY",
      "postal_code": "10001",
      "country": "USA",
      "time_zone": "America/New_York",
      "latitude": "40.712800",
      "longitude": "-74.006000",
      "type": "main",
      "is_active": true,
      "allow_negative_stock": false,
      "uses_bins": true,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    },
    {
      "id": 2,
      "code": "WH-002",
      "name": "Secondary Warehouse",
      "description": "",
      "company_id": 1,
      "address_line1": "",
      "address_line2": "",
      "city": "",
      "state": "",
      "postal_code": "",
      "country": "",
      "time_zone": "",
      "latitude": null,
      "longitude": null,
      "type": "store",
      "is_active": true,
      "allow_negative_stock": false,
      "uses_bins": true,
      "created_at": "2024-01-02T00:00:00Z",
      "updated_at": "2024-01-02T00:00:00Z"
    }
  ]
}
```

### Error Responses

**401 Unauthorized**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**403 Forbidden**
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### Frontend Implementation

#### TypeScript Interfaces
```typescript
interface Warehouse {
  id: number;
  code: string;
  name: string;
  description: string;
  company_id: number;
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
  time_zone: string;
  latitude: string | null;
  longitude: string | null;
  type: 'main' | 'store' | '3pl' | 'other';
  is_active: boolean;
  allow_negative_stock: boolean;
  uses_bins: boolean;
  created_at: string;
  updated_at: string;
}

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
```

#### API Client Function
```typescript
async function getWarehouses(page: number = 1, pageSize: number = 50): Promise<PaginatedResponse<Warehouse>> {
  const response = await fetch(
    `/api/v1/masterdata/warehouses/?page=${page}&page_size=${pageSize}`,
    {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${getAccessToken()}`,
        'Content-Type': 'application/json',
      },
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch warehouses: ${response.statusText}`);
  }

  return response.json();
}
```

#### React Component Example
```typescript
import { useState, useEffect } from 'react';

function WarehouseList() {
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    loadWarehouses();
  }, [page]);

  const loadWarehouses = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getWarehouses(page, 20);
      setWarehouses(data.results);
      setTotalCount(data.count);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load warehouses');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <WarehouseListSkeleton />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={loadWarehouses} />;
  }

  if (warehouses.length === 0) {
    return <EmptyState message="No warehouses found. Create your first warehouse to get started." />;
  }

  return (
    <div>
      <WarehouseTable warehouses={warehouses} />
      <Pagination
        currentPage={page}
        totalCount={totalCount}
        pageSize={20}
        onPageChange={setPage}
      />
    </div>
  );
}
```

#### UI/UX Considerations
- **Loading State**: Show skeleton loaders or spinner while fetching
- **Empty State**: Display helpful message with "Create Warehouse" CTA when no warehouses exist
- **Error State**: Show user-friendly error message with retry button
- **Pagination**: Implement page-based or infinite scroll pagination
- **Table Structure**: Display key fields (code, name, type, is_active, created_at)
- **Actions**: Include edit/delete buttons per row

---

## 2. Create Warehouse

### API Endpoint
**POST** `/api/v1/masterdata/warehouses/`

### Authentication
Required

### Request Body
```json
{
  "code": "WH-001",              // Required, unique per company, max 50 chars
  "name": "Main Warehouse",      // Required, max 255 chars
  "description": "",             // Optional
  "address_line1": "",           // Optional
  "address_line2": "",           // Optional
  "city": "",                    // Optional
  "state": "",                   // Optional
  "postal_code": "",             // Optional
  "country": "",                 // Optional
  "time_zone": "",               // Optional
  "latitude": null,              // Optional, decimal
  "longitude": null,             // Optional, decimal
  "type": "main",                // Optional, default: "main", choices: "main", "store", "3pl", "other"
  "is_active": true,             // Optional, default: true
  "allow_negative_stock": false, // Optional, default: false
  "uses_bins": true              // Optional, default: true
}
```

### Required Fields
- `code`: Unique warehouse code within company
- `name`: Warehouse name

### Validation Rules
- `code` must be unique within the company
- `code` max length: 50 characters
- `name` max length: 255 characters
- `type` must be one of: "main", "store", "3pl", "other"

### Request Example
```typescript
const createWarehouse = async (data: Partial<Warehouse>): Promise<Warehouse> => {
  const response = await fetch('/api/v1/masterdata/warehouses/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getAccessToken()}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create warehouse');
  }

  const result = await response.json();
  return result.warehouse;
};
```

### Expected Success Response (201 Created)
```json
{
  "warehouse": {
    "id": 1,
    "code": "WH-001",
    "name": "Main Warehouse",
    "description": "",
    "company_id": 1,
    "address_line1": "",
    "address_line2": "",
    "city": "",
    "state": "",
    "postal_code": "",
    "country": "",
    "time_zone": "",
    "latitude": null,
    "longitude": null,
    "type": "main",
    "is_active": true,
    "allow_negative_stock": false,
    "uses_bins": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  },
  "message": "Warehouse created successfully."
}
```

### Error Responses

**400 Bad Request** - Validation Error
```json
{
  "code": ["A warehouse with this code already exists for your company."]
}
```

**401 Unauthorized**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### Frontend Implementation

#### Form Component
```typescript
function CreateWarehouseForm({ onSuccess }: { onSuccess: () => void }) {
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    description: '',
    type: 'main' as const,
    is_active: true,
    allow_negative_stock: false,
    uses_bins: true,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [codeChecking, setCodeChecking] = useState(false);

  const handleCodeChange = async (value: string) => {
    setFormData(prev => ({ ...prev, code: value }));
    setErrors(prev => ({ ...prev, code: '' }));

    if (value.length >= 2) {
      setCodeChecking(true);
      try {
        const exists = await checkWarehouseCode(value);
        if (exists) {
          setErrors(prev => ({ ...prev, code: 'This code is already in use' }));
        }
      } catch (err) {
        // Handle error silently or show message
      } finally {
        setCodeChecking(false);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrors({});

    try {
      await createWarehouse(formData);
      onSuccess();
      // Reset form or navigate away
    } catch (err: any) {
      if (err.response?.data) {
        setErrors(err.response.data);
      } else {
        setErrors({ general: 'Failed to create warehouse' });
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label>Warehouse Code *</label>
        <input
          type="text"
          value={formData.code}
          onChange={(e) => handleCodeChange(e.target.value)}
          required
          maxLength={50}
        />
        {codeChecking && <span>Checking availability...</span>}
        {errors.code && <span className="error">{errors.code}</span>}
      </div>

      <div>
        <label>Warehouse Name *</label>
        <input
          type="text"
          value={formData.name}
          onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
          required
          maxLength={255}
        />
        {errors.name && <span className="error">{errors.name}</span>}
      </div>

      <div>
        <label>Type</label>
        <select
          value={formData.type}
          onChange={(e) => setFormData(prev => ({ ...prev, type: e.target.value as any }))}
        >
          <option value="main">Main DC</option>
          <option value="store">Store / Outlet</option>
          <option value="3pl">3PL / External</option>
          <option value="other">Other</option>
        </select>
      </div>

      <button type="submit" disabled={submitting}>
        {submitting ? 'Creating...' : 'Create Warehouse'}
      </button>
    </form>
  );
}
```

#### UI/UX Considerations
- **Real-time Validation**: Check code availability as user types (debounced)
- **Required Field Indicators**: Mark required fields with asterisk
- **Form Validation**: Validate on submit and show inline errors
- **Success Feedback**: Show success message and redirect or refresh list
- **Error Handling**: Display field-specific errors below inputs
- **Loading State**: Disable submit button and show loading indicator during submission

---

## 3. Check Warehouse Code Availability

### API Endpoint
**GET** `/api/v1/masterdata/warehouses/check-code/`  
**POST** `/api/v1/masterdata/warehouses/check-code/`

### Authentication
Required

### Query Parameters (GET)
- `warehouse_code` (required): Code to check
- `company_id` (optional): Company ID (defaults to user's company)
- `user_id` (optional): User ID (defaults to current user)

### Request Body (POST)
```json
{
  "warehouse_code": "WH-001",
  "company_id": 1  // Optional
}
```

### Request Example
```typescript
async function checkWarehouseCode(code: string): Promise<boolean> {
  const response = await fetch(
    `/api/v1/masterdata/warehouses/check-code/?warehouse_code=${encodeURIComponent(code)}`,
    {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${getAccessToken()}`,
        'Content-Type': 'application/json',
      },
    }
  );

  if (!response.ok) {
    throw new Error('Failed to check warehouse code');
  }

  const data = await response.json();
  return data.exists;
}
```

### Expected Response (200 OK)
```json
{
  "exists": false,
  "warehouse_code": "WH-001",
  "company_id": 1,
  "company_name": "My Company"
}
```

### Error Responses

**400 Bad Request**
```json
{
  "warehouse_code": ["warehouse_code query parameter is required."]
}
```

### Frontend Implementation

#### Debounced Hook
```typescript
import { useState, useEffect } from 'react';

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

function useWarehouseCodeCheck(code: string) {
  const [isAvailable, setIsAvailable] = useState<boolean | null>(null);
  const [checking, setChecking] = useState(false);
  const debouncedCode = useDebounce(code, 500);

  useEffect(() => {
    if (debouncedCode.length < 2) {
      setIsAvailable(null);
      return;
    }

    const checkCode = async () => {
      setChecking(true);
      try {
        const exists = await checkWarehouseCode(debouncedCode);
        setIsAvailable(!exists);
      } catch (err) {
        setIsAvailable(null);
      } finally {
        setChecking(false);
      }
    };

    checkCode();
  }, [debouncedCode]);

  return { isAvailable, checking };
}
```

#### Usage in Form
```typescript
function WarehouseCodeInput() {
  const [code, setCode] = useState('');
  const { isAvailable, checking } = useWarehouseCodeCheck(code);

  return (
    <div>
      <input
        type="text"
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="Enter warehouse code"
      />
      {checking && <span>Checking...</span>}
      {!checking && isAvailable === true && <span className="success">✓ Available</span>}
      {!checking && isAvailable === false && <span className="error">✗ Already in use</span>}
    </div>
  );
}
```

#### UI/UX Considerations
- **Debounce**: Wait 500ms after user stops typing before checking
- **Visual Feedback**: Show checkmark for available, X for unavailable
- **Loading Indicator**: Show spinner while checking
- **Minimum Length**: Only check codes with 2+ characters

---

## 4. View Warehouse Details

### API Endpoint
**GET** `/api/v1/masterdata/warehouses/{id}/`

### Authentication
Required

### Request Example
```typescript
async function getWarehouse(id: number): Promise<Warehouse> {
  const response = await fetch(`/api/v1/masterdata/warehouses/${id}/`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${getAccessToken()}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('Warehouse not found');
    }
    throw new Error('Failed to fetch warehouse');
  }

  return response.json();
}
```

### Expected Response (200 OK)
```json
{
  "id": 1,
  "code": "WH-001",
  "name": "Main Warehouse",
  "description": "Primary distribution center",
  "company_id": 1,
  "address_line1": "123 Warehouse St",
  "address_line2": "",
  "city": "New York",
  "state": "NY",
  "postal_code": "10001",
  "country": "USA",
  "time_zone": "America/New_York",
  "latitude": "40.712800",
  "longitude": "-74.006000",
  "type": "main",
  "is_active": true,
  "allow_negative_stock": false,
  "uses_bins": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Error Responses

**404 Not Found**
```json
{
  "detail": "Not found."
}
```

### Frontend Implementation

#### Detail View Component
```typescript
function WarehouseDetail({ warehouseId }: { warehouseId: number }) {
  const [warehouse, setWarehouse] = useState<Warehouse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadWarehouse();
  }, [warehouseId]);

  const loadWarehouse = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getWarehouse(warehouseId);
      setWarehouse(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load warehouse');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <WarehouseDetailSkeleton />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={loadWarehouse} />;
  }

  if (!warehouse) {
    return <NotFound message="Warehouse not found" />;
  }

  return (
    <div className="warehouse-detail">
      <header>
        <h1>{warehouse.name}</h1>
        <Badge variant={warehouse.is_active ? 'success' : 'warning'}>
          {warehouse.is_active ? 'Active' : 'Inactive'}
        </Badge>
      </header>

      <section>
        <h2>Basic Information</h2>
        <InfoRow label="Code" value={warehouse.code} />
        <InfoRow label="Type" value={warehouse.type} />
        <InfoRow label="Description" value={warehouse.description || '—'} />
      </section>

      <section>
        <h2>Address</h2>
        <AddressDisplay warehouse={warehouse} />
      </section>

      <section>
        <h2>Settings</h2>
        <InfoRow label="Allows Negative Stock" value={warehouse.allow_negative_stock ? 'Yes' : 'No'} />
        <InfoRow label="Uses Bins" value={warehouse.uses_bins ? 'Yes' : 'No'} />
      </section>
    </div>
  );
}
```

#### UI/UX Considerations
- **Loading Skeleton**: Show skeleton matching the layout while loading
- **Error State**: Display error with retry option
- **Layout**: Organize information into logical sections
- **Status Badge**: Visual indicator for active/inactive status
- **Edit Button**: Provide edit action in header

---

## 5. Update Warehouse

### API Endpoint
**PATCH** `/api/v1/masterdata/warehouses/{id}/` (partial update)  
**PUT** `/api/v1/masterdata/warehouses/{id}/` (full update)

### Authentication
Required

### Request Body (PATCH - partial update recommended)
```json
{
  "name": "Updated Warehouse Name",
  "description": "Updated description",
  "is_active": false
}
```

### Request Example
```typescript
async function updateWarehouse(
  id: number,
  data: Partial<Warehouse>
): Promise<Warehouse> {
  const response = await fetch(`/api/v1/masterdata/warehouses/${id}/`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${getAccessToken()}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to update warehouse');
  }

  return response.json();
}
```

### Expected Success Response (200 OK)
```json
{
  "id": 1,
  "code": "WH-001",
  "name": "Updated Warehouse Name",
  "description": "Updated description",
  "company_id": 1,
  // ... other fields
  "updated_at": "2024-01-02T00:00:00Z"
}
```

### Error Responses

**400 Bad Request** - Validation Error
```json
{
  "code": ["A warehouse with this code already exists for your company."]
}
```

**404 Not Found**
```json
{
  "detail": "Not found."
}
```

### Frontend Implementation

#### Edit Form Component
```typescript
function EditWarehouseForm({ warehouse, onSuccess }: { warehouse: Warehouse; onSuccess: () => void }) {
  const [formData, setFormData] = useState(warehouse);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrors({});

    try {
      await updateWarehouse(warehouse.id, formData);
      onSuccess();
    } catch (err: any) {
      if (err.response?.data) {
        setErrors(err.response.data);
      } else {
        setErrors({ general: 'Failed to update warehouse' });
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Form fields similar to create form */}
      <button type="submit" disabled={submitting}>
        {submitting ? 'Updating...' : 'Update Warehouse'}
      </button>
    </form>
  );
}
```

#### Optimistic Updates
```typescript
function useOptimisticUpdate() {
  const queryClient = useQueryClient();

  const updateWarehouseOptimistic = async (
    id: number,
    updates: Partial<Warehouse>
  ) => {
    // Cancel outgoing refetches
    await queryClient.cancelQueries(['warehouse', id]);

    // Snapshot previous value
    const previousWarehouse = queryClient.getQueryData<Warehouse>(['warehouse', id]);

    // Optimistically update
    queryClient.setQueryData<Warehouse>(['warehouse', id], (old) => {
      if (!old) return old;
      return { ...old, ...updates };
    });

    try {
      await updateWarehouse(id, updates);
      // Refetch to ensure consistency
      await queryClient.invalidateQueries(['warehouse', id]);
    } catch (error) {
      // Rollback on error
      queryClient.setQueryData(['warehouse', id], previousWarehouse);
      throw error;
    }
  };

  return { updateWarehouseOptimistic };
}
```

#### UI/UX Considerations
- **Optimistic Updates**: Update UI immediately, rollback on error
- **Dirty State**: Track form changes and warn before navigation
- **Conflict Handling**: Handle 409 conflicts if implementing versioning
- **Success Feedback**: Show toast notification on success
- **Form Reset**: Reset form state after successful update

---

## 6. Delete Warehouse

### API Endpoint
**DELETE** `/api/v1/masterdata/warehouses/{id}/`

### Authentication
Required

### Request Example
```typescript
async function deleteWarehouse(id: number): Promise<void> {
  const response = await fetch(`/api/v1/masterdata/warehouses/${id}/`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${getAccessToken()}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('Warehouse not found');
    }
    throw new Error('Failed to delete warehouse');
  }
}
```

### Expected Success Response (204 No Content)
Empty response body

### Error Responses

**404 Not Found**
```json
{
  "detail": "Not found."
}
```

**400 Bad Request** (if warehouse has dependencies)
```json
{
  "detail": "Cannot delete warehouse with existing inventory/orders."
}
```

### Frontend Implementation

#### Delete with Confirmation
```typescript
function DeleteWarehouseButton({ warehouse, onDelete }: { warehouse: Warehouse; onDelete: () => void }) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteWarehouse(warehouse.id);
      onDelete();
      setShowConfirm(false);
    } catch (err) {
      alert('Failed to delete warehouse');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <>
      <button onClick={() => setShowConfirm(true)}>Delete</button>
      
      {showConfirm && (
        <ConfirmDialog
          title="Delete Warehouse"
          message={`Are you sure you want to delete "${warehouse.name}"? This action cannot be undone.`}
          confirmLabel="Delete"
          cancelLabel="Cancel"
          onConfirm={handleDelete}
          onCancel={() => setShowConfirm(false)}
          loading={deleting}
          variant="danger"
        />
      )}
    </>
  );
}
```

#### UI/UX Considerations
- **Confirmation Dialog**: Always require confirmation before delete
- **Warning Message**: Explain consequences of deletion
- **Soft Delete**: Consider if warehouse should be deactivated instead
- **List Refresh**: Refresh warehouse list after successful delete
- **Error Handling**: Show user-friendly error messages

---

## 7. Warehouse Location Hierarchy

The warehouse location system is hierarchical: **Warehouse → Zones → Sections → Racks → Locations (Bins)**

### API Endpoints

#### Zones
- **List**: `GET /api/v1/masterdata/warehouses/{warehouse_id}/zones/`
- **Create**: `POST /api/v1/masterdata/warehouses/{warehouse_id}/zones/`
- **Detail**: `GET /api/v1/masterdata/warehouses/{warehouse_id}/zones/{id}/`
- **Update**: `PATCH /api/v1/masterdata/warehouses/{warehouse_id}/zones/{id}/`
- **Delete**: `DELETE /api/v1/masterdata/warehouses/{warehouse_id}/zones/{id}/`

#### Sections
- **List**: `GET /api/v1/masterdata/warehouses/{warehouse_id}/sections/`
- **Create**: `POST /api/v1/masterdata/warehouses/{warehouse_id}/sections/`
- **Detail**: `GET /api/v1/masterdata/warehouses/{warehouse_id}/sections/{id}/`
- **Update**: `PATCH /api/v1/masterdata/warehouses/{warehouse_id}/sections/{id}/`
- **Delete**: `DELETE /api/v1/masterdata/warehouses/{warehouse_id}/sections/{id}/`

#### Racks
- **List**: `GET /api/v1/masterdata/warehouses/{warehouse_id}/racks/`
- **Create**: `POST /api/v1/masterdata/warehouses/{warehouse_id}/racks/`
- **Detail**: `GET /api/v1/masterdata/warehouses/{warehouse_id}/racks/{id}/`
- **Update**: `PATCH /api/v1/masterdata/warehouses/{warehouse_id}/racks/{id}/`
- **Delete**: `DELETE /api/v1/masterdata/warehouses/{warehouse_id}/racks/{id}/`

#### Locations (Bins)
- **List**: `GET /api/v1/masterdata/warehouses/{warehouse_id}/locations/`
- **Create**: `POST /api/v1/masterdata/warehouses/{warehouse_id}/locations/`
- **Detail**: `GET /api/v1/masterdata/warehouses/{warehouse_id}/locations/{id}/`
- **Update**: `PATCH /api/v1/masterdata/warehouses/{warehouse_id}/locations/{id}/`
- **Delete**: `DELETE /api/v1/masterdata/warehouses/{warehouse_id}/locations/{id}/`
- **Check Code**: `GET /api/v1/masterdata/warehouses/{warehouse_id}/locations/check-code/?location_code=LOC-001`

### Zone Response Structure
```json
{
  "id": 1,
  "warehouse": 1,
  "warehouse_code": "WH-001",
  "name": "Inbound Zone",
  "description": "Receiving area",
  "color": "#FF5733",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Section Response Structure
```json
{
  "id": 1,
  "warehouse": 1,
  "warehouse_code": "WH-001",
  "zone": 1,
  "zone_name": "Inbound Zone",
  "code": "SEC-A",
  "name": "Section A",
  "description": "",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Location Response Structure
```json
{
  "id": 1,
  "warehouse": 1,
  "warehouse_code": "WH-001",
  "section": 1,
  "section_code": "SEC-A",
  "rack": 1,
  "rack_code": "R01",
  "location_type": 1,
  "location_type_name": "Picking Location",
  "code": "A1-R01-BIN05",
  "barcode": "1234567890",
  "description": "",
  "pick_sequence": 1,
  "length_cm": "100.00",
  "width_cm": "50.00",
  "height_cm": "200.00",
  "max_weight_kg": "500.00",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Frontend Implementation

#### Hierarchical Tree Component
```typescript
interface LocationHierarchy {
  warehouse: Warehouse;
  zones: Zone[];
  sections: Section[];
  racks: Rack[];
  locations: Location[];
}

function WarehouseLocationTree({ warehouseId }: { warehouseId: number }) {
  const [hierarchy, setHierarchy] = useState<LocationHierarchy | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadHierarchy();
  }, [warehouseId]);

  const loadHierarchy = async () => {
    const [zones, sections, racks, locations] = await Promise.all([
      getZones(warehouseId),
      getSections(warehouseId),
      getRacks(warehouseId),
      getLocations(warehouseId),
    ]);

    setHierarchy({ warehouse, zones, sections, racks, locations });
  };

  return (
    <TreeView>
      {hierarchy?.zones.map(zone => (
        <TreeNode
          key={zone.id}
          label={zone.name}
          expanded={expanded.has(`zone-${zone.id}`)}
          onToggle={() => toggleNode(`zone-${zone.id}`)}
        >
          {hierarchy.sections
            .filter(s => s.zone === zone.id)
            .map(section => (
              <TreeNode
                key={section.id}
                label={`${section.code} - ${section.name}`}
              >
                {/* Racks and locations nested similarly */}
              </TreeNode>
            ))}
        </TreeNode>
      ))}
    </TreeView>
  );
}
```

#### Breadcrumb Navigation
```typescript
function LocationBreadcrumb({ location }: { location: Location }) {
  return (
    <nav>
      <Link to={`/warehouses/${location.warehouse}`}>
        {location.warehouse_code}
      </Link>
      {' > '}
      {location.section_code && (
        <>
          <Link to={`/warehouses/${location.warehouse}/sections/${location.section}`}>
            {location.section_code}
          </Link>
          {' > '}
        </>
      )}
      {location.rack_code && (
        <>
          <Link to={`/warehouses/${location.warehouse}/racks/${location.rack}`}>
            {location.rack_code}
          </Link>
          {' > '}
        </>
      )}
      <span>{location.code}</span>
    </nav>
  );
}
```

#### UI/UX Considerations
- **Tree View**: Expandable/collapsible tree structure
- **Breadcrumbs**: Show full path for nested resources
- **Filtering**: Filter locations by zone, section, rack, or type
- **Bulk Operations**: Select multiple locations for bulk actions
- **Visual Hierarchy**: Use indentation and icons to show levels

---

## 8. Common Patterns & Best Practices

### State Management

#### Using React Query
```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Fetch warehouses
function useWarehouses(page: number = 1) {
  return useQuery({
    queryKey: ['warehouses', page],
    queryFn: () => getWarehouses(page),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Create warehouse
function useCreateWarehouse() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createWarehouse,
    onSuccess: () => {
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ['warehouses'] });
    },
  });
}
```

### Caching Strategies
- **Stale Time**: Cache warehouse list for 5 minutes
- **Cache Invalidation**: Invalidate on create/update/delete
- **Optimistic Updates**: Update cache immediately, rollback on error

### Error Recovery
```typescript
function useErrorRecovery() {
  const [retryCount, setRetryCount] = useState(0);

  const retry = async (fn: () => Promise<any>, maxRetries = 3) => {
    try {
      return await fn();
    } catch (error) {
      if (retryCount < maxRetries) {
        setRetryCount(prev => prev + 1);
        await new Promise(resolve => setTimeout(resolve, 1000 * retryCount));
        return retry(fn, maxRetries);
      }
      throw error;
    }
  };

  return { retry };
}
```

### Loading States
- **Skeleton Loaders**: Match actual content layout
- **Spinner**: For small actions (buttons)
- **Progress Bar**: For long operations
- **Optimistic UI**: Show expected result immediately

---

## 9. Code Examples

### Complete TypeScript Types
```typescript
// types/warehouse.ts
export interface Warehouse {
  id: number;
  code: string;
  name: string;
  description: string;
  company_id: number;
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
  time_zone: string;
  latitude: string | null;
  longitude: string | null;
  type: 'main' | 'store' | '3pl' | 'other';
  is_active: boolean;
  allow_negative_stock: boolean;
  uses_bins: boolean;
  created_at: string;
  updated_at: string;
}

export interface Zone {
  id: number;
  warehouse: number;
  warehouse_code: string;
  name: string;
  description: string;
  color: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Section {
  id: number;
  warehouse: number;
  warehouse_code: string;
  zone: number | null;
  zone_name: string | null;
  code: string;
  name: string;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Rack {
  id: number;
  warehouse: number;
  warehouse_code: string;
  section: number;
  section_code: string;
  code: string;
  description: string;
  levels: number;
  positions_per_level: number;
  max_weight_kg: string | null;
  max_volume_cbm: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Location {
  id: number;
  warehouse: number;
  warehouse_code: string;
  section: number | null;
  section_code: string | null;
  rack: number | null;
  rack_code: string | null;
  location_type: number | null;
  location_type_name: string | null;
  code: string;
  barcode: string;
  description: string;
  pick_sequence: number;
  length_cm: string | null;
  width_cm: string | null;
  height_cm: string | null;
  max_weight_kg: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
```

### API Client Functions
```typescript
// api/warehouse.ts
const API_BASE = '/api/v1';

export async function getWarehouses(
  page: number = 1,
  pageSize: number = 50
): Promise<PaginatedResponse<Warehouse>> {
  const response = await fetch(
    `${API_BASE}/masterdata/warehouses/?page=${page}&page_size=${pageSize}`,
    {
      method: 'GET',
      headers: getAuthHeaders(),
    }
  );
  handleResponse(response);
  return response.json();
}

export async function getWarehouse(id: number): Promise<Warehouse> {
  const response = await fetch(`${API_BASE}/masterdata/warehouses/${id}/`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });
  handleResponse(response);
  return response.json();
}

export async function createWarehouse(
  data: Partial<Warehouse>
): Promise<{ warehouse: Warehouse; message: string }> {
  const response = await fetch(`${API_BASE}/masterdata/warehouses/`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  handleResponse(response);
  return response.json();
}

export async function updateWarehouse(
  id: number,
  data: Partial<Warehouse>
): Promise<Warehouse> {
  const response = await fetch(`${API_BASE}/masterdata/warehouses/${id}/`, {
    method: 'PATCH',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  handleResponse(response);
  return response.json();
}

export async function deleteWarehouse(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/masterdata/warehouses/${id}/`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  handleResponse(response);
}

export async function checkWarehouseCode(code: string): Promise<boolean> {
  const response = await fetch(
    `${API_BASE}/masterdata/warehouses/check-code/?warehouse_code=${encodeURIComponent(code)}`,
    {
      method: 'GET',
      headers: getAuthHeaders(),
    }
  );
  handleResponse(response);
  const data = await response.json();
  return data.exists;
}

// Helper functions
function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token');
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}

function handleResponse(response: Response): void {
  if (!response.ok) {
    if (response.status === 401) {
      // Handle token refresh or redirect to login
      throw new Error('Unauthorized');
    }
    throw new Error(`API Error: ${response.statusText}`);
  }
}
```

### Custom Hooks
```typescript
// hooks/useWarehouses.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as warehouseAPI from '../api/warehouse';

export function useWarehouses(page: number = 1) {
  return useQuery({
    queryKey: ['warehouses', page],
    queryFn: () => warehouseAPI.getWarehouses(page),
    staleTime: 5 * 60 * 1000,
  });
}

export function useWarehouse(id: number) {
  return useQuery({
    queryKey: ['warehouse', id],
    queryFn: () => warehouseAPI.getWarehouse(id),
    enabled: !!id,
  });
}

export function useCreateWarehouse() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: warehouseAPI.createWarehouse,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warehouses'] });
    },
  });
}

export function useUpdateWarehouse() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Warehouse> }) =>
      warehouseAPI.updateWarehouse(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['warehouses'] });
      queryClient.invalidateQueries({ queryKey: ['warehouse', variables.id] });
    },
  });
}

export function useDeleteWarehouse() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: warehouseAPI.deleteWarehouse,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['warehouses'] });
    },
  });
}
```

---

## Summary

This guide covers all warehouse management APIs with:
- Complete API endpoint documentation
- Request/response examples
- TypeScript type definitions
- React component examples
- Error handling patterns
- Best practices for UI/UX
- Custom hooks for state management

Next steps: Implement Products (FRONTEND_PRODUCT_IMPLEMENTATION.md) and Stock (FRONTEND_STOCK_IMPLEMENTATION.md) following similar patterns.

