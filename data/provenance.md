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

  * __`ocse-report-contents.csv`__: Contents of CyberTipline reports, including
    the kind of reported sexual exploitation, the kind of attachments, and the
    uniqueness of attachments. Based on the
    [2022](https://www.missingkids.org/content/dam/missingkids/pdfs/OJJDP-NCMEC-Transparency_2022-Calendar-Year.pdf)
    and
    [2023](https://www.missingkids.org/content/dam/missingkids/pdfs/OJJDP-NCMEC-Transparency-CY-2023-Report.pdf)
    reports to the Office of Juvenile Justice and Delinquency Protection at the
    Department of Justice.

  * __`ocse-report-recipients.csv`__: The recipients of CyberTipline reports
    after NCMEC's triage. Also includes NCMEC's assessment of reports' level of
    detail, using *actionable* for more and *informational* for less detail.
    Based on the
    [2022](https://www.missingkids.org/content/dam/missingkids/pdfs/OJJDP-NCMEC-Transparency_2022-Calendar-Year.pdf)
    and
    [2023](https://www.missingkids.org/content/dam/missingkids/pdfs/OJJDP-NCMEC-Transparency-CY-2023-Report.pdf)
    reports to the Office of Juvenile Justice and Delinquency Protection at the
    Department of Justice.

  * __`ocse-reports-per-country.csv`__: CSAM reports received by NCMEC broken
    down by countries of reported users collects disclosures from
    [2019](https://www.missingkids.org/content/dam/missingkids/pdfs/2019-cybertipline-reports-by-country.pdf),
    [2020](https://www.missingkids.org/content/dam/missingkids/pdfs/2020-reports-by-country.pdf),
    [2021](https://www.missingkids.org/content/dam/missingkids/pdfs/2021-reports-by-country.pdf),
    and
    [2022](https://www.missingkids.org/content/dam/missingkids/pdfs/2022-reports-by-country.pdf),
    while also making them machine-readable and adding ISO-3166 Alpha-3 codes.

  * __`ocse-reports-per-platform.json`__: Transparency disclosures about CSAM by
    major social media platforms and companies as well as the corresponding
    disclosures by NCMEC. The dataset incorporates information about Alphabet
    (Google and YouTube), Automattic (Tumblr and Wordpress), Discord, Meta
    (Facebook, Instagram, and WhatsApp), Microsoft (including LinkedIn),
    Pinterest, Quora, Reddit, Snap, Telegram, TikTok, Twitch, and X née Twitter.
    Detailed source links are part of the dataset itself.

  * __`ocse-reports-per-year-country-capita.csv`__: The result of cleaning up and
    merging the following datasets into one denormalized table:

      - `countries.csv`
      - `ocse-reports-per-country.csv`
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

  * __`populations.csv`__: Per-country population statistics for 2019–2023 from
    the [United Nations Population Division](https://population.un.org/). That
    data used to be trivially downloadable through a URL, but no more. The
    `intransparent.fetch` module contains the code necessary for automating the
    download. You can execute it as follows:

    ```sh
    python -m intransparent --fetch-populations
    ```

  * __`regions.csv`__: Countries and their geographical regions based on [Luke
    Duncalfe's ISO-3166
    dataset](https://github.com/lukes/ISO-3166-Countries-with-Regional-Codes)
