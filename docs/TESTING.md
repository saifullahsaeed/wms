# Testing Guide for WMS

This document outlines the testing strategy and guidelines for the Warehouse Management System.

## Testing Framework

We use **pytest** with **pytest-django** for testing. This provides:
- Better test discovery
- Fixtures for test data
- Coverage reporting
- More readable test output

## Running Tests

### Run all tests
```bash
cd wms
pytest
```

### Run tests for a specific app
```bash
pytest accounts/tests.py
pytest inventory/tests.py
pytest operations/tests.py
```

### Run with coverage report
```bash
pytest --cov=accounts --cov=masterdata --cov=inventory --cov=operations --cov-report=html
```

Coverage HTML report will be generated in `htmlcov/index.html`

### Run specific test
```bash
pytest accounts/tests.py::TestAccountsServices::test_can_user_access_warehouse
```

### Run with verbose output
```bash
pytest -v
```

## Test Structure

### Test Organization

Tests are organized by app in `tests.py` files:
- `accounts/tests.py` - User, company, role, and permission tests
- `inventory/tests.py` - Inventory operations, stock management tests
- `operations/tests.py` - Warehouse operations, tasks, workflows tests
- `masterdata/tests.py` - (To be implemented) Product, location, warehouse structure tests

### Shared Fixtures

Common test fixtures are defined in `wms/conftest.py`:
- `company`, `company2` - Test companies
- `user`, `admin_user` - Test users
- `warehouse`, `warehouse2` - Test warehouses
- `location`, `staging_location` - Test locations
- `product`, `product2` - Test products
- `role`, `role_with_permissions` - Test roles
- `inventory_item` - Test inventory items
- `inbound_order`, `outbound_order` - Test orders
- And more...

### Test Classes

Tests are organized into classes by functionality:
- `TestCompanyModel` - Company model tests
- `TestUserModel` - User model tests
- `TestRoleModel` - Role model tests
- `TestAccountsServices` - Service function tests
- `TestInventoryServices` - Inventory service tests
- `TestOperationsServices` - Operations service tests

## Writing Tests

### Basic Test Structure

```python
class TestMyFeature:
    """Test description."""
    
    def test_specific_behavior(self, fixture1, fixture2):
        """Test that specific behavior works correctly."""
        # Arrange
        obj = MyModel.objects.create(...)
        
        # Act
        result = my_function(obj)
        
        # Assert
        assert result == expected_value
```

### Using Fixtures

Fixtures are automatically injected as function parameters:

```python
def test_with_company_and_user(self, company, user):
    """Test using company and user fixtures."""
    assert user.company == company
```

### Testing Services

Service functions should be tested thoroughly:

```python
def test_service_function(self, company, warehouse, product):
    """Test service function behavior."""
    result = my_service_function(
        company=company,
        warehouse=warehouse,
        product=product,
    )
    assert result is not None
```

### Testing Signals

Signals are tested by triggering the action that fires them:

```python
def test_signal_fires_on_save(self, company, warehouse, location, product):
    """Test that signal updates inventory."""
    # Create object that triggers signal
    adjustment = StockAdjustment.objects.create(...)
    
    # Check side effects
    item = InventoryItem.objects.get(...)
    assert item.quantity == expected_value
```

### Testing Permissions

Permission checks should test:
- Superuser access (always allowed)
- User with permission (allowed)
- User without permission (denied)
- User from different company (denied)

```python
def test_permission_check(self, user, warehouse, role):
    """Test permission checking."""
    # User without assignment
    assert can_user_access_warehouse(user, warehouse) is False
    
    # Assign user
    UserWarehouse.objects.create(...)
    
    # User with assignment
    assert can_user_access_warehouse(user, warehouse) is True
```

## Test Coverage Goals

- **Critical Services**: 90%+ coverage
  - `accounts/services.py` - Permission and access control
  - `inventory/services.py` - Stock operations
  - `operations/services.py` - Task management

- **Models**: 80%+ coverage
  - Core business logic
  - Property methods
  - Custom methods

- **Signals**: 100% coverage
  - All signal handlers must be tested
  - Test side effects (inventory updates, movements)

## Best Practices

1. **Test Isolation**: Each test should be independent and not rely on other tests
2. **Use Fixtures**: Reuse fixtures from `conftest.py` instead of creating test data in each test
3. **Clear Names**: Test names should clearly describe what they test
4. **Arrange-Act-Assert**: Structure tests with clear sections
5. **Test Edge Cases**: Test boundary conditions, empty inputs, None values
6. **Test Failures**: Test that functions fail correctly (raise exceptions, return False, etc.)
7. **Fast Tests**: Keep tests fast - use `--nomigrations` flag (already configured)

## Continuous Integration

Tests should be run:
- Before committing code
- In CI/CD pipeline
- Before merging pull requests

## Common Issues

### Database Issues
- Use `@pytest.fixture` with `db` parameter for database access
- Tests use a separate test database (automatically created by pytest-django)

### Migration Issues
- Tests run with `--nomigrations` flag to speed up execution
- If you need migrations, remove the flag temporarily

### Import Errors
- Make sure all imports use relative paths or full app paths
- Check that `INSTALLED_APPS` includes all your apps

## Future Improvements

- [ ] Add integration tests for full workflows
- [ ] Add performance tests for critical operations
- [ ] Add API tests (when DRF is implemented)
- [ ] Add frontend tests (when frontend is implemented)
- [ ] Set up CI/CD with automated test running

