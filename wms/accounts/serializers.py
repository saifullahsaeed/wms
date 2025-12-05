"""
Serializers for accounts app - authentication and user management.
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password

from .models import Company, User, UserWarehouse, Role


class CompanySerializer(serializers.ModelSerializer):
    """Serializer for Company model."""

    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "legal_name",
            "email",
            "phone",
            "website",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "tax_id",
            "registration_number",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model (read operations)."""

    company_name = serializers.CharField(source="company.name", read_only=True)
    company_id = serializers.IntegerField(source="company.id", read_only=True)
    warehouses = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "company_id",
            "company_name",
            "employee_code",
            "job_title",
            "phone",
            "mobile",
            "language",
            "time_zone",
            "is_warehouse_operator",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
            "warehouses",
        ]
        read_only_fields = [
            "id",
            "date_joined",
            "last_login",
            "warehouses",
        ]

    def get_warehouses(self, obj):
        """Get user's warehouse assignments."""
        assignments = UserWarehouse.objects.filter(user=obj, is_active=True)
        return [
            {
                "warehouse_id": assignment.warehouse.id,
                "warehouse_code": assignment.warehouse.code,
                "warehouse_name": assignment.warehouse.name,
                "role": assignment.role.name if assignment.role else None,
                "is_primary": assignment.is_primary,
            }
            for assignment in assignments
        ]


class SignupSerializer(serializers.Serializer):
    """
    Serializer for company signup - creates both company and user.
    The first user becomes the company owner/admin.
    """

    # Company fields
    company_name = serializers.CharField(max_length=255, required=True)
    company_legal_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    company_email = serializers.EmailField(required=False, allow_blank=True)
    company_phone = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )
    company_website = serializers.URLField(required=False, allow_blank=True)
    company_address_line1 = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    company_address_line2 = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    company_city = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    company_state = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    company_postal_code = serializers.CharField(
        max_length=30, required=False, allow_blank=True
    )
    company_country = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    company_tax_id = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    company_registration_number = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )

    # User fields
    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
    )
    password_confirm = serializers.CharField(write_only=True, required=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    employee_code = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    job_title = serializers.CharField(max_length=100, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    mobile = serializers.CharField(max_length=50, required=False, allow_blank=True)
    language = serializers.CharField(max_length=10, required=False, allow_blank=True)
    time_zone = serializers.CharField(max_length=50, required=False, allow_blank=True)

    def validate(self, attrs):
        """Validate that passwords match and company name is unique."""
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Password fields didn't match."}
            )

        # Check if company name already exists
        if Company.objects.filter(name=attrs["company_name"]).exists():
            raise serializers.ValidationError(
                {"company_name": "A company with this name already exists."}
            )

        return attrs

    def create(self, validated_data):
        """Create company and user."""
        # Extract company data
        company_data = {
            "name": validated_data.pop("company_name"),
            "legal_name": validated_data.pop("company_legal_name", ""),
            "email": validated_data.pop("company_email", ""),
            "phone": validated_data.pop("company_phone", ""),
            "website": validated_data.pop("company_website", ""),
            "address_line1": validated_data.pop("company_address_line1", ""),
            "address_line2": validated_data.pop("company_address_line2", ""),
            "city": validated_data.pop("company_city", ""),
            "state": validated_data.pop("company_state", ""),
            "postal_code": validated_data.pop("company_postal_code", ""),
            "country": validated_data.pop("company_country", ""),
            "tax_id": validated_data.pop("company_tax_id", ""),
            "registration_number": validated_data.pop(
                "company_registration_number", ""
            ),
        }

        # Create company
        company = Company.objects.create(**company_data)

        # Extract user data
        password = validated_data.pop("password")
        validated_data.pop("password_confirm")

        # Create user as company owner/admin
        user = User.objects.create_user(
            company=company,
            password=password,
            is_staff=True,  # First user is company admin
            **validated_data,
        )

        return user


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new users within an existing company.
    Used for admin adding users to their company.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
    )
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "employee_code",
            "job_title",
            "phone",
            "mobile",
            "language",
            "time_zone",
            "is_warehouse_operator",
        ]

    def validate(self, attrs):
        """Validate that passwords match."""
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Password fields didn't match."}
            )
        return attrs

    def create(self, validated_data):
        """Create a new user in the current user's company."""
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        # Get company from request context (set by view)
        company = self.context.get("company")
        if not company:
            raise serializers.ValidationError("Company context is required.")

        user = User.objects.create_user(
            company=company,
            password=password,
            **validated_data,
        )
        return user


