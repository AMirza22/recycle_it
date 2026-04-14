from django.test import TestCase, TransactionTestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from .models import (
    User, Donor, Donation, Item,
    Collection, EmissionRecord, SystemSettings
)
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
        collection_address='123 Test Street, Bolton, BL1 1AA',
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
#  MODEL TESTS
# ══════════════════════════════════════════════════════════════════════════════

class UserModelTest(TestCase):

    def test_create_user_sets_defaults(self):
        user = make_user()
        self.assertFalse(user.is_admin)
        self.assertTrue(user.is_active)

    def test_create_admin_user(self):
        user = make_user(is_admin=True)
        self.assertTrue(user.is_admin)

    def test_user_str_returns_email(self):
        user = make_user()
        self.assertEqual(str(user), 'staff@recycle-it.org.uk')

    def test_duplicate_email_raises_error(self):
        make_user()
        with self.assertRaises(ValueError):
            make_user()

    def test_password_is_hashed(self):
        user = make_user()
        self.assertNotEqual(user.password, 'TestPass123!')
        self.assertTrue(user.password.startswith('pbkdf2'))

class DonorModelTest(TestCase):

    def test_create_donor(self):
        donor = make_donor()
        self.assertEqual(donor.company_name, 'Test Corp')
        self.assertEqual(donor.contact_person, 'Jane Doe')

    def test_donor_str_returns_company_name(self):
        donor = make_donor()
        self.assertEqual(str(donor), 'Test Corp')

    def test_donor_created_at_auto_set(self):
        donor = make_donor()
        self.assertIsNotNone(donor.created_at)

    def test_phone_can_be_blank(self):
        donor = Donor.objects.create(
            company_name='No Phone Corp',
            contact_person='Person',
            contact_email='nophone@example.com',
        )
        self.assertEqual(donor.contact_phone, '')

class DonorUniqueConstraintTest(TestCase):

    def test_duplicate_email_raises_validation_error(self):
        make_donor()
        duplicate = Donor(
            company_name='Another Corp',
            contact_person='Someone',
            contact_email='donor@example.com',
        )
        with self.assertRaises(ValidationError):
            duplicate.full_clean()

class DonationModelTest(TestCase):

    def setUp(self):
        self.donor = make_donor()

    def test_default_approval_status(self):
        donation = make_donation(self.donor)
        self.assertEqual(donation.approval_status, 'awaiting_review')

    def test_default_status(self):
        donation = make_donation(self.donor)
        self.assertEqual(donation.status, 'awaiting_collection')

    def test_collection_can_be_null(self):
        donation = make_donation(self.donor)
        self.assertIsNone(donation.collection)

    def test_donation_str(self):
        donation = make_donation(self.donor)
        self.assertIn('Test Corp', str(donation))

    def test_donation_belongs_to_donor(self):
        donation = make_donation(self.donor)
        self.assertEqual(donation.donor, self.donor)

    def test_data_destruction_default_false(self):
        donation = make_donation(self.donor)
        self.assertFalse(donation.data_destruction_required)


class ItemModelTest(TestCase):

    def setUp(self):
        self.donor = make_donor()
        self.donation = make_donation(self.donor)

    def test_create_item(self):
        item = Item.objects.create(
            donation=self.donation,
            category='PROCESSOR',
            quantity=5,
        )
        self.assertEqual(item.category, 'PROCESSOR')
        self.assertEqual(item.quantity, 5)

    def test_item_str(self):
        item = Item.objects.create(
            donation=self.donation,
            category='MONITOR',
            quantity=3,
        )
        self.assertIn('MONITOR', str(item))
        self.assertIn('3', str(item))

    def test_item_belongs_to_donation(self):
        item = Item.objects.create(
            donation=self.donation,
            category='MOBILE',
            quantity=10,
        )
        self.assertEqual(item.donation, self.donation)

    def test_deleting_donation_deletes_items(self):
        Item.objects.create(donation=self.donation, category='PRINTER', quantity=2)
        donation_id = self.donation.pk
        self.donation.delete()
        self.assertEqual(Item.objects.filter(donation_id=donation_id).count(), 0)


