"""
API views for masterdata app - warehouse and product management.
"""

from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from django.contrib.auth import get_user_model

from .models import Warehouse
from .serializers import WarehouseSerializer, WarehouseCodeCheckSerializer
from accounts.models import Company

User = get_user_model()


class WarehouseListCreateView(generics.ListCreateAPIView):
    """
    List and create warehouses for the current user's company.

    GET /api/v1/masterdata/warehouses/ - List all warehouses for company
    POST /api/v1/masterdata/warehouses/ - Create a new warehouse
    """

    serializer_class = WarehouseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return warehouses for the current user's company."""
        user = self.request.user
        if not user.company:
            return Warehouse.objects.none()
        return Warehouse.objects.filter(company=user.company).order_by("code")

    def create(self, request, *args, **kwargs):
        """Create a new warehouse."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        warehouse = serializer.save()

        return Response(
            {
                "warehouse": WarehouseSerializer(warehouse).data,
                "message": "Warehouse created successfully.",
            },
            status=status.HTTP_201_CREATED,
        )


class WarehouseDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a warehouse.

    GET /api/v1/masterdata/warehouses/{id}/ - Get warehouse details
    PUT /api/v1/masterdata/warehouses/{id}/ - Update warehouse
    PATCH /api/v1/masterdata/warehouses/{id}/ - Partially update warehouse
    DELETE /api/v1/masterdata/warehouses/{id}/ - Delete warehouse
    """

    serializer_class = WarehouseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return warehouses for the current user's company."""
        user = self.request.user
        if not user.company:
            return Warehouse.objects.none()
        return Warehouse.objects.filter(company=user.company)


@api_view(["POST", "GET"])
@permission_classes([permissions.IsAuthenticated])
def check_warehouse_code(request):
    """
    Check if a warehouse code already exists for a company.

    Works with either user_id or company_id. If authenticated and neither
    is provided, uses the current user's company.

    POST /api/v1/masterdata/warehouses/check-code/
    GET /api/v1/masterdata/warehouses/check-code/?warehouse_code=WH-001&company_id=1

    Request Body (POST):
    {
        "warehouse_code": "WH-001",
        "user_id": 1,  // Optional
        "company_id": 1  // Optional
    }

    Response:
    {
        "exists": true,
        "warehouse_code": "WH-001",
        "company_id": 1,
        "company_name": "My Company"
    }
    """
    # Handle GET request with query parameters
    if request.method == "GET":
        warehouse_code = request.query_params.get("warehouse_code")
        user_id = request.query_params.get("user_id")
        company_id = request.query_params.get("company_id")

        if not warehouse_code:
            raise ValidationError(
                {"warehouse_code": "warehouse_code query parameter is required."}
            )

        data = {
            "warehouse_code": warehouse_code,
        }
        if user_id:
            try:
                data["user_id"] = int(user_id)
            except (ValueError, TypeError):
                raise ValidationError({"user_id": "user_id must be a valid integer."})
        if company_id:
            try:
                data["company_id"] = int(company_id)
            except (ValueError, TypeError):
                raise ValidationError(
                    {"company_id": "company_id must be a valid integer."}
                )
    else:
        # Handle POST request with body
        data = request.data

    serializer = WarehouseCodeCheckSerializer(data=data)
    serializer.is_valid(raise_exception=True)

    validated_data = serializer.validated_data
    warehouse_code = validated_data["warehouse_code"]
    user_id = validated_data.get("user_id")
    company_id = validated_data.get("company_id")

    # Determine which company to check
    company = None

    if company_id:
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            raise NotFound("Company not found.")
    elif user_id:
        try:
            user = User.objects.get(id=user_id)
            if not user.company:
                raise NotFound("User is not associated with a company.")
            company = user.company
        except User.DoesNotExist:
            raise NotFound("User not found.")
    else:
        # Use authenticated user's company
        if not request.user.company:
            raise ValidationError(
                {
                    "error": "User is not associated with a company. Please provide user_id or company_id."
                }
            )
        company = request.user.company

    # Check if warehouse code exists for this company
    exists = Warehouse.objects.filter(company=company, code=warehouse_code).exists()

    return Response(
        {
            "exists": exists,
            "warehouse_code": warehouse_code,
            "company_id": company.id,
            "company_name": company.name,
        },
        status=status.HTTP_200_OK,
    )
