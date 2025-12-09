# Frontend Common Patterns Guide

## Overview

This guide covers shared patterns, utilities, and best practices used across all WMS frontend features. These patterns should be implemented once and reused throughout the application.

---

## 1. Authentication & Authorization

### Token Management

#### Token Storage
```typescript
// utils/auth.ts
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setAccessToken(token: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setRefreshToken(token: string): void {
  localStorage.setItem(REFRESH_TOKEN_KEY, token);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}
```

#### Token Refresh
```typescript
// api/auth.ts
async function refreshAccessToken(): Promise<string> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }

  const response = await fetch('/api/v1/accounts/token/refresh/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh: refreshToken }),
  });

  if (!response.ok) {
    clearTokens();
    throw new Error('Token refresh failed');
  }

  const data = await response.json();
  setAccessToken(data.access);
  if (data.refresh) {
    setRefreshToken(data.refresh);
  }
  return data.access;
}
```

#### Automatic Token Refresh
```typescript
// hooks/useAuth.ts
import { useEffect } from 'react';

export function useTokenRefresh() {
  useEffect(() => {
    const refreshInterval = setInterval(async () => {
      try {
        await refreshAccessToken();
      } catch (error) {
        // Redirect to login on refresh failure
        window.location.href = '/login';
      }
    }, 14 * 60 * 1000); // Refresh every 14 minutes (tokens expire in 15)

    return () => clearInterval(refreshInterval);
  }, []);
}
```

### Permission Checks

#### Permission Hook
```typescript
// hooks/usePermissions.ts
import { useQuery } from '@tanstack/react-query';

export function usePermissions() {
  return useQuery({
    queryKey: ['user-permissions'],
    queryFn: async () => {
      const response = await fetch('/api/v1/accounts/user/permissions/', {
        headers: getAuthHeaders(),
      });
      handleResponse(response);
      return response.json();
    },
    staleTime: 10 * 60 * 1000, // Cache for 10 minutes
  });
}

export function useHasPermission(permission: string): boolean {
  const { data: permissions } = usePermissions();
  return permissions?.includes(permission) ?? false;
}
```

#### Permission Component
```typescript
// components/PermissionGate.tsx
function PermissionGate({
  permission,
  children,
  fallback,
}: {
  permission: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const hasPermission = useHasPermission(permission);

  if (!hasPermission) {
    return fallback ?? null;
  }

  return <>{children}</>;
}

// Usage
<PermissionGate permission="manage_inventory">
  <CreateAdjustmentButton />
</PermissionGate>
```

### Role-Based UI

```typescript
// hooks/useUserRole.ts
export function useUserRole() {
  return useQuery({
    queryKey: ['user-role'],
    queryFn: async () => {
      const response = await fetch('/api/v1/accounts/user/', {
        headers: getAuthHeaders(),
      });
      handleResponse(response);
      const user = await response.json();
      return user.role; // Assuming role is returned
    },
  });
}

// Usage
function WarehouseActions({ warehouse }: { warehouse: Warehouse }) {
  const { data: role } = useUserRole();

  return (
    <div>
      {role === 'admin' && <DeleteWarehouseButton warehouse={warehouse} />}
      {role === 'admin' || role === 'manager' ? (
        <EditWarehouseButton warehouse={warehouse} />
      ) : null}
    </div>
  );
}
```

---

## 2. API Client Setup

### Base Configuration

```typescript
// api/config.ts
export const API_BASE = '/api/v1';

export function getAuthHeaders(): HeadersInit {
  const token = getAccessToken();
  return {
    'Authorization': token ? `Bearer ${token}` : '',
    'Content-Type': 'application/json',
  };
}
```

### Request Interceptors

```typescript
// api/interceptors.ts
async function apiRequest(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const headers = {
    ...getAuthHeaders(),
    ...options.headers,
  };

  let response = await fetch(url, {
    ...options,
    headers,
  });

  // Handle 401 - try token refresh
  if (response.status === 401) {
    try {
      const newToken = await refreshAccessToken();
      // Retry request with new token
      response = await fetch(url, {
        ...options,
        headers: {
          ...headers,
          'Authorization': `Bearer ${newToken}`,
        },
      });
    } catch (error) {
      // Refresh failed, redirect to login
      clearTokens();
      window.location.href = '/login';
      throw error;
    }
  }

  return response;
}
```

