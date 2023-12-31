# Intransparent: Independent Validation of Social Media Transparency Data

This repository curates transparency data published by social media firms, with
a focus on child sexual abuse material (CSAM), and the code to analyze that same
data, with a focus on assessing its quality. The focus on CSAM is not arbitrary:
As "electronic communication service providers," all US-based social media firms
are [legally required](https://www.law.cornell.edu/uscode/text/18/2258A) to
report such material to the National Center for Missing and Exploited Children
(NCMEC). The Center receives reports through its CyberTipline, triages them, and
then routes them to appropriate national and international law enforcement
agencies. Similar to social media companies, NCMEC started making transparency
disclosures has startThat raises
the possibility of validating social media firms' transparency disclosures by
comparing them to those made by NCMEC.


## Dataset 1: CSAM Reports per Year (1998 onward)

The [CSAM reports per year](data/csam-reports-per-year.csv) dataset captures the
number of reports NCMEC received on its CyberTipline since inception in March
1998, as disclosed in Appendix A of its [CY 2022 Report to the Committees on
Appropriations](https://www.missingkids.org/content/dam/missingkids/pdfs/OJJDP-NCMEC-Transparency_2022-Calendar-Year.pdf).


## Dataset 2: CSAM Reports per Platform (2019 onward)

The [CSAM reports per platform](data/csam-reports-per-platform.json) dataset is
the main dataset provided by this repository. It collects:

  * the CSAM disclosures by major non-Chinese social networks;
  * corresponding disclosures about platforms' reporting by NCMEC.

The above linked JSON format is [automatically
generated](intransparent/platform/export.py) from a [Python
module](intransparent/platform/data.py). Both formats have the same structure
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

It also incorporates information about the following companies operating one or
more of the above platforms:

  * Automattic (Tumblr and Wordpress)
  * Meta (Facebook, Instagram, WhatsApp)
  * Google (YouTube)

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
      * _pieces_ tallies instances of CSAM such as pictures and videos;
      * _accounts_ tallies user registrations implicated *and* terminated
        for CSAM;

    Instead of "account termination," many platforms use a euphemism such as
    "permanent suspension." User registrations thusly impacted *are* included
    under *accounts*. However, temporarily impacted registrations are not.


## Dataset 3: CSAM Reports per Country (2019 onward)

[CSAM reports per country](data/csam-reports-per-country.csv) collects NCMEC's
per-country breakdown of CSAM reports for
[2019](https://www.missingkids.org/content/dam/missingkids/pdfs/2019-cybertipline-reports-by-country.pdf),
[2020](https://www.missingkids.org/content/dam/missingkids/pdfs/2020-reports-by-country.pdf),
[2021](https://www.missingkids.org/content/dam/missingkids/pdfs/2021-reports-by-country.pdf),
and
[2022](https://www.missingkids.org/content/dam/missingkids/pdfs/2022-reports-by-country.pdf)
in machine-readable form. The CSV table is mostly straightforward: Its first two
columns comprise the country name and ISO three-letter code, followed by a
column per year from 2019 through 2022. Still, a couple of details are
noteworthy:

  * When a country does not appear in NCMEC's report for the year, the
    corresponding entry is empty not zero.
  * When the count is larger than 999, the corresponding entry uses commas as
    thousand separators and hence is double-quoted.
  * To preserve all information from NCMEC's disclosures, the table includes
    rows for the Netherlands Antilles (ANT), "Europe" (EEE), and "No Country
    Listed" (*no code*). NCMEC does not explain its inclusion of Europe in
    addition to individual European countries nor the Netherlands Antilles in
    addition to its 2010 successors Bonaire, Sint Eustatius, and Saba (BES),
    Curaçao (CUW), and Sint Maarten (SXM).
  * For the same reason, the table includes a row for Bouvet Island (BVT) even
    though the subantarctic dependency of Norway is an uninhabited nature
    reserve.

This repository's Python package includes [code that
enriches](intransparent/country.py) this dataset with population counts,
geometries, and region/continent information. It leverages the following data:

  * Per-country population counts by the [United Nations Population
    Division](https://population.un.org/dataportal/data/indicators/49/locations/4,8,12,16,20,24,660,28,32,51,533,36,40,31,44,48,50,52,112,56,84,204,60,64,68,535,70,72,76,92,96,100,854,108,132,116,120,124,136,140,148,152,156,344,446,158,170,174,178,184,188,384,191,192,531,196,203,408,180,208,262,212,214,218,818,222,226,232,233,748,231,238,234,242,246,250,254,258,266,270,268,276,288,292,300,304,308,312,316,320,831,324,624,328,332,336,340,348,352,356,360,364,368,372,833,376,380,388,392,832,400,398,404,296,412,414,417,418,428,422,426,430,434,438,440,442,450,454,458,462,466,470,584,474,478,480,175,484,583,492,496,499,500,504,508,104,516,520,524,528,540,554,558,562,566,570,807,580,578,512,586,585,591,598,600,604,608,616,620,630,634,410,498,638,642,643,646,652,654,659,662,663,666,670,882,674,678,682,686,688,690,694,702,534,703,705,90,706,710,728,724,144,275,729,740,752,756,760,762,764,626,768,772,776,780,788,792,795,796,798,800,804,784,826,834,840,850,858,860,548,862,704,876,732,887,894,716/start/2019/end/2022/table/pivotbylocation);
  * Administrative boundaries for countries by [Natural Earth, version
    5.1.1](https://www.naturalearthdata.com/downloads/110m-cultural-vectors/);
  * Per-country ISO 3166 Alpha-2 and Alpha-3 codes scraped from [ISO's
    website](https://www.iso.org/obp/ui/#search/code/) and corresponding region
    names based on [Luke Duncalfe's ISO-3166
    dataset](https://github.com/lukes/ISO-3166-Countries-with-Regional-Codes).

The following choropleths using the Equal Earth projection visualize normalized
per country CSAM reports:

![CSAM reports per capita per country per
year](https://raw.githubusercontent.com/apparebit/intransparent/boss/csam-reports-per-capita.svg)


## Dataset 4: Meta's Quarterly Transparency Data (Q1 2021 onward)

Meta's quarterly transparency disclosures include a CSV file with data for the
current and all previous quarters in machine-readable form. Presumably, for just
reason Meta does not maintain an externally accessible archive of previously
released CSV files. This dataset collects the quarterly CSV files from Q2 2021
onward. Files prior to Q2 2022 were retrieved from archive.org's snapshots for
the [unchanging URL](https://transparency.fb.com/sr/community-standards/) for
the data and files for that and later quarters were manually downloaded from the
URL. The files are included because a small but significant number of historical
quantities changed every quarter until 2023.
