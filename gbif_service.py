import requests
import time
from typing import List, Dict, Callable, Optional
from config import Config


class GBIFService:
    """Service for interacting with the GBIF API"""

    def __init__(self):
        self.base_url = Config.GBIF_OCCURRENCE_SEARCH_URL
        self.limit = Config.GBIF_SEARCH_LIMIT
        self.timeout = Config.GBIF_REQUEST_TIMEOUT
        self.max_retries = Config.GBIF_MAX_RETRIES
        self.retry_delay = Config.GBIF_RETRY_DELAY

    def search_by_person(
        self,
        person_name: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Dict]:
        """
        Search GBIF for all occurrences associated with a person name.

        Args:
            person_name: Name of the person (recorder, collector, identifier, etc.)
            progress_callback: Optional callback function(fetched_count, total_count)

        Returns:
            List of occurrence dictionaries

        Raises:
            requests.RequestException: If API request fails after retries
        """
        all_results = []
        offset = 0
        total_count = None

        while True:
            # Fetch a batch of results
            data = self._fetch_batch(person_name, offset)

            if data is None:
                # Error occurred and retries exhausted
                break

            results = data.get('results', [])
            all_results.extend(results)

            # Get total count from first response
            if total_count is None:
                total_count = data.get('count', 0)

            # Progress callback
            if progress_callback:
                progress_callback(len(all_results), total_count)

            # Check if we've fetched all results
            if len(results) < self.limit:
                break

            offset += self.limit

        return all_results

    def _fetch_batch(self, person_name: str, offset: int) -> Optional[Dict]:
        """
        Fetch a single batch of results with retry logic.

        Args:
            person_name: Name of the person to search for
            offset: Offset for pagination

        Returns:
            Response data dictionary or None if all retries fail
        """
        params = {
            'recordedBy': person_name,
            'limit': self.limit,
            'offset': offset
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    self.base_url,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()

            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    raise Exception(f"Request timed out after {self.max_retries} attempts")

            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    raise Exception(f"Request failed after {self.max_retries} attempts: {str(e)}")

        return None

    @staticmethod
    def parse_occurrence(record: Dict) -> Dict:
        """
        Parse a GBIF occurrence record and extract relevant fields.

        Args:
            record: Raw GBIF occurrence record

        Returns:
            Dictionary with cleaned and organized occurrence data
        """
        def safe_get(data: Dict, key: str, default=None):
            """Safely get value from dictionary"""
            return data.get(key, default)

        # Build GBIF URL
        gbif_id = safe_get(record, 'key')
        gbif_url = f"https://www.gbif.org/occurrence/{gbif_id}" if gbif_id else None

        return {
            'gbif_id': str(gbif_id) if gbif_id else None,
            'occurrence_key': safe_get(record, 'occurrenceID'),

            # Person-related
            'recorded_by': safe_get(record, 'recordedBy'),
            'identified_by': safe_get(record, 'identifiedBy'),
            'associated_persons': None,  # Could be extracted from extensions

            # Taxonomy
            'scientific_name': safe_get(record, 'scientificName'),
            'kingdom': safe_get(record, 'kingdom'),
            'phylum': safe_get(record, 'phylum'),
            'class_name': safe_get(record, 'class'),
            'order': safe_get(record, 'order'),
            'family': safe_get(record, 'family'),
            'genus': safe_get(record, 'genus'),
            'species': safe_get(record, 'species'),
            'taxon_rank': safe_get(record, 'taxonRank'),

            # Location
            'country': safe_get(record, 'country'),
            'country_code': safe_get(record, 'countryCode'),
            'state_province': safe_get(record, 'stateProvince'),
            'locality': safe_get(record, 'locality'),
            'decimal_latitude': safe_get(record, 'decimalLatitude'),
            'decimal_longitude': safe_get(record, 'decimalLongitude'),
            'coordinate_uncertainty': safe_get(record, 'coordinateUncertaintyInMeters'),
            'elevation': safe_get(record, 'elevation'),

            # Date
            'event_date': safe_get(record, 'eventDate'),
            'year': safe_get(record, 'year'),
            'month': safe_get(record, 'month'),
            'day': safe_get(record, 'day'),

            # Data quality
            'basis_of_record': safe_get(record, 'basisOfRecord'),
            'identification_verification_status': safe_get(record, 'identificationVerificationStatus'),
            'coordinate_precision': safe_get(record, 'coordinatePrecision'),
            'issues': ','.join(safe_get(record, 'issues', [])),

            # Institution
            'institution_code': safe_get(record, 'institutionCode'),
            'collection_code': safe_get(record, 'collectionCode'),
            'catalog_number': safe_get(record, 'catalogNumber'),

            # Links
            'gbif_url': gbif_url
        }
