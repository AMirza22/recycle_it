from django.db import transaction
from ..models import EmissionRecord, SystemSettings, Collection


class EmissionsService:

    @staticmethod
    def _get_formula_constants():
        try:
            settings = SystemSettings.objects.get(pk=1)
            return settings.fuel_efficiency_km_per_litre, settings.co2_per_litre_kg
        except SystemSettings.DoesNotExist:
            return 8.8, 2.31

    @staticmethod
    @transaction.atomic
    def calculate_emissions(collection_id):
        collection = Collection.objects.get(pk=collection_id)

        if not collection.total_distance_km:
            return None

        fuel_efficiency, co2_per_litre = EmissionsService._get_formula_constants()

        fuel_litres_used = collection.total_distance_km / fuel_efficiency
        co2_kg = fuel_litres_used * co2_per_litre

        record, created = EmissionRecord.objects.update_or_create(
            collection=collection,
            defaults={
                'co2_kg': round(co2_kg, 2),
                'fuel_litres_used': round(fuel_litres_used, 2),
                'distance_km': collection.total_distance_km,
            }
        )
        return record

    @staticmethod
    def get_emission_record(collection_id):
        try:
            return EmissionRecord.objects.get(collection_id=collection_id)
        except EmissionRecord.DoesNotExist:
            return None