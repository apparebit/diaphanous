from types import MappingProxyType
from typing import TYPE_CHECKING

from .type import DisclosureCollectionType
from .. import __version__


# Pylance does not recognize MappingProxyType as adhering to TypedDict declarations.
if TYPE_CHECKING:
    frozen = lambda x: x
else:
    frozen = MappingProxyType

REPORTS_PER_PLATFORM: DisclosureCollectionType = frozen({
    "@": frozen({
        # ──────────────────────────────────────────────────────────────
        "author": "Robert Grimm",
        "title": "Social Media CSAM Disclosures",
        "url": "https://github.com/apparebit/diaphanous",
        "version": __version__,
        # ──────────────────────────────────────────────────────────────
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Alphabet": frozen({
        "brands": ("Google", "YouTube"),
        "features": frozen({
            "social_media": False,
        }),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Amazon": frozen({
        "brands": ("Twitch",),
        "sources": (
            "https://www.aboutamazon.com/news/policy-news-views/amazon-csam-transparency-report-2025",
            "https://www.aboutamazon.com/news/policy-news-views/amazon-csam-transparency-report-2024",
            "https://www.aboutamazon.com/news/policy-news-views/amazon-csam-transparency-report-2023",
            "https://www.aboutamazon.com/news/policy-news-views/amazon-csam-transparency-report-2022",
            "https://www.aboutamazon.com/news/policy-news-views/our-efforts-to-combat-child-sexual-abuse-material-in-2021",
            "https://www.aboutamazon.com/news/community/ncmec-report",
        ),
        "features": frozen({
            "data": None,
            "history": "linked list of pages",
            "terms": ("CSAM",),
            "quantities": "counts",
            "granularity": "Y",
            "frequency": "Y",
            "coverage": "2020",
            "social_media": False,
        }),
        "columns": (
            "reports",
            "images",
            "other content reported by third parties",
            "reported by hotlines",
            "accounts",
        ),
        "sums": frozen({
            "pieces": ("images", "other content reported by third parties"),
        }),
        "rows": (
            #fmt: off
            {"2025": (26_500, 21_437, None, 676, 3_069)},
            {"2024": (64_195, 30_778, 337, 752, 3_959)},
            {"2023": (31_281, 24_653, 103, 611, 4_111)},
            {"2022": (67_073, 52_633, 23, 398, 7_322)},
            {"2021": (33_848, 25_540, 1_704, 780, 2_451)},
            {"2020": (2_235, None, None, None, None)},
            #fmt: on
        ),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Amino": frozen({
        "features": frozen({
            "social_media": True,
        }),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Apple": frozen({
        "sources": ["https://www.apple.com/legal/transparency/"],
        "comments": [
            "Transparency reports cover government requests only.",
        ],
        "features": frozen({
            "social_media": False,
        }),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Automattic": frozen({
        "sources": ("https://transparency.automattic.com",),
        "brands": ("Tumblr", "Wordpress"),
        "features": frozen({
            "social_media": False,
        }),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Aylo": frozen({
        "aka": ("MindGeek",),
        "brands": ("Pornhub",),
        "features": frozen({
            "social_media": False,
        }),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Bluesky": frozen({
        "sources": (
            "https://bsky.social/about/blog/01-29-2026-transparency-report-2025",
            "https://bsky.social/about/blog/01-17-2025-moderation-2024",
        ),
        "features": frozen({
            "social_media": True,
        }),
        "columns": (
            "pieces",
            "reports",
        ),
        "rows": (
            #fmt: off
            {"2025": (12_647, 5_238)},
            {"2024": (None,   1_154)},
            #fmt: on
        )
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Discord": frozen({
        "sources": (
            "https://discord.com/blog/discord-transparency-report-july-dec-2020",
            "https://discord.com/blog/discord-transparency-report-h1-2021",
            "https://discord.com/blog/discord-transparency-report-h2-2021",
            "https://discord.com/blog/discord-transparency-report-q1-2022",
            "https://discord.com/blog/discord-transparency-report-q2-2022",
            "https://discord.com/blog/discord-transparency-report-q3-2022",
            "https://discord.com/safety-transparency-reports/2022-q4",
            "https://discord.com/safety-transparency-reports/2023-q1",
            "https://discord.com/safety-transparency-reports/2023-q2",
            "https://discord.com/safety-transparency-reports/2023-q3",
            "https://discord.com/safety-transparency-reports/2023-q4",
            "https://discord.com/safety-transparency-reports/2024-h1",
        ),
        "comments": [
            "As of mid-February 2026, Discord has not released a transparency",
            "report for H2 2024.",
        ],
        "features": frozen({
            "data": "csv",
            "history": "same page (dropdown)",
            "terms": ("child safety", "CSAM"),
            "quantities": "counts",
            "granularity": "Q",
            "frequency": "Q",
            "coverage": "2020 H2",
            "social_media": True,
        }),
        "columns": (
            "accounts (CSAM)",
            "accounts (grooming or endangerment)"
        ),
        "sums": frozen({
            "accounts": (
                "accounts (CSAM)",
                "accounts (grooming or endangerment)"
            ),
        }),
        "rows": (
            #fmt: off
            {"2024 H1": (103_035, 609)},
            {"2023 Q4": (55_638, 317)},
            {"2023 Q3": (51_674, 242)},
            {"2023 Q2": (36_323, 158)},
            {"2023 Q1": (20_001, 125)},
            {"2022 Q4": (11_520,  69)},
            {"2022 Q3": (14_303,  63)},
            {"2022 Q2": (21_425, 104)},
            {"2022 Q1": (10_641,  54)},
            {"2021 H2": (14_906, 220)},
            {"2021 H1": ( 9_347, 150)},
            {"2020 H2": ( 6_865,  83)},
            #fmt: on
        ),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Facebook": frozen({
        "sources": ("https://transparency.fb.com/sr/community-standards/",),
        "features": frozen({
            "data": "csv",
            "history": "data",
            "terms": ("child nudity & sexual exploitation", "child sexual exploitation",),
            "quantities": "rounded",
            "granularity": "Q",
            "frequency": "Q",
            "coverage": "2018 Q3",
            "social_media": True,
        }),
        "columns": (
            "reports",
            "pieces (Child Nudity & Sexual Exploitation)",
            "pieces (Child Endangerment: Nudity and Physical Abuse)",
            "pieces (Child Endangerment: Sexual Exploitation)",
            "appeals (Child Nudity & Sexual Exploitation)",
            "appeals (Child Endangerment: Nudity and Physical Abuse)",
            "appeals (Child Endangerment: Sexual Exploitation)",
            "reversals (Child Nudity & Sexual Exploitation)",
            "reversals (Child Endangerment: Nudity and Physical Abuse)",
            "reversals (Child Endangerment: Sexual Exploitation)",
            "reversals w/o appeal (Child Nudity & Sexual Exploitation)",
            "reversals w/o appeal (Child Endangerment: Nudity and Physical Abuse)",
            "reversals w/o appeal (Child Endangerment: Sexual Exploitation)",
        ),
        "sums": frozen({
            "pieces": (
                "pieces (Child Nudity & Sexual Exploitation)",
                "pieces (Child Endangerment: Sexual Exploitation)",
            ),
        }),
        "rows": (
            # fmt: off
            {"2025 Q4": (None,       None, 2_500_000,  9_900_000,    None, 213_600,   691_600,   None, 75_000, 263_300,   None,  44_000,    84_400)},
            {"2025 Q3": (None,       None, 3_700_000,  6_000_000,    None, 230_100,   501_400,   None, 48_800, 155_900,   None, 224_700,   432_900)},
            {"2025 Q2": (None,       None, 2_500_000,  5_000_000,    None, 202_000,   567_100,   None, 40_200, 150_000,   None, 472_600,   605_700)},
            {"2025 Q1": (None,       None, 1_500_000,  4_600_000,    None, 163_000,   398_100,   None, 32_000, 127_000,   None,  42_700,   287_400)},
            {"2024 Q4": (None,       None, 2_500_000,  6_200_000,    None, 199_300,   378_700,   None, 55_700, 108_400,   None,  11_900,   134_000)},
            {"2024 Q3": (None,       None, 1_400_000,  7_100_000,    None, 136_200,   722_000,   None, 38_000, 174_400,   None,  10_600,   106_000)},
            {"2024 Q2": (None,       None,   922_000,  9_700_000,    None,  83_500,   410_000,   None,  9_300,  90_000,   None,   1_100,    52_300)},
            {"2024 Q1": (None,       None,   771_700, 14_400_000,    None,  78_100,   380_900,   None, 11_200, 123_900,   None,     500,    73_400)},
            {"2023 Q4": (None,       None, 1_900_000, 16_200_000,    None, 135_100, 1_000_000,   None, 36_100, 317_500,   None, 279_500, 1_200_000)},
            {"2023 Q3": (None,       None, 1_800_000, 16_900_000,    None, 112_200,   266_600,   None, 20_300,  87_800,   None,   1_800,   116_600)},
            {"2023 Q2": (None,       None, 1_700_000,  7_200_000,    None,  94_400,   146_800,   None, 20_500,  38_700,   None,   1_400,    41_300)},
            {"2023 Q1": (None,       None, 1_900_000,  8_900_000,    None,  91_800,   104_500,   None, 12_300,  20_800,   None,   5_400,    17_200)},
            {"2022 Q4": (None,       None, 2_500_000, 25_100_000,    None,  94_700,    23_000,   None, 13_600,   2_600,   None, 541_700,    75_800)},
            {"2022 Q3": (None,       None, 2_300_000, 30_100_000,    None,  85_000,   414_200,   None, 14_600,   4_000,   None,  29_900,   205_300)},
            {"2022 Q2": (None,       None, 1_900_000, 20_400_000,    None,  61_700,   404_000,   None, 11_300,   1_400,   None,  18_700,    15_900)},
            {"2022 Q1": (None,       None, 2_100_000, 16_500_000,    None,   4_000,       800,   None,    700,     100,   None,  21_200,   687_800)},
            {"2021 Q4": (None,       None, 1_800_000, 19_800_000,    None,   3_700,       800,   None,    800,      70,   None,  19_200,   180_500)},
            {"2021 Q3": (None,       None, 1_800_000, 21_200_000,    None,   2_300,       700,   None,    700,      30,   None, 167_200,     2_800)},
            {"2021 Q2": (None,       None, 2_300_000, 25_600_000,    None,   3_000,     1_000,   None,    800,      50,   None,  21_100,     2_800)},
            {"2021 Q1": (None,  5_000_000,      None,       None,   3_800,    None,      None,    300,   None,    None, 46_600,    None,      None)},
            {"2020 Q4": (None,  5_300_000,      None,       None,   4_600,    None,      None,    100,   None,    None,  3_200,    None,      None)},
            {"2020 Q3": (None, 12_400_000,      None,       None,     300,    None,      None,      0,   None,    None,  1_200,    None,      None)},
            {"2020 Q2": (None,  9_400_000,      None,       None,      40,    None,      None,      0,   None,    None,     50,    None,      None)},
            {"2020 Q1": (None,  8_500_000,      None,       None,  55_000,    None,      None,  3_700,   None,    None,    500,    None,      None)},
            {"2019 Q4": (None, 13_300_000,      None,       None,  72_900,    None,      None,  4_400,   None,    None,  2_500,    None,      None)},
            {"2019 Q3": (None, 11_400_000,      None,       None, 128_800,    None,      None, 13_300,   None,    None,  3_400,    None,      None)},
            {"2019 Q2": (None,  6_900_000,      None,       None, 145_000,    None,      None, 14_200,   None,    None,  1_500,    None,      None)},
            {"2019 Q1": (None,  5_800_000,      None,       None,  27_400,    None,      None,    800,   None,    None,  5_300,    None,      None)},
            {"2018 Q4": (None,  7_200_000,      None,       None,    None,    None,      None,   None,   None,    None,   None,    None,      None)},
            {"2018 Q3": (None,  9_000_000,      None,       None,    None,    None,      None,   None,   None,    None,   None,    None,      None)},
            # fmt: on
        ),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "GitHub": frozen({
        "sources": (
            "https://transparencycenter.github.com/automated-detection/",
        ),
        "features": frozen({
            "data": None,
            "history": "same page (dropdown)",
            "terms": ("CSEAI",),
            "quantities": "counts",
            "granularity": "Y",
            "frequency": "Y",
            "coverage": "2021",
            "social_media": False,
        }),
        "columns": ("accounts", "reports"),
        "rows": (
            # fmt: off
            {"2025": (57, 14)},
            {"2024": (5, 16)},
            {"2023": (3, 37)},
            {"2022": (1, 6)},
            {"2021": (1, 4)},
            # fmt: on
        ),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Google": frozen({
        "sources": (
            "https://transparencyreport.google.com/child-sexual-abuse-material/",
        ),
        "comments": (
            "The account and URL counts are for Google and YouTube together.",
            "Unlike piece and report counts, Google does not break down these",
            "counts by platform."
        ),
        "features": frozen({
            "data": None,
            "history": "same page (dropdown)",
            "terms": ("CSAM",),
            "quantities": "counts",
            "granularity": "H",
            "frequency": "H",
            "coverage": "2020 H1",
            "social_media": False,
        }),
        "columns": ("pieces", "reports", "accounts", "urls"),
        "rows": (
            # fmt: off
            {"2025 H2": (5_406_758, 561_820, 365_597, 264_371)},
            {"2025 H1": (2_779_166, 273_052, 341_670, 293_493)},
            {"2024 H2": (2_286_288, 353_503, 282_584, 882_941)},
            {"2024 H1": (2_508_680, 318_568, 360_375, 402_839)},
            {"2023 H2": (3_450_886, 496_105, 249_924, 381_103)},
            {"2023 H1": (4_025_703, 586_832, 259_576, 463_462)},
            {"2022 H2": (6_344_753, 891_215, 365_428, 437_020)},
            {"2022 H1": (6_426_749, 826_667, 270_487, 484_573)},
            {"2021 H2": (3_147_307, 334_215, 140_868, 580_380)},
            {"2021 H1": (3_280_632, 287_368, 129_174, 596_710)},
            {"2020 H2": (2_804_726, 246_325, 97_958, 210_756)},
            {"2020 H1": (1_461_582, 112_595, 77_940, 331_865)},
            # fmt: on
        ),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Grindr": frozen({
        "features": frozen({
            "social_media": True,
        }),
        "comments": (
            "Grindr adheres to the European Union's Digital Services Act and",
            "publishes transparency reports about its content moderation.",
            "Alas, they are limited to the EU member countries only."
        ),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Imgur": frozen({
        "features": frozen({
            "social_media": True,
        }),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Instagram": frozen({
        "sources": ("https://transparency.fb.com/sr/community-standards/",),
        "features": frozen({
            "data": "csv",
            "history": "data",
            "terms": ("child nudity & sexual exploitation", "sexual exploitation",),
            "quantities": "rounded",
            "granularity": "Q",
            "frequency": "Q",
            "coverage": "2019 Q2",
            "social_media": True,
        }),
        "columns": (
            "reports",
            "pieces (Child Nudity & Sexual Exploitation)",
            "pieces (Child Endangerment: Nudity and Physical Abuse)",
            "pieces (Child Endangerment: Sexual Exploitation)",
            "appeals (Child Nudity & Sexual Exploitation)",
            "appeals (Child Endangerment: Nudity and Physical Abuse)",
            "appeals (Child Endangerment: Sexual Exploitation)",
            "reversals (Child Nudity & Sexual Exploitation)",
            "reversals (Child Endangerment: Nudity and Physical Abuse)",
            "reversals (Child Endangerment: Sexual Exploitation)",
            "reversals w/o appeal (Child Nudity & Sexual Exploitation)",
            "reversals w/o appeal (Child Endangerment: Nudity and Physical Abuse)",
            "reversals w/o appeal (Child Endangerment: Sexual Exploitation)",
            #"proactive rate",  TODO!
        ),
        "sums": frozen({
            "pieces": [
                "pieces (Child Nudity & Sexual Exploitation)",
                "pieces (Child Endangerment: Sexual Exploitation)",
            ],
        }),
        "rows": (
            # fmt: off
            {"2025 Q4": (None,      None,   799_000, 3_400_000,   None,  48_000, 414_500,   None, 16_700, 151_700,  None,  13_600,    56_800)},
            {"2025 Q3": (None,      None,   786_100, 4_200_000,   None,  46_600, 240_500,   None,  8_300,  80_100,  None,   2_700, 2_319_900)},
            {"2025 Q2": (None,      None,   579_600, 1_900_000,   None,  48_000, 171_600,   None, 10_400,  41_200,  None,   4_900,    38_100)},
            {"2025 Q1": (None,      None,   616_000, 1_500_000,   None,  58_800,  93_200,   None, 23_500,  28_900,  None,   7_200,    32_500)},
            {"2024 Q4": (None,      None,   946_400, 2_000_000,   None, 138_700,  67_000,   None, 60_400,  16_300,  None,   9_400,     4_900)},
            {"2024 Q3": (None,      None, 1_000_000, 5_600_000,   None, 150_700, 122_400,   None, 68_500,  25_600,  None,   9_000,     6_700)},
            {"2024 Q2": (None,      None,   176_800, 2_800_000,   None,  31_700,  71_100,   None,  5_300,  21_600,  None,     400,    11_500)},
            {"2024 Q1": (None,      None,   183_600, 2_700_000,   None,  39_400,  68_600,   None,  5_300,  26_900,  None,     300,    11_100)},
            {"2023 Q4": (None,      None,   198_500, 2_100_000,   None,  34_700,  79_100,   None,  4_600,  26_500,  None,  11_900,    86_800)},
            {"2023 Q3": (None,      None,   227_700, 1_600_000,   None,  44_400,  38_200,   None,  5_600,  14_300,  None,   1_100,     3_100)},
            {"2023 Q2": (None,      None,   320_700, 1_700_000,   None,  22_000,  22_800,   None,  5_200,   6_300,  None,     700,       700)},
            {"2023 Q1": (None,      None,   567_100, 8_700_000,   None,  29_100,  20_600,   None,  4_300,   2_100,  None,   2_400,     1_600)},
            {"2022 Q4": (None,      None,   620_700, 9_700_000,   None,  16_000,   5_800,   None,  2_000,     100,  None,   4_900,     2_400)},
            {"2022 Q3": (None,      None, 1_000_000, 1_300_000,   None,  36_000,   3_500,   None,  4_100,     200,  None,   6_400,     7_100)},
            {"2022 Q2": (None,      None,   480_500, 1_200_000,   None,  29_200,   4_100,   None,  3_800,     200,  None,   5_900,       400)},
            {"2022 Q1": (None,      None,   600_700, 1_500_000,   None,       0,       0,   None,      0,      20,  None,  10_700,   154_200)},
            {"2021 Q4": (None,      None,   983_400, 2_600_000,   None,       0,       0,   None,      0,       0,  None,  13_600,     1_600)},
            {"2021 Q3": (None,      None,   526_500, 1_600_000,   None,       0,       0,   None,      0,       0,  None, 168_300,       300)},
            {"2021 Q2": (None,      None,   458_300, 1_400_000,   None,       0,       0,   None,      0,       0,  None,   4_500,       300)},
            {"2021 Q1": (None,   812_400,      None,      None,      0,    None,    None,      0,   None,    None, 3_500,    None,      None)},
            {"2020 Q4": (None,   809_400,      None,      None,      0,    None,    None,      0,   None,    None, 2_900,    None,      None)},
            {"2020 Q3": (None, 1_000_000,      None,      None,      0,    None,    None,     10,   None,    None,   700,    None,      None)},
            {"2020 Q2": (None,   481_400,      None,      None,      0,    None,    None,      0,   None,    None,    30,    None,      None)},
            {"2020 Q1": (None, 1_000_000,      None,      None, 53_400,    None,    None, 16_100,   None,    None,   200,    None,      None)},
            {"2019 Q4": (None,   686_400,      None,      None,   None,    None,    None,   None,   None,    None,  None,    None,      None)},
            {"2019 Q3": (None,   755_800,      None,      None,   None,    None,    None,   None,   None,    None,  None,    None,      None)},
            {"2019 Q2": (None,   526_200,      None,      None,   None,    None,    None,   None,   None,    None,  None,    None,      None)},
            # fmt: on
        ),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Kik": frozen({
        "features": frozen({
            "social_media": True,
        }),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "LinkedIn": frozen({
        "sources": ("https://about.linkedin.com/transparency/community-report",),
        "features": frozen({
            "data": None,
            "history": "same page (tabs)",
            "terms": ("child exploitation",),
            "quantities": "counts",
            "granularity": "H",
            "frequency": "H",
            "coverage": "2019 H1",
            "social_media": True,
        }),
        "comments": ("numbers disclosed under 'content removed', hence pieces",),
        "columns": ("pieces",),
        "rows": (
            # fmt: off
            {"2025 H2": (122,)},
            {"2025 H1": (311,)},
            {"2024 H2": (112,)},
            {"2024 H1": (65,)},
            {"2023 H2": (210,)},
            {"2023 H1": (223,)},
            {"2022 H2": (274,)},
            {"2022 H1": (1663,)},
            {"2021 H2": (125,)},
            {"2021 H1": (101,)},
            {"2020 H2": (50,)},
            {"2020 H1": (153,)},
            {"2019 H2": (167,)},
            {"2019 H1": (22,)},
            # fmt: on
        ),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "MediaLab": frozen({
        "brands": ("Amino", "Imgur", "Kik"),
        "features": frozen({
            "social_media": True,
        }),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Meta": frozen({
        "brands": ("Facebook", "Instagram", "Meta AI", "Threads", "WhatsApp"),
        "features": frozen({
            "social_media": True,
        }),
        "sources": (
            "https://transparency.meta.com/ncmec-q2-2023/",
            "https://transparency.meta.com/integrity-reports-q3-2023/",
            "https://transparency.meta.com/integrity-reports-q4-2023/",
            "https://transparency.meta.com/integrity-reports-q1-2024",
            "https://transparency.meta.com/integrity-reports-q2-2024",
            "https://transparency.meta.com/integrity-reports-q3-2024",
            "https://transparency.meta.com/integrity-reports-q4-2024",
            "https://transparency.meta.com/integrity-reports-q1-2025",
            "https://transparency.meta.com/integrity-reports-q2-2025",
            "https://transparency.meta.com/reports/integrity-reports-q3-2025/",
            "https://transparency.meta.com/reports/integrity-reports-h1-2026/",
        ),
        "columns": (
            "reports",
            "pieces (Child Nudity & Sexual Exploitation)",
            "pieces (Child Endangerment: Nudity and Physical Abuse)",
            "pieces (Child Endangerment: Sexual Exploitation)",
            "appeals (Child Nudity & Sexual Exploitation)",
            "appeals (Child Endangerment: Nudity and Physical Abuse)",
            "appeals (Child Endangerment: Sexual Exploitation)",
            "reversals (Child Nudity & Sexual Exploitation)",
            "reversals (Child Endangerment: Nudity and Physical Abuse)",
            "reversals (Child Endangerment: Sexual Exploitation)",
            "reversals w/o appeal (Child Nudity & Sexual Exploitation)",
            "reversals w/o appeal (Child Endangerment: Nudity and Physical Abuse)",
            "reversals w/o appeal (Child Endangerment: Sexual Exploitation)",
            #"proactive rate",  TODO!
        ),
        "sums": frozen({
            "pieces": [
                "pieces (Child Nudity & Sexual Exploitation)",
                "pieces (Child Endangerment: Sexual Exploitation)",
            ],
        }),
        "rows": (
            # fmt: off
            {"2025 Q4": (2_600_000, None, None, None, None, None, None, None, None, None, None, None, None)},
            {"2025 Q3": (2_000_000, None, None, None, None, None, None, None, None, None, None, None, None)},
            {"2025 Q2": (2_000_000, None, None, None, None, None, None, None, None, None, None, None, None)},
            {"2025 Q1": (1_700_000, None, None, None, None, None, None, None, None, None, None, None, None)},
            {"2024 Q4": (2_000_000, None, None, None, None, None, None, None, None, None, None, None, None)},
            {"2024 Q3": (1_600_000, None, None, None, None, None, None, None, None, None, None, None, None)},
            {"2024 Q2": (2_800_000, None, None, None, None, None, None, None, None, None, None, None, None)},
            {"2024 Q1": (5_200_000, None, None, None, None, None, None, None, None, None, None, None, None)},
            {"2023 Q4": (6_000_000, None, None, None, None, None, None, None, None, None, None, None, None)},
            {"2023 Q3": (7_600_000, None, None, None, None, None, None, None, None, None, None, None, None)},
            {"2023 Q2": (3_700_000, None, None, None, None, None, None, None, None, None, None, None, None)},
            # fmt: on
        ),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Meta AI": frozen({
        "features": frozen({
            "social_media": False,
        }),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Microsoft": frozen({
        "sources": (
            "https://www.microsoft.com/en-us/corporate-responsibility/digital-safety-content-report",
        ),
        "comments": (
            "Semiannual counts are broken down into three lines:",
            "Hosted consumer services, Bing Search Engine, and CyberTipline reports.",
        ),
        "features": frozen({
            "data": "xls",
            "history": "same page (dropdown)",
            "terms": ("CSAM",),
            "quantities": "counts",
            "granularity": "H",
            "frequency": "H",
            "coverage": "2020 H1",
            "social_media": False,
        }),
        "brands": ["GitHub", "LinkedIn"],
        "columns": (
            "pieces",
            "proactively detected pieces",
            "accounts",
            "reinstated accounts",
            "reports",
        ),
        "schema": frozen({
            "proactively detected pieces": "float",
            "reinstated accounts": "float",
        }),
        "rows": (
            # fmt: off
            {"2025": (645_118, 99.38, None, None, None)},
            {"2025": (237_391, 99.73, 23_549, 14.50, None)},
            {"2025": (None, None, None, None, 111_931)},

            {"2024 H2": (226_811, 99.82, None, None, None)},
            {"2024 H2": (53_982, 99.64, 9_269, 4.49, None)},
            {"2024 H2": (None, None, None, None, 49_617)},

            {"2024 H1": (109_894, 99.3, None, None, None)},
            {"2024 H1": (69_807, 99.5, 8_758, 2.4, None)},
            {"2024 H1": (None, None, None, None, 51_827)},

            {"2023 H2": (66_603, 99.1, None, None, None)},
            {"2023 H2": (61_348, 99.2, 10_237, 0.8, None)},
            {"2023 H2": (None, None, None, None, 60_749)},

            {"2023 H1": (227_823, 94.7, None, None, None)},
            {"2023 H1": (46_856, 99.2, 7_456, 1.4, None)},
            {"2023 H1": (None, None, None, None, 79_971)},

            {"2022 H2": (200_000, 98.5, None, None, None)},
            {"2022 H2": (31_663, 99.2, 6_461, 1.6, None)},
            {"2022 H2": (None, None, None, None, 53_642)},

            {"2022 H1": (176_125, 93.5, None, None, None)},
            {"2022 H1": (40_722, 98.7, 10_207, 0.56, None)},
            {"2022 H1": (None, None, None, None, 53_957)},

            {"2021 H2": (274_392, 97.2, None, None, None)},
            {"2021 H2": (36_918, 99.4, 11_805, 0.04, None)},
            {"2021 H2": (None, None, None, None, 36_445)},

            {"2021 H1": (176_560, 97.2, None, None, None)},
            {"2021 H1": (76_061, 99.7, 18_568, 0.02, None)},
            {"2021 H1": (None, None, None, None, 42_481)},

            {"2020 H2": (360_338, 99.0, None, None, None)},
            {"2020 H2": (92_419, 99.9, 17_434, 0.0, None)},
            {"2020 H2": (None, None, None, None, 63_813)},

            {"2020 H1": (718_908, 99.8, None, None, None)},
            {"2020 H1": (84_581, 99.8, 15_935, 0.01, None)},
            {"2020 H1": (None, None, None, None, 32_622)},
            # fmt: on
        ),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Omegle": frozen({
        "comments": (
            "A website offering video chat between unregistered users. It was shut",
            "down in 2023 to settle a lawsuit by the victim of online child sexual",
            "exploitation. See https://www.bbc.com/news/technology-67485561 and",
            "https://www.bbc.com/news/business-67364634.",
        ),
        "features": frozen({
            "social_media": True,
        }),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "OpenAI": frozen({
        "sources": (
            "https://openai.com/trust-and-transparency/",
        ),
        "features": frozen({
            "data": None,
            "history": None,
            "terms": ("child safety",),
            "quantities": "counts",
            "granularity": "H",
            "frequency": "H",
            "coverage": "2023 H1",
            "social_media": False,
        }),
        "columns": (
            "reports",
            "pieces",
        ),
        "rows": (
            # fmt: off
            {"2025 H2": (107_817, 107_667)},
            {"2025 H1": ( 75_027,  74_559)},
            {"2024 H2": ( 31_132,  31_510)},
            {"2024 H1": (    947,   3_252)},
            {"2023 H2": (    249,     955)},
            {"2023 H1": (     79,     295)},
            # fmt: on
        ),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Pinterest": frozen({
        "sources": (
            "https://help.pinterest.com/en/guide/transparency-report-archive",
            "https://help.pinterest.com/en/guide/transparency-report-archive#chapter-26356",
            "https://policy.pinterest.com/en/transparency-report-h1-2022",
            "https://policy.pinterest.com/en/transparency-report-h2-2022",
            "https://policy.pinterest.com/en/transparency-report-h1-2023",
            "https://policy.pinterest.com/en/transparency-report-h2-2023",
            "https://policy.pinterest.com/en/transparency-report-h1-2024",
            "https://policy.pinterest.com/en/transparency-report-h2-2024",
            "https://policy.pinterest.com/en/transparency-report-h1-2025",
            "https://policy.pinterest.com/en/transparency-report-h2-2025",
            "https://policy.pinterest.com/en/transparency-report",
        ),
        "features": frozen({
            "data": None,
            "history": "same page (tabs)",
            "terms": ("child safety", "child sexual exploitation", "CSAM"),
            "quantities": "counts",
            "granularity": "Q",
            "frequency": "H",
            "coverage": "2020 H1",
            "social_media": True,
        }),
        "comments": (
            "Pin is Pinterest lingo for a media card with an image, hence a pin",
            "with CSAM is a piece.",
        ),
        "columns": (
            "reports",
            "distinct images",
            "pins",
            "pins appealed",
            "pins reversed",
            "distinct images CSAM",
            "pieces",
            "boards",
            "boards appealed",
            "boards reversed",
            "accounts",
            "account appeals",
            "account reversals",
            "actioned user reports",
            "% pins reached 0",
            "% pins reached 1-9",
            "% pins reached 10-100",
            "% pins reached >100",
        ),
        "rows": (
            # fmt: off
            #            Reports|        |           Pins           |      |  Pieces|       Boards      |        Accounts        |        |         Reach          |
            {"2025 Q4": (   None,  16_109, 10_075_038, 20_871, 5_480, 1_807,  91_156,    953,    4,    0,  50_042,  8_768,  2_684,  16_636,   66,   31,    2,    1)}, # Last quantity is <1%
            {"2025 Q3": (   None,  20_026, 13_519_577, 27_182, 2_743, 1_003, 184_587,  1_000,    7,    0, 127_577, 21_534,  6_665,  20_353,   78,   20,    1,    1)}, # Last two quantities are <1%
            {"2025 H2": (235_769,    None,       None,   None,  None,  None,    None,   None, None, None,    None,   None,   None,    None, None, None, None, None)},
            {"2025 Q2": (   None, 659_426, 16_966_208, 22_356,   992, 1_434, 202_866,    868,    8,    1, 615_313, 91_348,  6_883, 121_560,   63,   34,    2,    1)},
            {"2025 Q1": (   None,  12_083,  8_003_405,  8_350,   360,   506,  23_310,  1_144,    3,    3, 340_942, 39_979, 12_157,  37_394,   61,   35,    2,    1)}, # Last quantity is <1%
            {"2025 H1": (171_999,    None,       None,   None,  None,  None,    None,   None, None, None,    None,   None,   None,    None, None, None, None, None)},
            {"2024 Q4": (   None,  27_692,  5_591_489,  1_087,    21,   786,   3_111,    542,    0,    0, 134_105, 15_623,  7_249,  13_094,   59,   37,    2,    1)},
            {"2024 Q3": (   None,  40_223,  4_269_964,    332,    25, 1_992,   8_517,  1_068,    0,    0,  78_233,  8_197,  5_377,   9_624,   79,   20,    1,    1)}, # Last two quantities are <1%
            {"2024 H2": (  8_989,    None,       None,   None,  None,  None,    None,   None, None, None,    None,   None,   None,    None, None, None, None, None)},
            {"2024 Q2": (   None,   7_180,  4_533_695,     99,     1, 1_384,   4_123,    705,    1,    1,  55_814,  5_429,  4_016,   5_349,   82,   15,    2,    1)}, # Last quantity is <1%
            {"2024 Q1": (   None,   5_575,  3_322_789,     13,     0,   894,   3_770,  3_100,    0,    0,  68_230,  8_424,  5_191,   8_370,   78,   19,    3,    1)},
            {"2024 H1": ( 16_234,    None,       None,   None,  None,  None,    None,   None, None, None,    None,   None,   None,    None, None, None, None, None)},
            {"2023 Q4": (   None,   7_089,  3_602_828,     34,     6, 1_163,   7_488,  4_237,    0,    0, 173_110, 27_499, 19_754,   7_034,   78,   18,    3,    1)},
            {"2023 Q3": (   None,   5_489,  1_469_597,      2,     2, 2_246,  10_471,    318,    0,    0, 244_258, 65_254, 49_854,   7_303,   73,   22,    4,    2)},
            {"2023 H2": ( 16_234,    None,       None,   None,  None,  None,    None,   None, None, None,    None,   None,   None,    None, None, None, None, None)},
            {"2023 Q2": (   None,   9_691,  3_877_286,   None,  None, 1_071,  16_336, 48_039, None, None, 172_633, 20_136,  9_874,   3_896,   83,   14,    2,    1)},
            {"2023 Q1": (   None,   8_393,  1_846_326,   None,  None, 2_348,  23_479, 17_715, None, None,  63_761,  8_524,  3_925,   5_726,   65,   26,    6,    3)},
            {"2023 H1": ( 34_203,    None,       None,   None,  None,  None,    None,   None, None, None,    None,   None,   None,    None, None, None, None, None)},
            {"2022 Q4": (   None,  12_733,  1_716_192,   None,  None, 5_292,  24_288,  1_108, None, None,  33_228,  5_731,  2_686,   4_940,   51,   35,    9,    4)},
            {"2022 Q3": (   None,  10_772,    687_825,   None,  None, 2_987,   7_318,    633, None, None,  21_033,  3_896,  2_053,   2_513,   61,   29,    6,    3)},
            {"2022 H2": ( 27_995,    None,       None,   None,  None,  None,    None,   None, None, None,    None,   None,   None,    None, None, None, None, None)},
            {"2022 Q2": (   None,   9_085,    712_295,   None,  None, 2_038,   4_988,  1_162, None, None,  37_694,  7_467,  5_971,   2_399,   61,   30,    6,    2)},
            {"2022 Q1": (   None,   2_499,    300_003,   None,  None,   184,     542,    492, None, None,  10_743,  2_164,  1_169,   1_735,   63,   28,    6,    3)},
            {"2022 H1": (  4_969,    None,       None,   None,  None,  None,    None,   None, None, None,    None,   None,   None,    None, None, None, None, None)},
            {"2021 Q4": (   None,   2_545,    104_029,   None,  None,   228,     627,    578, None, None,  17_423,  3_110,  2_120,   1_044,   83,   13,    3,    2)},
            {"2021 Q3": (   None,   2_362,    262_164,   None,  None,   295,     981,    862, None, None,  28_289,  5_718,  4_305,   1_378,   72,   21,    4,    2)},
            {"2021 H2": (  1_794,    None,       None,   None,  None,  None,    None,   None, None, None,    None,   None,   None,    None, None, None, None, None)},
            {"2021 H1": (    890,    None,       None,   None,  None,  None,    None,   None, None, None,    None,   None,   None,    None, None, None, None, None)},
            {"2020 H2": (  1_794,    None,       None,   None,  None,  None,    None,   None, None, None,    None,   None,   None,    None, None, None, None, None)},
            {"2020 H1": (  1_638,    None,       None,   None,  None,  None,    None,   None, None, None,    None,   None,   None,    None, None, None, None, None)},
            # fmt: on
        ),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Pornhub": frozen({
        "sources": (
            "https://help.pornhub.com/hc/en-us/articles/50069808248339-2025-Transparency-Report-Second-Half",
            "https://help.pornhub.com/hc/en-us/articles/46213095031827-2025-Transparency-Report-First-Half",
            "https://help.pornhub.com/hc/en-us/articles/46213396642195-2024-Transparency-Report-Second-Half",
            "https://help.pornhub.com/hc/en-us/articles/46213097399315-2024-Transparency-Report-First-Half",
            "https://help.pornhub.com/hc/en-us/articles/46213147539347-2023-Transparency-Report-Second-Half",
            "https://help.pornhub.com/hc/en-us/articles/46213033364371-2023-Transparency-Report-First-Half",
            "https://help.pornhub.com/hc/en-us/articles/46213052959123-2022-Transparency-Report",
            "https://help.pornhub.com/hc/en-us/articles/46213008134419-2021-Transparency-Report",
            "https://help.pornhub.com/hc/en-us/articles/46213042243475-2020-Transparency-Report",
            "https://help.pornhub.com/hc/en-us/categories/4419836212499",
        ),
        "comments": (
            "In March 2023, the Ottawa-based private equity firm ECP (Ethical Capital",
            "Partners) acquired the Montreal-based MindGeek, Pornhub's parent company.",
            "In August 2023, MindGreek rebranded as Aylo. Both Aylo's and Pornhub's",
            "headquarters continue be in Montreal. However, Aylo's corporate structure",
            "is reportedly spread over a number of jurisdictions including Curaçao,",
            "Cyprus, and Luxembourg. Pornhub, in turn, seems to be domiciled in Cyprus.",
            "While NCMEC includes the corporate parent and sibling brands in its",
            "disclosures, only Pornhub makes its own disclosures.",
        ),
        "features": frozen({
            "data": None,
            "history": "page archive",
            "terms": ("CSAM"),
            "quantities": "counts",
            "granularity": "H",
            "frequency": "H",
            "coverage": "2020",
            "social_media": False,
        }),
        "columns": (
            "reports",
            "videos",
            "photos",
        ),
        "sums": frozen({
            "pieces": ["videos", "photos"],
        }),
        "rows": (
            # fmt: off
            {"2025 H2": (2_716,  4_355, 1_853)},
            {"2025 H1": (  975,  1_451,   293)},
            {"2024 H2": (4_037,  5_707, 1_057)},
            {"2024 H1": (1_471,  3_089,   670)},
            {"2023 H2": (1_289,  2_344, 1_018)},
            {"2023 H1": (1_214,  2_632, 1_319)},
            {"2022":    (1_996,  3_604, 5_984)},
            {"2021":    (9_029, 11_626, 8_775)},
            {"2020":    (4_171,   None,  None)},
            # fmt:on
        ),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Quora": frozen({
        "sources": (
            "https://help.quora.com/hc/en-us/articles/13294268051732-DSA-Transparency",
        ),
        "comments": (
            "Quora's first and only transparency report so far, with user numbers only",
        ),
        "features": frozen({
            "social_media": True,
        }),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Reddit": frozen({
        "sources": (
            "https://redditinc.com/policies/transparency-report-july-to-december-2025-reddit",
            "https://redditinc.com/policies/transparency-report-january-to-june-2025-reddit",
            "https://redditinc.com/policies/transparency-report-july-to-december-2024",
            "https://redditinc.com/policies/transparency-report-january-to-june-2024",
            "https://www.redditinc.com/policies/transparency-report-july-to-december-2023",
            "https://www.redditinc.com/policies/2023-h1-transparency-report",
            "https://www.redditinc.com/policies/2022-transparency-report",
            "https://www.redditinc.com/policies/mid-year-transparency-report-2022-2",
            "https://www.redditinc.com/policies/transparency-report-2021",
            "https://www.redditinc.com/policies/transparency-report-2020",
            "https://www.redditinc.com/policies/transparency-report-2019-1",
            "https://www.redditinc.com/policies/transparency",
        ),
        "features": frozen({
            "data": None,
            "history": "page archive",
            "terms": ("minor sexualization", "child sexual exploitation", "CSAM"),
            "quantities": "counts",
            "granularity": "H",
            "frequency": "H",
            "coverage": "2021",
            "social_media": True,
        }),
        "comments": (
            "`pieces (minor sexualization)` covers posts and comments only.",
            "Private messages are one-on-one, whereas chat messages are group-based.",

        ),
        "columns": (
            "pieces",
            "reports",
            "pieces (minor sexualization)",
            "private messages (minor sexualization)",
            "chat messages (minor sexualization)",
            "subreddits (minor sexualization)",
            "content appeals (minor sexualization)",
            "content reversals percent (minor sexualization)",
            "temporary account suspensions (minor sexualization)",
            "accounts (minor sexualization)",
            "account appeals (minor sexualization)",
            "account reversals percent (minor sexualization)",
        ),
        "schema": frozen({
            "content reversals percent (minor sexualization)": "float",
            "account reversals percent (minor sexualization)": "float",
        }),
        "rows": (
            # fmt: off
            {"2025 H2": ( 55_048,  32_747,  72_981,    7,  96_264,   267, 11_454, 17.4, 12_615,  48_660, 10_741, 10.1)},
            {"2025 H1": ( 46_414,  32_759,  84_916,  124, 133_866,   266,  4_752, 10.9, 10_086,  42_541,  8_167, 14.9)},
            {"2024 H2": (195_605, 113_568, 139_948,  171, 158_280,   388, 14_603, 12.0, 18_425,  65_098, 11_466, 13.2)},
            {"2024 H1": (   None, 221_029, 323_150,  304,  85_447, 1_110, 12_425, 15.4, 15_150, 176_679, 10_892, 15.1)},
            {"2023 H2": (   None, 133_588, 349_189,  263,    None, 1_536,   None, None, 15_744, 128_513,  5_801,  8.6)},
            {"2023 H1": (149_084, 156_533, 181_083,  296,    None,   987,   None, None, 27_219,  68_900,  2_924,  7.8)},
            {"2022 H2": ( 31_574,  40_243,    None, None,    None,  None,   None, None,   None,    None,   None, None), "redundant": True},
            {"2022 H1": (   None,  12_349,    None, None,    None,  None,   None, None,   None,    None,   None, None), "redundant": True},
            {"2022":    ( 80_888,  52_592, 266_473,  390,    None, 5_149,   None, None, 70_201,  93_997,  7_513,  9.5)},
            {"2021":    (  9_258,  10_059, 117_093,  243,    None, 1_914,   None, None,      0,   4_659,   None, None)},
            {"2020":    (   None,   2_233,    None, None,    None,  None,   None, None, 15_940,  21_946,   None, None)},
            {"2019":    (   None,     724,  38_410, None,    None,   280,   None, None,   None,  10_781,   None, None)},
            # fmt: on
        ),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Snap": frozen({
        "sources": (
            "https://values.snap.com/privacy/transparency",
            "https://values.snap.com/privacy/transparency-h2-2025",
            "https://values.snap.com/privacy/transparency-h1-2025",
            "https://values.snap.com/privacy/transparency-h2-2024",
            "https://values.snap.com/privacy/transparency-h1-2024",
            "https://values.snap.com/privacy/transparency-h2-2023",
            "https://values.snap.com/privacy/transparency-h1-2023",
            "https://values.snap.com/privacy/transparency-h2-2022",
            "https://values.snap.com/privacy/transparency-h1-2022",
            "https://www.snap.com/en-US/privacy/transparency/2021-12-31",
            "https://www.snap.com/en-US/privacy/transparency/2021-6-30",
            "https://www.snap.com/en-US/privacy/transparency/2020-12-31",
            "https://www.snap.com/en-US/privacy/transparency/2020-6-30",
            "https://www.snap.com/en-US/privacy/transparency/2019-12-31",
        ),
        "features": frozen({
            "data": None,
            "history": "page archive",
            "terms": ("child sexual exploitation and abuse imagery",),
            "quantities": "counts",
            "granularity": "H",
            "frequency": "H",
            "coverage": "2019 H2",
            "social_media": True,
        }),
        "columns": ("pieces", "accounts", "reports"),
        "schema": frozen({"accounts": "float"}),
        "rows": (
            # fmt: off
            {"2025 H2": (1_644_877, 245_643, 397_402)},
            {"2025 H1": (1_099_170, 187_387, 354_396)},
            {"2024 H2": (1_228_929, 242_306, 417_842)},
            {"2024 H1": (1_737_563, 385_864, 632_436)},
            {"2023 H2": (1_046_296, 343_865, 398_736)},
            {"2023 H1": (  548_509, 228_897, 292_489)},
            {"2022 H2": (  527_787, 204_490, 265_285)},
            {"2022 H1": (  746_051, 201_527, 285_470)},
            {"2021 H2": (     None, 198_109,    None)},
            {"2021 H1": (     None, "5.43 / 100 * 2,510,798", None), "redundant": True},
            {"2021 H1": (     None, 119_134,    None)},
            {"2020 H2": (     None, "2.99 / 100 * 2,100,124", None), "redundant": True},
            {"2020 H2": (     None,  47_550,    None)},
            {"2020 H1": (     None, "2.99 / 100 * 1,578,985", None), "redundant": True},
            {"2020 H1": (     None,  47_136,    None)},
            {"2019 H2": (     None, "2.51 / 100 * 1,355,163", None), "redundant": True},
            {"2019 H2": (     None,  34_830,    None)},
            # fmt: on
        ),
        "comments": (
            "For 2019 H2, a coarse continental breakdown is available:",
            "* CSAM accounts enforced EU 10,667; NorthAm 12,397; RestWorld 11,766",
            "* total accounts enforced EU 366,609; NorthAm 730,147; RestWorld 258,407",
        ),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Telegram": frozen({
        "features": frozen({
            "social_media": True,
        }),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Threads": frozen({
        "features": frozen({
            "social_media": True,
        }),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "TikTok": frozen({
        "sources": (
            "https://www.tiktok.com/transparency/en/community-guidelines-enforcement-2023-4/",
            "https://www.tiktok.com/transparency/en/community-guidelines-enforcement-2023-3/",
            "https://www.tiktok.com/transparency/en/community-guidelines-enforcement-2023-2/",
            "https://www.tiktok.com/transparency/en/community-guidelines-enforcement-2023-1/",
            "https://www.tiktok.com/transparency/en/community-guidelines-enforcement-2022-4/",
            "https://www.tiktok.com/transparency/en/community-guidelines-enforcement-2022-3/",
            "https://www.tiktok.com/transparency/en/community-guidelines-enforcement-2022-2/",
            "https://www.tiktok.com/transparency/en/community-guidelines-enforcement-2022-1/",
        ),
        "features": frozen({
            "data": "Excel, csv",
            "history": "page archive",
            "terms": ("sexual exploitation of minors", "CSAM", "youth exploitation and abuse"),
            "quantities": "fractions",
            "granularity": "Q",
            "frequency": "Q",
            "coverage": "2022 Q1",
            "social_media": True,
        }),
        "comments": (
            "Originally, TikTok's transparency disclosures were marred by the use",
            "of fractional shares. To derive actual counts, the shares of category",
            "and supercategory have to be known. But by disclosing some shares for",
            "human moderation only, TikTok made it impossible to derive piece counts.",
            "After changing the schema for its transparency data with Q2 2023,",
            "TikTok started to report the share for entire categories and super-",
            "categories. Alas, despite claims to the opposite, the firm also stopped",
            "disclosing granular data on youth safety including sexual exploitation.",
            "Columns from the original schema are marked as such, with exception of",
            "total videos removed and videos removed by automation, which appear in",
            "both schemas.",
        ),
        "columns": (
            "pieces (human moderation, original schema)",
            "category share (human moderation, original schema)",
            "minor safety category share of total (original schema)",
            "share of policy category (Youth Exploitation & Abuse)",
            "proactive removal rate (Youth Exploitation & Abuse)",
            "removal rate before any views (Youth Exploitation & Abuse)",
            "removal rate within 24 hours (Youth Exploitation & Abuse)",
            "share of total removals (Safety & Civility)",
            "total videos removed",
            "videos removed by automation",
            "videos restored",
            "removal rate within 24 hours (human moderation, original schema)",
            "removal rate before any views (human moderation, original schema)",
            "proactive removal rate (human moderation, original schema)",
        ),
        "schema": frozen({
            "category share (human moderation, original schema)": "float",
            "minor safety category share of total (original schema)": "float",
            "share of policy category (Youth Exploitation & Abuse)": "float",
            "proactive removal rate (Youth Exploitation & Abuse)": "float",
            "removal rate before any views (Youth Exploitation & Abuse)": "float",
            "removal rate within 24 hours (Youth Exploitation & Abuse)": "float",
            "share of total removals (Safety & Civility)": "float",
            "removal rate within 24 hours (human moderation, original schema)": "float",
            "removal rate before any views (human moderation, original schema)": "float",
            "proactive removal rate (human moderation, original schema)": "float",
        }),
        "rows": (
            # fmt: off
            {"2023 Q4": (   None,  None,  None, 0.232, 0.981, 0.781, 0.902, 0.135, 176_461_963, 128_300_584, 8_038_106,  None,  None,  None)},
            {"2023 Q3": (   None,  None,  None, 0.279, 0.987, 0.792, 0.916, 0.161, 136_530_418,  88_721_552, 7_084_629,  None,  None,  None)},
            {"2023 Q2": (   None,  None,  None, 0.308, 0.986, 0.836, 0.911, 0.145, 106_476_032,  66_440_775, 6_750_002,  None,  None,  None)},
            {"2023 Q1": (   None, 0.023, 0.306,  None,  None,  None,  None,  None,  91_003_510,  53_494_911,      None, 0.869, 0.784, 0.927)},
            {"2022 Q4": (415_278, 0.033, 0.333,  None,  None,  None,  None,  None,  85_680_819,  46_836_047,      None, 0.887, 0.821, 0.931)},
            {"2022 Q3": (792_473, 0.033, 0.429,  None,  None,  None,  None,  None, 110_954_663,  53_287_839,      None, 0.925, 0.883, 0.951,)},
            {"2022 Q2": (   None, 0.024, 0.437,  None,  None,  None,  None,  None, 113_809_300,  48_011_571,      None, 0.907, 0.858, 0.932)},
            {"2022 Q1": (   None, 0.019, 0.417,  None,  None,  None,  None,  None, 102_305_516,  34_726_592,      None, 0.903, 0.825, 0.906)},
            # fmt: on
        ),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Tumblr": frozen({
        "sources": ("https://www.tumblr.com/transparency",),
        "features": frozen({
            "social_media": True,
        }),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Twitch": frozen({
        "sources": (
            "https://safety.twitch.tv/s/article/H2-2025-Transparency-Report",
            "https://safety.twitch.tv/s/article/H1-2025-Transparency-Report",
            "https://safety.twitch.tv/s/article/H2-2024-Transparency-Report",
            "https://safety.twitch.tv/s/article/H1-2024-Transparency-Report",
            "https://safety.twitch.tv/s/article/H2-2023-Transparency-Report",
            "https://safety.twitch.tv/s/article/H1-2023-Transparency-Report",
            "https://safety.twitch.tv/s/article/H2-2022-Transparency-Report",
            "https://safety.twitch.tv/s/article/H1-2022-Transparency-Report",
            "https://safety.twitch.tv/s/article/H2-2021-Transparency-Report",
            "https://safety.twitch.tv/s/article/Transparency-Reports#5H12021TransparencyReport",
            "https://safety.twitch.tv/s/article/Transparency-Reports#62020TransparencyReport",
        ),
        "features": frozen({
            "data": None,
            "history": "page",
            "terms": ("youth safety", "child sexual exploitation and abuse"),
            "quantities": "counts",
            "granularity": "H",
            "frequency": "H",
            "coverage": "2020",
            "social_media": True,
        }),
        "comments": (
            "Twitch's data are marked as redundant because their report counts are",
            "included with Amazon's yearly disclosures. For years where NCMEC breaks",
            "out Twitch from Amazon, Twitch's report counts appear to be more accurate",
            "than those of Amazon. For 2025 H2, Twitch reported an increase of 46.92%",
            "over H2, but left out the absolute count."
        ),
        "columns": ("reports",),
        "rows": (
            # fmt: off
            {"2025 H2": (450,), "redundant": True},
            {"2025 H1": (959,), "redundant": True},
            {"2024 H2": (759,), "redundant": True},
            {"2024 H1": (1_523,), "redundant": True},
            {"2023 H2": (3_272,), "redundant": True},
            {"2023 H1": (3_285,), "redundant": True},
            {"2022 H2": (7_585,), "redundant": True},
            {"2022 H1": (6_711,), "redundant": True},
            {"2021 H2": (4_006,), "redundant": True},
            {"2021 H1": (2_615,), "redundant": True},
            {"2020 H2": (1_346,), "redundant": True},
            {"2020 H1": (812,), "redundant": True},
            # fmt: on
        ),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Twitter": frozen({
        "sources": (
            "https://transparency.twitter.com",
            "https://blog.twitter.com/en_us/topics/company/2023/an-update-on-twitter-transparency-reporting",
            "https://transparency.x.com/content/dam/transparency-twitter/download/2019-jul-dec/Twitter_Transparency_Report-16_Jul-Dec-2019.zip",
            "https://transparency.x.com/content/dam/transparency-twitter/download/2020-jan-jun/Twitter_Transparency_Report-17_Jan-Jun-2020.zip",
            "https://transparency.x.com/content/dam/transparency-twitter/download/2020-jul-dec/Twitter_Transparency_Report-18_Jul-Dec-2020.zip",
            "https://transparency.x.com/content/dam/transparency-twitter/download/2021-jan-jun/Twitter_Transparency_Report-19_Jan-Jun-2021.zip",
            "https://transparency.x.com/content/dam/transparency-twitter/download/2021-jul-dec/Twitter-Transparency-Report-20-Jul-Dec-2021.zip",
        ),
        "features": frozen({
            "data": None,
            "history": "same page (dropdown)",
            "terms": ("child sexual exploitation",),
            "quantities": "counts",
            "granularity": "H",
            "frequency": "H",
            "coverage": "2018 H2 - 2022 H1",
            "social_media": True,
        }),
        "comments": ("CSV download feature does not work in any browser",),
        "columns": (
            "accounts actioned",
            "accounts",
            "distinct pieces",
            "pieces (automated)",
            "pieces (human)",
            "reports (automated)",
            "reports (human)",
            "accounts (automated)",
            "accounts (human)",
        ),
        "sums": frozen({
            "pieces": ("pieces (automated)", "pieces (human)"),
            "reports": ("reports (automated)", "reports (human)"),
            "accounts": ("accounts (automated)", "accounts (human)"),
        }),
        "rows": (
            # fmt: off
            {"2022 H1": (696_015, 691_704, 11_927, None, None, None, None, None, None)},
            {"2021 H2": (599_523, 596_997, 6_796, None, None, None, None, None, None)},
            {"2021 H1": (456_146, 453_754, 6_087, None, None, None, None, None, None)},
            {"2020 H2": (469_439, 464_804, 9_178, None, None, None, None, None, None)},
            {"2020 H1": (444_781, 438_809, 10_343, None, None, None, None, None, None)},
            {"2019 H2": (264_625, 257_768, 11_026, None, None, None, None, None, None)},
            {"2019 H1": (246_642, 245_341, 2_751, None, None, None, None, None, None)},
            {"2018 H2": (457_231, 455_651, 2_777, None, None, None, None, None, None)},
            # fmt: on
        ),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "WhatsApp": frozen({
        "sources": (
            "https://www.whatsapp.com/legal/california-privacy-notice/transparency-report/",
        ),
        "comments": (
            "That appears to be the only transparency report WhatsApp ever released, as in 1.",
        ),
        "features": frozen({
            "social_media": True,
        }),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Wikimedia": frozen({
        "sources": ("https://wikimediafoundation.org/about/transparency/",),
        "features": frozen({
            "social_media": False,
        }),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "Wordpress": frozen({
        "sources": ("https://transparency.automattic.com",),
        "features": frozen({
            "social_media": False,
        })
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "X": frozen({
        "aka": ("Twitter",),
        "sources": (
            "https://transparency.x.com/content/dam/transparency-twitter/2024/x-global-transparency-report-h1.pdf",
            "https://transparency.x.com/en/reports/global-reports/2025-transparency-report",
        ),
        "features": frozen({
            "data": None,
            "history": None,
            "terms": ("child sexual exploitation", "physical child abuse"),
            "quantities": "counts",
            "granularity": "H",
            "frequency": "H",
            "coverage": "2024 H1 - 2024 H2",
            "social_media": True,
        }),
        "columns": (
            "accounts actioned",
            "accounts",
            "distinct pieces",
            "pieces (automated)",
            "pieces (human)",
            "reports (automated)",
            "reports (human)",
            "accounts (automated)",
            "accounts (human)",
        ),
        "sums": frozen({
            "pieces": ("pieces (automated)", "pieces (human)"),
            "reports": ("reports (automated)", "reports (human)"),
            "accounts": ("accounts (automated)", "accounts (human)"),
        }),
        "rows": (
            # fmt: off
            {"2024 H2": (None, None, None, 1_398, 1_383, 45_616, 268_301, 1_732_324, 58_528)},
            {"2024 H1": (None, None, None, 1_645, 12_926, 35_176, 335_412, 2_388_683, 392_951)},
            # fmt: on
        ),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "YouTube": frozen({
        "sources": (
            "https://transparencyreport.google.com/child-sexual-abuse-material/",
        ),
        "features": frozen({
            "data": None,
            "history": "same page (dropdown)",
            "terms": ("CSAM",),
            "quantities": "counts",
            "granularity": "H",
            "frequency": "H",
            "coverage": "2020 H1",
            "social_media": True,
        }),
        "columns": ("pieces", "reports"),
        "rows": (
            # fmt: off
            {"2025 H2": (300_804, 300_464)},
            {"2025 H1": (344_941, 321_868)},
            {"2024 H2": (242_121, 223_477)},
            {"2024 H1": (320_498, 280_478)},
            {"2023 H2": (265_371, 225_440)},
            {"2023 H1": (213_209, 163_844)},
            {"2022 H2": (359_931, 238_827)},
            {"2022 H1": (271_452, 217_610)},
            {"2021 H2": (135_517, 123_963)},
            {"2021 H1": (133_041, 124_773)},
            {"2020 H2": (99_591, 118_994)},
            {"2020 H1": (71_954, 69_961)},
            # fmt: on
        ),
    }),
    # ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
    "NCMEC": frozen({
        "sources": (
            "https://ncmec.org/content/dam/missingkids/pdfs/cybertiplinedata2024/2024-reports-by-esp.pdf",
            "https://www.missingkids.org/content/dam/missingkids/pdfs/2019-reports-by-esp.pdf",
            "https://www.missingkids.org/content/dam/missingkids/pdfs/2020-reports-by-esp.pdf",
            "https://www.missingkids.org/content/dam/missingkids/pdfs/2021-reports-by-esp.pdf",
            "https://www.missingkids.org/content/dam/missingkids/pdfs/2022-reports-by-esp.pdf",
            "https://www.missingkids.org/content/dam/missingkids/pdfs/2023-reports-by-esp.pdf",
            "https://www.missingkids.org/content/dam/missingkids/pdfs/cybertiplinedata2024/2024-reports-by-esp.pdf",
            "https://www.missingkids.org/content/dam/missingkids/pdfs/2021-notifications-by-ncmec-per-esp.pdf",
            "https://www.missingkids.org/content/dam/missingkids/pdfs/2022-notifications-by-ncmec-per-esp.pdf",
            "https://www.missingkids.org/content/dam/missingkids/pdfs/OJJDP-NCMEC-Transparency_2022-Calendar-Year.pdf",
            "https://www.missingkids.org/content/dam/missingkids/pdfs/OJJDP-NCMEC-Transparency-CY-2023-Report.pdf",
            "https://www.missingkids.org/content/dam/missingkids/pdfs/cybertiplinedata2024/OJJDP-NCMEC-Transparency-CY-2024.pdf",
        ),
        "features": frozen({
            "data": None,
            "history": "page archive",
            "terms": ("CSAM",),
            "quantities": "counts",
            "granularity": "Y",
            "frequency": "Y",
            "coverage": "2019",
            "social_media": False,
        }),
        "comments": (
            "reports: number of reports *received* by NCMEC from a platform",
            "notifications_sent: number of hosted CSAM notices *sent* by NCMEC",
            "response_time: average days platform takes to respond/takedown",
            "missing response_time implies no action despite repeated notices",
            "original reports has entries for Google only, listed here under Alphabet",
            "notifications_sent & response_time have entries for Google and YouTube",
        ),
        "columns": (
            "platform",
            "reports",
            "notifications_sent",
            "response_time",
        ),
        "schema": frozen({
            "platform": "string",
            "response_time": "float"
        }),
        "rows": (
            # fmt: off
            {"2019": ("Alphabet", 449_283, None, None)},
            {"2019": ("Amazon", 8, None, None)},
            {"2019": ("Amino", 383, None, None)},
            {"2019": ("Apple", 205, None, None)},
            {"2019": ("Automattic", 10_443, None, None)},
            {"2019": ("Aylo", None, None, None)},
            {"2019": ("Discord", 19_480, None, None)},
            {"2019": ("Facebook", None, None, None)},
            {"2019": ("GitHub", 2, None, None)},
            {"2019": ("Google", None, None, None)},
            {"2019": ("Grindr", 13, None, None)},
            {"2019": ("Imgur", 73_929, None, None)},
            {"2019": ("Instagram", None, None, None)},
            {"2019": ("Kik", None, None, None)},
            {"2019": ("LinkedIn", 88, None, None)},
            {"2019": ("MediaLab", 38, None, None)},
            {"2019": ("Meta", 15_884_511, None, None)},
            {"2019": ("Microsoft", 123_839, None, None)},
            {"2019": ("MindGeek", None, None, None)},
            {"2019": ("Omegle", 3_470, None, None)},
            {"2019": ("Pinterest", 7_360, None, None)},
            {"2019": ("Pornhub", None, None, None)},
            {"2019": ("Quora", 1, None, None)},
            {"2019": ("Reddit", 724, None, None)},
            {"2019": ("Snap", 82_030, None, None)},
            {"2019": ("Telegram", None, None, None)},
            {"2019": ("Threads", None, None, None)},
            {"2019": ("TikTok", 596, None, None)},
            {"2019": ("Tumblr", None, None, None)},
            {"2019": ("Twitch", 541, None, None)},
            {"2019": ("Twitter", 45_726, None, None)},
            {"2019": ("WhatsApp", None, None, None)},
            {"2019": ("Wikimedia", 13, None, None)},
            {"2019": ("Wordpress", None, None, None)},
            {"2019": ("X", None, None, None)},
            {"2019": ("YouTube", None, None, None)},
            {"2019": ("ESP Total", 16_836_694, None, None)},
            {"2019": ("Total", 16_987_361, None , None)},
            # ───────────────────────────────────────────────────────
            {"2020": ("Alphabet", 546_704, None, None)},
            {"2020": ("Amazon", 2_235, None, None)},
            {"2020": ("Amino", 97, None, None)},
            {"2020": ("Apple", 265, None, None)},
            {"2020": ("Automattic", 9_130, None, None)},
            {"2020": ("Aylo", None, None, None)},
            {"2020": ("Discord", 15_324, None, None)},
            {"2020": ("Facebook", None, None, None)},
            {"2020": ("GitHub", 2, None, None)},
            {"2020": ("Google", None, None, None)},
            {"2020": ("Grindr", 302, None, None)},
            {"2020": ("Imgur", 31_571, None, None)},
            {"2020": ("Instagram", None, None, None)},
            {"2020": ("Kik", 14_515, None, None)},
            {"2020": ("LinkedIn", 60, None, None)},
            {"2020": ("MediaLab", None, None, None)},
            {"2020": ("Meta", 20_307_216, None, None)},
            {"2020": ("Microsoft", 96_776, None, None)},
            {"2020": ("MindGeek", 13_229, None, None)},
            {"2020": ("Omegle", 20_265, None, None)},
            {"2020": ("Pinterest", 3_432, None, None)},
            {"2020": ("Pornhub", None, None, None)},
            {"2020": ("Quora", 2, None, None)},
            {"2020": ("Reddit", 2_233, None, None)},
            {"2020": ("Snap", 144_095, None, None)},
            {"2020": ("Telegram", None, None, None)},
            {"2020": ("Threads", None, None, None)},
            {"2020": ("TikTok", 22_692, None, None)},
            {"2020": ("Tumblr", None, None, None)},
            {"2020": ("Twitch", None, None, None)},
            {"2020": ("Twitter", 65_062, None, None)},
            {"2020": ("WhatsApp", None, None, None)},
            {"2020": ("Wikimedia", 11, None, None)},
            {"2020": ("Wordpress", None, None, None)},
            {"2020": ("X", None, None, None)},
            {"2020": ("YouTube", None, None, None)},
            {"2020": ("ESP Total", 21_447_786, None, None)},
            {"2020": ("Total", 21_751_085, None, None)},
            # ───────────────────────────────────────────────────────
            {"2021": ("Alphabet", 875_783, None, None)},
            {"2021": ("Amazon", 99, None, None)},
            {"2021": ("Amazon", 4, None, None)},
            {"2021": ("Amazon", 27_101, None, None)},
            {"2021": ("Amino", 75, None, None)},
            {"2021": ("Apple", 160, None, None)},
            {"2021": ("Automattic", None, None, None)},
            {"2021": ("Aylo", None, None, None)},
            {"2021": ("Discord", 29_606, 68, 3.21)},
            {"2021": ("Facebook", 22_118_952, 28, 7.27)},
            {"2021": ("GitHub", 4, None, None)},
            {"2021": ("Google", None, 975, 6.77)},
            {"2021": ("Grindr", 10_671, None, None)},
            {"2021": ("Imgur", 47_274, None, None)},
            {"2021": ("Instagram", 3_393_654, 22, 4.45)},
            {"2021": ("Kik", 33_619, None, None)},
            {"2021": ("LinkedIn", 110, None, None)},
            {"2021": ("MediaLab", None, None, None)},
            {"2021": ("Meta", None, None, None)},
            {"2021": ("MindGeek", 16, None, None)},
            {"2021": ("MindGeek", 21, None, None)},  # Redtube
            {"2021": ("MindGeek", 6, None, None)},  # Tube8
            {"2021": ("MindGeek", 31, None, None)},  # YouPorn
            {"2021": ("Microsoft", 78_603, None, None)},
            {"2021": ("Microsoft", 170, None, None)},  # Xbox
            {"2021": ("Microsoft", None, 2, 8.86)},
            {"2021": ("Microsoft", None, 128, 2.21)},
            {"2021": ("Omegle", 46_924, None, None)},
            {"2021": ("Pinterest", 2_283, 56, 0.69)},
            {"2021": ("Pornhub", 9_029, None, None)},
            {"2021": ("Quora", 25, 1, 0.71)},
            {"2021": ("Reddit", 10_059, 233, 1.39)},
            {"2021": ("Snap", 512_522, None, None)},
            {"2021": ("Telegram", None, 229, 8.0)},
            {"2021": ("Threads", None, None, None)},
            {"2021": ("TikTok", 154_618, None, None)},
            {"2021": ("Tumblr", 4_511, 52, 0.49)},
            {"2021": ("Twitch", 6_629, None, None)},
            {"2021": ("Twitter", 86_666, 1_017, 1.82)},
            {"2021": ("WhatsApp", 1_372_696, 2, 3.32)},
            {"2021": ("Wikimedia", 8, None, None)},
            {"2021": ("Wordpress", 310, 26, 1.95)},
            {"2021": ("X", None, None, None)},
            {"2021": ("YouTube", None, 10, 2.2)},
            {"2021": ("ESP Total", 29_157_083, 75_038, 1.22)},
            {"2021": ("Total", 29_397_681, None, None)},
            # ───────────────────────────────────────────────────────
            {"2022": ("Alphabet", 2_174_548, None, None)},
            {"2022": ("Amazon", 106, None, None)},
            {"2022": ("Amazon", 55_543, None, None)},
            {"2022": ("Amino", 177, None, None)},
            {"2022": ("Apple", 234, None, None)},
            {"2022": ("Automattic", None, None, None)},
            {"2022": ("Aylo", None, None, None)},
            {"2022": ("Discord", 169_800, 1_533, 4.7)},
            {"2022": ("Facebook", 21_165_208, 10, 4.4)},
            {"2022": ("GitHub", 6, None, None)},
            {"2022": ("Google", None, 916, 4.2)},
            {"2022": ("Grindr", 22_819, None, None)},
            {"2022": ("Imgur", 64_211, None, None)},
            {"2022": ("Instagram", 5_007_902, 13, 3.7)},
            {"2022": ("Kik", 36_801, None, None)},
            {"2022": ("LinkedIn", 201, None, None)},
            {"2022": ("MediaLab", None, None, None)},
            {"2022": ("Meta", None, None, None)},
            {"2022": ("MindGeek", 91, None, None)},
            {"2022": ("MindGeek", 6, None, None)},  # Redtube
            {"2022": ("MindGeek", 2, None, None)},  # YouPorn
            {"2022": ("Microsoft", 107_274, None, None)},
            {"2022": ("Microsoft", 138, None, None)},
            {"2022": ("Microsoft", 1_185, None, None)},
            {"2022": ("Microsoft", None, 29, 2.8)},
            {"2022": ("Microsoft", None, 136, 5.1)},
            {"2022": ("Microsoft", None, 577, 5.2)},
            {"2022": ("Omegle", 608_601, None, None)},
            {"2022": ("Pinterest", 34_310, 46, 1.1)},
            {"2022": ("Pornhub", 1_996, None, None)},
            {"2022": ("Quora", 2_242, None, None)},
            {"2022": ("Reddit", 52_592, 275, 2.4)},
            {"2022": ("Snap", 551_086, None, None)},
            {"2022": ("Telegram", None, 73, 5.1)},
            {"2022": ("Threads", None, None, None)},
            {"2022": ("TikTok", 288_125, 1, 0.2)},
            {"2022": ("Tumblr", 4_845, 92, 0.9)},
            {"2022": ("Twitch", 14_508, None, None)},
            {"2022": ("Twitter", 98_050, 1_278, 1.8)},
            {"2022": ("WhatsApp", 1_017_555, 2, 5.2)},
            {"2022": ("Wikimedia", 29, None, None)},
            {"2022": ("Wordpress", 190, 155, 1.6)},
            {"2022": ("X", None, None, None)},
            {"2022": ("YouTube", None, 14, 3.6)},
            {"2022": ("ESP Total", 31_802_525, 80_969, None)},
            {"2022": ("Total", 32_059_029, None, None)},
            # ───────────────────────────────────────────────────────
            {"2023": ("Alphabet", 1_470_958, None, None)},
            {"2023": ("Amazon", 197, None, None)},
            {"2023": ("Amazon", 25_497, None, None)},
            {"2023": ("Amino", 433, None, None)},
            {"2023": ("Apple", 267, None, None)},
            {"2023": ("Automattic", None, None, None)},
            {"2023": ("Aylo", 29, None, None)},  # Tube8
            {"2023": ("Aylo", 4, None, None)},  # YouPorn
            {"2023": ("Aylo", 8, None, None)},  # MyDirtyHobby
            {"2023": ("Bluesky", 1, None, None)},
            {"2023": ("Discord", 339_412, None, None)},
            {"2023": ("Facebook", 17_838_422, None, None)},
            {"2023": ("Google", None, None, None)},
            {"2023": ("Grindr", 45_073, None, None)},
            {"2023": ("GitHub", 1, None, None)},
            {"2023": ("Imgur", 58_957, None, None)},
            {"2023": ("Instagram", 11_430_007, None, None)},
            {"2023": ("Kik", 17_394, None, None)},
            {"2023": ("LinkedIn", 209, None, None)},
            {"2023": ("MediaLab", None, None, None)},
            {"2023": ("Meta", None, None, None)},
            {"2023": ("MindGeek", 44, None, None)},
            {"2023": ("MindGeek", 7, None, None)},  # Redtube
            {"2023": ("MindGeek", 1, None, None)},  # Tube8
            {"2023": ("Microsoft", 139_265, None, None)},
            {"2023": ("Microsoft", 1_537, None, None)},
            {"2023": ("Microsoft", 225, None, None)},
            {"2023": ("Omegle", 188_102, None, None)},
            {"2023": ("OpenAI", 329, None, None)},
            {"2023": ("Pinterest", 52_356, None, None)},
            {"2023": ("Pornhub", 16, None, None)},  # Under Aylo
            {"2023": ("Pornhub", 2_487, None, None)},  # Under MindGeek
            {"2023": ("Quora", 6_135, None, None)},
            {"2023": ("Reddit", 290_141, None, None)},
            {"2023": ("Snap", 713_055, None, None)},
            {"2023": ("Telegram", None, None, None)},
            {"2023": ("Threads", 663, None, None)},
            {"2023": ("TikTok", 590_376, None, None)},
            {"2023": ("Tumblr", 19_335, None, None)},
            {"2023": ("Twitch", 6_665, None, None)},
            {"2023": ("Twitter", 597_087, None, None)},
            {"2023": ("WhatsApp", 1_389_618, None, None)},
            {"2023": ("Wikimedia", 34, None, None)},
            {"2023": ("Wordpress", 256, None, None)},
            {"2023": ("X", 273_416, None, None)},
            {"2023": ("YouTube", None, None, None)},
            {"2023": ("ESP Total", 35_944_826, None, None)},
            {"2023": ("Total", 36_210_368, None, None)},
            # ───────────────────────────────────────────────────────
            {"2024": ("Alphabet", None, None, None)},
            {"2024": ("Amazon", 390, None, None)},
            {"2024": ("Amazon", 30_759, None, None)}, # AI Services
            {"2024": ("Amazon", 42_051, None, None)}, # Photos
            {"2024": ("Amino", 109, None, None)},
            {"2024": ("Apple", 250, None, None)},
            {"2024": ("Automattic", None, None, None)},
            {"2024": ("Aylo", 5_478, None, None)},  # Pornhub
            {"2024": ("Aylo", 3, None, None)},  # Redtube
            {"2024": ("Aylo", 1, None, None)},  # Tube8
            {"2024": ("Aylo", 2, None, None)},  # YouPorn
            {"2024": ("Aylo", 23, None, None)},  # MyDirtyHobby
            {"2024": ("Bluesky", 1_156, None, None)},
            {"2024": ("Discord", 241_354, None, None)},
            {"2024": ("Facebook", 8_590_357, None, None)},
            {"2024": ("GitHub", None, None, None)},
            {"2024": ("Google", 1_175_084, None, None)},
            {"2024": ("Grindr", 78_886, None, None)},
            {"2024": ("Imgur", 554_710, None, None)},
            {"2024": ("Instagram", 3_320_008, None, None)},
            {"2024": ("Kik", 114_155, None, None)},
            {"2024": ("LinkedIn", 127, None, None)},
            {"2024": ("MediaLab", None, None, None)},
            {"2024": ("Meta", None, None, None)},
            {"2024": ("MindGeek", 30, None, None)}, # Pornhub
            {"2024": ("Microsoft", 101_009, None, None)}, # Online Operations
            {"2024": ("Microsoft", 1_324, None, None)}, # Xbox
            {"2024": ("Microsoft", 324, None, None)}, # Other Products
            {"2024": ("Omegle", 12, None, None)},
            {"2024": ("OpenAI", 32_079, None, None)},
            {"2024": ("Pinterest", 65_810, None, None)},
            {"2024": ("Pornhub", None, None, None)},  # Under Aylo
            {"2024": ("Quora", 8_778, None, None)},
            {"2024": ("Reddit", 334_597, None, None)},
            {"2024": ("Snap", 1_174_698, None, None)},
            {"2024": ("Telegram", None, None, None)},
            {"2024": ("Threads", 3_354, None, None)},
            {"2024": ("TikTok", 1_359_806, None, None)},
            {"2024": ("Tumblr", 4_047, None, None)},
            {"2024": ("Twitch", 2_301, None, None)},
            {"2024": ("Twitter", None, None, None)},
            {"2024": ("WhatsApp", 1_851_086, None, None)},
            {"2024": ("Wikimedia", 102, None, None)},
            {"2024": ("Wordpress", 298, None, None)},
            {"2024": ("X", 686_176, None, None)},
            {"2024": ("YouTube", None, None, None)},
            {"2024": ("ESP Total", 20_348_306, None, None)},
            {"2024": ("Total", 20_512_803, None, None)},
            # ───────────────────────────────────────────────────────
            {"2025": ("Alphabet", None, None, None)},
            {"2025": ("Amazon", 435, None, None)},
            {"2025": ("Amazon", 1_105_405, None, None)}, # AI Services
            {"2025": ("Amazon", 21_360, None, None)}, # Photos
            {"2025": ("Amino", 62, None, None)},
            {"2025": ("Apple", 296, None, None)},
            {"2025": ("Automattic", None, None, None)},
            {"2025": ("Aylo", 3_534, None, None)},  # Pornhub
            {"2025": ("Aylo", 3, None, None)},  # Redtube
            {"2025": ("Aylo", 2, None, None)},  # YouPorn
            {"2025": ("Aylo", 17, None, None)},  # MyDirtyHobby
            {"2025": ("Bluesky", 5_264, None, None)},
            {"2025": ("Discord", 489_782, None, None)},
            {"2025": ("Facebook", 4_907_710, None, None)},
            {"2025": ("GitHub", None, None, None)},
            {"2025": ("Google", 1_461_378, None, None)},
            {"2025": ("Grindr", 111_334, None, None)},
            {"2025": ("Imgur", 22_459, None, None)},
            {"2025": ("Instagram", 3_673_045, None, None)},
            {"2025": ("Kik", 111_394, None, None)},
            {"2025": ("LinkedIn", 182, None, None)},
            {"2025": ("MediaLab", None, None, None)},
            {"2025": ("Meta", None, None, None)},
            {"2025": ("Meta AI", 582, None, None)},
            {"2025": ("MindGeek", 30, None, None)}, # Pornhub
            {"2025": ("Microsoft", 111_093, None, None)}, # Online Operations
            {"2025": ("Microsoft", 1_652, None, None)}, # Xbox
            {"2025": ("Microsoft", 8_477, None, None)}, # Other Products
            {"2025": ("Omegle", 11, None, None)},
            {"2025": ("OpenAI", 182_844, None, None)},
            {"2025": ("Pinterest", 418_394, None, None)},
            {"2025": ("Pornhub", None, None, None)},  # Under Aylo
            {"2025": ("Quora", 5_646, None, None)},
            {"2025": ("Reddit", 65_381, None, None)},
            {"2025": ("Snap", 752_031, None, None)},
            {"2025": ("Telegram", None, None, None)},
            {"2025": ("Threads", 56_094, None, None)},
            {"2025": ("TikTok", 3_623_177, None, None)},
            {"2025": ("Tumblr", 2_881, None, None)},
            {"2025": ("Twitch", 2_390, None, None)},
            {"2025": ("Twitter", None, None, None)},
            {"2025": ("WhatsApp", 2_355_302, None, None)},
            {"2025": ("Wikimedia", 60, None, None)},
            {"2025": ("Wordpress", 176, None, None)},
            {"2025": ("X", 816_611, None, None)},
            {"2025": ("X.AI", 135_373, None, None)},
            {"2025": ("YouTube", None, None, None)},
            {"2025": ("ESP Total", 21_181_300, None, None)},
            {"2025": ("Total", 21_351_493, None, None)},
            # fmt: on
        ),
    }),
})