### Response Interceptors

```typescript
// api/interceptors.ts
export async function handleResponse(response: Response): Promise<void> {
  if (!response.ok) {
    if (response.status === 401) {
      clearTokens();
      window.location.href = '/login';
      throw new Error('Unauthorized');
    }

    if (response.status === 403) {
      throw new Error('Forbidden - insufficient permissions');
    }

    if (response.status === 404) {
      throw new Error('Resource not found');
    }

    if (response.status === 400) {
      const error = await response.json();
      throw new ValidationError(error);
    }

    if (response.status >= 500) {
      throw new Error('Server error - please try again later');
    }

    throw new Error(`Request failed: ${response.statusText}`);
  }
}
```

### Error Handling Middleware

```typescript
// api/errors.ts
export class ValidationError extends Error {
  constructor(public errors: Record<string, string[]>) {
    super('Validation failed');
    this.name = 'ValidationError';
  }
}

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

// Error handler utility
export function handleAPIError(error: unknown): string {
  if (error instanceof ValidationError) {
    // Return first error message
    const firstError = Object.values(error.errors)[0];
    return Array.isArray(firstError) ? firstError[0] : firstError;
  }

  if (error instanceof APIError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'An unexpected error occurred';
}
```

---

## 3. State Management

### Data Fetching Patterns

#### React Query Setup
```typescript
// lib/queryClient.ts
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});
```

#### Custom Query Hook Pattern
```typescript
// hooks/useData.ts
export function useData<T>(
  queryKey: string[],
  queryFn: () => Promise<T>,
  options?: {
    enabled?: boolean;
    staleTime?: number;
  }
) {
  return useQuery({
    queryKey,
    queryFn,
    enabled: options?.enabled ?? true,
    staleTime: options?.staleTime,
  });
}
```

### Caching Strategies

#### Cache Invalidation
```typescript
// hooks/useMutationWithInvalidation.ts
export function useMutationWithInvalidation<TData, TVariables>(
  mutationFn: (variables: TVariables) => Promise<TData>,
  invalidateQueries: string[][]
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    onSuccess: () => {
      invalidateQueries.forEach(queryKey => {
        queryClient.invalidateQueries({ queryKey });
      });
    },
  });
}

// Usage
const createWarehouse = useMutationWithInvalidation(
  (data: WarehouseCreate) => createWarehouseAPI(data),
  [['warehouses']]
);
```

#### Optimistic Updates
```typescript
// hooks/useOptimisticUpdate.ts
export function useOptimisticUpdate<TData, TVariables>(
  queryKey: string[],
  mutationFn: (variables: TVariables) => Promise<TData>,
  updateFn: (old: TData, variables: TVariables) => TData
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    onMutate: async (variables) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey });

      // Snapshot previous value
      const previous = queryClient.getQueryData<TData>(queryKey);

      // Optimistically update
      queryClient.setQueryData<TData>(queryKey, (old) => {
        if (!old) return old;
        return updateFn(old, variables);
      });

      return { previous };
    },
    onError: (err, variables, context) => {
      // Rollback on error
      if (context?.previous) {
        queryClient.setQueryData(queryKey, context.previous);
      }
    },
    onSettled: () => {
      // Always refetch after error or success
      queryClient.invalidateQueries({ queryKey });
    },
  });
}
```

### Error State Management

```typescript
// hooks/useErrorState.ts
export function useErrorState() {
  const [error, setError] = useState<string | null>(null);

  const handleError = useCallback((err: unknown) => {
    const message = handleAPIError(err);
    setError(message);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return { error, handleError, clearError };
}
```

---

## 4. Form Handling

### Validation Patterns

