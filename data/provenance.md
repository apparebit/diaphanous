# Dataset Provenance

  * __`arab-league.csv`__: Member countries of the [Arab
    League](https://en.wikipedia.org/wiki/Arab_League)

  * __`countries.csv`__: Country names and ISO-3166 Alpha-2/3 codes scraped from
    [ISO's website](https://www.iso.org/obp/ui/#search/code/)

  * __`csam-pieces-by-relationship-to-victim.csv`__: Relationship between
    victims and prepetrators. Based on the
    [2022](https://www.missingkids.org/content/dam/missingkids/pdfs/OJJDP-NCMEC-Transparency_2022-Calendar-Year.pdf)
    and
    [2023](https://www.missingkids.org/content/dam/missingkids/pdfs/OJJDP-NCMEC-Transparency-CY-2023-Report.pdf)
    reports to the Office of Juvenile Justice and Delinquency Protection at the
    Department of Justice.

  * __`csam-report-contents.csv`__: Contents of CyberTipline reports, including
    the kind of reported sexual exploitation, the kind of attachments, and the
    uniqueness of attachments. Based on the
    [2022](https://www.missingkids.org/content/dam/missingkids/pdfs/OJJDP-NCMEC-Transparency_2022-Calendar-Year.pdf)
    and
    [2023](https://www.missingkids.org/content/dam/missingkids/pdfs/OJJDP-NCMEC-Transparency-CY-2023-Report.pdf)
    reports to the Office of Juvenile Justice and Delinquency Protection at the
    Department of Justice.

  * __`csam-report-recipients.csv`__: The recipients of CyberTipline reports
    after NCMEC's triage. Also includes NCMEC's assessment of reports' level of
    detail, using *actionable* for more and *informational* for less detail.
    Based on the
    [2022](https://www.missingkids.org/content/dam/missingkids/pdfs/OJJDP-NCMEC-Transparency_2022-Calendar-Year.pdf)
    and
    [2023](https://www.missingkids.org/content/dam/missingkids/pdfs/OJJDP-NCMEC-Transparency-CY-2023-Report.pdf)
    reports to the Office of Juvenile Justice and Delinquency Protection at the
    Department of Justice.

  * __`csam-reports-per-country.csv`__: CSAM reports received by NCMEC broken
    down by countries of reported users collects disclosures from
    [2019](https://www.missingkids.org/content/dam/missingkids/pdfs/2019-cybertipline-reports-by-country.pdf),
    [2020](https://www.missingkids.org/content/dam/missingkids/pdfs/2020-reports-by-country.pdf),
    [2021](https://www.missingkids.org/content/dam/missingkids/pdfs/2021-reports-by-country.pdf),
    and
    [2022](https://www.missingkids.org/content/dam/missingkids/pdfs/2022-reports-by-country.pdf),
    while also making them machine-readable and adding ISO-3166 Alpha-3 codes.

  * __`csam-reports-per-platform.json`__: Transparency disclosures about CSAM by
    major social media platforms and companies as well as the corresponding
    disclosures by NCMEC. The dataset incorporates information about Alphabet
    (Google and YouTube), Automattic (Tumblr and Wordpress), Discord, Meta
    (Facebook, Instagram, and WhatsApp), Microsoft (including LinkedIn),
    Pinterest, Quora, Reddit, Snap, Telegram, TikTok, Twitch, and X née Twitter.
    Detailed source links are part of the dataset itself.

  * __`csam-reports-per-year-country-capita.csv`__: The result of cleaning up and
    merging the following datasets into one denormalized table:

      - `countries.csv`
      - `csam-reports-per-country.csv`
      - `populations.csv`
      - `regions.csv`
      - `arab-league.csv`

    The table contains a set of rows with country code `☪` (both Alpha-2 and
    Alpha-3) and country name `Arab League` that accumulate reports, population,
    and reports per capita for all member countries of the Arab League. They are
    singled out because they account for an outsized share of CSAM reports both
    in absolute numbers and per capita.

  * __`discord/discord-2020-h2.csv`__ through __`discord/discord-2023-q4.csv`__:
    Discord's [machine-readable transparency
    disclosures](https://discord.com/safety-transparency-reports/2023-q4) from
    H2 2020 through Q4 2023.

  * __`meta/meta-2021-q2.csv`__ through __`meta/meta-2023-q4.csv`__: Meta's
    [machine-readable transparency
    disclosures](https://transparency.fb.com/sr/community-standards/) from Q2
    2021 through Q4 2023. Meta does not offer an archive of CSV files. Instead,
    their website only has a single, unchanging link pointing to the latest
    file. Files for Q2 2022 through Q1 2023 were downloaded from Meta's website
    when they were available, earlier files from archive.org based on the
    unchanging link.

  * __`naturalearth`__: Level 0 administrative boundaries from [Natural Earth,
    version
    5.1.1](https://www.naturalearthdata.com/downloads/110m-cultural-vectors/)

  * __`populations.csv`__: Per-country population statistics for 2019–2022 from
    the [United Nations Population
    Division](https://population.un.org/dataportal/data/indicators/49/locations/4,8,12,16,20,24,660,28,32,51,533,36,40,31,44,48,50,52,112,56,84,204,60,64,68,535,70,72,76,92,96,100,854,108,132,116,120,124,136,140,148,152,156,344,446,158,170,174,178,184,188,384,191,192,531,196,203,408,180,208,262,212,214,218,818,222,226,232,233,748,231,238,234,242,246,250,254,258,266,270,268,276,288,292,300,304,308,312,316,320,831,324,624,328,332,336,340,348,352,356,360,364,368,372,833,376,380,388,392,832,400,398,404,296,412,414,417,418,428,422,426,430,434,438,440,442,450,454,458,462,466,470,584,474,478,480,175,484,583,492,496,499,500,504,508,104,516,520,524,528,540,554,558,562,566,570,807,580,578,512,586,585,591,598,600,604,608,616,620,630,634,410,498,638,642,643,646,652,654,659,662,663,666,670,882,674,678,682,686,688,690,694,702,534,703,705,90,706,710,728,724,144,275,729,740,752,756,760,762,764,626,768,772,776,780,788,792,795,796,798,800,804,784,826,834,840,850,858,860,548,862,704,876,732,887,894,716/start/2019/end/2022/table/pivotbylocation)

  * __`regions.csv`__: Countries and their geographical regions based on [Luke
    Duncalfe's ISO-3166
    dataset](https://github.com/lukes/ISO-3166-Countries-with-Regional-Codes)
