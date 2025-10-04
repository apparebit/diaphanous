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
    granularity: str
    frequency: str
    coverage: str


class DisclosureType(TypedDict, total=False):
    """A dictionary with a specific platform's transparency disclosures."""

    aka: Sequence[str]
    brands: Sequence[str]
    comments: Sequence[str]
    sources: Sequence[str]
    features: FeatureType

    # Table with quantitative data
    columns: Sequence[str]
    rows: Sequence[RowType]
    schema: dict[str, SchemaEntryType]

    # Computed columns
    sums: dict[str, Sequence[str]]


# The dictionary with social media transparency disclosures.
DisclosureCollectionType = TypedDict(
    "DisclosureCollectionType",
    {
        "@": "MetadataType",
        "Alphabet": "DisclosureType",
        "Amazon": "DisclosureType",
        "Amino": "DisclosureType",
        "Apple": "DisclosureType",
        "Automattic": "DisclosureType",
        "Aylo": "DisclosureType",
        "Discord": "DisclosureType",
        "Facebook": "DisclosureType",
        "GitHub": "DisclosureType",
        "Google": "DisclosureType",
        "Imgur": "DisclosureType",
        "Instagram": "DisclosureType",
        "Kik": "DisclosureType",
        "LinkedIn": "DisclosureType",
        "MediaLab": "DisclosureType",
        "Meta": "DisclosureType",
        "Microsoft": "DisclosureType",
        "Omegle": "DisclosureType",
        "Pinterest": "DisclosureType",
        "Pornhub": "DisclosureType",
        "Quora": "DisclosureType",
        "Reddit": "DisclosureType",
        "Snap": "DisclosureType",
        "Telegram": None,
        "Threads": "DisclosureType",
        "TikTok": "DisclosureType",
        "Tumblr": "DisclosureType",
        "Twitch": "DisclosureType",
        "Twitter": "DisclosureType",
        "WhatsApp": "DisclosureType",
        "Wikimedia": "DisclosureType",
        "Wordpress": "DisclosureType",
        "X": "DisclosureType",
        "YouTube": "DisclosureType",
        "NCMEC": "DisclosureType",
    },
)
