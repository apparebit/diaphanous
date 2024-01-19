# Codebook: Social Media CSAM Reporting

The dataset is available in both [Python](intransparent/by_platform/data.py) and
[JSON](data/csam-reports-per-platform.json), with the latter [automatically
generated](intransparent/by_platform/export.py) from the former. This codebook
applies to both formats equally.

In fact, the two formats share the same data model comprising `null`, `true`
`false`, integers, floating point numbers, strings, sequences thereof, and
objects or mappings with string-valued keys for properties. The syntax is rather
similar as well but does diverge. Notably, the Python format uses tuples instead
of lists, `None` and `True` instead of `null` and `true`, includes a few
comments, i.e., lines starting with `#`, and utilizes trailing commas as much as
possible. Finally, its indentation takes up four characters per level instead of
only two for JSON.

The Python format started out using lists, too. But a (now fixed) bug during
ingestion modified the `REPORTS_PER_PLATFORM` data in place, making it
impossible to run ingestion more than once. To prevent similar bugs, I switched
to using tuples. Unfortunately, Python still doesn't support an immutable
dictionary within the standard library. (`MappingProxy` does protect against
mutation but requires explicitly wrapping every `dict` value, which isn't very
ergonomic.)


## 1. The Disclosure Collection

The top-level entity is an object mapping platform names to corresponding
values. The value is `null` if a platform was surveyed for this dataset but has
not made *any* transparency disclosures. Otherwise, the value is an object with
information about the platform's disclosures.

Some corporations, such as Meta, operate more than one social media platform,
such as Facebook, Instragram, and WhatsApp. The disclosure collection may
contain entries for both the corporation and all its platforms, Facebook,
Instagram, Meta, and WhatsApp in the example.

The National Center for Missing and Exploited Children is treated as the `NCMEC`
platform for the purposes of the dataset.


## 2. Citation Record

The one exception is the `@` property. Its value is an object with metadata
about the dataset itself. That includes `author`, `title`, `version`, and `url`.
The version number comprises a major and minor version separated by a dot.

Where the Python version uses comments, the JSON version of the citation record
also includes the `!` and `|` properties for visually highlighting the record
with horizontal rules. Their keys were chosen to come before and after all
alphabetic keys when naively sorting keys by codepoint in ASCII or UTF-8.


## 3. Disclosure Record

A platform's disclosure record contains information about the platform's
transparency disclosures.


### 3.1 Model: Arbitrary Quantities by Time Periods

Most importantly, it may contain a platform's quantitative CSAM disclosures in a
table with labeled columns and labeled rows.

Row labels are **time periods**. Individual periods may have different lengths,
be repeated, or overlap with others. Valid period durations are quarter, half,
and full calendar years. Quarter and half years are written as the four-digit
year, a space, the letter `Q` or `H`, respectively, and the one digit ordinal.
Years are written as four digits. Examples include `2021 Q1`, `2022 H2`, and
`2017`. All row labels, including years, are formatted as strings.

Column labels differ significantly between platforms and hence are explicitly
declared for each platform. Still, three labels have the same consistent meaning
across all platforms:

  * `reports`: the number of reports submitted to or received by NCMEC
  * `pieces`: the number of intercepted or removed CSAM photos or videos
  * `accounts`: the number of terminated or "permanently suspended" accounts

Any cell may be null but all non-null cells belonging to the same column are
either integers, floating point numbers, or strings.


### 3.2 Encoding: Disclosure Record Properties

A disclosure record may include the following properties:

  * `brands`: a list of strings naming subsidiary platforms
  * `sources`: a list of strings with the URLs of transparency disclosures
  * `comments`: a list of strings with human-readable comments
  * `features`: a dictionary with high-level properties of transparency reports

  * `columns`: a list of strings serving as column labels
  * `schema`: a dictionary mapping column labels to their types
  * `rows`: a list of row records with the row labels and cell data

All properties are optional. Since `columns`, `schema`, and `rows` encode the
same table, a disclosure record contains either none or all of them. Valid
schema types are `int`, `float`, and `string`. To avoid clutter, integer columns
need not be included and the schema may be omitted altogether if all columns
contain integers.


### 3.3 Encoding: Features

If a platform releases transparency reports, its disclosure record includes a
`features` dictionary with the following keys and values:

  * `data`: `null` or a string identifying the file format of machine-readable
    data, notably `csv`;
  * `history`: a string describing the historical information provided:
      * `data`: as part of machine-readable data;
      * `same page`: on the same, possibly dynamic HTML page;
      * `page archive`: through a list of linked reports;
  * `terms`: a list of strings containing terms used to describe violative
    content and/or behavior;
  * `quantities`: a string indicating whether reported quantities are `counts`,
    `rounded`, or `fractions`.
  * `granularity`: a string indicating the granularity of disclosures, `Q`, `H`,
    or `Y` for quarterly, semiannually, and yearly, respectively;
  * `frequency`: a string indicating the frequency of disclosures, `Q`, `H`, or
    `Y`;
  * `coverage`: a string indicating the coverage of CSAM disclosures;



### 3.4 Encoding: Row Records

A row record has one or two properties:

 1. The first, mandatory property has the row label as key and the list of cells
    as value.

    The row label determines the period, i.e., a year, half-year, or quarter.
    Like other periods, years are written as strings. Half-years are written as
    the year followed by a space and `H1` or `H2`. Quarters are written as the
    year followed by a space and `Q1`, `Q2`, `Q3`, or `Q4`.

    Each cell contains either `null`, an integer, a floating point number, or
    string. Note that a floating point column may contain integer cells as well
    as string cells formatted as follows.

    To preserve information presented as "*x*% out of *y* entities," a floating
    point value can also be written as a string with format "`F / 100 * N`,"
    where _F_ is a floating point number with at least one digit before and
    after the decimal point, _N_ is an integer with optional commas as thousands
    separators, and the three tokens `/`, `100`, and `*` between _F_ and _N_
    appear as written, with arbitrary spacing in between.

 2. The second, optional property has `redundant` as key and either `true` or
    `false` as value. It indicates that a platform's transparency disclosure
    contained the same quantity for the same time period more than once. While
    all such redundant data points should be the same, in practice they may not.
    The `redundant` property helps preserve such divergent disclosures.


### 3.5 Well-Formed Disclosure and Row Records

The dataset format imposes the following constraints:

  * Schema keys are distinct and also column names. The corresponding values are
    `int`, `float`, or `string`.
  * Every row has a valid period as key.
  * Every row has exactly the same number of cell values as there are columns.
  * Cell values are consistent with the column's implicit or explicit schema.
  * Row periods may overlap. They also may have gaps.
  * If two or more rows include non-null entries for the same column and period,
    all but one row are marked as `redundant`.

Due to the application domain, all integral quantities in the dataset represent
counts. As such, integral quantities in different, non-redundant rows with
overlapping time periods can be safely added together while preserving their
meaning (as long as the input rows completely cover the time periods of the
output rows).
