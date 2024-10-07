# Diaphanous: Transparency Disclosures About the Sexual Exploitation of Minors

This repository curates quantitative transparency disclosures about the online
sexual exploitation of minors, i.e., people under the age of eighteen, in
machine-readable form. It also includes a 4,400-line Python library for
validating and tidying the data and Python as well as R notebooks with the
analysis for the corresponding report [Putting the Count Back Into
Accountability: An Audit of Social Media Transparency Disclosures, Focusing on
Sexual Exploitation of Minors](https://arxiv.org/abs/2402.14625).

Please cite as: Robert Grimm. Diaphanous: Transparency Disclosures About the
Sexual Exploitation of Minors.


## The Code

To run the code in this repository, you'll need the following tools:

  * According to [vermin](https://github.com/netromdk/vermin), the minimmum
    required Python version is 3.11.
  * The [analysis/platform.ipynb](analysis/platform.ipynb) notebook is written
    in Python and R. The necessary bindings are provided by the
    [rpy2](https://rpy2.github.io) Python package. The package is installed like
    other Python packages as described in the next bullet point. But it does
    require a working R installation (e.g.,
    <code>brew&nbsp;install&nbsp;r</code>).
  * Required Python packages are listed in the repository's
    [pyproject.toml](pyproject.toml). The simplest way of installing the
    project's dependencies is create a local clone of this repository and then
    installing it thusly:
    ```sh
    $ python -m venv .venv   # Create virtual environment
    $ . .venv/bin/activate   # Activate virtual environment
    $ pip install -e .       # Install diaphanous as editable
    ```
    Thanks to the `-e` option, `pip install` creates a so-called editable
    install, i.e., it makes the Python code in the `diaphanous` package
    executable without copying it. It also installs all necessary dependencies.

Building the report requires additional tools, i.e., a working LaTeX
installation, though the necessary incantations [are scripted](report/build.sh).


## The Data

While a few CSV files contain [tidy
data](https://vita.had.co.nz/papers/tidy-data.pdf), others are decidedly untidy
with, for example, individual columns combining two variables. The organization
of a dataset usually reflects that of the original disclosure and helps ensuring
the correctness of data transcription. The Python package includes several
examples for how to tidy up such data.


### Dataset 1: CyberTipline Reports per Year (1998 onward)

The [CyberTipline reports per year](data/ocse-reports-per-year.csv) dataset
captures the number of reports NCMEC received on its CyberTipline since
inception in March 1998, largely based on the table included in Appendix A of
its
[2022](https://www.missingkids.org/content/dam/missingkids/pdfs/OJJDP-NCMEC-Transparency_2022-Calendar-Year.pdf)
and
[2023](https://www.missingkids.org/content/dam/missingkids/pdfs/OJJDP-NCMEC-Transparency-CY-2023-Report.pdf)
transparency reports to the Office for Juvenile Justice and Delinquency
Prevention at the Department of Justice.


### Dataset 2: CyberTipline Report Contents and Recipients (2020 onward)

The CyberTipline report [contents](data/ocse-report-contents.csv) and
[recipients](data/ocse-report-recipients.csv) dataset breaks down the reports
NCMEC received by:

  * the category of sexual exploitation, e.g., whether a report concerns child
    pornography, misleading words/images, online enticement, child sex
    trafficking, obscene material sent to a child, misleading domain names,
    child sexual molestation, or child sex tourism;
  * the kind of attachments, e.g., photos, videos, or other;
  * the uniqueness of attachments as determined by a precise hash (MD5) and a
    perceptual hash (PhotoDNA, Videntifier);
  * their level of detail, i.e., whether they are actionable or only
    informational;
  * their recipients in dedicated units, local, federal, or international law
    enforcement.

Labels for the uniqueness classification use "unique" for precisely hashed
attachments and "similar" for perceptually hashed ones. The dataset combines
several tables from NCMEC's
[2022](https://www.missingkids.org/content/dam/missingkids/pdfs/OJJDP-NCMEC-Transparency_2022-Calendar-Year.pdf)
and
[2023](https://www.missingkids.org/content/dam/missingkids/pdfs/OJJDP-NCMEC-Transparency-CY-2023-Report.pdf)
transparency reports to the Office for Juvenile Justice and Delinquency
Prevention at the Department of Justice.


### Dataset 3: CyberTipline Reports per Platform (2019 onward)

The [CyberTipline reports per platform](data/ocse-reports-per-platform.json)
dataset is the project's main dataset. It collects:

  * the CSAM disclosures by major non-Chinese social networks and other large
    service providers;
  * corresponding disclosures about service providers' reporting by NCMEC.

The above linked JSON format is [automatically
generated](diaphanous/platform/export.py) from a [Python
module](diaphanous/platform/data.py). Both formats have the same structure
and contain the same information.

The dataset incorporates information about these platforms:

  * Amazon (owns Twitch)
  * Apple
  * Automattic (owns Tumblr and Wordpress)
  * Aylo (née MindGeek)
  * Discord
  * Facebook (Meta)
  * GitHub (Microsoft)
  * Google (owns YouTube)
  * Instagram (Meta)
  * LinkedIn (Microsoft)
  * Meta (owns Facebook, Instagram, and WhatsApp)
  * Microsoft (owns GitHub and LinkedIn)
  * MindGeek (now Aylo)
  * Omegle
  * Pinterest
  * Pornhub (Aylo)
  * Quora
  * Reddit
  * Snap
  * Telegram
  * TikTok
  * Tumblr (Automattic)
  * Twitch (Amazon)
  * Twitter (now X)
  * WhatsApp (Meta)
  * Wikimedia
  * Wordpress (Automattic)
  * X (née Twitter)
  * YouTube (Google)

Surveyed organizations fall into at least one of the following categories:

  * Social media based on Buffer's list of [top social media
    sites](https://buffer.com/library/social-media-sites/),
  * Popular platforms based on the European Commission's list of [very large
    online
    platforms](https://digital-strategy.ec.europa.eu/en/policies/list-designated-vlops-and-vloses),
  * Platforms with considerable reported child sexual exploitation activity
    based on NCMEC's transparency disclosures.

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

      * _reports_ tallies CyberTipline reports to NCMEC;
      * _pieces_ tallies instances of CSAM such as pictures and videos;
      * _accounts_ tallies user registrations implicated *and* terminated
        for CSAM;

    Instead of "account termination," many platforms use a euphemism such as
    "permanent suspension." User registrations thusly impacted *are* included
    under *accounts*. However, temporarily impacted registrations are not.

[Comparable CyberTipline report counts](data/comparable-reports.csv) and
[per-provider comparable CyberTipline report
counts](data/comparable-reports-by-provider.csv) are materialized views onto the
same data. Both views are in long format and only include rows for counts that
were disclosed by both electronic service provider and NCMEC.

The latter, more precise view has _year_, _observer_, _count_, and _topic_
columns, with the topic column enabling the grouping of rows with service
provider and NCMEC as observers. The former, simplified view has only _id_,
_observer_, and _count_ columns, with the ID column effectively combining the
other view's _year_ and _topic_ columns and the _observer_ column only
distinguishing between a generic *ServiceProvider* and NCMEC.



### Dataset 4: CyberTipline Reports per Country (2019 onward)

[CyberTipline reports per country](data/ocse-reports-per-country.csv) collects
NCMEC's per-country breakdown of CyberTipline reports for
[2019](https://www.missingkids.org/content/dam/missingkids/pdfs/2019-cybertipline-reports-by-country.pdf),
[2020](https://www.missingkids.org/content/dam/missingkids/pdfs/2020-reports-by-country.pdf),
[2021](https://www.missingkids.org/content/dam/missingkids/pdfs/2021-reports-by-country.pdf),
[2022](https://www.missingkids.org/content/dam/missingkids/pdfs/2022-reports-by-country.pdf),
and
[2023](https://www.missingkids.org/content/dam/missingkids/pdfs/2023-reports-by-country.pdf)
in machine-readable form. The CSV table is mostly straightforward: Its first two
columns comprise the country name and ISO three-letter code, followed by a
column per year from 2019 through 2022.

To preserve all information from NCMEC's disclosures, the table includes rows
for the Netherlands Antilles (ANT), "Europe" (EEE), Bouvet Island (BVT), and "No
Country Listed" (*no code*). NCMEC does not explain its inclusion of Europe in
addition to individual European countries nor the Netherlands Antilles in
addition to its 2010 successors Bonaire, Sint Eustatius, and Saba (BES), Curaçao
(CUW), and Sint Maarten (SXM). Neither do they explain the inclusion of Bouvet
Island; the subantarctic dependency of Norway is an uninhabited nature reserve
and hence rather unlikely to serve as actual location of internet users.

This repository's Python package includes [code that
enriches](diaphanous/country.py) this dataset with population counts,
geometries, and region/continent information. It leverages the following data:

  * Per-country population counts by the [United Nations Population
    Division](https://population.un.org/dataportal/data/indicators/49/locations/4,8,12,16,20,24,660,28,32,51,533,36,40,31,44,48,50,52,112,56,84,204,60,64,68,535,70,72,76,92,96,100,854,108,132,116,120,124,136,140,148,152,156,344,446,158,170,174,178,184,188,384,191,192,531,196,203,408,180,208,262,212,214,218,818,222,226,232,233,748,231,238,234,242,246,250,254,258,266,270,268,276,288,292,300,304,308,312,316,320,831,324,624,328,332,336,340,348,352,356,360,364,368,372,833,376,380,388,392,832,400,398,404,296,412,414,417,418,428,422,426,430,434,438,440,442,450,454,458,462,466,470,584,474,478,480,175,484,583,492,496,499,500,504,508,104,516,520,524,528,540,554,558,562,566,570,807,580,578,512,586,585,591,598,600,604,608,616,620,630,634,410,498,638,642,643,646,652,654,659,662,663,666,670,882,674,678,682,686,688,690,694,702,534,703,705,90,706,710,728,724,144,275,729,740,752,756,760,762,764,626,768,772,776,780,788,792,795,796,798,800,804,784,826,834,840,850,858,860,548,862,704,876,732,887,894,716/start/2019/end/2022/table/pivotbylocation);
  * Per-country internet user counts prepared by [Our World in
    Data](https://ourworldindata.org/internet) from statistics released by the
    International Telecommunication Union via WorldBank as well as the United
    Nations;
  * Administrative boundaries for countries by [Natural Earth, version
    5.1.1](https://www.naturalearthdata.com/downloads/110m-cultural-vectors/);
  * Per-country ISO 3166 Alpha-2 and Alpha-3 codes scraped from [ISO's
    website](https://www.iso.org/obp/ui/#search/code/) and corresponding region
    names based on [Luke Duncalfe's ISO-3166
    dataset](https://github.com/lukes/ISO-3166-Countries-with-Regional-Codes).

The following choropleths using the Equal Earth projection visualize normalized
per country CSAM reports:

![CyberTipline reports per capita per country per
year](https://raw.githubusercontent.com/apparebit/diaphanous/boss/figure/reports-per-capita.svg)


### Dataset 5: Platform Data (2020 onward)

Discord, Meta, Microsoft, and TikTok have released (some) data in
machine-readable form. This dataset contains the corresponding files. Discord's
and Meta's data is in CSV format, Microsoft's in Excel format, and TikTok's in
Excel and later on CSV format. Meta's and TikTok's files include historical data
whereas Discord's and Microsoft's do not. Since Meta re-uses [the same
URL](https://transparency.fb.com/sr/community-standards/) every quarter, files
released before Q2 2022 were retrieved from the Internet Archive's snapshots.


### Dataset 6: Relationship between Offender and Victim

The [CSAM pieces by relationship to
victim](data/csam-pieces-by-relationship-to-victim.csv) dataset captures the
relationship between suspected offenders and victims as determined by law
enforcement agencies and tabulated by NCMEC. It is included in NCMEC's
[2022](https://www.missingkids.org/content/dam/missingkids/pdfs/OJJDP-NCMEC-Transparency_2022-Calendar-Year.pdf)
and
[2023](https://www.missingkids.org/content/dam/missingkids/pdfs/OJJDP-NCMEC-Transparency-CY-2023-Report.pdf)
transparency reports to the Office for Juvenile Justice and Delinquency
Prevention at the Department of Justice.

Since the number of victims in NCMEC's database seems to be very small, I pulled
in two more datasets characterizing relationships as well. [The
first](data/ojjdp-qa02403-2019.csv) stems from [OJJDP's Statistical Briefing
Book](https://www.ojjdp.gov/ojstatbb/victims/qa02403.asp?qaDate=2019) and covers
years 2018 and 2019. The data was originally extracted from the FBI's National
Incident-Based Reporting System Master Files. Note that all counts are relative
to "typical 1,000 sexual assaults." [The
second](data/learcat-relationship-2016.csv) stems from
[LEARCAT](https://learcat.bjs.ojp.gov) and covers the year 2016. It also draws
on the FBI's National Incident-Based Reporting System. While the Briefing Book
data is helpful indeed, the choice of relationship bins for the LEARCAT data
renders it close to useless in this context.


### Other Data

The `data` directory contains a few more tables, including one with [global
population sizes](data/global-population.csv) also provided by the UN Population
Division and one with Meta's [daily and monthly active
people](data/meta/family-active-people.csv), which captures the number of users
who logged into Facebook, Instagram, Messenger, or WhatsApp at least one over a
day or month. Both tables are used to calculate Meta's daily and monthly active
people as a fraction of the world population.


## Repository Layout

In addition to the data, this repository also contains the Python code for
analyzing it as well as resulting figures. In particular:

  - The `analysis` directory contains notebooks with the high-level analysis
    code. The `index.ipynb` notebook includes almost all other notebooks.
  - The `diaphanous` directory contains the Python library code used by the
    notebooks.
      - The remaining code in `diaphanous.main` should be refactored into
        notebooks.
      - The `show()` function in `diaphanous.show` is more generally useful.
        Most of this functionality should be up-streamed to Pandas because it
        significantly improves on the default table format.
  - The `figure` directory contains SVG figures.
  - The `stubs` directory contains typing stubs.
  - The `report` directory contains the LaTeX sources for the article discussing
    the work.


## Acronyms

  - **CSAM**: Child Sexual Abuse Material
  - **CSE**: Child Sexual Exploitation
  - **NCMEC**: National Center for Missing and Exploited Children
  - **OCSE**: Online Child Sexual Exploitation
  - **OJJDP**: Office for Juvenile Justice and Delinquency Prevention (at the US
    Departmet of Justice)


## Licensing

The code in this repository is ©️ 2023–2024 by Robert Grimm and has been
released under the [Apache 2.0](LICENSE) open source license. The datasets in
this repository combine disclosures by electronic service providers as well as
the National Center for Missing and Exploited Children (NCMEC) and make this
data more easily accessible in machine-readable form. It has been released under
the [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) license.
