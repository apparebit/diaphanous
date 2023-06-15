# Dataset Provenance

  * __`countries.csv`__: Country names and ISO-3166 Alpha-3 codes scraped from
    [ISO's website](https://www.iso.org/obp/ui/#search/code/)

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
    disclosures by NCMEC. The dataset incorporates information from:

      * [Automattic](https://transparency.automattic.com)
      * [Facebook and
        Instagram](https://transparency.fb.com/sr/community-standards/)
      * [Google including
        YouTube](https://transparencyreport.google.com/child-sexual-abuse-material/)
      * [LinkedIn](https://about.linkedin.com/transparency/community-report)
      * [Pinterest](https://policy.pinterest.com/en/transparency-report) and its
        [archive of past
        disclosures](https://help.pinterest.com/en/guide/transparency-report-archive)
      * [Quora](https://help.quora.com/hc/en-us/articles/13294268051732-DSA-Transparency)
      * [Reddit](https://www.redditinc.com/policies/transparency), in particular
        its disclosures for
        [2022](https://www.redditinc.com/policies/2022-transparency-report)
        including [mid-year
        update](https://www.redditinc.com/policies/mid-year-transparency-report-2022-2),
        [2021](https://www.redditinc.com/policies/transparency-report-2021),
        [2020](https://www.redditinc.com/policies/transparency-report-2020), and
        [2019](https://www.redditinc.com/policies/transparency-report-2019-1)
      * [Snap](https://values.snap.com/privacy/transparency), in particular its
        disclosures for [H2
        2021](https://www.snap.com/en-US/privacy/transparency/2021-12-31), [H1
        2021](https://www.snap.com/en-US/privacy/transparency/2021-6-30), [H2
        2020](https://www.snap.com/en-US/privacy/transparency/2020-12-31), [H1
        2020](https://www.snap.com/en-US/privacy/transparency/2020-6-30), and [H2
        2019](https://www.snap.com/en-US/privacy/transparency/2019-12-31)
      * [TikTok](https://www.tiktok.com/transparency/en/community-guidelines-enforcement-2022-4/)
        including datasets released for [Q4
        2022](https://sf16-va.tiktokcdn.com/obj/eden-va2/nuvlojeh7ryht/Transparency_CGE_2022Q4/2022Q4_raw_data_cger_English.csv)
        and [Q3
        2022](https://sf16-va.tiktokcdn.com/obj/eden-va2/nuvlojeh7ryht/Transparency_CGE_2022Q3/English_CGE_2022Q3.xlsx)
      * [Tumblr](https://www.tumblr.com/transparency)
      * [pre-Musk Twitter](https://transparency.twitter.com) and [current
        Twitter](https://blog.twitter.com/en_us/topics/company/2023/an-update-on-twitter-transparency-reporting)
      * [WhatsApp](https://www.whatsapp.com/legal/california-privacy-notice/transparency-report/")
      * NCMEC's per-platform disclosures for
        [2019](https://www.missingkids.org/content/dam/missingkids/pdfs/2019-reports-by-esp.pdf),
        [2020](https://www.missingkids.org/content/dam/missingkids/pdfs/2020-reports-by-esp.pdf),
        [2021](https://www.missingkids.org/content/dam/missingkids/pdfs/2021-reports-by-esp.pdf),
        and
        [2022](https://www.missingkids.org/content/dam/missingkids/pdfs/2022-reports-by-esp.pdf)

  * __`meta-q2-2022.csv`__, __`meta-q3-2022.csv`__, __`meta-q4-2022.csv`__, and
    __`meta-q1-2023.csv`__: Meta's machine-readable disclosures from Q2 2022 to
    Q1 2023.

  * __`populations`__: Per-country population statistics for 2019–2022 from the
    [United Nations Population
    Division](https://population.un.org/dataportal/data/indicators/49/locations/4,8,12,16,20,24,660,28,32,51,533,36,40,31,44,48,50,52,112,56,84,204,60,64,68,535,70,72,76,92,96,100,854,108,132,116,120,124,136,140,148,152,156,344,446,158,170,174,178,184,188,384,191,192,531,196,203,408,180,208,262,212,214,218,818,222,226,232,233,748,231,238,234,242,246,250,254,258,266,270,268,276,288,292,300,304,308,312,316,320,831,324,624,328,332,336,340,348,352,356,360,364,368,372,833,376,380,388,392,832,400,398,404,296,412,414,417,418,428,422,426,430,434,438,440,442,450,454,458,462,466,470,584,474,478,480,175,484,583,492,496,499,500,504,508,104,516,520,524,528,540,554,558,562,566,570,807,580,578,512,586,585,591,598,600,604,608,616,620,630,634,410,498,638,642,643,646,652,654,659,662,663,666,670,882,674,678,682,686,688,690,694,702,534,703,705,90,706,710,728,724,144,275,729,740,752,756,760,762,764,626,768,772,776,780,788,792,795,796,798,800,804,784,826,834,840,850,858,860,548,862,704,876,732,887,894,716/start/2019/end/2022/table/pivotbylocation)

  * __`naturalearth`__: Level 0 administrative boundaries from [Natural Earth,
    version
    5.1.1](https://www.naturalearthdata.com/downloads/110m-cultural-vectors/)

  * __`regions.csv`__: Countries and their geographical regions based on [Luke
    Duncalfe's ISO-3166
    dataset](https://github.com/lukes/ISO-3166-Countries-with-Regional-Codes)

  * __`arab-league.csv`__: Member countries of the [Arab
    League](https://en.wikipedia.org/wiki/Arab_League)
