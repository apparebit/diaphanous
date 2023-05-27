# Handle Dataset 1: CSAM Reports per Platform
from .platform.data import REPORTS_PER_PLATFORM
from .platform.ingest import ingest_reports_per_platform
from .platform.export import export_reports_per_platform
from .platform.compare import compare_all_platform_reports

# Handle Dataset 2: CSAM Reports per Country
from .country import (
    ingest_reports_per_country,
    without_populations,
)

# Shared utilities for nicely rendering tables
from .display import (
    # In terminal or LaTeX
    format_text,
    format_latex,

    # In HTML
    show_html,
    show_info,
    show_table,
)
