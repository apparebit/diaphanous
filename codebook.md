# Codebook: CyberTipline Reporting

This codebook documents the dataset capturing CyberTipline reports about online
child sexual exploitation (OCSE) including child sexual abuse materials (CSAM)
as disclosed by technology corporations, their brands, an independent nonprofit,
and the national clearinghouse for such reports in the US, the National Center
for Missing and Exploited Children (NCMEC).

The dataset is available in both [Python](intransparent/by_platform/data.py) and
[JSON](data/ocse-reports-per-platform.json), with the latter [automatically
generated](intransparent/by_platform/export.py) from the former. This codebook
applies to both formats equally. That is possible because both formats are based
on the same data model, JSON, and even syntactic differences between the two
formats are minor.

The one notable exception is that the Python format utilizes tuples instead of
lists and wraps most dictionaries (i.e., JSON objects) with the standard
library's `types.MappingProxyType`. For clarity, the class is renamed to
`frozen`. The Python format originally used lists and dictionaries, too. But a
(long fixed) bug during ingestion modified the `REPORTS_PER_PLATFORM` in place,
making it impossible to run ingestion more than once. To prevent similar bugs
from re-occuring, I switched to using tuples and eventually also `MappingProxy`.
The dictionaries capturing data rows are left untouched (for now) because
prepending each row with `frozen(` was judged as introducing too much visual
clutter.

This codebook uses `null`, `true`, and `false`, where the Python format uses
`None`, `True`, and `False`.


## 1. The Disclosure Collection

The top-level entity is an object mapping organization names to corresponding
values. The value is `null` if an organization was surveyed for this dataset but
has not made *any* transparency disclosures. Otherwise, the value is an object
with information about the platform's disclosures.

Surveyed organizations include corporations, such as Meta, their service brands,
such as Facebook, Instagram, and WhatsApp, the Wikimedia Foundation, as well as
the National Center for Missing and Exploited Children, which appears as
`NCMEC`. As described below, the relationship between corporations and their
brands is encoded through the `brands` property of a corporation's disclosure
record.


## 2. Citation Record

The disclosure collection includes one entry named `@` that encodes metadata
about the dataset itself. It includes `author`, `title`, `version`, and `url`
properties. The version number comprises a major and minor version separated by
a dot.

Where the Python version uses comments, the JSON version of the citation record
also includes the `!` and `|` properties for visually highlighting the record
with horizontal rules. The property names were chosen because they sort before
and after all alphabetic letter when naively sorting property names by ASCII or
UTF-8 codepoint.


## 3. Disclosure Record

A platform's disclosure record contains information about the platform's
transparency disclosures.


### 3.1 Model: Arbitrary Quantities by Time Periods

Quantitative OCSE disclosures are represented as a table with labeled columns
and labeled rows.

Row labels always are **time periods**. Individual periods may have different
lengths, be repeated, or overlap with others. Valid period durations are
quarter, half, and full calendar years. Quarter and half years are written as
the four-digit year, a space, the letter `Q` or `H`, respectively, and a
one-digit ordinal. Years are written as four digits. Examples include `2021 Q1`,
`2022 H2`, and `2017`. All row labels, including years, are formatted as
strings.

Column labels differ significantly between organizations and hence are
explicitly declared for each organization. Still, three labels have the same
consistent meaning across all organizations:

  * `reports`: the number of OCSE reports submitted to or received by NCMEC
  * `pieces`: the number of intercepted or removed CSAM photos or videos
  * `accounts`: the number of terminated or "permanently suspended" accounts

Any cell may be null but all non-null cells belonging to the same column are
either integers, floating point numbers, or strings.


### 3.2 Encoding: Disclosure Record Properties

A disclosure record may include the following properties:

  * `aka`: a list of strings with former names
  * `brands`: a list of strings naming subsidiary units
  * `sources`: a list of strings with the URLs of transparency disclosures
  * `comments`: a list of strings with human-readable comments
  * `features`: a dictionary with high-level properties of transparency reports

  * `columns`: a list of strings serving as column labels
  * `sums`: a dictionary mapping column labels to lists of column labels
  * `products`: a dictionary mapping column labels to lists of column labels
  * `schema`: a dictionary mapping column labels to their types
  * `rows`: a list of row records with the row labels and cell data

