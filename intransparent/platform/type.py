from collections.abc import Sequence
from typing import Literal, TypedDict

CellType = None | int | float | str
RowType = dict[str, bool | Sequence[CellType]]


class CitationType(TypedDict):
    """A dictionary with metadata about the dataset."""

    author: str
    title: str
    version: str
    date: str
    doi: str
    url: str


class DisclosureType(TypedDict, total=False):
    """A dictionary with a specific platform's transparency disclosures."""

    brands: Sequence[str]
    comments: Sequence[str]
    sources: Sequence[str]

    # Table with quantitative data
    row_index: Literal["period", "platform"]
    columns: Sequence[str]
    rows: Sequence[RowType]
    nonintegers: Sequence[str]


# The dictionary with social media transparency disclosures.
DisclosureCollectionType = TypedDict(
    "DisclosureCollectionType",
    {
        "@": "CitationType",
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
