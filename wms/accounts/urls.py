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
    change_password,
    logout,
    onboarding_status,
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
    # Company endpoints
    path("company/", CompanyView.as_view(), name="company"),
    # Team management endpoints
    path("team/", TeamListView.as_view(), name="team-list"),
    # Company onboarding endpoints
    path("onboarding/", CompanyOnboardingView.as_view(), name="onboarding"),
    path("onboarding/status/", onboarding_status, name="onboarding_status"),
]
