"""
populate_data.py — Recycle-IT! Sample Data Script
==================================================
Populates the database with realistic, varied sample data for demo and
development purposes. Safe to run multiple times (idempotent by default).

Usage
-----
    # From your Django project root:
    python populate_data.py

    # Wipe all existing app data first, then re-seed:
    python populate_data.py --reset


import os
import sys
import django
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ── Django bootstrap ──────────────────────────────────────────────────────────
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recycle_it.settings')
django.setup()

# ── Imports (after setup) ─────────────────────────────────────────────────────
from core.models import (
    User, Donor, Donation, Item,
    Collection, EmissionRecord, SystemSettings,
)
from core.services.auth_service import AuthService
from core.services.donation_service import DonationService

# ── Helpers ───────────────────────────────────────────────────────────────────

UK = ZoneInfo('Europe/London')


def dt(days_offset, hour=9, minute=0):
    """Return a timezone-aware datetime relative to today."""
    base = datetime.now(UK).replace(hour=hour, minute=minute, second=0, microsecond=0)
    return base + timedelta(days=days_offset)


def log(msg):
    print(f'  {msg}')


# ── Reset ─────────────────────────────────────────────────────────────────────

def reset_data():
    print('\n[RESET] Deleting existing app data...')
    EmissionRecord.objects.all().delete()
    Item.objects.all().delete()
    Donation.objects.all().delete()
    Collection.objects.all().delete()
    Donor.objects.all().delete()
    User.objects.filter(is_superuser=False).delete()
    SystemSettings.objects.all().delete()
    print('[RESET] Done.\n')


# ── 1. System Settings ────────────────────────────────────────────────────────

def seed_system_settings():
    print('[1/6] System Settings')
    settings, created = SystemSettings.objects.get_or_create(
        pk=1,
        defaults={
            'fuel_efficiency_km_per_litre': 8.8,
            'co2_per_litre_kg': 2.31,
        }
    )
    log('Created SystemSettings' if created else 'SystemSettings already exists — skipped')


# ── 2. Staff Users ────────────────────────────────────────────────────────────

def seed_users():
    print('[2/6] Staff Users')

    users_data = [
        {
            'email': 'admin@recycle-it.org.uk',
            'password': 'Admin1234!',
            'first_name': 'John',
            'last_name': 'Hastings',
            'is_admin': True,
        },
        {
            'email': 'sarah.malik@recycle-it.org.uk',
            'password': 'Staff1234!',
            'first_name': 'Sarah',
            'last_name': 'Malik',
            'is_admin': False,
        },
    ]

    created_users = {}
    for data in users_data:
        if User.objects.filter(email=data['email']).exists():
            log(f"User {data['email']} already exists — skipped")
            created_users[data['email']] = User.objects.get(email=data['email'])
        else:
            user = AuthService.create_user(
                email=data['email'],
                password=data['password'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                is_admin=data['is_admin'],
            )
            if data['is_admin']:
                user.is_staff = True
                user.is_superuser = True
                user.save()
            created_users[data['email']] = user
            label = 'admin' if data['is_admin'] else 'staff'
            log(f"Created {label} user: {data['email']}")

    return created_users


# ── 3. Donors ─────────────────────────────────────────────────────────────────

def seed_donors():
    print('[3/6] Donors')

    donors_data = [
        {
            'company_name': 'Bolton Council',
            'contact_person': 'Sarah Thompson',
            'contact_email': 's.thompson@bolton.gov.uk',
            'contact_phone': '01204 331100',
        },
        {
            'company_name': 'Royal Bolton Hospital NHS Foundation Trust',
            'contact_person': 'David Okafor',
            'contact_email': 'd.okafor@boltonft.nhs.uk',
            'contact_phone': '01204 390390',
        },
        {
            'company_name': 'University of Bolton',
            'contact_person': 'Priya Sharma',
            'contact_email': 'p.sharma@bolton.ac.uk',
            'contact_phone': '01204 900600',
        },
        {
            'company_name': 'Bolton Sixth Form College',
            'contact_person': 'James Carter',
            'contact_email': 'j.carter@boltonsfcollege.ac.uk',
            'contact_phone': '01204 846214',
        },
        {
            'company_name': 'YMCA Bolton',
            'contact_person': 'Fatima Al-Rashid',
            'contact_email': 'fatima@ymcabolton.org.uk',
            'contact_phone': '01204 521546',
        },
        {
            'company_name': 'Farnworth Community Centre',
            'contact_person': 'Mark Hughes',
            'contact_email': 'm.hughes@farnworthcc.co.uk',
            'contact_phone': '01204 573820',
        },
        {
            'company_name': 'Bolton Lads & Girls Club',
            'contact_person': 'Rachel Greenwood',
            'contact_email': 'r.greenwood@blgc.co.uk',
            'contact_phone': '01204 384064',
        },
        {
            'company_name': 'Salford City Council',
            'contact_person': 'Tom Brennan',
            'contact_email': 't.brennan@salford.gov.uk',
            'contact_phone': '0161 794 4711',
        },
    ]

    created = {}
    for data in donors_data:
        donor, was_created = Donor.objects.get_or_create(
            contact_email=data['contact_email'],
            defaults=data,
        )
        created[data['company_name']] = donor
        log(f'{"Created" if was_created else "Exists"}: {data["company_name"]}')

    return created


# ── 4. Donations ──────────────────────────────────────────────────────────────

def seed_donations(donors):
    print('[4/6] Donations')

    # Each tuple:
    #   donor_key, street_address, city, postcode, lat, lng,
    #   approval_status, status, data_destruction_required, notes,
    #   preferred_dt, items [(category, quantity), ...]
    #
    # lat/lng are real Bolton-area coordinates so the route planner works.
    donations_data = [

        # ── Awaiting Review ──────────────────────────────────────────────────
        (
            'Bolton Council',
            'Town Hall, Victoria Square', 'Bolton', 'BL1 1RU',
            53.5784, -2.4284,
            'awaiting_review', 'awaiting_collection', True,
            'Please call ahead — reception is on the 2nd floor.',
            dt(-2, 9),
            [('PROCESSOR', 12), ('MONITOR', 8), ('ACCESSORIES', 3)],
        ),
        (
            'YMCA Bolton',
            '1 Spa Road', 'Bolton', 'BL1 4AG',
            53.5751, -2.4198,
            'awaiting_review', 'awaiting_collection', False,
            'Items are boxed and ready in the storage room.',
            dt(-1, 14),
            [('PROCESSOR', 5), ('MONITOR', 4), ('PRINTER', 2)],
        ),
        (
            'Bolton Lads & Girls Club',
            'Civic Centre, Bridgeman Street', 'Bolton', 'BL2 1AT',
            53.5782, -2.4181,
            'awaiting_review', 'awaiting_collection', False,
            '',
            dt(3, 10),
            [('ACCESSORIES', 10), ('NETWORKING', 3), ('MOBILE', 6)],
        ),

        # ── Approved — awaiting collection ───────────────────────────────────
        (
            'Royal Bolton Hospital NHS Foundation Trust',
            'Minerva Road, Farnworth', 'Bolton', 'BL4 0JR',
            53.5526, -2.3998,
            'approved', 'awaiting_collection', True,
            'Large quantity — may need two trips. Contact David before arriving.',
            dt(5, 9),
            [('PROCESSOR', 30), ('MONITOR', 20), ('PRINTER', 8), ('ACCESSORIES', 15)],
        ),
        (
            'University of Bolton',
            'Deane Road', 'Bolton', 'BL3 5AB',
            53.5697, -2.4461,
            'approved', 'awaiting_collection', True,
            'IT office is on floor 3. Ask for Priya at main reception.',
            dt(7, 13),
            [('PROCESSOR', 18), ('MONITOR', 12), ('NETWORKING', 6)],
        ),
        (
            'Bolton Sixth Form College',
            'Manchester Road', 'Bolton', 'BL2 1ER',
            53.5764, -2.4082,
            'approved', 'awaiting_collection', False,
            'Please use the rear car park entrance on Thicketford Road.',
            dt(6, 10),
            [('PROCESSOR', 8), ('MONITOR', 6), ('PRINTER', 3)],
        ),
        (
            'Farnworth Community Centre',
            'King Street, Farnworth', 'Bolton', 'BL4 7AH',
            53.5499, -2.3940,
            'approved', 'awaiting_collection', False,
            'Small collection — items are in the main hall.',
            dt(4, 11),
            [('PROCESSOR', 4), ('ACCESSORIES', 6), ('MOBILE', 3)],
        ),
        (
            'Salford City Council',
            'Salford Civic Centre, Chorley Road, Swinton', 'Salford', 'M27 5BY',
            53.5136, -2.3421,
            'approved', 'awaiting_collection', False,
            'Salford — slightly outside usual zone, approved by John.',
            dt(8, 9),
            [('PROCESSOR', 10), ('MONITOR', 8), ('NETWORKING', 4), ('PRINTER', 2)],
        ),

        # ── Approved — collected (assigned to the completed collection) ───────
        (
            'Bolton Council',
            'St Peters Way Life Chances Office', 'Bolton', 'BL1 2JH',
            53.5771, -2.4317,
            'approved', 'collected', False,
            'Previously collected on schedule without issues.',
            dt(-14, 9),
            [('PROCESSOR', 6), ('MONITOR', 4)],
        ),
        (
            'Royal Bolton Hospital NHS Foundation Trust',
            'Outpatients Wing, Hulton Lane', 'Bolton', 'BL3 4JZ',
            53.5599, -2.4401,
            'approved', 'collected', True,
            'Data destruction certificate issued post-collection.',
            dt(-14, 11),
            [('PROCESSOR', 10), ('MONITOR', 5), ('ACCESSORIES', 8)],
        ),
        (
            'University of Bolton',
            'Institute of Management, Deane Road', 'Bolton', 'BL3 5AB',
            53.5697, -2.4461,
            'approved', 'collected', True,
            '',
            dt(-14, 14),
            [('PROCESSOR', 7), ('NETWORKING', 3), ('MONITOR', 3)],
        ),

        # ── Rejected ─────────────────────────────────────────────────────────
        (
            'Farnworth Community Centre',
            'King Street, Farnworth', 'Bolton', 'BL4 7AH',
            53.5499, -2.3940,
            'rejected', 'awaiting_collection', False,
            'Items include CRT monitors which fall outside our current collection scope.',
            dt(-10, 9),
            [('MONITOR', 3), ('OTHER', 2)],
        ),
        (
            'YMCA Bolton',
            '1 Spa Road', 'Bolton', 'BL1 4AG',
            53.5751, -2.4198,
            'rejected', 'awaiting_collection', False,
            'Insufficient item quantity to justify a dedicated collection visit.',
            dt(-5, 10),
            [('OTHER', 1)],
        ),
    ]

    created_donations = []

    for (
        donor_key, street, city, postcode, lat, lng,
        approval, status, data_dest, notes, pref_dt, items
    ) in donations_data:
        donor = donors[donor_key]

        # Deduplication: same donor + street + postcode + approval won't be created twice
        existing = Donation.objects.filter(
            donor=donor,
            street_address=street,
            postcode=postcode,
            approval_status=approval,
        ).first()

        if existing:
            log(f'Exists (skipped): {donor_key} — {street}')
            created_donations.append(existing)
            continue

        rejection_reason = ''
        if approval == 'rejected':
            rejection_reason = notes
            notes = ''

        donation = Donation.objects.create(
            donor=donor,
            street_address=street,
            city=city,
            postcode=postcode,
            latitude=lat,
            longitude=lng,
            preferred_collection_datetime=pref_dt,
            data_destruction_required=data_dest,
            notes=notes,
            rejection_reason=rejection_reason,
            approval_status=approval,
            status=status,
            reference_id=DonationService.generate_reference_id(),
        )

        for category, quantity in items:
            Item.objects.create(
                donation=donation,
                category=category,
                quantity=quantity,
            )

        created_donations.append(donation)
        log(f'Created [{approval}]: {donor_key} — {donation.reference_id}')

    return created_donations


# ── 5. Collections ────────────────────────────────────────────────────────────

def seed_collections(users, donations):
    print('[5/6] Collections')

    admin_user = users.get('admin@recycle-it.org.uk')
    staff_user = users.get('sarah.malik@recycle-it.org.uk')

    # --- Collection 1: COMPLETED (past, will receive an EmissionRecord) ------
    col1, c1_created = Collection.objects.get_or_create(
        driver_name='Mike Patel',
        vehicle_id='BL21 RIT',
        status='completed',
        defaults={
            'created_by': admin_user,
            'scheduled_datetime': dt(-14, 8),
            'total_distance_km': 34.7,
        }
    )
    if c1_created:
        collected = [d for d in donations if d.status == 'collected']
        for donation in collected:
            donation.collection = col1
            donation.save()
        log(f'Created Collection COMPLETED (id={col1.pk}) — {len(collected)} donations assigned')
    else:
        log(f'Collection COMPLETED already exists (id={col1.pk}) — skipped')

    # --- Collection 2: SCHEDULED (upcoming, some donations pre-assigned) -----
    col2, c2_created = Collection.objects.get_or_create(
        driver_name='Mike Patel',
        vehicle_id='BL21 RIT',
        status='scheduled',
        defaults={
            'created_by': staff_user,
            'scheduled_datetime': dt(5, 8, 30),
            'total_distance_km': 28.3,
        }
    )
    if c2_created:
        unassigned = [
            d for d in donations
            if d.approval_status == 'approved'
            and d.status == 'awaiting_collection'
            and d.collection is None
        ][:3]
        for donation in unassigned:
            donation.collection = col2
            donation.save()
        log(f'Created Collection SCHEDULED (id={col2.pk}) — {len(unassigned)} donations assigned')
    else:
        log(f'Collection SCHEDULED already exists (id={col2.pk}) — skipped')

    # --- Collection 3: DRAFT (being built, nothing assigned yet) -------------
    col3, c3_created = Collection.objects.get_or_create(
        status='draft',
        driver_name='',
        vehicle_id='',
        defaults={
            'created_by': staff_user,
            'scheduled_datetime': dt(12, 9),
            'total_distance_km': None,
        }
    )
    if c3_created:
        log(f'Created Collection DRAFT (id={col3.pk}) — no donations assigned yet')
    else:
        log(f'Collection DRAFT already exists (id={col3.pk}) — skipped')

    return col1, col2, col3


# ── 6. Emission Records ───────────────────────────────────────────────────────

def seed_emissions(completed_collection):
    print('[6/6] Emission Records')

    if hasattr(completed_collection, 'emission_record'):
        log('EmissionRecord already exists — skipped')
        return

    # Uses the same defaults as SystemSettings
    distance_km = completed_collection.total_distance_km or 34.7
    fuel_litres = round(distance_km / 8.8, 3)
    co2_kg = round(fuel_litres * 2.31, 3)

    EmissionRecord.objects.create(
        collection=completed_collection,
        co2_kg=co2_kg,
        fuel_litres_used=fuel_litres,
        distance_km=distance_km,
    )
    log(f'Created EmissionRecord: {distance_km} km → {fuel_litres} L → {co2_kg} kg CO₂')


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    reset = '--reset' in sys.argv

    print('=' * 56)
    print('  Recycle-IT! Sample Data Population Script')
    print('=' * 56)

    if reset:
        reset_data()

    seed_system_settings()
    users     = seed_users()
    donors    = seed_donors()
    donations = seed_donations(donors)
    col1, col2, col3 = seed_collections(users, donations)
    seed_emissions(col1)

    print()
    print('=' * 56)
    print('  Done! Summary:')
    print(f'    Users       : {User.objects.filter(is_superuser=False).count()}')
    print(f'    Donors      : {Donor.objects.count()}')
    print(f'    Donations   : {Donation.objects.count()}')
    print(f'    Items       : {Item.objects.count()}')
    print(f'    Collections : {Collection.objects.count()}')
    print(f'    Emissions   : {EmissionRecord.objects.count()}')
    print('=' * 56)
    print()
    print('  Staff login credentials:')
    print('    admin@recycle-it.org.uk          Admin1234!  (admin)')
    print('    sarah.malik@recycle-it.org.uk    Staff1234!  (staff)')
    print()


if __name__ == '__main__':
    main()