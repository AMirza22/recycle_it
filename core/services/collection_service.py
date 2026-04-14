from django.db import transaction
from ..models import Collection, Donation


class CollectionService:

    @staticmethod
    @transaction.atomic
    def create_collection(user, scheduled_datetime=None, driver_name='', vehicle_id='', status='draft'):
        collection = Collection.objects.create(
            created_by=user,
            scheduled_datetime=scheduled_datetime,
            driver_name=driver_name,
            vehicle_id=vehicle_id,
            status=status,
        )
        return collection

    @staticmethod
    def get_collections(filters=None):
        queryset = Collection.objects.prefetch_related('donations__donor').order_by('-scheduled_datetime')

        if filters:
            if filters.get('status'):
                queryset = queryset.filter(status=filters['status'])
            if filters.get('created_by'):
                queryset = queryset.filter(created_by=filters['created_by'])

        return queryset

    @staticmethod
    def get_collection_by_id(collection_id):
        return Collection.objects.prefetch_related('donations__donor').get(pk=collection_id)

    @staticmethod
    def add_donation(collection_id, donation_id):
        try:
            donation = Donation.objects.get(pk=donation_id)
        except Donation.DoesNotExist:
            return False, 'Donation not found.'

        if donation.approval_status != 'approved':
            return False, 'Only approved donations can be assigned to a collection.'

        if donation.collection_id is not None:
            return False, 'This donation is already assigned to a collection.'

        donation.collection_id = collection_id
        donation.save()
        return True, 'Donation added successfully.'

    @staticmethod
    def remove_donation(donation_id):
        try:
            donation = Donation.objects.get(pk=donation_id)
        except Donation.DoesNotExist:
            return False, 'Donation not found.'

        donation.collection = None
        donation.save()
        return True, 'Donation removed from collection.'

    @staticmethod
    def update_status(collection_id, new_status):
        collection = Collection.objects.get(pk=collection_id)
        collection.status = new_status
        collection.save()
        return collection

    @staticmethod
    def get_unassigned_donations():
        return Donation.objects.filter(
            approval_status='approved',
            collection__isnull=True,
        ).select_related('donor').order_by('-created_at')

    @staticmethod
    def get_collection_stats(collection):
        donations = collection.donations.all()
        donation_count = donations.count()
        total_items = sum(
            item.quantity
            for donation in donations
            for item in donation.items.all()
        )
        return {
            'donation_count': donation_count,
            'total_items': total_items,
        }