#### Form Validation Hook
```typescript
// hooks/useFormValidation.ts
export function useFormValidation<T extends Record<string, any>>(
  initialValues: T,
  validationRules: Record<keyof T, (value: any) => string | null>
) {
  const [values, setValues] = useState<T>(initialValues);
  const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({});
  const [touched, setTouched] = useState<Partial<Record<keyof T, boolean>>>({});

  const validate = useCallback((field?: keyof T) => {
    const newErrors: Partial<Record<keyof T, string>> = {};

    if (field) {
      const rule = validationRules[field];
      if (rule) {
        const error = rule(values[field]);
        if (error) {
          newErrors[field] = error;
        }
      }
    } else {
      // Validate all fields
      Object.keys(validationRules).forEach((key) => {
        const rule = validationRules[key as keyof T];
        const error = rule(values[key as keyof T]);
        if (error) {
          newErrors[key as keyof T] = error;
        }
      });
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [values, validationRules]);

  const setValue = useCallback((field: keyof T, value: any) => {
    setValues(prev => ({ ...prev, [field]: value }));
    setTouched(prev => ({ ...prev, [field]: true }));
    // Clear error for this field
    setErrors(prev => {
      const next = { ...prev };
      delete next[field];
      return next;
    });
  }, []);

  const setFieldTouched = useCallback((field: keyof T) => {
    setTouched(prev => ({ ...prev, [field]: true }));
    validate(field);
  }, [validate]);

  return {
    values,
    errors,
    touched,
    setValue,
    setFieldTouched,
    validate,
    isValid: Object.keys(errors).length === 0,
  };
}
```

#### Real-time Validation
```typescript
// components/ValidatedInput.tsx
function ValidatedInput<T extends Record<string, any>>({
  form,
  field,
  label,
  type = 'text',
  ...props
}: {
  form: ReturnType<typeof useFormValidation<T>>;
  field: keyof T;
  label: string;
  type?: string;
}) {
  const error = form.errors[field];
  const touched = form.touched[field];

  return (
    <div>
      <label>{label}</label>
      <input
        type={type}
        value={form.values[field]}
        onChange={(e) => form.setValue(field, e.target.value)}
        onBlur={() => form.setFieldTouched(field)}
        {...props}
      />
      {touched && error && <span className="error">{error}</span>}
    </div>
  );
}
```

### Form State Management

```typescript
// hooks/useForm.ts
export function useForm<T extends Record<string, any>>(
  initialValues: T,
  onSubmit: (values: T) => Promise<void>
) {
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const validation = useFormValidation(initialValues, {});

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    if (!validation.validate()) {
      return;
    }

    setSubmitting(true);
    try {
      await onSubmit(validation.values);
    } catch (error) {
      setSubmitError(handleAPIError(error));
    } finally {
      setSubmitting(false);
    }
  };

  return {
    ...validation,
    submitting,
    submitError,
    handleSubmit,
  };
}
```

### Submission Handling

```typescript
// components/Form.tsx
function Form<T extends Record<string, any>>({
  initialValues,
  onSubmit,
  children,
  validationRules,
}: FormProps<T>) {
  const validation = useFormValidation(initialValues, validationRules);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validation.validate()) {
      return;
    }

    setSubmitting(true);
    try {
      await onSubmit(validation.values);
    } catch (error) {
      // Handle error
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {children(validation, submitting)}
    </form>
  );
}
```

---

## 5. Loading States

### Skeleton Loaders

```typescript
// components/Skeletons.tsx
export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="skeleton-table">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton-row">
          {Array.from({ length: cols }).map((_, j) => (
            <div key={j} className="skeleton-cell" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function CardSkeleton() {
  return (
    <div className="skeleton-card">
      <div className="skeleton-title" />
      <div className="skeleton-content" />
      <div className="skeleton-content" />
    </div>
  );
}
```

### Spinner Patterns

```typescript
// components/LoadingSpinner.tsx
export function LoadingSpinner({ size = 'medium' }: { size?: 'small' | 'medium' | 'large' }) {
  return (
    <div className={`spinner spinner-${size}`}>
      <div className="spinner-circle" />
    </div>
  );
}

export function ButtonSpinner() {
  return <div className="button-spinner" />;
}
```

### Progressive Loading

```typescript
// hooks/useProgressiveLoad.ts
export function useProgressiveLoad<T>(
  queryKey: string[],
  queryFn: () => Promise<T>,
  placeholder: T
) {
  const { data, isLoading } = useQuery({
    queryKey,
    queryFn,
    placeholderData: placeholder,
  });

  return {
    data: data ?? placeholder,
    isLoading,
    isPlaceholder: data === placeholder,
  };
}
```

---

## 6. Error Handling

### Error Types

