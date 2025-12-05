"""
API views for accounts app - authentication and user management.
"""

from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.db.models import Q, Value as V, CharField
from django.db.models.functions import Concat, Coalesce

from .serializers import (
    CompanyOnboardingSerializer,
    CompanySerializer,
    CustomTokenObtainPairSerializer,
    UserSerializer,
    SignupSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    PasswordChangeSerializer,
    TeamMemberSerializer,
)
from .models import UserWarehouse, Role

User = get_user_model()


class LoginView(TokenObtainPairView):
    """
    Login endpoint that returns JWT access and refresh tokens.

    POST /api/v1/accounts/auth/login/
    Body: {"email": "...", "password": "..."}
    Returns: {"access": "...", "refresh": "...", "user": {...}}
    """

    serializer_class = CustomTokenObtainPairSerializer


class TokenRefreshView(TokenRefreshView):
    """
    Refresh JWT access token using refresh token.

    POST /api/auth/refresh/
    Body: {"refresh": "..."}
    Returns: {"access": "..."}
    """

    pass


class RegisterView(generics.CreateAPIView):
    """
    Signup endpoint - creates both company and user account.
    The first user becomes the company owner/admin.

    POST /api/auth/register/
    Body: {
        "company_name": "My Company",
        "company_email": "company@example.com",
        "username": "owner",
        "email": "owner@example.com",
        "password": "...",
        "password_confirm": "...",
        "first_name": "John",
        "last_name": "Doe",
        ...
    }
    Returns: User object with tokens
    """

    serializer_class = SignupSerializer
    permission_classes = [permissions.AllowAny]  # Allow public signup

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate tokens for the new user
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": UserSerializer(user).data,
                "company": {
                    "id": user.company.id,
                    "name": user.company.name,
                },
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
                "message": "Company and user registered successfully.",
            },
            status=status.HTTP_201_CREATED,
        )


class UserMeView(generics.RetrieveAPIView):
    """
    Get basic info about the current logged-in user.
    Lightweight endpoint for frontend to check authentication status and get user context.

    GET /api/v1/accounts/auth/me/ - Get current user basic info
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Return the current authenticated user."""
        return self.request.user


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Get or update current user profile.

    GET /api/auth/profile/ - Get current user profile
    PUT /api/auth/profile/ - Update current user profile
    PATCH /api/auth/profile/ - Partially update current user profile
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Return the current authenticated user."""
        return self.request.user


class CompanyView(generics.RetrieveAPIView):
    """
    Get current user's company details.

    GET /api/v1/accounts/company/ - Get current user's company information
    """

    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Return the current user's company."""
        user = self.request.user
        if not user.company:
            raise NotFound("User is not associated with a company.")

        return user.company