class CompanyOnboardingSerializer(serializers.ModelSerializer):
    """
    Serializer for company onboarding - collects essential business information.
    Designed for good UX with minimal required fields.

    Required: email, country (for timezone/regulations)
    Optional: Everything else can be added later
    """

    # Required fields (minimal for good UX)
    email = serializers.EmailField(
        required=True,
        help_text="Company email for notifications and system communications.",
    )
    country = serializers.CharField(
        max_length=100,
        required=True,
        help_text="Country code or name (e.g., 'US', 'United States'). Required for timezone and regulations.",
    )

    # Optional fields (can be added later)
    legal_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)
    address_line1 = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    address_line2 = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    postal_code = serializers.CharField(max_length=30, required=False, allow_blank=True)
    tax_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    registration_number = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )

    class Meta:
        model = Company
        fields = [
            "legal_name",
            "email",
            "phone",
            "website",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "tax_id",
            "registration_number",
        ]

    def validate(self, attrs):
        """Validate that required fields are present if not already set."""
        instance = self.instance

        # Check if this is initial onboarding (company doesn't have email/country yet)
        if instance:
            if not instance.email and "email" not in attrs:
                raise serializers.ValidationError(
                    {"email": "Email is required for onboarding."}
                )
            if not instance.country and "country" not in attrs:
                raise serializers.ValidationError(
                    {"country": "Country is required for onboarding."}
                )

        return attrs

    def update(self, instance, validated_data):
        """Update company with onboarding data."""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "employee_code",
            "job_title",
            "phone",
            "mobile",
            "language",
            "time_zone",
            "is_warehouse_operator",
        ]


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for changing user password."""

    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
    )
    new_password_confirm = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        """Validate password change."""
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "New password fields didn't match."}
            )
        return attrs

    def validate_old_password(self, value):
        """Validate old password."""
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that uses email instead of username for login.
    """

    username_field = "email"  # Use email field instead of username

    @classmethod
    def get_token(cls, user):
        """Add custom claims to token."""
        token = super().get_token(user)

        # Add custom claims
        token["username"] = user.username
        token["email"] = user.email
        token["company_id"] = user.company.id if user.company else None
        token["is_warehouse_operator"] = user.is_warehouse_operator
        token["is_staff"] = user.is_staff
        token["is_superuser"] = user.is_superuser

        return token

    def validate(self, attrs):
        """
        Validate credentials using email and check user is active.
        Override to use email instead of username.
        """
        # Get email and password from attrs
        email = attrs.get("email")
        password = attrs.get("password")

        if not email or not password:
            raise serializers.ValidationError(
                "Email and password are required.",
                code="missing_credentials",
            )

        # Find user by email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "Invalid email or password.",
                code="invalid_credentials",
            )

        # Check password
        if not user.check_password(password):
            raise serializers.ValidationError(
                "Invalid email or password.",
                code="invalid_credentials",
            )

        # Check if user is active
        if not user.is_active:
            raise serializers.ValidationError(
                "User account is disabled.",
                code="user_inactive",
            )

        # Check if user has a company
        if not user.company:
            raise serializers.ValidationError(
                "User must be assigned to a company.",
                code="no_company",
            )

        # Set user for token generation
        self.user = user

        # Generate token
        refresh = self.get_token(user)

        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

        # Add custom response data
        data["user"] = UserSerializer(user).data

        return data


class TeamMemberSerializer(serializers.ModelSerializer):
    """Serializer for team members list with role information."""

    company_name = serializers.CharField(source="company.name", read_only=True)
    full_name = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    primary_warehouse = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "employee_code",
            "job_title",
            "phone",
            "mobile",
            "is_warehouse_operator",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
            "roles",
            "primary_warehouse",
        ]
        read_only_fields = [
            "id",
            "username",
            "date_joined",
            "last_login",
            "roles",
            "primary_warehouse",
        ]

    def get_full_name(self, obj):
        """Get full name of the user."""
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}"
        elif obj.first_name:
            return obj.first_name
        elif obj.last_name:
            return obj.last_name
        return obj.username

    def get_roles(self, obj):
        """Get all roles assigned to user across warehouses."""
        assignments = UserWarehouse.objects.filter(
            user=obj, is_active=True
        ).select_related("role", "warehouse")

        roles = []
        for assignment in assignments:
            role_info = {
                "warehouse_id": assignment.warehouse.id,
                "warehouse_code": assignment.warehouse.code,
                "warehouse_name": assignment.warehouse.name,
                "is_primary": assignment.is_primary,
            }

            if assignment.role:
                # New role system
                role_info["role_id"] = assignment.role.id
                role_info["role_name"] = assignment.role.name
                role_info["role_type"] = "custom"
            elif assignment.legacy_role:
                # Legacy role system
                role_info["role_name"] = assignment.legacy_role
                role_info["role_type"] = "legacy"
            else:
                role_info["role_name"] = None
                role_info["role_type"] = None

            roles.append(role_info)

        return roles

    def get_primary_warehouse(self, obj):
        """Get primary warehouse assignment."""
        primary_assignment = UserWarehouse.objects.filter(
            user=obj, is_active=True, is_primary=True
        ).select_related("warehouse", "role").first()

        if not primary_assignment:
            return None

        return {
            "warehouse_id": primary_assignment.warehouse.id,
            "warehouse_code": primary_assignment.warehouse.code,
            "warehouse_name": primary_assignment.warehouse.name,
            "role": (
                primary_assignment.role.name
                if primary_assignment.role
                else primary_assignment.legacy_role
            ),
        }
