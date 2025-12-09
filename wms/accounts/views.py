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
from drf_spectacular.utils import extend_schema, extend_schema_view

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
    WarehouseUserAssignmentSerializer,
)
from .models import UserWarehouse, Role
from .services import get_user_permissions, assign_user_to_warehouse
from rest_framework.exceptions import PermissionDenied
from masterdata.models import Warehouse

User = get_user_model()


@extend_schema(
    tags=["Accounts - Authentication"],
    summary="Login",
    description="Login endpoint that returns JWT access and refresh tokens.",
)
class LoginView(TokenObtainPairView):
    """
    Login endpoint that returns JWT access and refresh tokens.

    POST /api/v1/accounts/auth/login/
    Body: {"email": "...", "password": "..."}
    Returns: {"access": "...", "refresh": "...", "user": {...}}
    """

    serializer_class = CustomTokenObtainPairSerializer


@extend_schema(
    tags=["Accounts - Authentication"],
    summary="Refresh Token",
    description="Refresh JWT access token using refresh token.",
)
class TokenRefreshView(TokenRefreshView):
    """
    Refresh JWT access token using refresh token.

    POST /api/auth/refresh/
    Body: {"refresh": "..."}
    Returns: {"access": "..."}
    """

    pass


@extend_schema(
    tags=["Accounts - Authentication"],
    summary="Register",
    description="Signup endpoint - creates both company and user account. The first user becomes the company owner/admin.",
)
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


