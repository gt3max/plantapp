"""
Configuration for plant-parser.
API keys from environment variables, Turso connection settings.
"""
import os
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent  # plantapp/
DATA_DIR = PROJECT_ROOT / 'data' / 'plants'
POPULAR_PLANTS_TS = PROJECT_ROOT / 'src' / 'constants' / 'popular-plants.ts'

# Turso DB
TURSO_DB_URL = os.environ.get('TURSO_DB_URL', '')
TURSO_AUTH_TOKEN = os.environ.get('TURSO_AUTH_TOKEN', '')

# API keys (optional, for enrichment)
TREFLE_API_KEY = os.environ.get('TREFLE_API_KEY', '')
PERENUAL_API_KEY = os.environ.get('PERENUAL_API_KEY', '')

# Wikipedia
WIKI_REST_BASE = 'https://en.wikipedia.org/api/rest_v1'
WIKIDATA_API = 'https://www.wikidata.org/w/api.php'

# Trefle
TREFLE_API_BASE = 'https://trefle.io/api/v1'

# Perenual
PERENUAL_API_BASE = 'https://perenual.com/api'

# Rate limits
WIKIPEDIA_DELAY = 0.1   # seconds between requests (polite)
TREFLE_DELAY = 0.5      # 120 req/min = ~0.5s
PERENUAL_DELAY = 1.0    # 100/day — be conservative

# Schema version
SCHEMA_VERSION = 1