```typescript
// types/errors.ts
export interface APIErrorResponse {
  detail?: string;
  [key: string]: string[] | string | undefined;
}

export class ValidationError extends Error {
  constructor(public errors: Record<string, string[]>) {
    super('Validation failed');
    this.name = 'ValidationError';
  }
}

export class NotFoundError extends Error {
  constructor(public resource: string) {
    super(`${resource} not found`);
    this.name = 'NotFoundError';
  }
}

export class UnauthorizedError extends Error {
  constructor() {
    super('Unauthorized');
    this.name = 'UnauthorizedError';
  }
}
```

### User-Friendly Messages

```typescript
// utils/errorMessages.ts
export function getUserFriendlyError(error: unknown): string {
  if (error instanceof ValidationError) {
    const firstError = Object.values(error.errors)[0];
    return Array.isArray(firstError) ? firstError[0] : firstError;
  }

  if (error instanceof NotFoundError) {
    return `The ${error.resource} you're looking for doesn't exist.`;
  }

  if (error instanceof UnauthorizedError) {
    return 'You need to log in to perform this action.';
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'Something went wrong. Please try again.';
}
```

### Retry Mechanisms

```typescript
// hooks/useRetry.ts
export function useRetry<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  delay: number = 1000
) {
  const [retryCount, setRetryCount] = useState(0);
  const [error, setError] = useState<Error | null>(null);

  const execute = useCallback(async (): Promise<T> => {
    try {
      setError(null);
      const result = await fn();
      setRetryCount(0);
      return result;
    } catch (err) {
      if (retryCount < maxRetries) {
        setRetryCount(prev => prev + 1);
        await new Promise(resolve => setTimeout(resolve, delay * retryCount));
        return execute();
      }
      setError(err instanceof Error ? err : new Error('Unknown error'));
      throw err;
    }
  }, [fn, maxRetries, delay, retryCount]);

  return { execute, retryCount, error };
}
```

### Offline Handling

```typescript
// hooks/useOffline.ts
export function useOffline() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return isOnline;
}

// Usage
function App() {
  const isOnline = useOffline();

  if (!isOnline) {
    return <OfflineBanner />;
  }

  return <MainApp />;
}
```

---

## 7. Pagination

### Infinite Scroll

```typescript
// hooks/useInfiniteScroll.ts
export function useInfiniteScroll<T>(
  queryKey: string[],
  queryFn: (page: number) => Promise<PaginatedResponse<T>>
) {
  return useInfiniteQuery({
    queryKey,
    queryFn: ({ pageParam = 1 }) => queryFn(pageParam),
    getNextPageParam: (lastPage) => {
      if (lastPage.next) {
        const url = new URL(lastPage.next);
        return parseInt(url.searchParams.get('page') || '1');
      }
      return undefined;
    },
  });
}

// Usage
function InfiniteList() {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteScroll(
    ['items'],
    (page) => getItems({ page })
  );

  const items = data?.pages.flatMap(page => page.results) ?? [];

  return (
    <div>
      {items.map(item => <ItemCard key={item.id} item={item} />)}
      {hasNextPage && (
        <button onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
          {isFetchingNextPage ? 'Loading...' : 'Load More'}
        </button>
      )}
    </div>
  );
}
```

### Page-Based Pagination

```typescript
// components/Pagination.tsx
function Pagination({
  currentPage,
  totalCount,
  pageSize,
  onPageChange,
}: {
  currentPage: number;
  totalCount: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}) {
  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="pagination">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
      >
        Previous
      </button>
      <span>
        Page {currentPage} of {totalPages}
      </span>
      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
      >
        Next
      </button>
    </div>
  );
}
```

### URL State Management

```typescript
// hooks/usePaginationFromURL.ts
export function usePaginationFromURL(defaultPage: number = 1) {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseInt(searchParams.get('page') || defaultPage.toString());

  const setPage = useCallback((newPage: number) => {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev);
      next.set('page', newPage.toString());
      return next;
    });
  }, [setSearchParams]);

  return { page, setPage };
}
```

---

## 8. Search & Filtering

### Debounced Search

```typescript
// hooks/useDebounce.ts
export function useDebounce<T>(value: T, delay: number): T {
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

// Usage
function SearchInput({ onSearch }: { onSearch: (query: string) => void }) {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 500);

  useEffect(() => {
    onSearch(debouncedQuery);
  }, [debouncedQuery, onSearch]);
}
```

### Filter State Management

