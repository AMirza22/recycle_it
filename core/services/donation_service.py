import random
import string
from datetime import datetime
from django.core.mail import send_mail
from django.db import transaction
from ..models import Donor, Donation, Item


class DonationService:

    @staticmethod
    def generate_reference_id():
        date_str = datetime.now().strftime('%Y%m%d')
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f'RIT-{date_str}-{suffix}'

    @staticmethod
    @transaction.atomic
    def create_donation(donor_data, donation_data, items_data):
        donor, created = Donor.objects.get_or_create(
            contact_email__iexact=donor_data['contact_email'],
            defaults=donor_data,
        )

        if not created:
            for field, value in donor_data.items():
                setattr(donor, field, value)
            donor.save()

        reference_id = DonationService.generate_reference_id()

        donation = Donation.objects.create(
            donor=donor,
            reference_id=reference_id,
            **donation_data,
        )

        for item_data in items_data:
            Item.objects.create(donation=donation, **item_data)

        return donation, reference_id

    @staticmethod
    def get_donations(filters=None):
        queryset = Donation.objects.select_related('donor', 'collection').order_by('-created_at')

        if filters:
            if filters.get('approval_status'):
                queryset = queryset.filter(approval_status=filters['approval_status'])
            if filters.get('status'):
                queryset = queryset.filter(status=filters['status'])
            if filters.get('donor_id'):
                queryset = queryset.filter(donor_id=filters['donor_id'])

        return queryset

    @staticmethod
    def get_donation_by_id(donation_id):
        return Donation.objects.select_related('donor', 'collection').get(pk=donation_id)

    @staticmethod
    def toggle_approval_status(donation_id, new_status, rejection_reason=''):
        donation = Donation.objects.get(pk=donation_id)
        donation.approval_status = new_status
        if rejection_reason:
            donation.rejection_reason = rejection_reason
        donation.save()
        return donation

    @staticmethod
    def send_confirmation_email(donation, reference_id):
        send_mail(
            subject=f'Recycle-IT! — Collection Request Received ({reference_id})',
            message=(
                f'Dear {donation.donor.contact_person},\n\n'
                f'Thank you for submitting your collection request.\n\n'
                f'Your reference ID is: {reference_id}\n'
                f'Collection address: {donation.full_address}\n\n'
                f'A member of our team will review your request shortly.\n\n'
                f'Kind regards,\n'
                f'The Recycle-IT! Team\n'
                f'01204 356996 | info@recycle-it.org.uk'
            ),
            from_email='info@recycle-it.org.uk',
            recipient_list=[donation.donor.contact_email],
            fail_silently=True,
        )

    @staticmethod
    def send_approval_email(donation):
        send_mail(
            subject=f'Recycle-IT! — Collection Request Approved ({donation.reference_id})',
            message=(
                f'Dear {donation.donor.contact_person},\n\n'
                f'Your collection request ({donation.reference_id}) has been approved.\n\n'
                f'We will be in touch to confirm your collection date and time.\n\n'
                f'Kind regards,\n'
                f'The Recycle-IT! Team'
            ),
            from_email='info@recycle-it.org.uk',
            recipient_list=[donation.donor.contact_email],
            fail_silently=True,
        )

    @staticmethod
    def send_rejection_email(donation, rejection_reason):
        send_mail(
            subject=f'Recycle-IT! — Collection Request Update ({donation.reference_id})',
            message=(
                f'Dear {donation.donor.contact_person},\n\n'
                f'Unfortunately your collection request ({donation.reference_id}) '
                f'could not be accepted at this time.\n\n'
                f'Reason: {rejection_reason}\n\n'
                f'Please contact us if you have any questions.\n\n'
                f'Kind regards,\n'
                f'The Recycle-IT! Team'
            ),
            from_email='info@recycle-it.org.uk',
            recipient_list=[donation.donor.contact_email],
            fail_silently=True,
        )