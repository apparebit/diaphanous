# You are not drunk. Python is.
__all__ = (
    '__version__',
    'REPORTS_PER_PLATFORM',
    'ingest_reports_per_platform',
    'reshape_reports_per_platform',
    'encode_reports_per_platform',
    'compare_all_platform_reports',
    'YEAR_LABELS',
    'ingest_reports_per_country',
    'without_populations',
    'reports_per_capita_country_year',
    'create_map',
    'DisplayMethod',
    'show_map',
    'show',
    'to_schema',
)

__version__ = "1.0b1"

# CSAM Reports per Platform
from .platform.data import REPORTS_PER_PLATFORM
from .platform.ingest import ingest_reports_per_platform, reshape_reports_per_platform
from .platform.export import encode_reports_per_platform
from .platform.compare import compare_all_platform_reports

# CSAM Reports per Country
from .country import (
    YEAR_LABELS,
    ingest_reports_per_country,
    without_populations,
    reports_per_capita_country_year,
)
from .mapping import create_map, DisplayMethod, show_map

# Help display things
from .show import show, to_schema
