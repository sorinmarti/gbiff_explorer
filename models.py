from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Search(db.Model):
    """Model for storing search queries"""
    __tablename__ = 'searches'

    id = db.Column(db.Integer, primary_key=True)
    person_name = db.Column(db.String(200), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    result_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='pending')  # pending, downloading, completed, error
    error_message = db.Column(db.Text)

    # Relationship to occurrences
    occurrences = db.relationship('Occurrence', backref='search', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Search {self.id}: {self.person_name}>'


class Occurrence(db.Model):
    """Model for storing GBIF occurrence records"""
    __tablename__ = 'occurrences'

    id = db.Column(db.Integer, primary_key=True)
    search_id = db.Column(db.Integer, db.ForeignKey('searches.id'), nullable=False, index=True)

    # GBIF identifiers
    gbif_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    occurrence_key = db.Column(db.String(100))

    # Person-related fields (MOST IMPORTANT)
    recorded_by = db.Column(db.String(500), index=True)
    identified_by = db.Column(db.String(500), index=True)
    associated_persons = db.Column(db.Text)  # JSON or comma-separated

    # Taxonomy
    scientific_name = db.Column(db.String(500), index=True)
    kingdom = db.Column(db.String(100))
    phylum = db.Column(db.String(100))
    class_name = db.Column('class', db.String(100))
    order = db.Column(db.String(100))
    family = db.Column(db.String(100), index=True)
    genus = db.Column(db.String(100), index=True)
    species = db.Column(db.String(100))
    taxon_rank = db.Column(db.String(50))

    # Location
    country = db.Column(db.String(100), index=True)
    country_code = db.Column(db.String(10))
    state_province = db.Column(db.String(200))
    locality = db.Column(db.Text)
    decimal_latitude = db.Column(db.Float)
    decimal_longitude = db.Column(db.Float)
    coordinate_uncertainty = db.Column(db.Float)
    elevation = db.Column(db.Float)

    # Date
    event_date = db.Column(db.String(100))
    year = db.Column(db.Integer, index=True)
    month = db.Column(db.Integer)
    day = db.Column(db.Integer)

    # Data quality
    basis_of_record = db.Column(db.String(100))
    identification_verification_status = db.Column(db.String(100))
    coordinate_precision = db.Column(db.Float)
    issues = db.Column(db.Text)  # JSON array of issue flags

    # Institution
    institution_code = db.Column(db.String(100))
    collection_code = db.Column(db.String(100))
    catalog_number = db.Column(db.String(100))

    # Links
    gbif_url = db.Column(db.String(500))

    # Metadata
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Occurrence {self.gbif_id}: {self.scientific_name}>'

    def to_dict(self):
        """Convert occurrence to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'gbif_id': self.gbif_id,
            'recorded_by': self.recorded_by,
            'identified_by': self.identified_by,
            'scientific_name': self.scientific_name,
            'family': self.family,
            'genus': self.genus,
            'species': self.species,
            'country': self.country,
            'locality': self.locality,
            'decimal_latitude': self.decimal_latitude,
            'decimal_longitude': self.decimal_longitude,
            'coordinate_uncertainty': self.coordinate_uncertainty,
            'event_date': self.event_date,
            'year': self.year,
            'month': self.month,
            'day': self.day,
            'basis_of_record': self.basis_of_record,
            'identification_verification_status': self.identification_verification_status,
            'institution_code': self.institution_code,
            'collection_code': self.collection_code,
            'catalog_number': self.catalog_number,
            'gbif_url': self.gbif_url
        }
