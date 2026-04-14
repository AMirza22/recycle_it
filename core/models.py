from django import db
from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.

class User(AbstractUser):
    is_admin = models.BooleanField(default=False)

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.email
    
class Donor(models.Model):
    company_name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'donors'

    def __str__(self):
        return self.company_name
    

class Collection(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='collections'
    )
    scheduled_datetime = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    driver_name = models.CharField(max_length=255, blank=True)
    vehicle_id = models.CharField(max_length=50, blank=True)
    total_distance_km = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'collections'

    def __str__(self):
        return f'Collection #{self.pk} — {self.status}'


class Donation(models.Model):
    STATUS_CHOICES = [
        ('awaiting_collection', 'Awaiting Collection'),
        ('collected', 'Collected'),
    ]

    APPROVAL_CHOICES = [
        ('awaiting_review', 'Awaiting Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    donor = models.ForeignKey(
        Donor,
        on_delete=models.CASCADE,
        related_name='donations'
    )
    collection = models.ForeignKey(
        Collection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donations'
    )
    collection_address = models.CharField(max_length=500)
    preferred_collection_datetime = models.DateTimeField(null=True, blank=True)
    data_destruction_required = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='awaiting_collection')
    approval_status = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default='awaiting_review')
    rejection_reason = models.TextField(blank=True)
    reference_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'donations'

    def __str__(self):
        return f'{self.reference_id} — {self.donor.company_name}'


class Item(models.Model):
    CATEGORY_CHOICES = [
        ('PROCESSOR', 'Processors (CPU, Tower, Desktop, Tablet, Laptop)'),
        ('MONITOR', 'TFT/LCD Flat Screen Monitors'),
        ('PRINTER', 'Printers (desktop inkjet / office laser, fax)'),
        ('ACCESSORIES', 'Accessories (mice, cables, keyboards)'),
        ('NETWORKING', 'Networking Equipment (routers, switches, hubs)'),
        ('MOBILE', 'Mobile Phones'),
        ('OTHER', 'Other'),
    ]

    donation = models.ForeignKey(
        Donation,
        on_delete=models.CASCADE,
        related_name='items'
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    other_description = models.CharField(max_length=255, blank=True)
    quantity = models.PositiveIntegerField(default=0)
    weight = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'items'

    def __str__(self):
        return f'{self.category} x{self.quantity}'


class EmissionRecord(models.Model):
    collection = models.OneToOneField(
        Collection,
        on_delete=models.CASCADE,
        related_name='emission_record'
    )
    co2_kg = models.FloatField()
    fuel_litres_used = models.FloatField()
    distance_km = models.FloatField()
    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'emission_records'

    def __str__(self):
        return f'Emissions for Collection #{self.collection_id}'


class SystemSettings(models.Model):
    fuel_efficiency_km_per_litre = models.FloatField(default=8.8)
    co2_per_litre_kg = models.FloatField(default=2.31)

    class Meta:
        db_table = 'system_settings'

    def __str__(self):
        return 'System Settings'