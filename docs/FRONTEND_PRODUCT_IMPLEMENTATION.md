# Frontend Product Implementation Guide

## Overview & Dependencies

### Prerequisites
- User must be authenticated (JWT token required)
- User must be associated with a company
- Base URL: `/api/v1`

### Feature Dependencies
- **Warehouse Setup**: Not strictly required, but recommended for inventory management
- **Product Categories**: Optional but recommended for organization
- **Units of Measure (UOM)**: Required for product creation (default_uom field)

### User Permissions
- All authenticated users can create, view, update, and manage products for their company
- Products are scoped to the user's company

---

## 1. Product List View

### API Endpoint
**GET** `/api/v1/masterdata/products/`

### Authentication
Required

### Query Parameters
- `page` (optional): Page number for pagination
- `page_size` (optional): Number of results per page (default: 50)
- `search` (optional): Search by SKU or name (case-insensitive)
- `category_id` (optional): Filter by product category
- `status` (optional): Filter by status (`active`, `inactive`, `discontinued`)

### Request Example
```typescript
const response = await fetch(
  '/api/v1/masterdata/products/?search=laptop&category_id=5&status=active&page=1',
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
{
  "count": 150,
  "next": "http://api.example.com/api/v1/masterdata/products/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "sku": "LAPTOP-001",
      "name": "Gaming Laptop",
      "category_name": "Electronics",
      "status": "active",
      "default_uom": "EA",
      "created_at": "2024-01-01T00:00:00Z"
    },
    {
      "id": 2,
      "sku": "LAPTOP-002",
      "name": "Business Laptop",
      "category_name": "Electronics",
      "status": "active",
      "default_uom": "EA",
      "created_at": "2024-01-02T00:00:00Z"
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

### Frontend Implementation

#### TypeScript Interfaces
```typescript
interface Product {
  id: number;
  sku: string;
  name: string;
  description: string;
  company_id: number;
  category_id: number | null;
  category_name: string | null;
  status: 'active' | 'inactive' | 'discontinued';
  default_uom: string;
  storage_uom: string;
  weight_kg: string | null;
  length_cm: string | null;
  width_cm: string | null;
  height_cm: string | null;
  volume_cbm: string | null;
  track_batch: boolean;
  track_serial: boolean;
  hazardous: boolean;
  requires_lot_expiry: boolean;
  storage_requirements: string;
  image_url: string;
  created_at: string;
  updated_at: string;
}

interface ProductListItem {
  id: number;
  sku: string;
  name: string;
  category_name: string | null;
  status: 'active' | 'inactive' | 'discontinued';
  default_uom: string;
  created_at: string;
}
```

#### API Client Function
```typescript
interface ProductListParams {
  page?: number;
  pageSize?: number;
  search?: string;
  categoryId?: number;
  status?: 'active' | 'inactive' | 'discontinued';
}

