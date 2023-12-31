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

One of the table's dimensions are **time periods**. Individual periods may have
different lengths, be repeated, or overlap with others. Valid period durations
are quarter, half, and full calendar years. Quarter and half years are written
as the four-digit year, a space, the letter `Q` or `H`, respectively, and the
one digit ordinal. Years are written as four digits. Examples include `2021 Q1`,
`2022 H2`, and `2017`.

While the entities for the other dimension differ considerably between
individual platforms, three names have the same consistent meaning:

  * `reports`: the number of reports submitted to or received by NCMEC
  * `pieces`: the number of intercepted or removed CSAM photos or videos
  * `accounts`: the number of terminated or "permanently suspended" accounts


### 3.2 Encoding: Disclosure Record Properties

A disclosure record may include the following properties:

  * `brands`: a list of strings naming subsidiary platforms
  * `comments`: a list of strings with human-readable comments
  * `sources`: a list of strings with the URLs of transparency disclosures

  * `row_index`: the string `period` or `platform`
  * `columns`: a list of strings serving as column labels
  * `rows`: a list of row records with the row labels and cell data
  * `nonintegers`: a list of strings naming columns with floating point values

All properties are optional. Since `row_index`, `columns`, `rows`, and
`nonintegers` encode the same table, a disclosure record contains either none or
all of them. To avoid clutter, the record may omit the `nonintegers` if the
table does not contain floating point numbers.


### 3.3 Encoding: Row Records

A row record has one or two properties:

 1. The first, mandatory property has the row index entry as key and the list of
    cells as value. Each cell contains either `null`, an integer, or a floating
    point number.

    To preserve information presented as "*x*% out of *y* entities," a floating
    point value can also be written as a string with format "`F / 100 * N`,"
    where _F_ is a floating point number with at least one digit before and
    after the decimal point, _N_ is an integer with optional commas as thousands
    separators, and the three tokens `/`, `100`, and `*` between _F_ and _N_
    appear as written, with arbitrary spacing in between.

    In the future, percentage values may be automatically coerced to integers
    when appearing in columns that are not included in the nonintegers.

 2. The second, optional property has `redundant` as key and either `true` or
    `false` as value. It indicates that a platform's transparency disclosure
    contained the same quantity for the same time period more than once. While
    all such redundant data points should be the same, in practice they may not.
    The `redundant` property helps preserve them.


### 3.4 Well-Formed Disclosure and Row Records

The dataset format imposes the following constraints:

  * If the row index is `period`, every row has a valid period as label.
  * If the row index is `platform`, every column is a valid period and every row
    label is a valid platform.
  * If any rows are marked as redundant, the row index is `period`.
  * The number of columns in a disclosure record is the same as the number of
    cells in each of its row records.
  * All nonintegers are column labels.
  * Cells with floating point values appear only in columns that also are
    nonintegers.

Due to the application domain, all integral quantities in the dataset represent
counts. As such, integral quantities in different, non-redundant rows with
overlapping time periods can be safely added together while preserving their
meaning (as long as the input rows completely cover the time periods of the
output rows).