@extend_schema(
    tags=["Accounts - User Management"],
    summary="Get Current User",
    description="Get basic info about the current logged-in user. Lightweight endpoint for frontend to check authentication status and get user context.",
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


@extend_schema(
    tags=["Accounts - User Management"],
    summary="User Profile",
    description="Get or update current user profile.",
)
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


@extend_schema(
    tags=["Accounts - Company"],
    summary="Get Company",
    description="Get current user's company details.",
)
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


@extend_schema(
    tags=["Accounts - Company"],
    summary="Company Onboarding",
    description="Company onboarding endpoint - update company with essential business information. Only the company owner/admin can update their company.",
)
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


@extend_schema(
    tags=["Accounts - User Management"],
    summary="Change Password",
    description="Change user password.",
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


@extend_schema(
    tags=["Accounts - Company"],
    summary="Onboarding Status",
    description="Check onboarding completion status. Returns whether company info is complete and at least one warehouse exists.",
)
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


@extend_schema(
    tags=["Accounts - Authentication"],
    summary="Logout",
    description="Logout user by blacklisting refresh token.",
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


@extend_schema(
    tags=["Accounts - Team Management"],
    summary="List/Create Team Members",
    description="Get paginated list of team members or add a new team member.",
)
class TeamListView(generics.ListCreateAPIView):
    """
    Get paginated list of team members or add a new team member.

    GET /api/v1/accounts/team/ - List team members
    POST /api/v1/accounts/team/ - Add new team member

    Query Parameters (GET):
    - search: Search by email, first_name, or last_name
    - role: Filter by role ID (from Role model) or legacy role name (admin, manager, operator, viewer)
    - page: Page number for pagination
    - page_size: Number of results per page
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """Return appropriate serializer based on request method."""
        if self.request.method == "POST":
            return UserCreateSerializer
        return TeamMemberSerializer

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

    def get_serializer_context(self):
        """Add company to serializer context."""
        context = super().get_serializer_context()
        user = self.request.user
        if not user.company:
            raise NotFound("User is not associated with a company.")
        context["company"] = user.company
        return context

    def create(self, request, *args, **kwargs):
        """Create a new team member. Only company owners can add team members."""
        user = request.user

        # Check if user is company owner (is_staff)
        if not user.is_staff:
            raise PermissionDenied("Only company owners can add team members.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_user = serializer.save()

        return Response(
            {
                "user": TeamMemberSerializer(new_user).data,
                "message": "Team member added successfully.",
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["Accounts - Team Management"],
    summary="Team Member Details",
    description="Get, update, or remove a team member.",
)
class TeamMemberDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Get, update, or remove a team member.

    GET /api/v1/accounts/team/{id}/ - Get team member details
    PUT /api/v1/accounts/team/{id}/ - Full update
    PATCH /api/v1/accounts/team/{id}/ - Partial update
    DELETE /api/v1/accounts/team/{id}/ - Remove team member (deactivate)
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """Return appropriate serializer based on request method."""
        if self.request.method in ["PUT", "PATCH"]:
            return UserUpdateSerializer
        return TeamMemberSerializer

    def get_queryset(self):
        """Return users from the current user's company."""
        user = self.request.user
        if not user.company:
            return User.objects.none()
        return User.objects.filter(company=user.company)

    def get_object(self):
        """Get team member and verify they belong to the same company."""
        obj = super().get_object()
        user = self.request.user

        # Verify the team member belongs to the same company
        if obj.company != user.company:
            raise NotFound("Team member not found.")

        # Check permissions for update/delete operations
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            # Only company owners can update or delete team members
            if not user.is_staff:
                raise PermissionDenied(
                    "Only company owners can update or remove team members."
                )

            # Prevent users from deleting themselves
            if self.request.method == "DELETE" and obj == user:
                raise PermissionDenied("You cannot remove yourself from the team.")

        return obj

    def update(self, request, *args, **kwargs):
        """Update team member. Only company owners can update."""
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Deactivate team member instead of deleting. Only company owners can remove."""
        instance = self.get_object()

        # Deactivate the user instead of deleting
        instance.is_active = False
        instance.save()

        return Response(
            {"message": "Team member removed successfully."},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Accounts - User Management"],
    summary="Get User Permissions",
    description="Get user permissions for frontend to conditionally show/hide features.",
)
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def user_permissions(request):
    """
    Get user permissions for frontend to conditionally show/hide features.

    GET /api/v1/accounts/permissions/
    GET /api/v1/accounts/permissions/?warehouse_id=1

    Query Parameters:
    - warehouse_id (optional): Get permissions for a specific warehouse only

    Returns:
    {
        "is_company_owner": true,
        "can_manage_team": true,
        "warehouses": [
            {
                "warehouse_id": 1,
                "warehouse_code": "WH-001",
                "warehouse_name": "Main Warehouse",
                "can_access": true,
                "can_manage_warehouse": true,
                "can_pick_orders": true,
                "can_putaway": true,
                "can_view_inventory": true,
                "can_manage_inventory": true,
                "can_view_orders": true,
                "can_manage_orders": true,
                "role": {...}
            }
        ]
    }
    """
    user = request.user
    warehouse_id = request.query_params.get("warehouse_id")

    warehouse = None
    if warehouse_id:
        try:
            warehouse = Warehouse.objects.get(id=warehouse_id, company=user.company)
        except Warehouse.DoesNotExist:
            raise NotFound("Warehouse not found or does not belong to your company.")

    permissions = get_user_permissions(user, warehouse=warehouse)

    return Response(permissions, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Accounts - Warehouse Assignment"],
    summary="Assign User to Warehouse",
    description="Assign a user to a warehouse with a role. Only company owners can do this.",
)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def assign_user_to_warehouse_view(request, warehouse_id):
    """
    Assign a user to a warehouse with a role. Only company owners can do this.

    POST /api/v1/accounts/warehouses/{warehouse_id}/assign-user/

    Request Body:
    {
        "user_id": 2,
        "role_id": 1,  // Optional - custom role
        "legacy_role": "operator",  // Optional - legacy role (used if role_id not provided)
        "is_primary": false
    }
    """
    user = request.user

    # Only company owners can assign users to warehouses
    if not user.is_staff:
        raise PermissionDenied("Only company owners can assign users to warehouses.")

    # Get warehouse
    try:
        warehouse = Warehouse.objects.get(id=warehouse_id, company=user.company)
    except Warehouse.DoesNotExist:
        raise NotFound("Warehouse not found or does not belong to your company.")

    # Validate request data
    serializer = WarehouseUserAssignmentSerializer(
        data=request.data, context={"request": request}
    )
    serializer.is_valid(raise_exception=True)

    validated_data = serializer.validated_data
    target_user_id = validated_data["user_id"]
    role_id = validated_data.get("role_id")
    legacy_role = validated_data.get("legacy_role")
    is_primary = validated_data.get("is_primary", False)

    # Get target user
    try:
        target_user = User.objects.get(id=target_user_id, company=user.company)
    except User.DoesNotExist:
        raise NotFound("User not found or does not belong to your company.")

    # Get role if role_id provided
    role = None
    if role_id:
        try:
            role = Role.objects.get(id=role_id, company=user.company)
        except Role.DoesNotExist:
            raise NotFound("Role not found or does not belong to your company.")
    elif legacy_role:
        role = legacy_role

    # Assign user to warehouse
    assignment = assign_user_to_warehouse(
        user=target_user,
        warehouse=warehouse,
        role=role,
        is_primary=is_primary,
    )

    return Response(
        {
            "message": "User assigned to warehouse successfully.",
            "assignment": {
                "user_id": target_user.id,
                "user_email": target_user.email,
                "warehouse_id": warehouse.id,
                "warehouse_code": warehouse.code,
                "role": (
                    {
                        "id": assignment.role.id,
                        "name": assignment.role.name,
                        "type": "custom",
                    }
                    if assignment.role
                    else {
                        "name": assignment.legacy_role,
                        "type": "legacy",
                    }
                ),
                "is_primary": assignment.is_primary,
            },
        },
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    tags=["Accounts - Warehouse Assignment"],
    summary="Remove User from Warehouse",
    description="Remove a user from a warehouse. Only company owners can do this.",
)
@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def remove_user_from_warehouse_view(request, warehouse_id, user_id):
    """
    Remove a user from a warehouse. Only company owners can do this.

    DELETE /api/v1/accounts/warehouses/{warehouse_id}/users/{user_id}/
    """
    user = request.user

    # Only company owners can remove users from warehouses
    if not user.is_staff:
        raise PermissionDenied("Only company owners can remove users from warehouses.")

    # Get warehouse
    try:
        warehouse = Warehouse.objects.get(id=warehouse_id, company=user.company)
    except Warehouse.DoesNotExist:
        raise NotFound("Warehouse not found or does not belong to your company.")

    # Get target user
    try:
        target_user = User.objects.get(id=user_id, company=user.company)
    except User.DoesNotExist:
        raise NotFound("User not found or does not belong to your company.")

    # Get assignment
    try:
        assignment = UserWarehouse.objects.get(user=target_user, warehouse=warehouse)
    except UserWarehouse.DoesNotExist:
        raise NotFound("User is not assigned to this warehouse.")

    # Deactivate the assignment
    assignment.is_active = False
    assignment.save()

    return Response(
        {"message": "User removed from warehouse successfully."},
        status=status.HTTP_200_OK,
    )
