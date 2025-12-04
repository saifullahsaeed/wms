"""
Tests for onboarding API endpoint.
"""

import pytest
from accounts.models import Company, User


class TestOnboardingAPI:
    """Test onboarding API endpoints."""

    def test_onboarding_success_minimal(self, client, company, user):
        """Test onboarding with minimal required fields."""
        user.set_password("testpass123")
        user.save()
        login_response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": user.email, "password": "testpass123"},
            content_type="application/json",
        )
        access_token = login_response.data["access"]

        # Onboard with minimal required fields
        response = client.patch(
            "/api/v1/accounts/onboarding/",
            {
                "email": "company@example.com",
                "country": "United States",
            },
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
            content_type="application/json",
        )

        assert response.status_code == 200
        assert "company" in response.data
        assert response.data["company"]["email"] == "company@example.com"
        assert response.data["company"]["country"] == "United States"

        # Verify in database
        company.refresh_from_db()
        assert company.email == "company@example.com"
        assert company.country == "United States"

    def test_onboarding_success_full(self, client, company, user):
        """Test onboarding with all optional fields."""
        user.set_password("testpass123")
        user.save()
        login_response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": user.email, "password": "testpass123"},
            content_type="application/json",
        )
        access_token = login_response.data["access"]

        # Onboard with all fields
        response = client.patch(
            "/api/v1/accounts/onboarding/",
            {
                "email": "info@company.com",
                "country": "USA",
                "legal_name": "Company Inc LLC",
                "phone": "1234567890",
                "website": "https://company.com",
                "address_line1": "123 Main St",
                "city": "New York",
                "state": "NY",
                "postal_code": "10001",
                "tax_id": "TAX123",
                "registration_number": "REG456",
            },
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.data["company"]["email"] == "info@company.com"
        assert response.data["company"]["legal_name"] == "Company Inc LLC"
        assert response.data["company"]["phone"] == "1234567890"

        # Verify in database
        company.refresh_from_db()
        assert company.email == "info@company.com"
        assert company.legal_name == "Company Inc LLC"
        assert company.phone == "1234567890"
        assert company.country == "USA"

    def test_onboarding_missing_required_email(self, client, company, user):
        """Test onboarding without required email fails."""
        # Clear email to simulate first-time onboarding
        company.email = ""
        company.country = ""
        company.save()

        user.set_password("testpass123")
        user.save()
        login_response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": user.email, "password": "testpass123"},
            content_type="application/json",
        )
        access_token = login_response.data["access"]

        response = client.patch(
            "/api/v1/accounts/onboarding/",
            {
                "country": "United States",
                # Missing email
            },
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "email" in response.data

    def test_onboarding_missing_required_country(self, client, company, user):
        """Test onboarding without required country fails."""
        user.set_password("testpass123")
        user.save()
        login_response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": user.email, "password": "testpass123"},
            content_type="application/json",
        )
        access_token = login_response.data["access"]

        response = client.patch(
            "/api/v1/accounts/onboarding/",
            {
                "email": "company@example.com",
                # Missing country
            },
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "country" in response.data

    def test_onboarding_invalid_email(self, client, company, user):
        """Test onboarding with invalid email fails."""
        user.set_password("testpass123")
        user.save()
        login_response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": user.email, "password": "testpass123"},
            content_type="application/json",
        )
        access_token = login_response.data["access"]

        response = client.patch(
            "/api/v1/accounts/onboarding/",
            {
                "email": "invalid-email",
                "country": "United States",
            },
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "email" in response.data

    def test_onboarding_unauthenticated(self, client, company):
        """Test onboarding without authentication fails."""
        response = client.patch(
            "/api/v1/accounts/onboarding/",
            {
                "email": "company@example.com",
                "country": "United States",
            },
            content_type="application/json",
        )

        assert response.status_code == 401

    def test_onboarding_user_without_company(self, client, db):
        """Test onboarding for user without company fails."""
        user = User.objects.create_user(
            username="nocompany",
            email="nocompany@example.com",
            password="testpass123",
            company=None,
        )

        login_response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": "nocompany@example.com", "password": "testpass123"},
            content_type="application/json",
        )

        # User without company can't login (validation fails)
        assert login_response.status_code in [400, 401]

    def test_onboarding_partial_update(self, client, company, user):
        """Test onboarding allows partial updates after initial onboarding."""
        # Set initial values (company already has email and country)
        company.email = "old@example.com"
        company.country = "Canada"
        company.save()

        user.set_password("testpass123")
        user.save()
        login_response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": user.email, "password": "testpass123"},
            content_type="application/json",
        )
        access_token = login_response.data["access"]

        # Update only email (should work since country is already set)
        response = client.patch(
            "/api/v1/accounts/onboarding/",
            {
                "email": "new@example.com",
            },
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
            content_type="application/json",
        )

        assert response.status_code == 200
        company.refresh_from_db()
        assert company.email == "new@example.com"
        assert company.country == "Canada"  # Unchanged

        # Update country too
        response = client.patch(
            "/api/v1/accounts/onboarding/",
            {
                "country": "USA",
            },
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
            content_type="application/json",
        )

        assert response.status_code == 200
        company.refresh_from_db()
        assert company.country == "USA"

    def test_onboarding_optional_fields_can_be_empty(self, client, company, user):
        """Test that optional fields can be left empty."""
        user.set_password("testpass123")
        user.save()
        login_response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": user.email, "password": "testpass123"},
            content_type="application/json",
        )
        access_token = login_response.data["access"]

        response = client.patch(
            "/api/v1/accounts/onboarding/",
            {
                "email": "company@example.com",
                "country": "United States",
                "phone": "",  # Empty optional field
                "legal_name": "",  # Empty optional field
            },
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
            content_type="application/json",
        )

        assert response.status_code == 200
        company.refresh_from_db()
        assert company.email == "company@example.com"
        assert company.country == "United States"
        assert company.phone == ""
        assert company.legal_name == ""

    def test_onboarding_status_complete(self, client, company, user, warehouse):
        """Test onboarding status when company info and warehouse are complete."""
        user.set_password("testpass123")
        user.save()
        # Ensure company has required fields
        company.email = "company@example.com"
        company.country = "United States"
        company.save()

        login_response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": user.email, "password": "testpass123"},
            content_type="application/json",
        )
        access_token = login_response.data["access"]

        response = client.get(
            "/api/v1/accounts/onboarding/status/",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        assert response.status_code == 200
        assert response.data["is_complete"] is True
        assert response.data["company_info_complete"] is True
        assert response.data["has_warehouse"] is True
        assert response.data["warehouse_count"] == 1
        assert response.data["missing_fields"] == []

    def test_onboarding_status_incomplete_company_info(
        self, client, company, user, warehouse
    ):
        """Test onboarding status when company info is incomplete."""
        user.set_password("testpass123")
        user.save()
        # Clear required fields
        company.email = ""
        company.country = ""
        company.save()

        login_response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": user.email, "password": "testpass123"},
            content_type="application/json",
        )
        access_token = login_response.data["access"]

        response = client.get(
            "/api/v1/accounts/onboarding/status/",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        assert response.status_code == 200
        assert response.data["is_complete"] is False
        assert response.data["company_info_complete"] is False
        assert response.data["has_warehouse"] is True
        assert "email" in response.data["missing_fields"]
        assert "country" in response.data["missing_fields"]

    def test_onboarding_status_no_warehouse(self, client, company, user):
        """Test onboarding status when no warehouse exists."""
        user.set_password("testpass123")
        user.save()
        # Ensure company has required fields
        company.email = "company@example.com"
        company.country = "United States"
        company.save()

        login_response = client.post(
            "/api/v1/accounts/auth/login/",
            {"email": user.email, "password": "testpass123"},
            content_type="application/json",
        )
        access_token = login_response.data["access"]

        response = client.get(
            "/api/v1/accounts/onboarding/status/",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        assert response.status_code == 200
        assert response.data["is_complete"] is False
        assert response.data["company_info_complete"] is True
        assert response.data["has_warehouse"] is False
        assert response.data["warehouse_count"] == 0

    def test_onboarding_status_unauthenticated(self, client):
        """Test onboarding status without authentication fails."""
        response = client.get("/api/v1/accounts/onboarding/status/")

        assert response.status_code == 401
