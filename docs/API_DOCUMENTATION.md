# WMS API Documentation

Base URL: `/api/v1`

All endpoints require authentication unless specified otherwise. Use JWT Bearer token in the Authorization header:
```
Authorization: Bearer <access_token>
```

---

## Authentication APIs

### 1. Register (Signup)
**POST** `/accounts/auth/register/`

**Authentication:** Not required (public endpoint)

**Request Body:**
```json
{
  "company_name": "My Company",          // Required
  "username": "owner",                    // Required
  "email": "owner@example.com",          // Required
  "password": "SecurePass123!",           // Required
  "password_confirm": "SecurePass123!",   // Required
  
  // Optional company fields
  "company_legal_name": "My Company Inc",
  "company_email": "info@company.com",
  "company_phone": "+1234567890",
  "company_website": "https://company.com",
  "company_address_line1": "123 Main St",
  "company_address_line2": "Suite 100",
  "company_city": "New York",
  "company_state": "NY",
  "company_postal_code": "10001",
  "company_country": "USA",
  "company_tax_id": "TAX123",
  "company_registration_number": "REG456",
  
  // Optional user fields
  "first_name": "John",
  "last_name": "Doe",
  "employee_code": "EMP001",
  "job_title": "Manager",
  "phone": "+1234567890",
  "mobile": "+1234567891",
  "language": "en",
  "time_zone": "America/New_York"
}
```

**Response (201 Created):**
```json
{
  "user": {
    "id": 1,
    "username": "owner",
    "email": "owner@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "company_id": 1,
    "company_name": "My Company",
    "is_staff": true,
    "is_active": true,
    "date_joined": "2024-01-01T00:00:00Z"
  },
  "company": {
    "id": 1,
    "name": "My Company"
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  },
  "message": "Company and user registered successfully."
}
```

**Error Responses:**
- `400 Bad Request`: Validation errors (passwords don't match, company name exists, etc.)

---

### 2. Login
**POST** `/accounts/auth/login/`

**Authentication:** Not required (public endpoint)

**Request Body:**
```json
{
  "email": "owner@example.com",    // Required
  "password": "SecurePass123!"      // Required
}
```

**Response (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "owner",
    "email": "owner@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "company_id": 1,
    "company_name": "My Company",
    "employee_code": "EMP001",
    "job_title": "Manager",
    "phone": "+1234567890",
    "is_warehouse_operator": true,
    "is_staff": true,
    "is_active": true,
    "warehouses": [
      {
        "warehouse_id": 1,
        "warehouse_code": "WH-001",
        "warehouse_name": "Main Warehouse",
        "role": "Manager",
        "is_primary": true
      }
    ]
  }
}
```

**Error Responses:**
- `400 Bad Request`: Invalid credentials, user inactive, or no company assigned

---

### 3. Refresh Token
**POST** `/accounts/auth/refresh/`

**Authentication:** Not required (public endpoint)

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

### 4. Get Current User (Me)
**GET** `/accounts/auth/me/`

**Authentication:** Required

**Response (200 OK):**
```json
{
  "id": 1,
  "username": "owner",
  "email": "owner@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "company_id": 1,
  "company_name": "My Company",
  "employee_code": "EMP001",
  "job_title": "Manager",
  "phone": "+1234567890",
  "mobile": "+1234567891",
  "language": "en",
  "time_zone": "America/New_York",
  "is_warehouse_operator": true,
  "is_active": true,
  "is_staff": true,
  "is_superuser": false,
  "date_joined": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-01T12:00:00Z",
  "warehouses": [
    {
      "warehouse_id": 1,
      "warehouse_code": "WH-001",
      "warehouse_name": "Main Warehouse",
      "role": "Manager",
      "is_primary": true
    }
  ]
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or missing token

---

### 5. Get/Update User Profile
**GET** `/accounts/auth/profile/` - Get profile
**PUT** `/accounts/auth/profile/` - Full update
**PATCH** `/accounts/auth/profile/` - Partial update

**Authentication:** Required

**Request Body (PATCH):**
```json
{
  "email": "newemail@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "employee_code": "EMP002",
  "job_title": "Supervisor",
  "phone": "+1987654321",
  "mobile": "+1987654322",
  "language": "es",
  "time_zone": "America/Los_Angeles",
  "is_warehouse_operator": false
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "username": "owner",
  "email": "newemail@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "company_id": 1,
  "company_name": "My Company",
  // ... other fields
}
```

---

### 6. Change Password
**POST** `/accounts/auth/change-password/`

**Authentication:** Required

**Request Body:**
```json
{
  "old_password": "OldPass123!",
  "new_password": "NewPass123!",
  "new_password_confirm": "NewPass123!"
}
```

**Response (200 OK):**
```json
{
  "message": "Password changed successfully."
}
```

**Error Responses:**
- `400 Bad Request`: Old password incorrect, passwords don't match, or validation errors

---

### 7. Logout
**POST** `/accounts/auth/logout/`

**Authentication:** Required

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200 OK):**
```json
{
  "message": "Successfully logged out."
}
```

