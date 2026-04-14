import requests
from django.conf import settings
from ..models import Collection


class RouteService:

    DEPOT = [-2.4282, 53.5800]
    GEOCODE_URL = 'https://api.openrouteservice.org/geocode/search'
    OPTIMISE_URL = 'https://api.openrouteservice.org/optimization'
    DIRECTIONS_URL = 'https://api.openrouteservice.org/v2/directions/driving-hgv'

    @staticmethod
    def geocode_address(address):
        api_key = getattr(settings, 'ORS_API_KEY', None)
        if not api_key:
            return None

        try:
            response = requests.get(
                RouteService.GEOCODE_URL,
                params={
                    'api_key': api_key,
                    'text': address,
                    'boundary.country': 'GBR',
                    'focus.point.lon': RouteService.DEPOT[0],
                    'focus.point.lat': RouteService.DEPOT[1],
                    'size': 1,
                },
                timeout=10,
            )
            response.raise_for_status()
            features = response.json().get('features', [])
            if features:
                return features[0]['geometry']['coordinates']
        except requests.RequestException:
            return None

        return None

    @staticmethod
    def get_distance_km(ordered_coords):
        """
        Given a list of [lon, lat] coordinates in stop order,
        call the ORS directions API to get the actual route distance.
        Includes depot at start and end.
        """
        api_key = getattr(settings, 'ORS_API_KEY', None)
        if not api_key or not ordered_coords:
            return None

        # Full route: depot → stops → depot
        full_route = [RouteService.DEPOT] + ordered_coords + [RouteService.DEPOT]

        try:
            response = requests.post(
                RouteService.DIRECTIONS_URL,
                json={'coordinates': full_route},
                headers={
                    'Authorization': api_key,
                    'Content-Type': 'application/json',
                },
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            # ORS directions returns distance in metres
            distance_m = data['routes'][0]['summary']['distance']
            return round(distance_m / 1000, 2)
        except (requests.RequestException, KeyError, IndexError):
            return None

    @staticmethod
    def optimise_route(collection_id):
        collection = Collection.objects.prefetch_related(
            'donations__donor'
        ).get(pk=collection_id)
        donations = list(collection.donations.all())

        if not donations:
            return {
                'ordered_stops': [],
                'total_distance_km': 0,
                'optimised': False,
            }

        api_key = getattr(settings, 'ORS_API_KEY', None)
        if not api_key:
            return RouteService._fallback(donations)

        jobs = []
        stop_map = {}

        for index, donation in enumerate(donations):
            coords = RouteService.geocode_address(donation.collection_address)
            if not coords:
                return RouteService._fallback(donations)

            job_id = index + 1
            jobs.append({'id': job_id, 'location': coords})
            stop_map[job_id] = {
                'donation_id': donation.pk,
                'address': donation.collection_address,
                'donor': donation.donor.company_name,
                'coords': coords,
            }

        payload = {
            'jobs': jobs,
            'vehicles': [{
                'id': 1,
                'profile': 'driving-hgv',
                'start': RouteService.DEPOT,
                'end': RouteService.DEPOT,
            }],
        }

        try:
            response = requests.post(
                RouteService.OPTIMISE_URL,
                json=payload,
                headers={
                    'Authorization': api_key,
                    'Content-Type': 'application/json',
                },
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            routes = data.get('routes', [])
            if not routes:
                return RouteService._fallback(donations)

            # Extract optimised job order
            steps = [s for s in routes[0]['steps'] if s['type'] == 'job']
            ordered_stops = [stop_map[step['job']] for step in steps]

            # Get actual distance via directions API using optimised order
            ordered_coords = [stop['coords'] for stop in ordered_stops]
            total_distance_km = RouteService.get_distance_km(ordered_coords)

            # Fall back to duration-based estimate if directions call fails
            # duration is in seconds, assume 50 km/h average
            if total_distance_km is None:
                duration_seconds = routes[0].get('duration', 0)
                total_distance_km = round((duration_seconds / 3600) * 50, 2)

            # Save distance to collection
            collection.total_distance_km = total_distance_km
            collection.save()

            # Strip coords from stop data before returning
            for stop in ordered_stops:
                stop.pop('coords', None)

            return {
                'ordered_stops': ordered_stops,
                'total_distance_km': total_distance_km,
                'optimised': True,
            }

        except requests.RequestException:
            return RouteService._fallback(donations)

    @staticmethod
    def _fallback(donations):
        ordered_stops = [
            {
                'donation_id': d.pk,
                'address': d.collection_address,
                'donor': d.donor.company_name,
            }
            for d in donations
        ]
        return {
            'ordered_stops': ordered_stops,
            'total_distance_km': None,
            'optimised': False,
        }

    @staticmethod
    def get_route(collection_id):
        collection = Collection.objects.prefetch_related(
            'donations__donor'
        ).get(pk=collection_id)
        donations = list(collection.donations.all())
        return RouteService._fallback(donations)