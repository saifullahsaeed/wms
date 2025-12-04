"""
Tests for authentication API endpoints.
"""

import pytest
from accounts.models import User


class TestAuthenticationAPI:
    """Test authentication API endpoints."""

    def test_login_success(self, client, company):
        """Test successful login returns tokens and user data."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            company=company,
        )

        response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": "test@example.com", "password": "testpass123"},
            content_type="application/json",
        )

        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data
        assert "user" in response.data
        assert response.data["user"]["username"] == "testuser"
        assert response.data["user"]["company_id"] == company.id

    def test_login_invalid_credentials(self, client, company):
        """Test login with invalid credentials fails."""
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            company=company,
        )

        response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": "test@example.com", "password": "wrongpass"},
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "invalid_credentials" in str(response.data)

    def test_login_inactive_user(self, client, company):
        """Test login with inactive user fails."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            company=company,
            is_active=False,
        )

        response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": "test@example.com", "password": "testpass123"},
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "user_inactive" in str(response.data)

    def test_login_user_without_company(self, client, db):
        """Test login with user without company fails."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            company=None,
        )

        response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": "test@example.com", "password": "testpass123"},
            content_type="application/json",
        )

        # Serializer validation returns 400 (validation error) not 401 (auth error)
        assert response.status_code == 400
        assert "no_company" in str(response.data)

    def test_register_success(self, client, db):
        """Test successful company and user registration."""
        response = client.post(
            "/api/v1/accounts/auth/register/",
            {
                "company_name": "New Company Inc",
                "company_email": "info@newcompany.com",
                "company_phone": "1234567890",
                "username": "owner",
                "email": "owner@newcompany.com",
                "password": "securepass123",
                "password_confirm": "securepass123",
                "first_name": "John",
                "last_name": "Doe",
            },
            content_type="application/json",
        )

        assert response.status_code == 201
        assert "user" in response.data
        assert "company" in response.data
        assert "tokens" in response.data
        assert response.data["user"]["username"] == "owner"
        assert response.data["company"]["name"] == "New Company Inc"

        # Verify company was created
        from accounts.models import Company

        company = Company.objects.get(name="New Company Inc")
        assert company is not None

        # Verify user was created and is staff (company owner)
        user = User.objects.get(username="owner")
        assert user.company == company
        assert user.is_staff is True  # First user is company admin

    def test_register_password_mismatch(self, client, db):
        """Test registration with mismatched passwords fails."""
        response = client.post(
            "/api/v1/accounts/auth/register/",
            {
                "company_name": "Test Company",
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "securepass123",
                "password_confirm": "differentpass",
            },
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "password_confirm" in response.data

    def test_register_duplicate_company_name(self, client, db, company):
        """Test registration with duplicate company name fails."""
        response = client.post(
            "/api/v1/accounts/auth/register/",
            {
                "company_name": company.name,  # Use existing company name
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "securepass123",
                "password_confirm": "securepass123",
            },
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "company_name" in response.data

    def test_token_refresh(self, client, company):
        """Test refreshing access token."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            company=company,
        )

        # First, login to get tokens
        login_response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": "test@example.com", "password": "testpass123"},
            content_type="application/json",
        )
        refresh_token = login_response.data["refresh"]

        # Refresh the token
        response = client.post(
            "/api/v1/accounts/auth/refresh/",
            {"refresh": refresh_token},
            content_type="application/json",
        )

        assert response.status_code == 200
        assert "access" in response.data

    def test_get_profile_authenticated(self, client, company, user):
        """Test getting user profile when authenticated."""
        # Login first
        user.set_password("testpass123")
        user.save()
        login_response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": user.email, "password": "testpass123"},
            content_type="application/json",
        )
        access_token = login_response.data["access"]

        # Get profile
        response = client.get(
            "/api/v1/accounts/auth/profile/",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        assert response.status_code == 200
        assert response.data["username"] == user.username
        assert response.data["company_id"] == company.id

    def test_get_profile_unauthenticated(self, client):
        """Test getting profile without authentication fails."""
        response = client.get("/api/v1/accounts/auth/profile/")

        assert response.status_code == 401

    def test_update_profile(self, client, company, user):
        """Test updating user profile."""
        user.set_password("testpass123")
        user.save()
        login_response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": user.email, "password": "testpass123"},
            content_type="application/json",
        )
        access_token = login_response.data["access"]

        # Update profile
        response = client.patch(
            "/api/v1/accounts/auth/profile/",
            {
                "first_name": "Updated",
                "last_name": "Name",
                "phone": "1234567890",
            },
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.data["first_name"] == "Updated"
        assert response.data["last_name"] == "Name"
        assert response.data["phone"] == "1234567890"

        # Verify in database
        user.refresh_from_db()
        assert user.first_name == "Updated"
        assert user.last_name == "Name"

    def test_change_password_success(self, client, company, user):
        """Test successful password change."""
        user.set_password("oldpass123")
        user.save()
        login_response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": user.email, "password": "oldpass123"},
            content_type="application/json",
        )
        access_token = login_response.data["access"]

        # Change password
        response = client.post(
            "/api/v1/accounts/auth/change-password/",
            {
                "old_password": "oldpass123",
                "new_password": "newpass123",
                "new_password_confirm": "newpass123",
            },
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
            content_type="application/json",
        )

        assert response.status_code == 200
        assert "message" in response.data

        # Verify password changed
        user.refresh_from_db()
        assert user.check_password("newpass123")

    def test_change_password_wrong_old_password(self, client, company, user):
        """Test password change with wrong old password fails."""
        user.set_password("oldpass123")
        user.save()
        login_response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": user.email, "password": "oldpass123"},
            content_type="application/json",
        )
        access_token = login_response.data["access"]

        response = client.post(
            "/api/v1/accounts/auth/change-password/",
            {
                "old_password": "wrongpass",
                "new_password": "newpass123",
                "new_password_confirm": "newpass123",
            },
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "old_password" in response.data

    def test_change_password_mismatch(self, client, company, user):
        """Test password change with mismatched new passwords fails."""
        user.set_password("oldpass123")
        user.save()
        login_response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": user.email, "password": "oldpass123"},
            content_type="application/json",
        )
        access_token = login_response.data["access"]

        response = client.post(
            "/api/v1/accounts/auth/change-password/",
            {
                "old_password": "oldpass123",
                "new_password": "newpass123",
                "new_password_confirm": "differentpass",
            },
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "new_password_confirm" in response.data

    def test_logout_success(self, client, company, user):
        """Test successful logout blacklists token."""
        user.set_password("testpass123")
        user.save()
        login_response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": user.email, "password": "testpass123"},
            content_type="application/json",
        )
        refresh_token = login_response.data["refresh"]

        # Logout
        response = client.post(
            "/api/v1/accounts/auth/logout/",
            {"refresh": refresh_token},
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}",
            content_type="application/json",
        )

        assert response.status_code == 200
        assert "message" in response.data

        # Try to refresh with blacklisted token (should fail)
        refresh_response = client.post(
            "/api/v1/accounts/auth/refresh/",
            {"refresh": refresh_token},
            content_type="application/json",
        )
        assert refresh_response.status_code == 401

    def test_logout_missing_token(self, client, company, user):
        """Test logout without refresh token fails."""
        user.set_password("testpass123")
        user.save()
        login_response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": user.email, "password": "testpass123"},
            content_type="application/json",
        )
        access_token = login_response.data["access"]

        response = client.post(
            "/api/v1/accounts/auth/logout/",
            {},
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "error" in response.data

    def test_get_current_user_me(self, client, company, user):
        """Test GET /auth/me/ returns current user basic info."""
        user.set_password("testpass123")
        user.save()
        login_response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": user.email, "password": "testpass123"},
            content_type="application/json",
        )
        access_token = login_response.data["access"]

        response = client.get(
            "/api/v1/accounts/auth/me/",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        assert response.status_code == 200
        assert response.data["id"] == user.id
        assert response.data["username"] == user.username
        assert response.data["email"] == user.email
        assert response.data["company_id"] == company.id
        assert response.data["company_name"] == company.name
        assert "warehouses" in response.data
        assert "is_staff" in response.data
        assert "is_warehouse_operator" in response.data

    def test_get_current_user_me_unauthenticated(self, client):
        """Test GET /auth/me/ without authentication fails."""
        response = client.get("/api/v1/accounts/auth/me/")

        assert response.status_code == 401