class CollectionModelTest(TestCase):

    def setUp(self):
        self.user = make_user()

    def test_default_status_is_draft(self):
        collection = make_collection(self.user)
        self.assertEqual(collection.status, 'draft')

    def test_collection_str(self):
        collection = make_collection(self.user)
        self.assertIn('draft', str(collection))

    def test_created_by_set_null_on_user_delete(self):
        collection = make_collection(self.user)
        self.user.delete()
        collection.refresh_from_db()
        self.assertIsNone(collection.created_by)

    def test_distance_can_be_null(self):
        collection = make_collection(self.user)
        self.assertIsNone(collection.total_distance_km)


class EmissionRecordModelTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.collection = make_collection(self.user, distance=50.0)

    def test_create_emission_record(self):
        record = EmissionRecord.objects.create(
            collection=self.collection,
            co2_kg=12.5,
            fuel_litres_used=5.4,
            distance_km=50.0,
        )
        self.assertEqual(record.co2_kg, 12.5)
        self.assertEqual(record.collection, self.collection)

    def test_one_to_one_constraint(self):
        EmissionRecord.objects.create(
            collection=self.collection,
            co2_kg=12.5,
            fuel_litres_used=5.4,
            distance_km=50.0,
        )
        with self.assertRaises(IntegrityError):
            EmissionRecord.objects.create(
                collection=self.collection,
                co2_kg=9.0,
                fuel_litres_used=4.0,
                distance_km=50.0,
            )

    def test_deleting_collection_deletes_emission_record(self):
        record = EmissionRecord.objects.create(
            collection=self.collection,
            co2_kg=12.5,
            fuel_litres_used=5.4,
            distance_km=50.0,
        )
        record_id = record.pk
        self.collection.delete()
        self.assertFalse(EmissionRecord.objects.filter(pk=record_id).exists())


