from collections.abc import Sequence
from typing import Literal, TypeAlias, TypedDict


CellType: TypeAlias = None | int | float | str
RowType: TypeAlias = dict[str, bool | Sequence[CellType]]
SchemaEntryType: TypeAlias = Literal["int", "float", "string"]
HistoryType: TypeAlias = Literal[
    "data", "same page (dropdown)", "same page (tabs)", "page archive"
]


class MetadataType(TypedDict):
    """A dictionary with metadata about the dataset."""

    author: str
    title: str
    version: str
    date: str
    url: str


class FeatureType(TypedDict):
    """"A dictionary with qualitative data about transparency disclosure."""
    data: None | Literal["csv"]
    history: None | HistoryType
    terms: tuple[str, ...]
    quantities: Literal["counts", "fractions", "rounded"]


class DisclosureType(TypedDict, total=False):
    """A dictionary with a specific platform's transparency disclosures."""

    brands: Sequence[str]
    comments: Sequence[str]
    sources: Sequence[str]
    features: FeatureType

    # Table with quantitative data
    columns: Sequence[str]
    rows: Sequence[RowType]
    schema: dict[str, SchemaEntryType]


# The dictionary with social media transparency disclosures.
DisclosureCollectionType = TypedDict(
    "DisclosureCollectionType",
    {
        "@": "MetadataType",
        "Automattic": "DisclosureType",
        "Facebook": "DisclosureType",
        "Google": "DisclosureType",
        "Instagram": "DisclosureType",
        "LinkedIn": "DisclosureType",
        "Meta": "DisclosureType",
        "Pinterest": "DisclosureType",
        "Quora": "DisclosureType",
        "Reddit": "DisclosureType",
        "Snap": "DisclosureType",
        "Telegram": None,
        "TikTok": "DisclosureType",
        "Tumblr": "DisclosureType",
        "Twitter": "DisclosureType",
        "WhatsApp": "DisclosureType",
        "Wordpress": "DisclosureType",
        "YouTube": "DisclosureType",
        "NCMEC": "DisclosureType",
    },
)