class CompanyOnboardingView(generics.UpdateAPIView):
    """
    Company onboarding endpoint - update company with essential business information.
    Only the company owner/admin can update their company.

    PATCH /api/auth/onboarding/ - Update company onboarding information
    PUT /api/auth/onboarding/ - Full update (not recommended, use PATCH)
    """

    serializer_class = CompanyOnboardingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Return the current user's company."""
        user = self.request.user
        if not user.company:
            raise NotFound("User is not associated with a company.")

        return user.company

    def update(self, request, *args, **kwargs):
        """Update company onboarding information."""
        partial = kwargs.pop("partial", True)  # Default to PATCH behavior
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {
                "company": CompanySerializer(instance).data,
                "message": "Company onboarding information updated successfully.",
            },
            status=status.HTTP_200_OK,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def change_password(request):
    """
    Change user password.

    POST /api/auth/change-password/
    Body: {
        "old_password": "...",
        "new_password": "...",
        "new_password_confirm": "..."
    }
    """
    serializer = PasswordChangeSerializer(
        data=request.data,
        context={"request": request},
    )

    if serializer.is_valid():
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save()

        return Response(
            {"message": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def onboarding_status(request):
    """
    Check onboarding completion status.
    Returns whether company info is complete and at least one warehouse exists.

    GET /api/v1/accounts/onboarding/status/
    Returns: {
        "is_complete": false,
        "company_info_complete": false,
        "has_warehouse": false,
        "missing_fields": ["email", "country"],
        "warehouse_count": 0
    }
    """
    user = request.user
    if not user.company:
        return Response(
            {
                "is_complete": False,
                "company_info_complete": False,
                "has_warehouse": False,
                "missing_fields": ["company"],
                "warehouse_count": 0,
            },
            status=status.HTTP_200_OK,
        )

    company = user.company
    warehouses = company.warehouses.filter(is_active=True)

    # Check if required company fields are filled
    missing_fields = []
    if not company.email:
        missing_fields.append("email")
    if not company.country:
        missing_fields.append("country")

    company_info_complete = len(missing_fields) == 0
    has_warehouse = warehouses.exists()
    is_complete = company_info_complete and has_warehouse

    return Response(
        {
            "is_complete": is_complete,
            "company_info_complete": company_info_complete,
            "has_warehouse": has_warehouse,
            "missing_fields": missing_fields,
            "warehouse_count": warehouses.count(),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def logout(request):
    """
    Logout user by blacklisting refresh token.

    POST /api/auth/logout/
    Body: {"refresh": "..."}
    """
    try:
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"error": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = RefreshToken(refresh_token)
        token.blacklist()

        return Response(
            {"message": "Successfully logged out."},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response(
            {"error": "Invalid token or token already blacklisted."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class TeamListView(generics.ListAPIView):
    """
    Get paginated list of team members (employees) for the current user's company.

    GET /api/v1/accounts/team/

    Query Parameters:
    - search: Search by email, first_name, or last_name
    - role: Filter by role ID (from Role model) or legacy role name (admin, manager, operator, viewer)
    - page: Page number for pagination
    - page_size: Number of results per page
    """

    serializer_class = TeamMemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return users from the current user's company with filtering and search."""
        user = self.request.user

        if not user.company:
            return User.objects.none()

        # Base queryset: all users in the same company
        queryset = User.objects.filter(company=user.company).select_related("company")

        # Search functionality - search by email, first_name, or last_name
        search_query = self.request.query_params.get("search", "").strip()
        if search_query:
            # Search in email, first_name, last_name, or username
            # Use Coalesce to handle null values in name fields
            queryset = queryset.annotate(
                full_name=Concat(
                    Coalesce("first_name", V("")),
                    V(" "),
                    Coalesce("last_name", V("")),
                    output_field=CharField(),
                )
            )
            # Search in email, first_name, last_name, full_name, or username
            queryset = queryset.filter(
                Q(email__icontains=search_query)
                | Q(first_name__icontains=search_query)
                | Q(last_name__icontains=search_query)
                | Q(full_name__icontains=search_query)
                | Q(username__icontains=search_query)
            )

        # Filter by role
        role_filter = self.request.query_params.get("role", "").strip()
        if role_filter:
            # Try to find by role ID first (new system)
            try:
                role_id = int(role_filter)
                role_obj = Role.objects.filter(id=role_id, company=user.company).first()
                if role_obj:
                    # Filter users who have this role in any warehouse assignment
                    user_ids = UserWarehouse.objects.filter(
                        role=role_obj, is_active=True
                    ).values_list("user_id", flat=True)
                    queryset = queryset.filter(id__in=user_ids)
                else:
                    # Role ID not found, return empty queryset
                    return User.objects.none()
            except ValueError:
                # Not a number, try legacy role names
                legacy_roles = [choice[0] for choice in UserWarehouse.ROLE_CHOICES]
                if role_filter.lower() in legacy_roles:
                    # Filter users who have this legacy role in any warehouse assignment
                    user_ids = UserWarehouse.objects.filter(
                        legacy_role=role_filter.lower(), is_active=True
                    ).values_list("user_id", flat=True)
                    queryset = queryset.filter(id__in=user_ids)
                else:
                    # Invalid role, return empty queryset
                    return User.objects.none()

        # Order by date_joined (newest first) or by name
        queryset = queryset.order_by("-date_joined", "first_name", "last_name")

        return queryset