class SystemSettingsModelTest(TestCase):

    def test_defaults(self):
        settings = SystemSettings.objects.create()
        self.assertEqual(settings.fuel_efficiency_km_per_litre, 8.8)
        self.assertEqual(settings.co2_per_litre_kg, 2.31)

    def test_str(self):
        settings = SystemSettings.objects.create()
        self.assertEqual(str(settings), 'System Settings')

    def test_custom_values(self):
        settings = SystemSettings.objects.create(
            fuel_efficiency_km_per_litre=10.0,
            co2_per_litre_kg=2.5,
        )
        self.assertEqual(settings.fuel_efficiency_km_per_litre, 10.0)


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

    def test_create_user_email_case_insensitive_duplicate(self):
        AuthService.create_user('Test@Example.com', 'Pass123!', 'A', 'A')
        with self.assertRaises(ValueError):
            AuthService.create_user('test@example.com', 'Pass123!', 'B', 'B')

    def test_create_admin_user(self):
        user = AuthService.create_user('admin@a.com', 'Pass123!', 'A', 'A', is_admin=True)
        self.assertTrue(user.is_admin)

    def test_verify_user_correct_credentials(self):
        AuthService.create_user('v@v.com', 'Pass123!', 'V', 'V')
        user = AuthService.verify_user('v@v.com', 'Pass123!')
        self.assertIsNotNone(user)

    def test_verify_user_wrong_password(self):
        AuthService.create_user('v@v.com', 'Pass123!', 'V', 'V')
        user = AuthService.verify_user('v@v.com', 'WrongPass!')
        self.assertIsNone(user)

    def test_verify_user_nonexistent_email(self):
        user = AuthService.verify_user('nobody@example.com', 'Pass123!')
        self.assertIsNone(user)

    def test_edit_user_success(self):
        user = AuthService.create_user('e@e.com', 'Pass123!', 'Old', 'Name')
        AuthService.edit_user(user.pk, 'e@e.com', 'New', 'Name', False)
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'New')

    def test_edit_user_email_taken_by_other_raises(self):
        user1 = AuthService.create_user('u1@e.com', 'Pass123!', 'U', '1')
        user2 = AuthService.create_user('u2@e.com', 'Pass123!', 'U', '2')
        with self.assertRaises(ValueError):
            AuthService.edit_user(user2.pk, 'u1@e.com', 'U', '2', False)

    def test_edit_user_same_email_does_not_raise(self):
        user = AuthService.create_user('same@e.com', 'Pass123!', 'U', 'U')
        AuthService.edit_user(user.pk, 'same@e.com', 'Updated', 'U', False)
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Updated')

    def test_delete_user_returns_true(self):
        user = AuthService.create_user('del@e.com', 'Pass123!', 'D', 'D')
        result = AuthService.delete_user(user.pk)
        self.assertTrue(result)

    def test_delete_nonexistent_user_returns_false(self):
        result = AuthService.delete_user(99999)
        self.assertFalse(result)


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
            'collection_address': 'Town Hall, Bolton, BL1 1RU',
            'data_destruction_required': True,
            'notes': 'Call ahead.',
        }

    def _items_data(self):
        return [
            {'category': 'PROCESSOR', 'quantity': 5, 'weight': None, 'other_description': ''},
            {'category': 'MONITOR', 'quantity': 3, 'weight': None, 'other_description': ''},
        ]

    def test_generate_reference_id_format(self):
        ref = DonationService.generate_reference_id()
        self.assertTrue(ref.startswith('RIT-'))
        parts = ref.split('-')
        self.assertEqual(len(parts), 3)
        self.assertEqual(len(parts[1]), 8)
        self.assertEqual(len(parts[2]), 4)

    def test_reference_ids_are_unique(self):
        refs = {DonationService.generate_reference_id() for _ in range(100)}
        self.assertEqual(len(refs), 100)

    def test_create_donation_creates_donor(self):
        donation, ref = DonationService.create_donation(
            self._donor_data(), self._donation_data(), self._items_data()
        )
        self.assertEqual(Donor.objects.count(), 1)
        self.assertEqual(donation.donor.company_name, 'Bolton Council')

    def test_create_donation_creates_items(self):
        donation, ref = DonationService.create_donation(
            self._donor_data(), self._donation_data(), self._items_data()
        )
        self.assertEqual(donation.items.count(), 2)

    def test_create_donation_returns_reference_id(self):
        donation, ref = DonationService.create_donation(
            self._donor_data(), self._donation_data(), self._items_data()
        )
        self.assertTrue(ref.startswith('RIT-'))
        self.assertEqual(donation.reference_id, ref)

    def test_create_donation_duplicate_donor_not_duplicated(self):
        DonationService.create_donation(
            self._donor_data(), self._donation_data(), self._items_data()
        )
        DonationService.create_donation(
            self._donor_data(), self._donation_data(), self._items_data()
        )
        self.assertEqual(Donor.objects.count(), 1)
        self.assertEqual(Donation.objects.count(), 2)

    def test_create_donation_default_approval_status(self):
        donation, _ = DonationService.create_donation(
            self._donor_data(), self._donation_data(), self._items_data()
        )
        self.assertEqual(donation.approval_status, 'awaiting_review')

    def test_toggle_approval_status_approve(self):
        donation, _ = DonationService.create_donation(
            self._donor_data(), self._donation_data(), self._items_data()
        )
        updated = DonationService.toggle_approval_status(donation.pk, 'approved')
        self.assertEqual(updated.approval_status, 'approved')

    def test_toggle_approval_status_reject_with_reason(self):
        donation, _ = DonationService.create_donation(
            self._donor_data(), self._donation_data(), self._items_data()
        )
        updated = DonationService.toggle_approval_status(
            donation.pk, 'rejected', rejection_reason='Outside collection area.'
        )
        self.assertEqual(updated.approval_status, 'rejected')
        self.assertEqual(updated.rejection_reason, 'Outside collection area.')

    def test_get_donations_returns_all(self):
        DonationService.create_donation(self._donor_data('a@a.com'), self._donation_data(), self._items_data())
        DonationService.create_donation(self._donor_data('b@b.com'), self._donation_data(), self._items_data())
        results = DonationService.get_donations()
        self.assertEqual(results.count(), 2)

    def test_get_donations_filter_by_approval_status(self):
        donation, _ = DonationService.create_donation(
            self._donor_data(), self._donation_data(), self._items_data()
        )
        DonationService.toggle_approval_status(donation.pk, 'approved')
        results = DonationService.get_donations(filters={'approval_status': 'approved'})
        self.assertEqual(results.count(), 1)

    def test_get_donation_by_id(self):
        donation, _ = DonationService.create_donation(
            self._donor_data(), self._donation_data(), self._items_data()
        )
        fetched = DonationService.get_donation_by_id(donation.pk)
        self.assertEqual(fetched.pk, donation.pk)


