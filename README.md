# Intransparent: Child Sexual Abuse Material Reporting

This repository curates two datasets and supporting Python library covering
reports of child sexual abuse material (CSAM) made to the National Center for
Missing and Exploited Children (NCMEC). In the United States, all electronic
platforms are [legally
required](https://www.law.cornell.edu/uscode/text/18/2258A) to report even
possession or receipt of CSAM to this clearing house. The datasets combine the
transparency disclosures of major platforms and the clearing house.


## Dataset 1: CSAM Reports per Platform

The [CSAM reports per platform](data/csam-reports-per-platform.json) dataset
collects:

  * the CSAM disclosures by major non-Chinese social networks;
  * corresponding disclosures about platforms' reporting by NCMEC.

The above linked JSON format is [automatically
generated](intransparent/by_platform.py/export.py) from a [Python
module](intransparent/by_platform/data.py). Both formats have the same structure
and contain the same information.

The dataset incorporates information about these platforms:

  * Facebook
  * Instagram
  * LinkedIn
  * Pinterest
  * Quora
  * Reddit
  * Snap
  * Telegram
  * TikTok
  * Tumblr
  * Twitter
  * WhatsApp
  * Wordpress
  * YouTube

It also incorporates information about the following companies (with each
operating at least one of the above platforms):

  * Automattic
  * Meta
  * Google

A separate [codebook](codebook.md) documents the JSON and Python formats.
Basically, they consist of a top-level object that maps organization names to an
object with the data about that organization. Since platforms vary widely in
what metrics they disclose, the format necessarily is rather generic and
collects all of a platform's quantitative disclosures within one table:

  * Since platforms make transparency disclosures for quarter, half, and full
    years, each table also organizes metrics into time periods with the same
    granularity.
  * To faithfully capture disclosures, time periods may vary within a table.
    They may also overlap, both to capture several partial disclosures and to
    capture several redundant disclosures. A flag clearly marks the latter
    entries.
  * Where possible, the table uses standard labels for equivalent metrics:

      * _reports_ tallies CSAM reports to NCMEC;
      * _pieces_ tallies individual pictures and videos that are CSAM;
      * _accounts_ tallies user registrations terminated or "permanently suspended"
        for CSAM.


### Data Quality Issues Abound

Ideally, such a dataset would enable the comparison of metrics across platforms.
Furthermore, counts of "CSAM reports" disclosed by platforms would closely match
equivalent counts disclosed by NCMEC. But in practice, many platforms don't
disclose the necessary metrics and thus we can match reports submitted by a
platform with reports received by NCMEC for only four out of the 17 social media
platforms and companies listed above. They are Google including YouTube,
Pinterest, Reddit, and Snap.

  * Reddit's counts are identical to NCMEC's counts for the four years covered
    by matching disclosures.
  * Google/YouTube's counts are well within +/- 1% of NCMEC's for the three
    years covered by matching disclosures.
  * Snap's single matching count differs by 93% from NCMEC's.
  * Worse, Pinterest's count matches NCMEC's in 2020, differs by -15% in 2021,
    and then differs by 590% in 2022. That's the wrong trend!

The other platforms cannot be matched because they do not make meaningful
transparency disclosures or because they focus on pieces of CSAM and ignore
reports to NCMEC. In particular, Telegram is entirely intransparent. Quora has
disclosed a single count so far, its user number to satisfy the [EU's
DSA](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32022R2065). In
contrast, Automattic has been making actual disclosures, though they focus on
government actions, terrorist content, and violations of intellectual property
rights.

Twitter discloses the number of accounts penalized, almost 600,000 in H2 2021,
and the number of CSAM pieces removed from the platform, barely 6,800 in H2
2021. Typically, pieces are clearly larger than accounts actioned, which
suggests that the latter really are *unique* CSAM pieces. In other words Twitter
is cherry-picking the metrics, using accounts actioned to show off how effective
its efforts are and unique pieces to obscure that significantly more than 6,800
pieces were shared on Twitter during the same time period.

Next, TikTok's disclosures omit critical data and hence make no sense. Meta is
responsible for well over 90% of all CSAM pieces and reports. For unknown
reasons, the company does not release data about WhatsApp and its data for
Facebook and Instagram suffers from several, significant data quality issues.
Finally, LinkedIn's disclosures seem largely perfunctory. But then again, CSAM
just doesn't occur on LinkedIn, with the firm reporting less than 2,600 pieces
over four years. By contrast, Meta reported 25,100,000 pieces for Facebook only
during the fourth quarter of 2022 only.


## Dataset 2: CSAM Reports per Country

[CSAM reports per country](data/csam-reports-per-country.csv) collects NCMEC's
per-country breakdown of CSAM reports for
[2019](https://www.missingkids.org/content/dam/missingkids/pdfs/2019-cybertipline-reports-by-country.pdf),
[2020](https://www.missingkids.org/content/dam/missingkids/pdfs/2020-reports-by-country.pdf),
[2021](https://www.missingkids.org/content/dam/missingkids/pdfs/2021-reports-by-country.pdf),
and
[2022](https://www.missingkids.org/content/dam/missingkids/pdfs/2022-reports-by-country.pdf)
together in machine-readable form. The corresponding table is rather simple. Its
six columns comprise the country name, the ISO three-letter code, as well as the
numbers of reports for the country in 2019, 2020, 2021, and 2022, one count per
country per year.

The supporting Python package includes [code that
enriches](intransparent/country.py) this dataset with population counts,
geometries, and region/continent information. It leverages the following data:

  * Per-country population counts by the [United Nations Population
    Division](https://population.un.org/dataportal/data/indicators/49/locations/4,8,12,16,20,24,660,28,32,51,533,36,40,31,44,48,50,52,112,56,84,204,60,64,68,535,70,72,76,92,96,100,854,108,132,116,120,124,136,140,148,152,156,344,446,158,170,174,178,184,188,384,191,192,531,196,203,408,180,208,262,212,214,218,818,222,226,232,233,748,231,238,234,242,246,250,254,258,266,270,268,276,288,292,300,304,308,312,316,320,831,324,624,328,332,336,340,348,352,356,360,364,368,372,833,376,380,388,392,832,400,398,404,296,412,414,417,418,428,422,426,430,434,438,440,442,450,454,458,462,466,470,584,474,478,480,175,484,583,492,496,499,500,504,508,104,516,520,524,528,540,554,558,562,566,570,807,580,578,512,586,585,591,598,600,604,608,616,620,630,634,410,498,638,642,643,646,652,654,659,662,663,666,670,882,674,678,682,686,688,690,694,702,534,703,705,90,706,710,728,724,144,275,729,740,752,756,760,762,764,626,768,772,776,780,788,792,795,796,798,800,804,784,826,834,840,850,858,860,548,862,704,876,732,887,894,716/start/2019/end/2022/table/pivotbylocation);
  * Administrative boundaries for countries by [Natural Earth, version
    5.1.1](https://www.naturalearthdata.com/downloads/110m-cultural-vectors/);
  * Per-country ISO 3166 Alpha-3 codes scraped from [ISO's
    website](https://www.iso.org/obp/ui/#search/code/) and corresponding region
    names based on [Luke Duncalfe's ISO-3166
    dataset](https://github.com/lukes/ISO-3166-Countries-with-Regional-Codes).


### Some Data Quality Concerns

NCMEC's CSAM reports per country suffer from data quality issues as well. But
they only impact a tiny fraction of reports. In particular:

  * The Netherlands Antilles (ANT) was split into Bonaire, Sint Eustatius, and
    Saba (BES), Curaçao (CUW), and Sint Maarten (SXM) in 2010. Yet four years
    include counts for ANT, CUW, as well as SXM, and three years include counts
    for BES.
  * Bouvet Island (BVT) is a subantarctic Norwegian territory. It is a nature
    preserve and has no man-made structures besides an automated weather
    station. Yet one year includes counts for BVT.
  * "Europe" is a rather ill-defined entity (and hence only maybe EUR). Its
    makes little sense, since all European countries down to the smallest three,
    i.e., Vatican City (VAT), Monaco (MCO), and San Marino (SMR), are already
    present.
  * "French Guiana" and "Guiana, French" (GUF) obviously are the same French
    overseas department in South America. Yet two years include distinct counts
    for each.