```typescript
// hooks/useFilters.ts
export function useFilters<T extends Record<string, any>>(
  initialFilters: T
) {
  const [filters, setFilters] = useState<T>(initialFilters);

  const updateFilter = useCallback(<K extends keyof T>(
    key: K,
    value: T[K]
  ) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  }, []);

  const clearFilters = useCallback(() => {
    setFilters(initialFilters);
  }, [initialFilters]);

  return { filters, updateFilter, clearFilters };
}
```

### URL Query Params

```typescript
// hooks/useFiltersFromURL.ts
export function useFiltersFromURL<T extends Record<string, any>>(
  defaultFilters: T
) {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo(() => {
    const result = { ...defaultFilters };
    Object.keys(defaultFilters).forEach(key => {
      const value = searchParams.get(key);
      if (value !== null) {
        result[key as keyof T] = value as T[keyof T];
      }
    });
    return result;
  }, [searchParams, defaultFilters]);

  const updateFilters = useCallback((newFilters: Partial<T>) => {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev);
      Object.entries(newFilters).forEach(([key, value]) => {
        if (value === null || value === undefined || value === '') {
          next.delete(key);
        } else {
          next.set(key, String(value));
        }
      });
      return next;
    });
  }, [setSearchParams]);

  return { filters, updateFilters };
}
```

### Filter Persistence

```typescript
// hooks/usePersistedFilters.ts
export function usePersistedFilters<T extends Record<string, any>>(
  key: string,
  defaultFilters: T
) {
  const [filters, setFilters] = useState<T>(() => {
    const stored = localStorage.getItem(key);
    if (stored) {
      try {
        return { ...defaultFilters, ...JSON.parse(stored) };
      } catch {
        return defaultFilters;
      }
    }
    return defaultFilters;
  });

  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(filters));
  }, [key, filters]);

  return { filters, setFilters };
}
```

---

## 9. TypeScript Types

### API Response Types

```typescript
// types/api.ts
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface APIErrorResponse {
  detail?: string;
  [key: string]: string[] | string | undefined;
}
```

### Request Types

```typescript
// types/requests.ts
export interface CreateRequest<T> {
  [K in keyof T]?: T[K];
}

export interface UpdateRequest<T> {
  [K in keyof T]?: T[K];
}

export interface ListRequest {
  page?: number;
  page_size?: number;
  search?: string;
  [key: string]: any;
}
```

### Shared Interfaces

```typescript
// types/common.ts
export interface Timestamped {
  created_at: string;
  updated_at: string;
}

export interface CompanyScoped {
  company_id: number;
}

export interface SoftDeletable {
  is_active: boolean;
}
```

---

## 10. Testing Patterns

### API Mocking

```typescript
// __mocks__/api.ts
export const mockWarehouses: Warehouse[] = [
  {
    id: 1,
    code: 'WH-001',
    name: 'Main Warehouse',
    // ... other fields
  },
];

export const mockGetWarehouses = jest.fn(() =>
  Promise.resolve({
    count: mockWarehouses.length,
    next: null,
    previous: null,
    results: mockWarehouses,
  })
);
```

### Component Testing

```typescript
// __tests__/WarehouseList.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import WarehouseList from '../WarehouseList';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

test('renders warehouse list', async () => {
  render(
    <QueryClientProvider client={queryClient}>
      <WarehouseList />
    </QueryClientProvider>
  );

  await waitFor(() => {
    expect(screen.getByText('Main Warehouse')).toBeInTheDocument();
  });
});
```

### Integration Testing

```typescript
// __tests__/integration/warehouseFlow.test.tsx
test('complete warehouse creation flow', async () => {
  const { getByLabelText, getByText } = render(<CreateWarehouseForm />);

  // Fill form
  fireEvent.change(getByLabelText('Code'), { target: { value: 'WH-002' } });
  fireEvent.change(getByLabelText('Name'), { target: { value: 'New Warehouse' } });

  // Submit
  fireEvent.click(getByText('Create Warehouse'));

  // Wait for success
  await waitFor(() => {
    expect(screen.getByText('Warehouse created successfully')).toBeInTheDocument();
  });
});
```

---

## Summary

This guide provides reusable patterns for:
- Authentication and token management
- API client setup with interceptors
- State management with React Query
- Form handling and validation
- Loading and error states
- Pagination and filtering
- TypeScript type definitions
- Testing utilities

These patterns should be implemented once and reused across all features to ensure consistency and maintainability.

