# %%
from collections.abc import Sequence
import http
import json
from pathlib import Path
from urllib.request import Request, urlopen


def fetch_json(url: str) -> object:
    """Fetch the JSON payload from the given URL."""
    response = urlopen(Request(url))
    assert 200 <= response.status < 300
    return json.loads(response.read())


def fetch_locations() -> list[object]:
    """
    Fetch all locations supported by the UN API. This function transparently
    handles paged responses.
    """
    pages = []

    url = "https://population.un.org/dataportalapi/api/v1/locations?sort=id"
    while url is not None:
        page = fetch_json(url)
        pages.append(page)
        url = page.get("nextPage")

    countries = []
    for page in pages:
        countries.extend(page.get("data"))
    return countries


def format(data: Sequence[int | str]):
    """
    Format the sequence of integers or strings as clean looking Python source
    code. This function assumes that each item requires at most five characters,
    i.e., either is an ISO3 code or UN location ID.
    """
    fragments = ["[\n    "]
    for index, datum in enumerate(data):
        fragments.append(f"{json.dumps(datum)}, ")
        if index > 0 and index % 10 == 9:
            fragments.append("\n    ")
    return "".join(fragments) + "\n]\n"


# %%
# The universe of countries and territories
ISO3 = [
    "ABW", "AFG", "AGO", "AIA", "ALA", "ALB", "AND", "ANT", "ARE", "ARG",
    "ARM", "ASM", "ATA", "ATF", "ATG", "AUS", "AUT", "AZE", "BDI", "BEL",
    "BEN", "BES", "BFA", "BGD", "BGR", "BHR", "BHS", "BIH", "BLM", "BLR",
    "BLZ", "BMU", "BOL", "BRA", "BRB", "BRN", "BTN", "BVT", "BWA", "CAF",
    "CAN", "CCK", "CHE", "CHL", "CHN", "CIV", "CMR", "COD", "COG", "COK",
    "COL", "COM", "CPV", "CRI", "CUB", "CUW", "CXR", "CYM", "CYP", "CZE",
    "DEU", "DJI", "DMA", "DNK", "DOM", "DZA", "ECU", "EEE", "EGY", "ERI",
    "ESH", "ESP", "EST", "ETH", "FIN", "FJI", "FLK", "FRA", "FRO", "FSM",
    "GAB", "GBR", "GEO", "GGY", "GHA", "GIB", "GIN", "GLP", "GMB", "GNB",
    "GNQ", "GRC", "GRD", "GRL", "GTM", "GUF", "GUM", "GUY", "HKG", "HMD",
    "HND", "HRV", "HTI", "HUN", "IDN", "IMN", "IND", "IOT", "IRL", "IRN",
    "IRQ", "ISL", "ISR", "ITA", "JAM", "JEY", "JOR", "JPN", "KAZ", "KEN",
    "KGZ", "KHM", "KIR", "KNA", "KOR", "KWT", "LAO", "LBN", "LBR", "LBY",
    "LCA", "LIE", "LKA", "LSO", "LTU", "LUX", "LVA", "MAC", "MAF", "MAR",
    "MCO", "MDA", "MDG", "MDV", "MEX", "MHL", "MKD", "MLI", "MLT", "MMR",
    "MNE", "MNG", "MNP", "MOZ", "MRT", "MSR", "MTQ", "MUS", "MWI", "MYS",
    "MYT", "NAM", "NCL", "NER", "NFK", "NGA", "NIC", "NIU", "NLD", "NOR",
    "NPL", "NRU", "NZL", "OMN", "PAK", "PAN", "PCN", "PER", "PHL", "PLW",
    "PNG", "POL", "PRI", "PRK", "PRT", "PRY", "PSE", "PYF", "QAT", "REU",
    "ROU", "RUS", "RWA", "SAU", "SDN", "SEN", "SGP", "SGS", "SHN", "SJM",
    "SLB", "SLE", "SLV", "SMR", "SOM", "SPM", "SRB", "SSD", "STP", "SUR",
    "SVK", "SVN", "SWE", "SWZ", "SXM", "SYC", "SYR", "TCA", "TCD", "TGO",
    "THA", "TJK", "TKL", "TKM", "TLS", "TON", "TTO", "TUN", "TUR", "TUV",
    "TWN", "TZA", "UGA", "UKR", "UMI", "URY", "USA", "UZB", "VAT", "VCT",
    "VEN", "VGB", "VIR", "VNM", "VUT", "WLF", "WSM", "XKX", "YEM", "ZAF",
    "ZMB", "ZWE",
]

