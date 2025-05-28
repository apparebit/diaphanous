# You are not drunk. Python is.
__all__ = (
    '__version__',
    'annualize',
    'combine_brands',
    'compare_all_platform_reports',
    'compare_platform_reports',
    'create_map',
    'delete_latex_tables',
    'DisplayMethod',
    'encode_reports_per_platform',
    'fetch_populations',
    'ingest_reports_per_country',
    'ingest_reports_per_platform',
    'long_ncmec_reports',
    'REPORT_TOTALS',
    'reports_per_country_year',
    'REPORTS_PER_PLATFORM',
    'show',
    'show_map',
    'to_schema',
    'wide_ncmec_reports',
    'without_populations',
    'YEAR_LABELS',
)

__version__ = "0.1"

# CSAM Reports per Platform
from .platform.data import REPORTS_PER_PLATFORM
from .platform.ingest import (
    ingest_reports_per_platform,
    wide_ncmec_reports,
    long_ncmec_reports,
    combine_brands,
)
from .platform.export import encode_reports_per_platform
from .platform.compare import (
    annualize, compare_all_platform_reports, compare_platform_reports
)

# CSAM Reports per Country
from .fetch import fetch_populations

from .country import (
    REPORT_TOTALS,
    YEAR_LABELS,
    ingest_reports_per_country,
    without_populations,
    reports_per_country_year,
)
from .mapping import create_map, DisplayMethod, show_map

# Help display things
from .show import delete_latex_tables, show, to_schema
