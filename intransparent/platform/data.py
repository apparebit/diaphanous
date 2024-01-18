from .type import DisclosureCollectionType
from .. import __version__

REPORTS_PER_PLATFORM: DisclosureCollectionType = {
    "@": {
        # ──────────────────────────────────────────────────────────────
        "author": "Robert Grimm",
        "title": "Social Media CSAM Disclosures",
        "url": "https://github.com/apparebit/intransparent",
        "version": __version__,
        # ──────────────────────────────────────────────────────────────
    },
    "Alphabet": {
        "brands": ("Google", "YouTube"),
    },
    "Automattic": {
        "sources": ("https://transparency.automattic.com",),
        "brands": ("Tumblr", "Wordpress"),
    },
    "Facebook": {
        "sources": ("https://transparency.fb.com/sr/community-standards/",),
        "columns": (
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
        "rows": (
            # fmt: off
            {"2023 Q3": (None, 1_800_000, 16_900_000, None, 112_200, 266_600, None, 20_300, 87_800, None, 1_800, 116_600)},
            {"2023 Q2": (None, 1_700_000, 7_200_000, None, 94_400, 146_800, None, 20_500, 38_700, None, 1_400, 41_300)},
            {"2023 Q1": (None, 1_900_000, 8_900_000, None, 91_800, 104_500, None, 12_300, 20_800, None, 5_400, 17_200)},
            {"2022 Q4": (None, 2_500_000, 25_100_000, None, 94_700, 23_000, None, 13_600, 2_600, None, 541_700, 75_800)},
            {"2022 Q3": (None, 2_300_000, 30_100_000, None, 85_000, 414_200, None, 14_600, 4_000, None, 29_900, 205_300)},
            {"2022 Q2": (None, 1_900_000, 20_400_000, None, 61_700, 404_000, None, 11_300, 1_400, None, 18_700, 15_900)},
            {"2022 Q1": (None, 2_100_000, 16_500_000, None, 4_000, 800, None, 700, 100, None, 21_200, 687_800)},
            {"2021 Q4": (None, 1_800_000, 19_800_000, None, 3_700, 800, None, 800, 70, None, 19_200, 180_500)},
            {"2021 Q3": (None, 1_800_000, 21_200_000, None, 2_300, 700, None, 700, 30, None, 167_200, 2_800)},
            {"2021 Q2": (None, 2_300_000, 25_600_000, None, 3_000, 1_000, None, 800, 50, None, 21_100, 2_800)},
            {"2021 Q1": (5_000_000, None, None, 3_800, None, None, 300, None, None, 46_600, None, None)},
            {"2020 Q4": (5_300_000, None, None, 4_600, None, None, 100, None, None, 3_200, None, None)},
            {"2020 Q3": (12_400_000, None, None, 300, None, None, 0, None, None, 1_200, None, None)},
            {"2020 Q2": (9_400_000, None, None, 40, None, None, 0, None, None, 50, None, None)},
            {"2020 Q1": (8_500_000, None, None, 55_000, None, None, 3_700, None, None, 500, None, None)},
            {"2019 Q4": (13_300_000, None, None, 72_900, None, None, 4_400, None, None, 2_500, None, None)},
            {"2019 Q3": (11_400_000, None, None, 128_800, None, None, 13_300, None, None, 3_400, None, None)},
            {"2019 Q2": (6_900_000, None, None, 145_000, None, None, 14_200, None, None, 1_500, None, None)},
            {"2019 Q1": (5_800_000, None, None, 27_400, None, None, 800, None, None, 5_300, None, None)},
            {"2018 Q4": (7_200_000, None, None, None, None, None, None, None, None, None, None, None)},
            {"2018 Q3": (9_000_000, None, None, None, None, None, None, None, None, None, None, None)},
            # fmt: on
        ),
    },
    "Google": {
        "sources": (
            "https://transparencyreport.google.com/child-sexual-abuse-material/",
        ),
        "columns": ("pieces", "reports", "accounts", "urls"),
        "rows": (
            # fmt: off
            {"2023 H1": (4_025_703, 586_832, 259_576, 463_462)},
            {"2022 H2": (6_344_753, 891_215, 365_428, 437_020)},
            {"2022 H1": (6_426_749, 826_667, 270_487, 484_573)},
            {"2021 H2": (3_147_307, 334_215, 140_868, 580_380)},
            {"2021 H1": (3_280_632, 287_368, 129_174, 596_710)},
            {"2020 H2": (2_804_726, 246_325, 97_958, 210_756)},
            {"2020 H1": (1_461_582, 112_595, 77_940, 331_865)},
            # fmt: on
        ),
    },
    "Instagram": {
        "sources": ("https://transparency.fb.com/sr/community-standards/",),
        "columns": (
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
        "rows": (
            # fmt: off
            {"2023 Q3": (None, 227_700, 1_600_000, None, 44_400, 38_200, None, 5_600, 14_300, None, 1_100, 3_100)},
            {"2023 Q2": (None, 320_700, 1_700_000, None, 22_000, 22_800, None, 5_200, 6_300, None, 700, 700)},
            {"2023 Q1": (None, 567_100, 8_700_000, None, 29_100, 20_600, None, 4_300, 2_100, None, 2_400, 1_600)},
            {"2022 Q4": (None, 620_700, 9_700_000, None, 16_000, 5_800, None, 2_000, 100, None, 4_900, 2_400)},
            {"2022 Q3": (None, 1_000_000, 1_300_000, None, 36_000, 3_500, None, 4_100, 200, None, 6_400, 7_100)},
            {"2022 Q2": (None, 480_500, 1_200_000, None, 29_200, 4_100, None, 3_800, 200, None, 5_900, 400)},
            {"2022 Q1": (None, 600_700, 1_500_000, None, 0, 0, None, 0, 20, None, 10_700, 154_200)},
            {"2021 Q4": (None, 983_400, 2_600_000, None, 0, 0, None, 0, 0, None, 13_600, 1_600)},
            {"2021 Q3": (None, 526_500, 1_600_000, None, 0, 0, None, 0, 0, None, 168_300, 300)},
            {"2021 Q2": (None, 458_300, 1_400_000, None, 0, 0, None, 0, 0, None, 4_500, 300)},
            {"2021 Q1": (812_400, None, None, 0, None, None, 0, None, None, 3_500, None, None)},
            {"2020 Q4": (809_400, None, None, 0, None, None, 0, None, None, 2_900, None, None)},
            {"2020 Q3": (1_000_000, None, None, 0, None, None, 10, None, None, 700, None, None)},
            {"2020 Q2": (481_400, None, None, 0, None, None, 0, None, None, 30, None, None)},
            {"2020 Q1": (1_000_000, None, None, 53_400, None, None, 16_100, None, None, 200, None, None)},
            {"2019 Q4": (686_400, None, None, None, None, None, None, None, None, None, None, None)},
            {"2019 Q3": (755_800, None, None, None, None, None, None, None, None, None, None, None)},
            {"2019 Q2": (526_200, None, None, None, None, None, None, None, None, None, None, None)},
            # fmt: on
        ),
    },
    "LinkedIn": {
        "sources": ("https://about.linkedin.com/transparency/community-report",),
        "comments": ("numbers disclosed under 'content removed', hence pieces",),
        "columns": ("pieces",),
        "rows": (
            # fmt: off
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
    },
    "Meta": {
        "brands": ("Facebook", "Instagram", "WhatsApp"),
    },
    "Pinterest": {
        "sources": (
            "https://policy.pinterest.com/en/transparency-report",
            "https://help.pinterest.com/en/guide/transparency-report-archive",
        ),
        "comments": (
            "Pin is lingo for a media card with picture, hence pin with CSAM is piece.",
            "Pinterest's disclosure language explains 2nd through 5th columns:",
            "We deactivated a distinct images, which comprised b Pins, for violating",
            "our CSE policy. Of these, we determined that c distinct images, which",
            "comprised d Pins, were illegal CSAM, and we reported them to NCMEC.",
        ),
        "columns": (
            "reports",
            "distinct images",
            "pins",
            "distinct images CSAM",
            "pieces",
            "boards",
            "accounts",
            "account appeals",
            "account reversals",
            "% pins reached 0",
            "% pins reached 1-9",
            "% pins reached 10-100",
            "% pins reached >100",
        ),
        "rows": (
            # fmt: off
            {"2023 Q2": (None, 9_691, 3_877_286, 1_071, 16_336, 48_039, 172_633, 20_136, 9_874, 83, 14, 2, 1)},
            {"2023 Q1": (None, 8_393, 1_846_326, 2_348, 23_479, 17_715, 63_761, 8_524, 3_925, 65, 26, 6, 3)},
            {"2023 H1": (34_203, None, None, None, None, None, None, None, None, None, None, None, None)},
            {"2022 Q4": (None, 12_733, 1_716_192, 5_292, 24_288, 1_108, 33_228, 5_731, 2_686, 51, 35,9, 4)},
            {"2022 Q3": (None, 10_772, 687_825, 2_987, 7_318, 633, 21_033, 3_896, 2_053, 61, 29, 6, 3)},
            {"2022 H2": (27_995, None, None, None, None, None, None, None, None, None, None, None, None)},
            {"2022 Q2": (None, 9_085, 712_295, 2_038, 4_988, 1_162, 37_694, 7_467, 5_971, 61, 30, 6, 2)},
            {"2022 Q1": (None, 2_499, 300_003, 184, 542, 492, 10_743, 2_164, 1_169, 63, 28, 6, 3)},
            {"2022 H1": (4_969, None, None, None, None, None, None, None, None, None, None, None, None)},
            {"2021 Q4": (None, 2_545, 104_029, 228, 627, 578, 17_423, 3_110, 2_120, 83, 13, 3, 2)},
            {"2021 Q3": (None, 2_362, 262_164, 295, 981, 862, 28_289, 5_718, 4_305, 72, 21, 4, 2)},
            {"2021 H2": (1_794, None, None, None, None, None, None, None, None, None, None, None, None)},
            {"2021 H1": (890, None, None, None, None, None, None, None, None, None, None, None, None)},
            {"2020 H2": (1_794, None, None, None, None, None, None, None, None, None, None, None, None)},
            {"2020 H1": (1_638, None, None, None, None, None, None, None, None, None, None, None, None)},
            # fmt: on
        ),
    },
    "Quora": {
        "sources": (
            "https://help.quora.com/hc/en-us/articles/13294268051732-DSA-Transparency",
        ),
        "comments": (
            "Quora's first and only transparency report so far, with user numbers only",
        ),
    },
    "Reddit": {
        "sources": (
            "https://www.redditinc.com/policies/2023-h1-transparency-report",
            "https://www.redditinc.com/policies/2022-transparency-report",
            "https://www.redditinc.com/policies/mid-year-transparency-report-2022-2",
            "https://www.redditinc.com/policies/transparency-report-2021",
            "https://www.redditinc.com/policies/transparency-report-2020",
            "https://www.redditinc.com/policies/transparency-report-2019-1",
            "https://www.redditinc.com/policies/transparency",
        ),
        "comments": [
            "pieces includes posts and comments but not private messages"
        ],
        "columns": (
            "pieces",
            "reports",
            "pieces (minor sexualization)",
            "private messages (minor sexualization)",
            "subreddits (minor sexualization)",
            "temporary account suspensions (minor sexualization)",
            "accounts (minor sexualization)",
            "account appeals (minor sexualization)",
            "account reversals percent (minor sexualization)",
        ),
        "schema": {
            "account reversals percent (minor sexualization)": "float",
        },
        "rows": (
            # fmt: off
            {"2023 H1": (149_084, 156_533, 181_083, 296, 987, 27_219, 68_900, 2_924, 7.8)},
            {"2022 H2": (31_574, 40_243, None, None, None, None, None, None, None), "redundant": True},
            {"2022 H1": (None, 12_349, None, None, None, None, None, None, None), "redundant": True},
            {"2022": (80_888, 52_592, 266_473, 390, 5_149, 70_201, 93_997, 7_513, 9.5)},
            {"2021": (9_258, 10_059, 117_093, 243, 1_914, 0, 4_659, None, None)},
            {"2020": (None, 2_233, None, None, None, 15_940, 21_946, None, None)},
            {"2019": (None, 724, 38_410, None, 280, None, 10_781, None, None)},
            # fmt: on
        ),
    },
    "Snap": {
        "sources": (
            "https://values.snap.com/privacy/transparency",
            "https://values.snap.com/privacy/transparency-h2-2022",
            "https://values.snap.com/privacy/transparency-h1-2022",
            "https://www.snap.com/en-US/privacy/transparency/2021-12-31",
            "https://www.snap.com/en-US/privacy/transparency/2021-6-30",
            "https://www.snap.com/en-US/privacy/transparency/2020-12-31",
            "https://www.snap.com/en-US/privacy/transparency/2020-6-30",
            "https://www.snap.com/en-US/privacy/transparency/2019-12-31",
        ),
        "columns": ("pieces", "accounts", "reports"),
        "schema": {"accounts": "float"},
        "rows": (
            # fmt: off
            {"2023 H1": (548_509, 228_897, 292_489)},
            {"2022 H2": (527_787, 204_490, 265_285)},
            {"2022 H1": (746_051, 201_527, 285_470)},
            {"2021 H2": (None, 198_109, None)},
            {"2021 H1": (None, "5.43 / 100 * 2,510,798", None), "redundant": True},
            {"2021 H1": (None, 119_134, None)},
            {"2020 H2": (None, "2.99 / 100 * 2,100,124", None), "redundant": True},
            {"2020 H2": (None, 47_550, None)},
            {"2020 H1": (None, "2.99 / 100 * 1,578,985", None), "redundant": True},
            {"2020 H1": (None, 47_136, None)},
            {"2019 H2": (None, "2.51 / 100 * 1,355,163", None), "redundant": True},
            {"2019 H2": (None, 34_830, None)},
            # fmt: on
        ),
        "comments": (
            "For 2019 H2, a coarse continental breakdown is available:",
            "* CSAM accounts enforced EU 10,667; NorthAm 12,397; RestWorld 11,766",
            "* total accounts enforced EU 366,609; NorthAm 730,147; RestWorld 258,407",
        ),
    },
    "Telegram": None,
    "TikTok": {
        "sources": (
            "https://www.tiktok.com/transparency/en/community-guidelines-enforcement-2023-1/",
            "https://www.tiktok.com/transparency/en/community-guidelines-enforcement-2022-4/",
            "https://www.tiktok.com/transparency/en/community-guidelines-enforcement-2022-3/",
            "https://www.tiktok.com/transparency/en/community-guidelines-enforcement-2022-2/",
            "https://www.tiktok.com/transparency/en/community-guidelines-enforcement-2022-1/",
            "https://sf16-va.tiktokcdn.com/obj/eden-va2/nuvlojeh7ryht/Transparency_CGE_2022Q4/2022Q4_raw_data_cger_English.csv",
            "https://sf16-va.tiktokcdn.com/obj/eden-va2/nuvlojeh7ryht/Transparency_CGE_2022Q3/English_CGE_2022Q3.xlsx",
        ),
        "comments": (
            "category: minor safety; subcategory: sexual exploitation of minors",
            "category share only being given for human moderation renders data meaningless",
        ),
        "columns": (
            "pieces (human moderation)",
            "category share (human moderation)",
            "minor safety category share of total",
            "total videos removed (automation)",
            "total videos removed",
            "removal rate within 24 hours (human moderation)",
            "removal rate before any views (human moderation)",
            "proactive removal rate (human moderation)",
        ),
        "schema": {
            "category share (human moderation)": "float",
            "minor safety category share of total": "float",
            "removal rate within 24 hours (human moderation)": "float",
            "removal rate before any views (human moderation)": "float",
            "proactive removal rate (human moderation)": "float",
        },
        "rows": (
            # fmt: off
            {"2023 Q1": (None, 0.023, 0.306, 53_494_911, 91_003_510, 0.869, 0.784, 0.927)},
            {"2022 Q4": (415_278, 0.033, 0.333, 46_836_047, 85_680_819, 0.887, 0.821, 0.931)},
            {"2022 Q3": (792_473, 0.033, 0.429, 53_287_839, 110_954_663, 0.925, 0.883, 0.951,)},
            {"2022 Q2": (None, 0.024, 0.437, 48_011_571, 113_809_300, 0.907, 0.858, 0.932)},
            {"2022 Q1": (None, 0.019, 0.417, 34_726_592, 102_305_516, 0.903, 0.825, 0.906)},
            # fmt: on
        ),
    },
    "Tumblr": {
        "sources": ("https://www.tumblr.com/transparency",),
    },
    "Twitter": {
        "sources": (
            "https://transparency.twitter.com",
            "https://blog.twitter.com/en_us/topics/company/2023/an-update-on-twitter-transparency-reporting",
        ),
        "comments": ("'child sexual exploitation' is reported to NCMEC, hence CSAM",),
        "columns": (
            "accounts actioned",
            "accounts suspended",
            "distinct pieces",
        ),
        "rows": (
            # fmt: off
            {"2022 H1": (696_015, 691_704, 11_927)},
            {"2021 H2": (599_523, 596_997, 6_796)},
            {"2021 H1": (456_146, 453_754, 6_087)},
            {"2020 H2": (469_439, 464_804, 9_178)},
            {"2020 H1": (444_781, 438_809, 10_343)},
            {"2019 H2": (264_625, 257_768, 11_026)},
            {"2019 H1": (246_642, 245_341, 2_751)},
            {"2018 H2": (457_231, 455_651, 2_777)},
            # fmt: on
        ),
    },
    "WhatsApp": {
        "sources": (
            "https://www.whatsapp.com/legal/california-privacy-notice/transparency-report/",
        ),
        "comments": (
            "That appears to be the only transparency report WhatsApp ever released, as in 1.",
        ),
    },
    "Wordpress": {
        "sources": ("https://transparency.automattic.com",),
    },
    "YouTube": {
        "sources": (
            "https://transparencyreport.google.com/child-sexual-abuse-material/",
        ),
        "columns": ("pieces", "reports"),
        "rows": (
            # fmt: off
            {"2023 H1": (213_209, 163_844)},
            {"2022 H2": (359_931, 238_827)},
            {"2022 H1": (271_452, 217_610)},
            {"2021 H2": (135_517, 123_963)},
            {"2021 H1": (133_041, 124_773)},
            {"2020 H2": (99_591, 118_994)},
            {"2020 H1": (71_954, 69_961)},
            # fmt: on
        ),
    },
    "NCMEC": {
        "sources": (
            "https://www.missingkids.org/content/dam/missingkids/pdfs/2019-reports-by-esp.pdf",
            "https://www.missingkids.org/content/dam/missingkids/pdfs/2020-reports-by-esp.pdf",
            "https://www.missingkids.org/content/dam/missingkids/pdfs/2021-reports-by-esp.pdf",
            "https://www.missingkids.org/content/dam/missingkids/pdfs/2022-reports-by-esp.pdf",
            "https://www.missingkids.org/content/dam/missingkids/pdfs/2021-notifications-by-ncmec-per-esp.pdf",
            "https://www.missingkids.org/content/dam/missingkids/pdfs/2022-notifications-by-ncmec-per-esp.pdf",
        ),
        "comments": (
            "reports: number of reports *received* by NCMEC from a platform",
            "notifications_sent: number of hosted CSAM notices *sent* by NCMEC",
            "response_time: average days platform takes to respond/takedown",
            "missing response_time implies no action despite repeated notices",
            "original reports has entries for Google only, listed here under Alphabet",
            "notifications_sent & response_time have entries for Google and YouTube",
        ),
        "columns": ("platform", "reports", "notifications_sent", "response_time"),
        "schema": {
            "platform": "string",
            "response_time": "float"
        },
        "rows": (
            # fmt: off
            {"2019": ("Alphabet", 449_283, None, None)},
            {"2019": ("Automattic", 10_443, None, None)},
            {"2019": ("Facebook", None, None, None)},
            {"2019": ("Google", None, None, None)},
            {"2019": ("Instagram", None, None, None)},
            {"2019": ("LinkedIn", 88, None, None)},
            {"2019": ("Meta", 15_884_511, None, None)},
            {"2019": ("Pinterest", 7_360, None, None)},
            {"2019": ("Quora", 1, None, None)},
            {"2019": ("Reddit", 724, None, None)},
            {"2019": ("Snap", 82_030, None, None)},
            {"2019": ("Telegram", None, None, None)},
            {"2019": ("TikTok", 596, None, None)},
            {"2019": ("Tumblr", None, None, None)},
            {"2019": ("Twitter", 45_726, None, None)},
            {"2019": ("WhatsApp", None, None, None)},
            {"2019": ("Wordpress", None, None, None)},
            {"2019": ("YouTube", None, None, None)},
            {"2019": ("Total", 16_836_694, None, None)},

            {"2020": ("Alphabet", 546_704, None, None)},
            {"2020": ("Automattic", 9_130, None, None)},
            {"2020": ("Facebook", None, None, None)},
            {"2020": ("Google", None, None, None)},
            {"2020": ("Instagram", None, None, None)},
            {"2020": ("LinkedIn", 60, None, None)},
            {"2020": ("Meta", 20_307_216, None, None)},
            {"2020": ("Pinterest", 3_432, None, None)},
            {"2020": ("Quora", 2, None, None)},
            {"2020": ("Reddit", 2_233, None, None)},
            {"2020": ("Snap", 144_095, None, None)},
            {"2020": ("Telegram", None, None, None)},
            {"2020": ("TikTok", 22_692, None, None)},
            {"2020": ("Tumblr", None, None, None)},
            {"2020": ("Twitter", 65_062, None, None)},
            {"2020": ("WhatsApp", None, None, None)},
            {"2020": ("Wordpress", None, None, None)},
            {"2020": ("YouTube", None, None, None)},
            {"2020": ("Total", 21_447_786, None, None)},

            {"2021": ("Alphabet", 875_783, None, None)},
            {"2021": ("Automattic", None, None, None)},
            {"2021": ("Facebook", 22_118_952, 28, 7.27)},
            {"2021": ("Google", None, 975, 6.77)},
            {"2021": ("Instagram", 3_393_654, 22, 4.45)},
            {"2021": ("LinkedIn", 110, None, None)},
            {"2021": ("Meta", None, None, None)},
            {"2021": ("Pinterest", 2_283, 56, 0.69)},
            {"2021": ("Quora", 25, 1, 0.71)},
            {"2021": ("Reddit", 10_059, 233, 1.39)},
            {"2021": ("Snap", 512_522, None, None)},
            {"2021": ("Telegram", None, 229, 8.0)},
            {"2021": ("TikTok", 154_618, None, None)},
            {"2021": ("Tumblr", 4_511, 52, 0.49)},
            {"2021": ("Twitter", 86_666, 1_017, 1.82)},
            {"2021": ("WhatsApp", 1_372_696, 2, 3.32)},
            {"2021": ("Wordpress", 310, 26, 1.95)},
            {"2021": ("YouTube", None, 10, 2.2)},
            {"2021": ("Total", 29_157_083, 75_038, 1.22)},

            {"2022": ("Alphabet", 2_174_548, None, None)},
            {"2022": ("Automattic", None, None, None)},
            {"2022": ("Facebook", 21_165_208, 10, 4.4)},
            {"2022": ("Google", None, 916, 4.2)},
            {"2022": ("Instagram", 5_007_902, 13, 3.7)},
            {"2022": ("LinkedIn", 201, None, None)},
            {"2022": ("Meta", None, None, None)},
            {"2022": ("Pinterest", 34_310, 46, 1.1)},
            {"2022": ("Quora", 2_242, None, None)},
            {"2022": ("Reddit", 52_592, 275, 2.4)},
            {"2022": ("Snap", 551_086, None, None)},
            {"2022": ("Telegram", None, 73, 5.1)},
            {"2022": ("TikTok", 288_125, 1, 0.2)},
            {"2022": ("Tumblr", 4_845, 92, 0.9)},
            {"2022": ("Twitter", 98_050, 1_278, 1.8)},
            {"2022": ("WhatsApp", 1_017_555, 2, 5.2)},
            {"2022": ("Wordpress", 190, 155, 1.6)},
            {"2022": ("YouTube", None, 14, 3.6)},
            {"2022": ("Total", 31_802_525, 80_969, None)},
            # fmt: on
        ),
    },
}