# The corresponding UN location IDs, though not necessarily in the same order.
IDENT = [
    4, 8, 12, 16, 20, 24, 28, 31, 32, 36,
    40, 44, 48, 50, 51, 52, 56, 60, 64, 68,
    70, 72, 76, 84, 90, 92, 96, 100, 104, 108,
    112, 116, 120, 124, 132, 136, 140, 144, 148, 152,
    156, 158, 170, 174, 175, 178, 180, 184, 188, 191,
    192, 196, 203, 204, 208, 212, 214, 218, 222, 226,
    231, 232, 233, 234, 238, 242, 246, 250, 254, 258,
    262, 266, 268, 270, 275, 276, 288, 292, 296, 300,
    304, 308, 312, 316, 320, 324, 328, 332, 336, 340,
    344, 348, 352, 356, 360, 364, 368, 372, 376, 380,
    384, 388, 392, 398, 400, 404, 408, 410, 412, 414,
    417, 418, 422, 426, 428, 430, 434, 438, 440, 442,
    446, 450, 454, 458, 462, 466, 470, 474, 478, 480,
    484, 492, 496, 498, 499, 500, 504, 508, 512, 516,
    520, 524, 528, 531, 533, 534, 535, 540, 548, 554,
    558, 562, 566, 570, 578, 580, 583, 584, 585, 586,
    591, 598, 600, 604, 608, 616, 620, 624, 626, 630,
    634, 638, 642, 643, 646, 652, 654, 659, 660, 662,
    663, 666, 670, 674, 678, 682, 686, 688, 690, 694,
    702, 703, 704, 705, 706, 710, 716, 724, 728, 729,
    732, 740, 748, 752, 756, 760, 762, 764, 768, 772,
    776, 780, 784, 788, 792, 795, 796, 798, 800, 804,
    807, 818, 826, 831, 832, 833, 834, 840, 850, 854,
    858, 860, 862, 876, 882, 887, 894,
]


# %%
def fetch_populations(
    path: str | Path,
    start: int = 2019,
    end: int = 2023,
    batch_size: int = 10,
) -> None:
    """
    Download UN population data for the given, inclusive range of years in CSV
    format to the given file system location. If the response is too big, the
    API does not return an error, but simply redirects to the homepage. Hence,
    this function batches countries. The default values for year range and batch
    size worked in April 2024.
    """
    count = len(IDENT)
    batch_count = count // batch_size
    if count % batch_size > 0:
        batch_count += 1

    print("Fetching UN population data...")

    all_lines = []
    for batch_index in range(batch_count):
        batch_start = batch_index * batch_size
        batch_end = min(count, (batch_index + 1) * batch_size)
        batch = IDENT[batch_start:batch_end]

        print(f"Fetching batch {batch_index + 1}/{batch_count}...")

        url = (
            "https://population.un.org/dataportalapi/api/v1/data/indicators/49/locations/"
            + ",".join(str(ident) for ident in batch)
            + f"/start/{start}/end/{end}?format=csv"
        )

        response = urlopen(Request(url))
        if not 200 <= response.status < 300:
            error = http.client.responses.get(http.HTTPStatus(response.status))
            raise AssertionError(error or str(response.status))

        lines = response.read().decode("utf8").splitlines()
        if not lines[0] == "sep =|":
            raise AssertionError("first line did not declare separator as 'sep =|'")

        # Keep line with column names only for first batch.
        line_start = 1 if batch_index == 0 else 2
        all_lines.extend(lines[line_start:])

    print(f'Saving UN population data to "{path}"...')

    with open(path, mode="w", encoding="utf8") as file:
        file.write("\n".join(all_lines) + "\n")
