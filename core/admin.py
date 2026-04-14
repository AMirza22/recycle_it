from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Donor, Donation, Item, Collection, EmissionRecord, SystemSettings


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Recycle-IT! Permissions', {'fields': ('is_admin',)}),
    )
    list_display = ['email', 'first_name', 'last_name', 'is_admin', 'is_active']


@admin.register(Donor)
class DonorAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'contact_person', 'contact_email', 'created_at']
    search_fields = ['company_name', 'contact_email']


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ['reference_id', 'donor', 'approval_status', 'status', 'created_at']
    list_filter = ['approval_status', 'status']
    search_fields = ['reference_id', 'donor__company_name']


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['donation', 'category', 'quantity']


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['pk', 'status', 'scheduled_datetime', 'created_by', 'created_at']
    list_filter = ['status']


@admin.register(EmissionRecord)
class EmissionRecordAdmin(admin.ModelAdmin):
    list_display = ['collection', 'co2_kg', 'fuel_litres_used', 'distance_km', 'calculated_at']


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ['fuel_efficiency_km_per_litre', 'co2_per_litre_kg']