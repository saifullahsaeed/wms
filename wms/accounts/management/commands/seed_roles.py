"""
Management command to seed default roles with permissions for a company.

Usage:
    python manage.py seed_roles --company-id 1
    python manage.py seed_roles --company-name "My Company"
    python manage.py seed_roles  # Seeds for all companies
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Permission
from django.db import transaction

from accounts.models import Company, Role


class Command(BaseCommand):
    help = "Seed default roles (Admin, Manager, Operator, Viewer) with permissions for companies"

    def add_arguments(self, parser):
        parser.add_argument(
            "--company-id",
            type=int,
            help="ID of the company to seed roles for",
        )
        parser.add_argument(
            "--company-name",
            type=str,
            help="Name of the company to seed roles for",
        )

    def handle(self, *args, **options):
        company_id = options.get("company_id")
        company_name = options.get("company_name")

        # Determine which companies to process
        if company_id:
            companies = Company.objects.filter(id=company_id)
            if not companies.exists():
                raise CommandError(f"Company with ID {company_id} not found.")
        elif company_name:
            companies = Company.objects.filter(name=company_name)
            if not companies.exists():
                raise CommandError(f"Company '{company_name}' not found.")
        else:
            companies = Company.objects.all()
            self.stdout.write(
                self.style.WARNING(
                    f"No company specified. Seeding roles for all {companies.count()} companies."
                )
            )

        # Define role permissions mapping
        role_permissions = {
            "Admin": {
                "description": "Full access to all warehouse operations and management",
                "permissions": [
                    # Warehouse management
                    ("accounts", "manage_warehouse"),
                    # Operations
                    ("operations", "pick_orders"),
                    ("operations", "putaway"),
                    ("operations", "manage_orders"),
                    ("operations", "view_orders"),
                    # Inventory
                    ("inventory", "view_inventory"),
                    ("inventory", "manage_inventory"),
                    # Masterdata (Django default CRUD permissions)
                    ("masterdata", "add_warehouse"),
                    ("masterdata", "change_warehouse"),
                    ("masterdata", "delete_warehouse"),
                    ("masterdata", "view_warehouse"),
                ],
            },
            "Manager": {
                "description": "Can manage warehouse operations and inventory, but not warehouse settings",
                "permissions": [
                    # Operations
                    ("operations", "pick_orders"),
                    ("operations", "putaway"),
                    ("operations", "manage_orders"),
                    ("operations", "view_orders"),
                    # Inventory
                    ("inventory", "view_inventory"),
                    ("inventory", "manage_inventory"),
                    # Masterdata (view only)
                    ("masterdata", "view_warehouse"),
                ],
            },
            "Operator": {
                "description": "Can perform warehouse operations like picking and putaway",
                "permissions": [
                    # Operations
                    ("operations", "pick_orders"),
                    ("operations", "putaway"),
                    ("operations", "view_orders"),
                    # Inventory (view only)
                    ("inventory", "view_inventory"),
                    # Masterdata (view only)
                    ("masterdata", "view_warehouse"),
                ],
            },
            "Viewer": {
                "description": "Read-only access to warehouse data",
                "permissions": [
                    # Operations (view only)
                    ("operations", "view_orders"),
                    # Inventory (view only)
                    ("inventory", "view_inventory"),
                    # Masterdata (view only)
                    ("masterdata", "view_warehouse"),
                ],
            },
        }

        total_created = 0
        total_updated = 0

        for company in companies:
            self.stdout.write(f"\nProcessing company: {company.name} (ID: {company.id})")

            with transaction.atomic():
                for role_name, role_config in role_permissions.items():
                    # Get or create the role
                    role, created = Role.objects.get_or_create(
                        company=company,
                        name=role_name,
                        defaults={
                            "description": role_config["description"],
                            "is_system_role": True,
                            "is_active": True,
                        },
                    )

                    if created:
                        self.stdout.write(
                            self.style.SUCCESS(f"  ✓ Created role: {role_name}")
                        )
                        total_created += 1
                    else:
                        # Update existing role
                        role.description = role_config["description"]
                        role.is_system_role = True
                        role.is_active = True
                        role.save()
                        self.stdout.write(
                            self.style.WARNING(f"  ↻ Updated role: {role_name}")
                        )
                        total_updated += 1

                    # Clear existing permissions and add new ones
                    role.permissions.clear()

                    # Add permissions
                    permissions_added = 0
                    for app_label, codename in role_config["permissions"]:
                        try:
                            permission = Permission.objects.get(
                                content_type__app_label=app_label, codename=codename
                            )
                            role.permissions.add(permission)
                            permissions_added += 1
                        except Permission.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"    ⚠ Permission '{app_label}.{codename}' not found. Skipping."
                                )
                            )

                    self.stdout.write(
                        f"    → Added {permissions_added} permissions to {role_name}"
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Completed! Created {total_created} roles, updated {total_updated} roles."
            )
        )

