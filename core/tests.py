from django.test import TestCase
from .models import Donor, Donation, Item, Collection, SystemSettings
from .services.auth_service import AuthService
from .services.donation_service import DonationService
from .services.collection_service import CollectionService
from .services.emissions_service import EmissionsService


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(email='staff@recycle-it.org.uk', is_admin=False):
    return AuthService.create_user(
        email=email,
        password='TestPass123!',
        first_name='Test',
        last_name='User',
        is_admin=is_admin,
    )


def make_donor(email='donor@example.com'):
    return Donor.objects.create(
        company_name='Test Corp',
        contact_person='Jane Doe',
        contact_email=email,
        contact_phone='01204000000',
    )


def make_donation(donor, collection=None, approval_status='awaiting_review'):
    return Donation.objects.create(
        donor=donor,
        collection=collection,
        street_address='123 Test Street',
        city='Bolton',
        postcode='BL1 1AA',
        data_destruction_required=False,
        approval_status=approval_status,
        reference_id=DonationService.generate_reference_id(),
    )


def make_collection(user, status='draft', distance=None):
    c = Collection.objects.create(
        created_by=user,
        status=status,
        driver_name='Test Driver',
        vehicle_id='VAN-01',
    )
    if distance:
        c.total_distance_km = distance
        c.save()
    return c


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH SERVICE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class AuthServiceTest(TestCase):

    def test_create_user_success(self):
        user = AuthService.create_user(
            email='test@example.com',
            password='Pass123!',
            first_name='John',
            last_name='Smith',
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'John')

    def test_create_user_duplicate_email_raises(self):
        AuthService.create_user('a@a.com', 'Pass123!', 'A', 'A')
        with self.assertRaises(ValueError):
            AuthService.create_user('a@a.com', 'Pass123!', 'B', 'B')

    def test_verify_user_correct_credentials(self):
        AuthService.create_user('v@v.com', 'Pass123!', 'V', 'V')
        user = AuthService.verify_user('v@v.com', 'Pass123!')
        self.assertIsNotNone(user)


# ══════════════════════════════════════════════════════════════════════════════
#  DONATION SERVICE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class DonationServiceTest(TestCase):

    def _donor_data(self, email='d@example.com'):
        return {
            'company_name': 'Bolton Council',
            'contact_person': 'Sarah Thompson',
            'contact_email': email,
            'contact_phone': '01204000000',
        }

    def _donation_data(self):
        return {
            'street_address': 'Town Hall',
            'city': 'Bolton',
            'postcode': 'BL1 1RU',
            'data_destruction_required': True,
            'notes': 'Call ahead.',
        }

    def _items_data(self):
        return [
            {'category': 'PROCESSOR', 'quantity': 5, 'weight': None, 'other_description': ''},
            {'category': 'MONITOR', 'quantity': 3, 'weight': None, 'other_description': ''},
        ]

    def test_create_donation_success(self):
        donation, ref = DonationService.create_donation(
            self._donor_data(), self._donation_data(), self._items_data()
        )
        self.assertEqual(Donor.objects.count(), 1)
        self.assertEqual(donation.donor.company_name, 'Bolton Council')
        self.assertEqual(donation.items.count(), 2)
        self.assertTrue(ref.startswith('RIT-'))
        self.assertEqual(donation.reference_id, ref)

    def test_toggle_approval_status(self):
        donation, _ = DonationService.create_donation(
            self._donor_data(), self._donation_data(), self._items_data()
        )
        updated = DonationService.toggle_approval_status(donation.pk, 'approved')
        self.assertEqual(updated.approval_status, 'approved')

    def test_get_donations_filter_by_approval_status(self):
        donation, _ = DonationService.create_donation(
            self._donor_data(), self._donation_data(), self._items_data()
        )
        DonationService.toggle_approval_status(donation.pk, 'approved')
        results = DonationService.get_donations(filters={'approval_status': 'approved'})
        self.assertEqual(results.count(), 1)


# ══════════════════════════════════════════════════════════════════════════════
#  COLLECTION SERVICE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class CollectionServiceTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.donor = make_donor()

    def test_add_donation_success(self):
        collection = make_collection(self.user)
        donation = make_donation(self.donor, approval_status='approved')
        success, msg = CollectionService.add_donation(collection.pk, donation.pk)
        self.assertTrue(success)
        donation.refresh_from_db()
        self.assertEqual(donation.collection, collection)

    def test_add_unapproved_donation_fails(self):
        collection = make_collection(self.user)
        donation = make_donation(self.donor, approval_status='awaiting_review')
        success, msg = CollectionService.add_donation(collection.pk, donation.pk)
        self.assertFalse(success)
        self.assertIn('approved', msg)

    def test_get_collection_stats(self):
        collection = make_collection(self.user)
        donation = make_donation(self.donor, collection=collection, approval_status='approved')
        Item.objects.create(donation=donation, category='PROCESSOR', quantity=4)
        Item.objects.create(donation=donation, category='MONITOR', quantity=2)
        stats = CollectionService.get_collection_stats(collection)
        self.assertEqual(stats['donation_count'], 1)
        self.assertEqual(stats['total_items'], 6)


# ══════════════════════════════════════════════════════════════════════════════
#  EMISSIONS SERVICE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class EmissionsServiceTest(TestCase):

    def setUp(self):
        self.user = make_user()

    def test_calculate_emissions_correct_formula(self):
        collection = make_collection(self.user, distance=44.0)
        record = EmissionsService.calculate_emissions(collection.pk)
        # 44 / 8.8 = 5.0 litres; 5.0 * 2.31 = 11.55 kg CO2
        self.assertAlmostEqual(record.fuel_litres_used, 5.0, places=1)
        self.assertAlmostEqual(record.co2_kg, 11.55, places=1)

    def test_calculate_emissions_no_distance_returns_none(self):
        collection = make_collection(self.user)
        result = EmissionsService.calculate_emissions(collection.pk)
        self.assertIsNone(result)

    def test_calculate_emissions_uses_custom_settings(self):
        SystemSettings.objects.create(
            fuel_efficiency_km_per_litre=10.0,
            co2_per_litre_kg=2.5,
        )
        collection = make_collection(self.user, distance=100.0)
        record = EmissionsService.calculate_emissions(collection.pk)
        # 100 / 10 = 10.0 litres; 10.0 * 2.5 = 25.0 kg CO2
        self.assertAlmostEqual(record.fuel_litres_used, 10.0, places=1)
        self.assertAlmostEqual(record.co2_kg, 25.0, places=1)