**Error Responses:**
- `400 Bad Request`: Missing refresh token or invalid token

---

## Company APIs

### 8. Get My Company
**GET** `/accounts/company/`

**Authentication:** Required

**Response (200 OK):**
```json
{
  "id": 1,
  "name": "My Company",
  "legal_name": "My Company Inc LLC",
  "email": "company@example.com",
  "phone": "+1234567890",
  "website": "https://company.com",
  "address_line1": "123 Main St",
  "address_line2": "Suite 100",
  "city": "New York",
  "state": "NY",
  "postal_code": "10001",
  "country": "United States",
  "tax_id": "TAX123",
  "registration_number": "REG456",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

**Error Responses:**
- `401 Unauthorized`: Missing or invalid authentication token
- `404 Not Found`: User is not associated with a company

**Use Case:**
Get complete company information for the current logged-in user. Useful for displaying company details in settings, profile pages, or company management screens.

---

## Onboarding APIs

### 9. Check Onboarding Status
**GET** `/accounts/onboarding/status/`

**Authentication:** Required

**Response (200 OK):**
```json
{
  "is_complete": false,
  "company_info_complete": false,
  "has_warehouse": false,
  "missing_fields": ["email", "country"],
  "warehouse_count": 0
}
```

**Field Descriptions:**
- `is_complete`: `true` when both company info is complete AND at least one warehouse exists
- `company_info_complete`: `true` when company has `email` and `country` set
- `has_warehouse`: `true` when at least one active warehouse exists
- `missing_fields`: Array of required company fields that are missing (e.g., `["email", "country"]`)
- `warehouse_count`: Number of active warehouses for the company

**Use Case:**
Check this endpoint after signup to determine if user needs to complete onboarding. If `is_complete` is `false`, guide user through:
1. Completing company info (if `company_info_complete` is `false`)
2. Creating first warehouse (if `has_warehouse` is `false`)

---

### 10. Update Company Onboarding Info
**PATCH** `/accounts/onboarding/`

**Authentication:** Required

**Request Body:**
```json
{
  // Required fields (if not already set)
  "email": "company@example.com",        // Required for onboarding
  "country": "United States",            // Required for onboarding
  
  // Optional fields
  "legal_name": "My Company Inc LLC",
  "phone": "+1234567890",
  "website": "https://company.com",
  "address_line1": "123 Main St",
  "address_line2": "Suite 100",
  "city": "New York",
  "state": "NY",
  "postal_code": "10001",
  "tax_id": "TAX123",
  "registration_number": "REG456"
}
```

**Response (200 OK):**
```json
{
  "company": {
    "id": 1,
    "name": "My Company",
    "legal_name": "My Company Inc LLC",
    "email": "company@example.com",
    "phone": "+1234567890",
    "website": "https://company.com",
    "address_line1": "123 Main St",
    "address_line2": "Suite 100",
    "city": "New York",
    "state": "NY",
    "postal_code": "10001",
    "country": "United States",
    "tax_id": "TAX123",
    "registration_number": "REG456",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
  },
  "message": "Company onboarding information updated successfully."
}
```

**Error Responses:**
- `400 Bad Request`: Missing required fields (`email` or `country` if not already set)
- `404 Not Found`: User not associated with a company

**Note:** After initial onboarding, you can update individual fields. The `email` and `country` are only required if they're currently empty.

---

## Warehouse APIs

### 11. List Warehouses
**GET** `/masterdata/warehouses/`

**Authentication:** Required

**Query Parameters:**
- `page` (optional): Page number for pagination
- `page_size` (optional): Number of results per page

**Response (200 OK):**
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
      "latitude": "40.7128",
      "longitude": "-74.0060",
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
      // ... same structure
    }
  ]
}
```

**Note:** Users only see warehouses from their company. Results are paginated.

---

### 12. Create Warehouse
**POST** `/masterdata/warehouses/`

**Authentication:** Required

**Request Body:**
```json
{
  "code": "WH-001",                    // Required, unique per company
  "name": "Main Warehouse",            // Required
  
  // Optional fields
  "description": "Primary distribution center",
  "address_line1": "123 Warehouse St",
  "address_line2": "Building A",
  "city": "New York",
  "state": "NY",
  "postal_code": "10001",
  "country": "USA",
  "time_zone": "America/New_York",
  "latitude": "40.7128",
  "longitude": "-74.0060",
  "type": "main",                      // Options: "main", "store", "3pl", "other"
  "is_active": true,
  "allow_negative_stock": false,
  "uses_bins": true
}
```

