# Intransparent: Social Media Disclosures about Child Sexual Abuse Material

This repository curates transparency disclosures about child sexual abuse
material (CSAM) on social media. It collects transparency disclosures (or the
lack thereof) by social media firms and the National Center for Missing and
Exploited Children (NCMEC), which is the [legally
mandated](https://www.law.cornell.edu/uscode/text/18/2258A) clearing house for
such material in the United States. It also provides Python code for the
curation, validation, and analysis of the data.

If you use data, code, or results, please cite this work as follows:

> Robert Grimm. Intransparent: Social Media Disclosures about Child Sexual Abuse
> Material. Dataset and analysis code, version 1.0, July 2023, hosted by Zenodo.


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
      * _pieces_ tallies instances of CSAM such as pictures and videos;
      * _accounts_ tallies user registrations implicated *and* terminated
        for CSAM;

    Instead of "account termination," many platforms use a euphemism such as
    "permanent suspension." User registrations thusly impacted *are* included
    under *accounts*. However, temporarily impacted registrations are not.


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
numbers of reports for the country in 2019, 2020, 2021, and 2022, with exactly
one quantity per country per year.

The supporting Python package includes [code that
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


### Fewer, Lesser Data Quality Concerns

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


### Regional Oddities

When it comes to CSAM reports per capita per country, between 9 and 11 of the 20
countries with the highest rates are in North Africa abutting the Mediterranean
or on the Arab peninsula, i.e., all member countries of the Arab League. Libya
and the United Arab Emirates is the country with the highest rate for two out of
four years. Since the two countries differ significantly when it comes to
political stability and wealth, it seems likely that some shared cultural factor
explains the relatively high prevalence of CSAM in Arab League countries.

Having said that, the total number of CSAM reports made to NCMEC doubled over
four years. However, the number of reports per capita per country in the Arab
League has not been growing and even declined a little during the last year.
Almost all the growth is due to other countries. In other words, if this trend
continues, countries that are not in the Arab League are likely to catch up or
even exceed the rates observed for countries that are in the Arab League.


## Dataset #3: Meta's Quarterly Transparency Data

Meta makes quarterly transparency disclosures. A CSV file contains all this data
in machine-readable form. Presumably because such a CSV file contains all
historical data, Meta does not maintain an externally accessible archive of
these CSV files. It only exposes the most current file through a single,
unchanging link. This dataset collects Meta's CSV files from Q2 2021 onward.
Starting with Q2 2022, the CSV files were downloaded from Meta's website during
the quarter they were available. The files for earlier quarters were downloaded
from archive.org's snapshots of that single, unchanging link.


### Meta Fails to Preserve History

The default expectation for transparency data should be its immutability. Once a
reporting period is in the past, no new data can be generated for that period
because for all practical purposes time flows only forward. So once all data
sources have been correctly tabulated, the resulting measures should not change.
If a bug is discovered later on, the fact that there is a retroactive update
should be prominently disclosed and explained. Furthermore, to be transparent
about this change of history, a corrected entry should never replace the
original entry but only augment it. A reasonable alternative to explicitly
modelling such changes is to place the data under version control. In any case,
since none of the measures collected for transparency reports are particularly
deep or complex, we'd also expect that such bugs are exceedingly rare.

The just outlined requirements and practices are so fundamental that making
changes to the historical record without prominent explanation must be
considered suspect, a probable indicator that data tabulation is unreliable and
that the resulting statistics may be inaccurate or even invalid. Unfortunately,
Meta's CSV data contains such unacknowledged updates for every pair of
successive quarters included in the dataset. The scope and severity differ,
ranging from 18 entries from the previous quarter out of 2,927 entries or 0.6%
to 203 entries going back between 1 to 9 quarters out of 2,780 entries or 7.3%.
The observed rate of divergence for Meta's data is bad enough, raising strong
reservations about the accuracy of the data. But any trust in Meta's disclosures
is further eroded by the fact that the two extremes were the most recent back to
back quarters and that Meta's disclosures obviously omit one of its brands,
WhatsApp. The firm makes no meaningful disclosures in Meta's transparency center
and only an insignificant bit on WhatsApp's website.


### Known Knowns aud Unknowns

Yet NCMEC's disclosures show that Meta is the single largest source of CSAM
reports, accounting for 94%, 95%, 92%, and 86% of all reports made to NCMEC in
each of the four years covered by NCMEC's transparency disclosures. Since NCMEC
switched from tabulation by company to tabulation by brand two years ago, we
know that WhatsApp accounts for only 4-5% of Meta's CSAM reports. But at over
1,000,000 reports that's still an awful lot of horrendous content.


 While it is
impossible to compare CSAM rates between social media, since detected CSAM does
not necessarily imply prevalence of CSAM. Though YouTube use the same
algorithms, Microsoft's and Google's own, and does not

It's not all bad, however. First, at least the share of CSAM reports filed by
Meta is shrinking. Second, there is strong evidence that the current statistics
are too pessimistic because they count incidents but not unique pieces while
also failing to account for intent. The latter matters: Exceedingly tasteless
memes, people sharing examples out of disgust, and teenagers sexting with each
other all violate laws against the possession of CSAM, but do not come close to
the depravity of people who share CSAM for economic or sexual gain. Alas, making
such determinations requires human moderation and hence is difficult to
implement and scale.