async function getProducts(params: ProductListParams = {}): Promise<PaginatedResponse<ProductListItem>> {
  const queryParams = new URLSearchParams();
  if (params.page) queryParams.append('page', params.page.toString());
  if (params.pageSize) queryParams.append('page_size', params.pageSize.toString());
  if (params.search) queryParams.append('search', params.search);
  if (params.categoryId) queryParams.append('category_id', params.categoryId.toString());
  if (params.status) queryParams.append('status', params.status);

  const response = await fetch(
    `/api/v1/masterdata/products/?${queryParams.toString()}`,
    {
      method: 'GET',
      headers: getAuthHeaders(),
    }
  );

  handleResponse(response);
  return response.json();
}
```

#### React Component Example
```typescript
function ProductList() {
  const [products, setProducts] = useState<ProductListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    search: '',
    categoryId: undefined as number | undefined,
    status: undefined as 'active' | 'inactive' | 'discontinued' | undefined,
  });
  const [page, setPage] = useState(1);

  useEffect(() => {
    loadProducts();
  }, [page, filters]);

  const loadProducts = async () => {
    try {
      setLoading(true);
      const data = await getProducts({ ...filters, page });
      setProducts(data.results);
    } catch (err) {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <ProductFilters
        filters={filters}
        onChange={setFilters}
      />
      <ProductSearchBar
        value={filters.search}
        onChange={(search) => setFilters(prev => ({ ...prev, search }))}
      />
      {loading ? (
        <ProductListSkeleton />
      ) : (
        <ProductTable products={products} />
      )}
      <Pagination page={page} onPageChange={setPage} />
    </div>
  );
}
```

#### UI/UX Considerations
- **Search Bar**: Debounced search input (500ms delay)
- **Filter Sidebar**: Category dropdown, status checkboxes
- **Table Columns**: SKU, Name, Category, Status, UOM, Actions
- **Status Badge**: Color-coded badges (green=active, gray=inactive, red=discontinued)
- **Bulk Actions**: Select multiple products for bulk operations
- **Sort Options**: Sort by SKU, name, created date

---

## 2. Create Product

### API Endpoint
**POST** `/api/v1/masterdata/products/`

### Authentication
Required

### Request Body
```json
{
  "sku": "LAPTOP-001",                    // Required, unique per company, max 100 chars
  "name": "Gaming Laptop",                // Required, max 255 chars
  "description": "High-performance laptop", // Optional
  "category_id": 5,                       // Optional, must belong to company
  "status": "active",                     // Optional, default: "active"
  "default_uom": "EA",                    // Required, max 20 chars
  "storage_uom": "BOX",                   // Optional, max 20 chars
  "weight_kg": "2.5",                     // Optional, decimal
  "length_cm": "35.5",                    // Optional, decimal
  "width_cm": "24.0",                     // Optional, decimal
  "height_cm": "2.5",                     // Optional, decimal
  "volume_cbm": "0.002",                  // Optional, decimal
  "track_batch": false,                   // Optional, default: false
  "track_serial": false,                   // Optional, default: false
  "hazardous": false,                     // Optional, default: false
  "requires_lot_expiry": false,           // Optional, default: false
  "storage_requirements": "Keep dry",     // Optional
  "image_url": "https://example.com/img.jpg" // Optional, URL
}
```

### Required Fields
- `sku`: Unique product SKU within company
- `name`: Product name
- `default_uom`: Primary unit of measure code

### Validation Rules
- `sku` must be unique within the company
- `sku` max length: 100 characters
- `name` max length: 255 characters
- `category_id` must belong to user's company (if provided)
- `default_uom` max length: 20 characters

### Request Example
```typescript
async function createProduct(data: Partial<Product>): Promise<Product> {
  const response = await fetch('/api/v1/masterdata/products/', {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });

  handleResponse(response);
  const result = await response.json();
  return result;
}
```

### Expected Success Response (201 Created)
```json
{
  "id": 1,
  "sku": "LAPTOP-001",
  "name": "Gaming Laptop",
  "description": "High-performance laptop",
  "company_id": 1,
  "category_id": 5,
  "category_name": "Electronics",
  "status": "active",
  "default_uom": "EA",
  "storage_uom": "BOX",
  "weight_kg": "2.500",
  "length_cm": "35.50",
  "width_cm": "24.00",
  "height_cm": "2.50",
  "volume_cbm": "0.0021",
  "track_batch": false,
  "track_serial": false,
  "hazardous": false,
  "requires_lot_expiry": false,
  "storage_requirements": "Keep dry",
  "image_url": "",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Error Responses

**400 Bad Request** - Validation Error
```json
{
  "sku": ["A product with this SKU already exists for your company."],
  "category_id": ["Category not found or does not belong to your company."]
}
```

### Frontend Implementation

#### Multi-Step Form Component
```typescript
function CreateProductForm({ onSuccess }: { onSuccess: () => void }) {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<Partial<Product>>({
    status: 'active',
    track_batch: false,
    track_serial: false,
    hazardous: false,
    requires_lot_expiry: false,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const steps = [
    { id: 1, title: 'Basic Information', fields: ['sku', 'name', 'description', 'category_id'] },
    { id: 2, title: 'Units & Dimensions', fields: ['default_uom', 'storage_uom', 'weight_kg', 'dimensions'] },
    { id: 3, title: 'Tracking & Storage', fields: ['track_batch', 'track_serial', 'hazardous', 'storage_requirements'] },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrors({});

    try {
      await createProduct(formData);
      onSuccess();
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
      <StepIndicator currentStep={step} steps={steps} />
      
      {step === 1 && (
        <BasicInfoStep
          data={formData}
          onChange={setFormData}
          errors={errors}
        />
      )}
      
      {step === 2 && (
        <UnitsStep
          data={formData}
          onChange={setFormData}
          errors={errors}
        />
      )}
      
      {step === 3 && (
        <TrackingStep
          data={formData}
          onChange={setFormData}
          errors={errors}
        />
      )}

      <div className="form-actions">
        {step > 1 && (
          <button type="button" onClick={() => setStep(step - 1)}>
            Previous
          </button>
        )}
        {step < steps.length ? (
          <button type="button" onClick={() => setStep(step + 1)}>
            Next
          </button>
        ) : (
          <button type="submit" disabled={submitting}>
            {submitting ? 'Creating...' : 'Create Product'}
          </button>
        )}
      </div>
    </form>
  );
}
```

#### SKU Validation Component
```typescript
function SKUInput({ value, onChange, error }: SKUInputProps) {
  const { isAvailable, checking } = useSKUCheck(value);

  return (
    <div>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Enter SKU"
        required
        maxLength={100}
      />
      {checking && <span>Checking...</span>}
      {!checking && isAvailable === true && <span className="success">✓ Available</span>}
      {!checking && isAvailable === false && <span className="error">✗ Already in use</span>}
      {error && <span className="error">{error}</span>}
    </div>
  );
}
```

#### UI/UX Considerations
- **Multi-Step Form**: Break complex form into logical steps
- **Real-time SKU Validation**: Check availability as user types
- **Category Picker**: Dropdown or tree selector for categories
- **UOM Selection**: Dropdown with available UOMs
- **Conditional Fields**: Show/hide fields based on tracking options
- **Form Validation**: Validate each step before allowing next
- **Progress Indicator**: Show step progress

---

## 3. Check SKU Availability

### API Endpoint
**GET** `/api/v1/masterdata/products/check-sku/`  
**POST** `/api/v1/masterdata/products/check-sku/`

### Authentication
Required

### Query Parameters (GET)
- `sku` (required): SKU to check
- `company_id` (optional): Company ID (defaults to user's company)

### Request Body (POST)
```json
{
  "sku": "LAPTOP-001",
  "company_id": 1  // Optional
}
```

### Request Example
```typescript
async function checkProductSKU(sku: string): Promise<boolean> {
  const response = await fetch(
    `/api/v1/masterdata/products/check-sku/?sku=${encodeURIComponent(sku)}`,
    {
      method: 'GET',
      headers: getAuthHeaders(),
    }
  );

  handleResponse(response);
  const data = await response.json();
  return data.exists;
}
```

### Expected Response (200 OK)
```json
{
  "exists": false,
  "sku": "LAPTOP-001",
  "company_id": 1,
  "company_name": "My Company"
}
```

### Frontend Implementation

#### Custom Hook
```typescript
function useSKUCheck(sku: string) {
  const [isAvailable, setIsAvailable] = useState<boolean | null>(null);
  const [checking, setChecking] = useState(false);
  const debouncedSKU = useDebounce(sku, 500);

  useEffect(() => {
    if (debouncedSKU.length < 2) {
      setIsAvailable(null);
      return;
    }

    const checkSKU = async () => {
      setChecking(true);
      try {
        const exists = await checkProductSKU(debouncedSKU);
        setIsAvailable(!exists);
      } catch (err) {
        setIsAvailable(null);
      } finally {
        setChecking(false);
      }
    };

    checkSKU();
  }, [debouncedSKU]);

  return { isAvailable, checking };
}
```

---

## 4. Product Details View

### API Endpoint
**GET** `/api/v1/masterdata/products/{id}/`

### Authentication
Required

### Request Example
```typescript
async function getProduct(id: number): Promise<Product> {
  const response = await fetch(`/api/v1/masterdata/products/${id}/`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });

  handleResponse(response);
  return response.json();
}
```

### Expected Response (200 OK)
```json
{
  "id": 1,
  "sku": "LAPTOP-001",
  "name": "Gaming Laptop",
  "description": "High-performance laptop",
  "company_id": 1,
  "category_id": 5,
  "category_name": "Electronics",
  "status": "active",
  "default_uom": "EA",
  "storage_uom": "BOX",
  "weight_kg": "2.500",
  "length_cm": "35.50",
  "width_cm": "24.00",
  "height_cm": "2.50",
  "volume_cbm": "0.0021",
  "track_batch": false,
  "track_serial": false,
  "hazardous": false,
  "requires_lot_expiry": false,
  "storage_requirements": "Keep dry",
  "image_url": "https://example.com/img.jpg",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Frontend Implementation

#### Tabbed Detail View
```typescript
function ProductDetail({ productId }: { productId: number }) {
  const [product, setProduct] = useState<Product | null>(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProduct();
  }, [productId]);

  const loadProduct = async () => {
    try {
      setLoading(true);
      const data = await getProduct(productId);
      setProduct(data);
    } catch (err) {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <ProductDetailSkeleton />;
  if (!product) return <NotFound />;

  return (
    <div className="product-detail">
      <header>
        <h1>{product.name}</h1>
        <StatusBadge status={product.status} />
      </header>

      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tab value="overview" label="Overview">
          <ProductOverview product={product} />
        </Tab>
        <Tab value="barcodes" label="Barcodes">
          <ProductBarcodes productId={product.id} />
        </Tab>
        <Tab value="inventory" label="Inventory">
          <ProductInventory productId={product.id} />
        </Tab>
      </Tabs>
    </div>
  );
}
```

#### UI/UX Considerations
- **Tabbed Interface**: Overview, Barcodes, Inventory, History
- **Status Badge**: Visual status indicator
- **Image Display**: Show product image if available
- **Related Information**: Display category, dimensions, tracking info
- **Edit Button**: Quick edit action in header

---

## 5. Update Product

### API Endpoint
**PATCH** `/api/v1/masterdata/products/{id}/`

### Authentication
Required

### Request Body (Partial Update)
```json
{
  "name": "Updated Product Name",
  "status": "inactive",
  "description": "Updated description"
}
```

### Request Example
```typescript
async function updateProduct(
  id: number,
  data: Partial<Product>
): Promise<Product> {
  const response = await fetch(`/api/v1/masterdata/products/${id}/`, {
    method: 'PATCH',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });

  handleResponse(response);
  return response.json();
}
```

### Expected Success Response (200 OK)
```json
{
  "id": 1,
  "sku": "LAPTOP-001",
  "name": "Updated Product Name",
  // ... other fields with updated values
  "updated_at": "2024-01-02T00:00:00Z"
}
```

### Status Management

Products have three statuses:
- `active`: Product is active and can be used
- `inactive`: Product is inactive (soft delete)
- `discontinued`: Product is discontinued

**Note**: Deleting a product sets status to `inactive` (soft delete).

### Frontend Implementation

#### Status Change Workflow
```typescript
function ProductStatusManager({ product }: { product: Product }) {
  const updateMutation = useUpdateProduct();

  const handleStatusChange = async (newStatus: Product['status']) => {
    if (newStatus === 'inactive') {
      const confirmed = await showConfirmDialog({
        title: 'Deactivate Product',
        message: 'Are you sure you want to deactivate this product?',
      });
      if (!confirmed) return;
    }

    updateMutation.mutate({
      id: product.id,
      data: { status: newStatus },
    });
  };

  return (
    <StatusDropdown
      value={product.status}
      onChange={handleStatusChange}
      options={[
        { value: 'active', label: 'Active' },
        { value: 'inactive', label: 'Inactive' },
        { value: 'discontinued', label: 'Discontinued' },
      ]}
    />
  );
}
```

---

## 6. Product Categories

### API Endpoints

#### List Categories
**GET** `/api/v1/masterdata/product-categories/`

**Query Parameters:**
- `parent_id` (optional): Filter by parent category (default: shows root categories)

#### Create Category
**POST** `/api/v1/masterdata/product-categories/`

#### Get Category
**GET** `/api/v1/masterdata/product-categories/{id}/`

#### Update Category
**PATCH** `/api/v1/masterdata/product-categories/{id}/`

#### Delete Category
**DELETE** `/api/v1/masterdata/product-categories/{id}/`

### Category Response Structure
```json
{
  "id": 1,
  "name": "Electronics",
  "description": "Electronic products",
  "company_id": 1,
  "parent_id": null,
  "parent_name": null,
  "children_count": 3,
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Request Body (Create/Update)
```json
{
  "name": "Electronics",        // Required, unique per company
  "description": "",            // Optional
  "parent_id": null,           // Optional, for subcategories
  "is_active": true            // Optional, default: true
}
```

### Frontend Implementation

#### Category Tree Component
```typescript
interface Category {
  id: number;
  name: string;
  description: string;
  company_id: number;
  parent_id: number | null;
  parent_name: string | null;
  children_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

function CategoryTree() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  useEffect(() => {
    loadCategories();
  }, []);

  const loadCategories = async () => {
    // Load root categories
    const roots = await getCategories();
    
    // Load children for expanded categories
    const withChildren = await Promise.all(
      roots.map(async (cat) => {
        if (expanded.has(cat.id)) {
          const children = await getCategories({ parentId: cat.id });
          return { ...cat, children };
        }
        return cat;
      })
    );
    
    setCategories(withChildren);
  };

  const toggleCategory = async (categoryId: number) => {
    if (expanded.has(categoryId)) {
      setExpanded(prev => {
        const next = new Set(prev);
        next.delete(categoryId);
        return next;
      });
    } else {
      setExpanded(prev => new Set(prev).add(categoryId));
      // Load children
      const children = await getCategories({ parentId: categoryId });
      setCategories(prev =>
        prev.map(cat =>
          cat.id === categoryId ? { ...cat, children } : cat
        )
      );
    }
  };

  return (
    <TreeView>
      {categories.map(category => (
        <CategoryTreeNode
          key={category.id}
          category={category}
          expanded={expanded.has(category.id)}
          onToggle={() => toggleCategory(category.id)}
        />
      ))}
    </TreeView>
  );
}
```

#### Category Picker Component
```typescript
function CategoryPicker({
  value,
  onChange,
}: {
  value: number | null;
  onChange: (categoryId: number | null) => void;
}) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [showTree, setShowTree] = useState(false);

  useEffect(() => {
    loadCategories();
  }, []);

  const loadCategories = async () => {
    const data = await getCategories();
    setCategories(data);
  };

  const selectedCategory = categories.find(c => c.id === value);

  return (
    <div className="category-picker">
      <button onClick={() => setShowTree(!showTree)}>
        {selectedCategory ? selectedCategory.name : 'Select Category'}
      </button>
      
      {showTree && (
        <CategoryTree
          categories={categories}
          selectedId={value}
          onSelect={(id) => {
            onChange(id);
            setShowTree(false);
          }}
        />
      )}
    </div>
  );
}
```

#### UI/UX Considerations
- **Tree Structure**: Expandable/collapsible tree view
- **Parent/Child Relationships**: Visual hierarchy with indentation
- **Category Selection**: Tree picker or flat dropdown
- **Breadcrumbs**: Show category path when viewing products
- **Category Management**: Create/edit/delete categories inline

---

## 7. Product Barcodes

### API Endpoints

#### List Barcodes
**GET** `/api/v1/masterdata/products/{product_id}/barcodes/`

#### Create Barcode
**POST** `/api/v1/masterdata/products/{product_id}/barcodes/`

#### Delete Barcode
**DELETE** `/api/v1/masterdata/products/{product_id}/barcodes/{id}/`

#### Lookup Product by Barcode
**POST** `/api/v1/masterdata/products/lookup-by-barcode/`

### Barcode Response Structure
```json
{
  "id": 1,
  "product": 1,
  "product_sku": "LAPTOP-001",
  "barcode": "1234567890123",
  "is_primary": true,
  "label": "EAN13",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Request Body (Create Barcode)
```json
{
  "barcode": "1234567890123",  // Required, unique per product
  "is_primary": true,          // Optional, default: false
  "label": "EAN13"             // Optional, e.g., "EAN13", "UPC", "Case barcode"
}
```

### Frontend Implementation

#### Barcode List Component
```typescript
interface ProductBarcode {
  id: number;
  product: number;
  product_sku: string;
  barcode: string;
  is_primary: boolean;
  label: string;
  created_at: string;
  updated_at: string;
}

function ProductBarcodes({ productId }: { productId: number }) {
  const [barcodes, setBarcodes] = useState<ProductBarcode[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadBarcodes();
  }, [productId]);

  const loadBarcodes = async () => {
    try {
      setLoading(true);
      const data = await getProductBarcodes(productId);
      setBarcodes(data);
    } catch (err) {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  const handleAddBarcode = async (barcodeData: Partial<ProductBarcode>) => {
    try {
      await createProductBarcode(productId, barcodeData);
      loadBarcodes();
    } catch (err) {
      // Handle error
    }
  };

  const handleSetPrimary = async (barcodeId: number) => {
    try {
      // Update all barcodes - set this one as primary, others as not primary
      await Promise.all(
        barcodes.map(b =>
          updateProductBarcode(productId, b.id, {
            is_primary: b.id === barcodeId,
          })
        )
      );
      loadBarcodes();
    } catch (err) {
      // Handle error
    }
  };

  return (
    <div>
      <BarcodeList
        barcodes={barcodes}
        onSetPrimary={handleSetPrimary}
        onDelete={handleDeleteBarcode}
      />
      <AddBarcodeForm onSubmit={handleAddBarcode} />
    </div>
  );
}
```

#### Barcode Scanner Integration
```typescript
function BarcodeScannerInput({
  onScan,
}: {
  onScan: (barcode: string) => void;
}) {
  const [scanning, setScanning] = useState(false);

  const handleBarcodeScan = (barcode: string) => {
    onScan(barcode);
    setScanning(false);
  };

  return (
    <div>
      <button onClick={() => setScanning(true)}>
        Scan Barcode
      </button>
      {scanning && (
        <BarcodeScanner
          onScan={handleBarcodeScan}
          onCancel={() => setScanning(false)}
        />
      )}
    </div>
  );
}
```

#### Barcode Lookup
```typescript
async function lookupProductByBarcode(barcode: string): Promise<Product | null> {
  const response = await fetch('/api/v1/masterdata/products/lookup-by-barcode/', {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ barcode }),
  });

  handleResponse(response);
  const data = await response.json();
  
  if (data.found) {
    return data.product;
  }
  return null;
}

// Usage
function BarcodeLookup() {
  const [barcode, setBarcode] = useState('');
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(false);

  const handleLookup = async () => {
    setLoading(true);
    try {
      const found = await lookupProductByBarcode(barcode);
      setProduct(found);
    } catch (err) {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        type="text"
        value={barcode}
        onChange={(e) => setBarcode(e.target.value)}
        onKeyPress={(e) => e.key === 'Enter' && handleLookup()}
        placeholder="Scan or enter barcode"
      />
      <button onClick={handleLookup} disabled={loading}>
        Lookup
      </button>
      {product && <ProductCard product={product} />}
    </div>
  );
}
```

#### UI/UX Considerations
- **Primary Barcode**: Visual indicator for primary barcode
- **Barcode List**: Table with barcode, label, primary status
- **Add Barcode**: Form with validation
- **Scanner Integration**: Support for barcode scanner hardware
- **Lookup Feature**: Quick product lookup by barcode
- **Barcode Validation**: Validate barcode format if needed

---

## 8. Product Search & Filtering

### Search Implementation

#### Advanced Search Hook
```typescript
function useProductSearch() {
  const [searchParams, setSearchParams] = useState({
    search: '',
    categoryId: undefined as number | undefined,
    status: undefined as 'active' | 'inactive' | 'discontinued' | undefined,
  });

  const debouncedSearch = useDebounce(searchParams.search, 500);

  const { data, isLoading, error } = useQuery({
    queryKey: ['products', searchParams, debouncedSearch],
    queryFn: () => getProducts({
      search: debouncedSearch,
      categoryId: searchParams.categoryId,
      status: searchParams.status,
    }),
    enabled: debouncedSearch.length >= 2 || searchParams.categoryId !== undefined,
  });

  return {
    products: data?.results || [],
    loading: isLoading,
    error,
    searchParams,
    setSearchParams,
  };
}
```

#### Filter Sidebar Component
```typescript
function ProductFilters({
  filters,
  onChange,
}: {
  filters: ProductFilters;
  onChange: (filters: ProductFilters) => void;
}) {
  const [categories, setCategories] = useState<Category[]>([]);

  useEffect(() => {
    loadCategories();
  }, []);

  const loadCategories = async () => {
    const data = await getCategories();
    setCategories(data);
  };

  return (
    <div className="filters-sidebar">
      <div>
        <label>Category</label>
        <CategoryPicker
          value={filters.categoryId}
          onChange={(id) => onChange({ ...filters, categoryId: id })}
        />
      </div>

      <div>
        <label>Status</label>
        <CheckboxGroup
          options={[
            { value: 'active', label: 'Active' },
            { value: 'inactive', label: 'Inactive' },
            { value: 'discontinued', label: 'Discontinued' },
          ]}
          value={filters.status}
          onChange={(status) => onChange({ ...filters, status })}
        />
      </div>

      <button onClick={() => onChange({ search: '', categoryId: undefined, status: undefined })}>
        Clear Filters
      </button>
    </div>
  );
}
```

#### URL Query Params Integration
```typescript
function useProductFiltersFromURL() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = {
    search: searchParams.get('search') || '',
    categoryId: searchParams.get('category') ? Number(searchParams.get('category')) : undefined,
    status: searchParams.get('status') as 'active' | 'inactive' | 'discontinued' | undefined,
  };

  const updateFilters = (newFilters: typeof filters) => {
    const params = new URLSearchParams();
    if (newFilters.search) params.set('search', newFilters.search);
    if (newFilters.categoryId) params.set('category', newFilters.categoryId.toString());
    if (newFilters.status) params.set('status', newFilters.status);
    setSearchParams(params);
  };

  return { filters, updateFilters };
}
```

#### UI/UX Considerations
- **Debounced Search**: Wait 500ms after typing stops
- **Filter Persistence**: Save filters in URL or localStorage
- **Clear Filters**: Easy way to reset all filters
- **Filter Count**: Show number of active filters
- **Search Suggestions**: Autocomplete for SKU/name search

---

## 9. Code Examples

### Complete TypeScript Types
```typescript
// types/product.ts
export interface Product {
  id: number;
  sku: string;
  name: string;
  description: string;
  company_id: number;
  category_id: number | null;
  category_name: string | null;
  status: 'active' | 'inactive' | 'discontinued';
  default_uom: string;
  storage_uom: string;
  weight_kg: string | null;
  length_cm: string | null;
  width_cm: string | null;
  height_cm: string | null;
  volume_cbm: string | null;
  track_batch: boolean;
  track_serial: boolean;
  hazardous: boolean;
  requires_lot_expiry: boolean;
  storage_requirements: string;
  image_url: string;
  created_at: string;
  updated_at: string;
}

export interface ProductListItem {
  id: number;
  sku: string;
  name: string;
  category_name: string | null;
  status: 'active' | 'inactive' | 'discontinued';
  default_uom: string;
  created_at: string;
}

export interface ProductCategory {
  id: number;
  name: string;
  description: string;
  company_id: number;
  parent_id: number | null;
  parent_name: string | null;
  children_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductBarcode {
  id: number;
  product: number;
  product_sku: string;
  barcode: string;
  is_primary: boolean;
  label: string;
  created_at: string;
  updated_at: string;
}
```

### API Client Functions
```typescript
// api/product.ts
export async function getProducts(
  params: ProductListParams = {}
): Promise<PaginatedResponse<ProductListItem>> {
  const queryParams = new URLSearchParams();
  if (params.page) queryParams.append('page', params.page.toString());
  if (params.pageSize) queryParams.append('page_size', params.pageSize.toString());
  if (params.search) queryParams.append('search', params.search);
  if (params.categoryId) queryParams.append('category_id', params.categoryId.toString());
  if (params.status) queryParams.append('status', params.status);

  const response = await fetch(
    `${API_BASE}/masterdata/products/?${queryParams.toString()}`,
    { method: 'GET', headers: getAuthHeaders() }
  );
  handleResponse(response);
  return response.json();
}

export async function getProduct(id: number): Promise<Product> {
  const response = await fetch(`${API_BASE}/masterdata/products/${id}/`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });
  handleResponse(response);
  return response.json();
}

export async function createProduct(data: Partial<Product>): Promise<Product> {
  const response = await fetch(`${API_BASE}/masterdata/products/`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  handleResponse(response);
  return response.json();
}

export async function updateProduct(
  id: number,
  data: Partial<Product>
): Promise<Product> {
  const response = await fetch(`${API_BASE}/masterdata/products/${id}/`, {
    method: 'PATCH',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  handleResponse(response);
  return response.json();
}

export async function deleteProduct(id: number): Promise<void> {
  const response = await fetch(`${API_BASE}/masterdata/products/${id}/`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  handleResponse(response);
  // Note: This sets status to 'inactive', doesn't actually delete
}

export async function checkProductSKU(sku: string): Promise<boolean> {
  const response = await fetch(
    `${API_BASE}/masterdata/products/check-sku/?sku=${encodeURIComponent(sku)}`,
    { method: 'GET', headers: getAuthHeaders() }
  );
  handleResponse(response);
  const data = await response.json();
  return data.exists;
}

// Category APIs
export async function getCategories(
  params: { parentId?: number } = {}
): Promise<Category[]> {
  const queryParams = new URLSearchParams();
  if (params.parentId) {
    queryParams.append('parent_id', params.parentId.toString());
  }

  const response = await fetch(
    `${API_BASE}/masterdata/product-categories/?${queryParams.toString()}`,
    { method: 'GET', headers: getAuthHeaders() }
  );
  handleResponse(response);
  return response.json();
}

export async function createCategory(data: Partial<Category>): Promise<Category> {
  const response = await fetch(`${API_BASE}/masterdata/product-categories/`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  handleResponse(response);
  return response.json();
}

// Barcode APIs
export async function getProductBarcodes(
  productId: number
): Promise<ProductBarcode[]> {
  const response = await fetch(
    `${API_BASE}/masterdata/products/${productId}/barcodes/`,
    { method: 'GET', headers: getAuthHeaders() }
  );
  handleResponse(response);
  return response.json();
}

export async function createProductBarcode(
  productId: number,
  data: Partial<ProductBarcode>
): Promise<ProductBarcode> {
  const response = await fetch(
    `${API_BASE}/masterdata/products/${productId}/barcodes/`,
    {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    }
  );
  handleResponse(response);
  return response.json();
}

export async function deleteProductBarcode(
  productId: number,
  barcodeId: number
): Promise<void> {
  const response = await fetch(
    `${API_BASE}/masterdata/products/${productId}/barcodes/${barcodeId}/`,
    { method: 'DELETE', headers: getAuthHeaders() }
  );
  handleResponse(response);
}

export async function lookupProductByBarcode(
  barcode: string
): Promise<{ found: boolean; barcode: string; product: Product | null }> {
  const response = await fetch(
    `${API_BASE}/masterdata/products/lookup-by-barcode/`,
    {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ barcode }),
    }
  );
  handleResponse(response);
  return response.json();
}
```

### Custom Hooks
```typescript
// hooks/useProducts.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as productAPI from '../api/product';

export function useProducts(params: ProductListParams = {}) {
  return useQuery({
    queryKey: ['products', params],
    queryFn: () => productAPI.getProducts(params),
    staleTime: 5 * 60 * 1000,
  });
}

export function useProduct(id: number) {
  return useQuery({
    queryKey: ['product', id],
    queryFn: () => productAPI.getProduct(id),
    enabled: !!id,
  });
}

export function useCreateProduct() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: productAPI.createProduct,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
  });
}

export function useUpdateProduct() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Product> }) =>
      productAPI.updateProduct(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      queryClient.invalidateQueries({ queryKey: ['product', variables.id] });
    },
  });
}

export function useDeleteProduct() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: productAPI.deleteProduct,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
  });
}

export function useProductCategories(parentId?: number) {
  return useQuery({
    queryKey: ['product-categories', parentId],
    queryFn: () => productAPI.getCategories({ parentId }),
    staleTime: 10 * 60 * 1000, // Categories change less frequently
  });
}

export function useProductBarcodes(productId: number) {
  return useQuery({
    queryKey: ['product-barcodes', productId],
    queryFn: () => productAPI.getProductBarcodes(productId),
    enabled: !!productId,
  });
}
```

---

## Summary

This guide covers all product management APIs including:
- Product CRUD operations
- Product categories with tree structure
- Product barcodes management
- Barcode lookup functionality
- Search and filtering
- Status management (active/inactive/discontinued)

Next: Implement Stock Management (FRONTEND_STOCK_IMPLEMENTATION.md) which depends on both Warehouses and Products.