**Response (201 Created):**
```json
{
  "warehouse": {
    "id": 1,
    "code": "WH-001",
    "name": "Main Warehouse",
    "description": "Primary distribution center",
    "company_id": 1,
    // ... all warehouse fields
  },
  "message": "Warehouse created successfully."
}
```

**Error Responses:**
- `400 Bad Request`: Validation errors (duplicate code, invalid data)
- `401 Unauthorized`: Not authenticated

**Note:** Warehouse code must be unique within the company. The warehouse is automatically associated with the user's company.

---

### 13. Get Warehouse Details
**GET** `/masterdata/warehouses/{id}/`

**Authentication:** Required

**Response (200 OK):**
```json
{
  "id": 1,
  "code": "WH-001",
  "name": "Main Warehouse",
  "description": "Primary distribution center",
  "company_id": 1,
  // ... all warehouse fields
}
```

**Error Responses:**
- `404 Not Found`: Warehouse not found or belongs to another company

---

### 14. Update Warehouse
**PUT** `/masterdata/warehouses/{id}/` - Full update
**PATCH** `/masterdata/warehouses/{id}/` - Partial update

**Authentication:** Required

**Request Body (PATCH):**
```json
{
  "name": "Updated Warehouse Name",
  "city": "Los Angeles",
  "is_active": false
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "code": "WH-001",
  "name": "Updated Warehouse Name",
  "city": "Los Angeles",
  // ... all warehouse fields
}
```

**Error Responses:**
- `400 Bad Request`: Validation errors
- `404 Not Found`: Warehouse not found or belongs to another company

---

### 15. Delete Warehouse
**DELETE** `/masterdata/warehouses/{id}/`

**Authentication:** Required

**Response (204 No Content):** Empty response body

**Error Responses:**
- `404 Not Found`: Warehouse not found or belongs to another company

---

## Error Response Format

All error responses follow this format:

```json
{
  "field_name": ["Error message"],
  "non_field_errors": ["General error message"]
}
```

**Example:**
```json
{
  "email": ["This field is required."],
  "password_confirm": ["Password fields didn't match."]
}
```

---

## HTTP Status Codes

- `200 OK`: Successful GET, PUT, PATCH request
- `201 Created`: Successful POST request (resource created)
- `204 No Content`: Successful DELETE request
- `400 Bad Request`: Validation errors or bad request data
- `401 Unauthorized`: Missing or invalid authentication token
- `404 Not Found`: Resource not found or user doesn't have access
- `500 Internal Server Error`: Server error

---

## Authentication Flow

1. **User Registration:**
   - POST `/accounts/auth/register/` → Returns `access` and `refresh` tokens
   - Store tokens securely (e.g., localStorage or httpOnly cookies)

2. **User Login:**
   - POST `/accounts/auth/login/` → Returns `access` and `refresh` tokens
   - Store tokens securely

3. **Making Authenticated Requests:**
   - Include `Authorization: Bearer <access_token>` header in all requests

4. **Token Refresh:**
   - When access token expires (1 hour), use refresh token:
   - POST `/accounts/auth/refresh/` with `refresh` token → Get new `access` token
   - Refresh tokens expire after 7 days

5. **Logout:**
   - POST `/accounts/auth/logout/` with `refresh` token → Blacklists refresh token

---

## Onboarding Flow

1. **After Signup:**
   - User registers → Gets tokens
   - Check onboarding status: GET `/accounts/onboarding/status/`

2. **If `is_complete: false`:**
   - If `company_info_complete: false`:
     - Show company onboarding form
     - PATCH `/accounts/onboarding/` with `email` and `country` (required)
   - If `has_warehouse: false`:
     - Show warehouse creation form
     - POST `/masterdata/warehouses/` to create first warehouse

3. **Re-check Status:**
   - GET `/accounts/onboarding/status/` again
   - If `is_complete: true`, allow access to main app

---

## CORS Configuration

The API is configured to accept requests from:
- `http://localhost:3000` (Next.js default dev port)
- `http://127.0.0.1:3000`

Credentials (cookies, authorization headers) are allowed for JWT authentication.

**For production:** Update `CORS_ALLOWED_ORIGINS` in Django settings to include your frontend domain.

---

## Token Expiration

- **Access Token:** Valid for 1 hour
- **Refresh Token:** Valid for 7 days

When the access token expires, use the refresh token to get a new access token. If the refresh token expires, the user must log in again.

---

## Notes

- All timestamps are in ISO 8601 format (UTC)
- All endpoints are versioned under `/api/v1/`
- Pagination is used for list endpoints (default page size may vary)
- Users can only access resources from their own company
- Warehouse codes must be unique within a company
- Company email and country are required for onboarding completion
- Access tokens expire after 1 hour - implement automatic token refresh in your frontend
- Refresh tokens expire after 7 days - prompt user to re-login if refresh fails

