"""
URL configuration for accounts app - authentication endpoints.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CompanyOnboardingView,
    CompanyView,
    LoginView,
    RegisterView,
    UserMeView,
    UserProfileView,
    TeamListView,
    TeamMemberDetailView,
    assign_user_to_warehouse_view,
    remove_user_from_warehouse_view,
    change_password,
    logout,
    onboarding_status,
    user_permissions,
)

app_name = "accounts"

urlpatterns = [
    # Authentication endpoints
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/logout/", logout, name="logout"),
    # User endpoints
    path("auth/me/", UserMeView.as_view(), name="me"),
    path("auth/profile/", UserProfileView.as_view(), name="profile"),
    path("auth/change-password/", change_password, name="change_password"),
    path("auth/permissions/", user_permissions, name="user_permissions"),
    # Company endpoints
    path("company/", CompanyView.as_view(), name="company"),
    # Team management endpoints
    path("team/", TeamListView.as_view(), name="team-list"),
    path("team/<int:pk>/", TeamMemberDetailView.as_view(), name="team-member-detail"),
    # Warehouse user assignment endpoints (only owners)
    path(
        "warehouses/<int:warehouse_id>/assign-user/",
        assign_user_to_warehouse_view,
        name="assign-user-to-warehouse",
    ),
    path(
        "warehouses/<int:warehouse_id>/users/<int:user_id>/",
        remove_user_from_warehouse_view,
        name="remove-user-from-warehouse",
    ),
    # Company onboarding endpoints
    path("onboarding/", CompanyOnboardingView.as_view(), name="onboarding"),
    path("onboarding/status/", onboarding_status, name="onboarding_status"),
]