All properties are optional. Since `columns`, `schema`, and `rows` encode the
same table, a disclosure record contains either none or all of them. Valid
schema types are `int`, `float`, and `string`. To avoid clutter, integer columns
need not be included and the schema may be omitted altogether if all columns
contain integers.

`sums` and `products` are useful for combining more granular columns into a
single one, even if that implies some semantic loss. For example, Meta changed
the definition of pieces in Q2 2021, which is why the firm's data includes a
column for each definition. However, for analysis, it is more convenient to
treat both kinds of pieces as a single time series. As another example, TikTok
reports only fractions for different content categories and subcategories. They
need to be multiplied with the total number of videos removed before analysis.
The `sums` and `products` properties make it possible to automate such
preparatory steps.


### 3.3 Encoding: Features

If an organization releases transparency reports, its disclosure record includes
a `features` dictionary with the following keys and values:

  * `data`: `null` or a string identifying the file format of machine-readable
    data, notably `csv`;
  * `history`: a string describing how historical information is conveyed; for
    example:
      * `data`: as part of machine-readable data;
      * `same page`: on the same, possibly dynamic HTML page;
      * `page archive`: through a list of linked reports;
  * `terms`: a list of strings containing terms used to describe violative
    content and/or behavior;
  * `quantities`: a string indicating whether reported quantities are `counts`,
    `rounded`, or `fractions`.
  * `granularity`: a string indicating the *current* granularity of disclosures,
    `Q`, `H`, or `Y` for quarterly, semiannually, and yearly, respectively;
  * `frequency`: a string indicating the *current* frequency of disclosures,
    `Q`, `H`, or `Y`;
  * `coverage`: a string indicating the period of the first OCSE disclosure;



### 3.4 Encoding: Row Records

A row record has one or two properties:

 1. The first property is mandatory, has the row label as key, and the list of
    cells as value.

    The row label determines the period, i.e., a year, half-year, or quarter.
    Like other periods, years are written as strings. Half-years are written as
    the year followed by a space and `H1` or `H2`. Quarters are written as the
    year followed by a space and `Q1`, `Q2`, `Q3`, or `Q4`.

    Each cell contains either `null`, an integer, a floating point number, or a
    string.

    Unusually, floating point columns may contain not only integer cells but
    also string cells that adhere to a specific format. To preserve information
    presented as "_P_% out of _N_ entities," a floating point value can also be
    written as "`P / 100 * N`," where _P_ is a floating point number with at
    least one digit before and after the decimal point, _N_ is an integer with
    optional commas as thousands separators, and the three tokens `/`, `100`,
    and `*` between _P_ and _N_ appear as written, with arbitrary spacing in
    between.

 2. The second property is optional, boolean, and named `redundant`.

    This property indicates that a platform's transparency disclosure contained
    the same quantity for the same time period more than once. While all such
    redundant data points should be the same, in practice they may not. The
    `redundant` property helps preserve such divergent disclosures.

    Rows without this property are assumed to be non-redundant and hence the
    property only appears on rows that are, in fact, redundant.


### 3.5 Well-Formed Disclosure and Row Records

Disclosure and row records adhere to the following constraints:

  * Every schema key is distinct and also a column name. Its value is either
    `int`, `float`, or `string`.
  * Every row has a valid period as key.
  * Every row has exactly the same number of cells as there are columns.
  * The types of cells are consistent with their column's implicit or explicit
    schema.
  * Row periods do not have gaps.
  * If more than one non-redundant row includes quantities for the same column
    and period, integer-valued columns must be additive.

Most of the above constraints simply ensure that the rows and columns really
encode a table. Unusually, however, the constraints allow for divergent row
periods within a table. They also allow for multiple non-redundant rows with the
same period and non-null cells for the same column. The dataset makes use of
both allowances.
