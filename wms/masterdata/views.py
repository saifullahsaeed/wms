"""
API views for masterdata app - warehouse and product management.
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response

from .models import Warehouse
from .serializers import WarehouseSerializer


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