# ══════════════════════════════════════════════════════════════════════════════
#  COLLECTION SERVICE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class CollectionServiceTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.donor = make_donor()

    def test_create_collection_success(self):
        collection = CollectionService.create_collection(self.user, status='draft')
        self.assertEqual(collection.status, 'draft')
        self.assertEqual(collection.created_by, self.user)

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

    def test_add_already_assigned_donation_fails(self):
        collection1 = make_collection(self.user)
        collection2 = make_collection(self.user)
        donation = make_donation(self.donor, approval_status='approved')
        CollectionService.add_donation(collection1.pk, donation.pk)
        success, msg = CollectionService.add_donation(collection2.pk, donation.pk)
        self.assertFalse(success)
        self.assertIn('already assigned', msg)

    def test_add_nonexistent_donation_fails(self):
        collection = make_collection(self.user)
        success, msg = CollectionService.add_donation(collection.pk, 99999)
        self.assertFalse(success)

    def test_remove_donation_success(self):
        collection = make_collection(self.user)
        donation = make_donation(self.donor, collection=collection, approval_status='approved')
        success, msg = CollectionService.remove_donation(donation.pk)
        self.assertTrue(success)
        donation.refresh_from_db()
        self.assertIsNone(donation.collection)

    def test_remove_nonexistent_donation_returns_false(self):
        success, msg = CollectionService.remove_donation(99999)
        self.assertFalse(success)

    def test_update_status(self):
        collection = make_collection(self.user, status='draft')
        updated = CollectionService.update_status(collection.pk, 'scheduled')
        self.assertEqual(updated.status, 'scheduled')

    def test_get_unassigned_donations_only_approved(self):
        make_donation(self.donor, approval_status='awaiting_review')
        approved = make_donation(
            make_donor('other@example.com'),
            approval_status='approved'
        )
        results = CollectionService.get_unassigned_donations()
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().pk, approved.pk)

    def test_get_unassigned_excludes_assigned(self):
        collection = make_collection(self.user)
        donation = make_donation(self.donor, collection=collection, approval_status='approved')
        results = CollectionService.get_unassigned_donations()
        self.assertEqual(results.count(), 0)

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
        # 44 / 8.8 = 5.0 litres
        # 5.0 * 2.31 = 11.55 kg CO2
        self.assertAlmostEqual(record.fuel_litres_used, 5.0, places=1)
        self.assertAlmostEqual(record.co2_kg, 11.55, places=1)

    def test_calculate_emissions_no_distance_returns_none(self):
        collection = make_collection(self.user)
        result = EmissionsService.calculate_emissions(collection.pk)
        self.assertIsNone(result)

    def test_calculate_emissions_creates_record(self):
        collection = make_collection(self.user, distance=30.0)
        EmissionsService.calculate_emissions(collection.pk)
        self.assertEqual(EmissionRecord.objects.filter(collection=collection).count(), 1)

    def test_calculate_emissions_update_or_create(self):
        collection = make_collection(self.user, distance=30.0)
        EmissionsService.calculate_emissions(collection.pk)
        collection.total_distance_km = 60.0
        collection.save()
        EmissionsService.calculate_emissions(collection.pk)
        self.assertEqual(EmissionRecord.objects.filter(collection=collection).count(), 1)
        record = EmissionRecord.objects.get(collection=collection)
        self.assertEqual(record.distance_km, 60.0)

    def test_calculate_emissions_uses_custom_settings(self):
        SystemSettings.objects.create(
            fuel_efficiency_km_per_litre=10.0,
            co2_per_litre_kg=2.5,
        )
        collection = make_collection(self.user, distance=100.0)
        record = EmissionsService.calculate_emissions(collection.pk)
        # 100 / 10 = 10.0 litres
        # 10.0 * 2.5 = 25.0 kg CO2
        self.assertAlmostEqual(record.fuel_litres_used, 10.0, places=1)
        self.assertAlmostEqual(record.co2_kg, 25.0, places=1)

    def test_calculate_emissions_fallback_defaults_when_no_settings(self):
        collection = make_collection(self.user, distance=88.0)
        record = EmissionsService.calculate_emissions(collection.pk)
        # 88 / 8.8 = 10.0 litres (default efficiency)
        self.assertAlmostEqual(record.fuel_litres_used, 10.0, places=1)

    def test_get_emission_record_returns_record(self):
        collection = make_collection(self.user, distance=50.0)
        EmissionsService.calculate_emissions(collection.pk)
        record = EmissionsService.get_emission_record(collection.pk)
        self.assertIsNotNone(record)
        self.assertEqual(record.distance_km, 50.0)

    def test_get_emission_record_returns_none_when_missing(self):
        collection = make_collection(self.user)
        record = EmissionsService.get_emission_record(collection.pk)
        self.assertIsNone(record)