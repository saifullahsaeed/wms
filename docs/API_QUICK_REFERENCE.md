# WMS API Quick Reference

Base URL: `/api/v1`

## Authentication Endpoints

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| POST | `/accounts/auth/register/` | No | Sign up (create company + user) |
| POST | `/accounts/auth/login/` | No | Login (email + password) |
| POST | `/accounts/auth/refresh/` | No | Refresh access token |
| POST | `/accounts/auth/logout/` | Yes | Logout (blacklist refresh token) |
| GET | `/accounts/auth/me/` | Yes | Get current user info |
| GET | `/accounts/auth/profile/` | Yes | Get user profile |
| PATCH | `/accounts/auth/profile/` | Yes | Update user profile |
| POST | `/accounts/auth/change-password/` | Yes | Change password |

## Company Endpoints

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| GET | `/accounts/company/` | Yes | Get current user's company details |

## Onboarding Endpoints

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| GET | `/accounts/onboarding/status/` | Yes | Check onboarding completion status |
| PATCH | `/accounts/onboarding/` | Yes | Update company onboarding info |

## Warehouse Endpoints

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| GET | `/masterdata/warehouses/` | Yes | List all warehouses (paginated) |
| POST | `/masterdata/warehouses/` | Yes | Create new warehouse |
| GET | `/masterdata/warehouses/{id}/` | Yes | Get warehouse details |
| PATCH | `/masterdata/warehouses/{id}/` | Yes | Update warehouse |
| PUT | `/masterdata/warehouses/{id}/` | Yes | Full update warehouse |
| DELETE | `/masterdata/warehouses/{id}/` | Yes | Delete warehouse |

## Request Headers

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

## Token Expiration

- **Access Token:** 1 hour
- **Refresh Token:** 7 days

## Onboarding Flow

1. User signs up → `POST /accounts/auth/register/`
2. Check status → `GET /accounts/onboarding/status/`
3. If incomplete:
   - Complete company info → `PATCH /accounts/onboarding/` (email, country required)
   - Create warehouse → `POST /masterdata/warehouses/`
4. Re-check status → `GET /accounts/onboarding/status/`
5. If `is_complete: true`, allow access to main app

## Common Response Codes

- `200 OK` - Success
- `201 Created` - Resource created
- `204 No Content` - Success (delete)
- `400 Bad Request` - Validation error
- `401 Unauthorized` - Missing/invalid token
- `404 Not Found` - Resource not found

## Required Fields

### Signup
- `company_name`
- `username`
- `email`
- `password`
- `password_confirm`

### Company Onboarding
- `email` (if not already set)
- `country` (if not already set)

### Warehouse Creation
- `code` (unique per company)
- `name`

