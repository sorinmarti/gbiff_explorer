import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Application configuration"""

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'gbif_explorer.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # GBIF API settings
    GBIF_API_BASE_URL = 'https://api.gbif.org/v1'
    GBIF_OCCURRENCE_SEARCH_URL = f'{GBIF_API_BASE_URL}/occurrence/search'
    GBIF_SEARCH_LIMIT = 300  # Max records per request
    GBIF_REQUEST_TIMEOUT = 30  # Seconds
    GBIF_MAX_RETRIES = 3
    GBIF_RETRY_DELAY = 2  # Seconds

    # Pagination settings
    RESULTS_PER_PAGE = 50
