from abc import ABCMeta, abstractmethod
import enum
from types import MappingProxyType

import altair as alt
import great_tables as gt
import polars as pl

from .._const import TOTAL
from ..util import to_title

# Files and Schemas

class NibrsTable(enum.StrEnum):
    """The names of essential NIBRS tables."""
    AGENCIES = "agencies"
    ARRESTEE = "arrestee"
    CRIMINAL_ACT = "criminal_act"
    INCIDENT = "incident"
    OFFENDER = "offender"
    OFFENSE = "offense"
    SUSPECT_USING = "suspect_using"
    VICTIM = "victim"
    VICTIM_OFFENSE = "victim_offense"

    @property
    def csv_file(self) -> str:
        name = self
        if name == self.AGENCIES:
            return f"agencies.csv"
        if name != self.INCIDENT:
            name = name.upper()
        return f"NIBRS_{name}.csv"


NIBRS_SOURCE_FILES = frozenset(["postgres_load.sql"]) | frozenset(
    t.csv_file for t in NibrsTable.__members__.values()
)
"""The names of essential files in the NIBRS distribution."""


class NibrsSchema(enum.Enum):
    """The schemata of core NIBRS tables."""

    AGENCIES = pl.Schema({
        "yearly_agency_id": pl.Int64,
        "agency_id": pl.Int64,
        "data_year": pl.Int32,
        "ori": pl.String,
        "legacy_ori": pl.String,
        "covered_by_legacy_ori": pl.String,
        "direct_contributor_flag": pl.String,
        "dormant_flag": pl.String,
        "dormant_year": pl.Int32,
        "reporting_type": pl.String,
        "ucr_agency_name": pl.String,
        "ncic_agency_name": pl.String,
        "pub_agency_name": pl.String,
        "pub_agency_unit": pl.String,
        "agency_status": pl.String,
        "state_id": pl.Int32,
        "state_name": pl.String,
        "state_abbr": pl.String,
        "state_postal_abbr": pl.String,
        "division_code": pl.Int32,
        "division_name": pl.String,
        "region_code": pl.Int32,
        "region_name": pl.String,
        "region_desc": pl.String,
        "agency_type_name": pl.String,
        "population": pl.Int32,
        "submitting_agency_id": pl.Int32,
        "sai": pl.String,
        "submitting_agency_name": pl.String,
        "suburban_area_flag": pl.String,
        "population_group_id": pl.Int32,
        "population_group_code": pl.String,
        "population_group_desc": pl.String,
        "parent_pop_group_code": pl.Int32,
        "parent_pop_group_desc": pl.String,
        "mip_flag": pl.String,
        "pop_sort_order": pl.Int32,
        "summary_rape_def": pl.String,
        "pe_reported_flag": pl.String,
        "male_officer": pl.Int32,
        "male_civilian": pl.Int32,
        "male_total": pl.Int32,
        "female_officer": pl.Int32,
        "female_civilian": pl.Int32,
        "female_total": pl.Int32,
        "officer_rate": pl.Decimal(6, 2),
        "employee_rate": pl.Decimal(6, 2),
        "nibrs_cert_date": pl.String,
        "nibrs_start_date": pl.String,
        "nibrs_leoka_start_date": pl.String,
        "nibrs_ct_start_date": pl.String,
        "nibrs_multi_bias_start_date": pl.String,
        "nibrs_off_eth_start_date": pl.String,
        "covered_flag": pl.String,
        "county_name": pl.String,
        "msa_name": pl.String,
        "publishable_flag": pl.String,
        "participated": pl.String,
        "nibrs_participated": pl.String,
    })
    ARRESTEE = pl.Schema({
        "data_year": pl.Int16,
        "arrestee_id": pl.Int64,
        "incident_id": pl.Int64,
        "arrestee_seq_num": pl.Int16,
        "arrest_date": pl.String,
        "arrest_type_id": pl.Int16,
        "multiple_indicator": pl.String,
        "offense_code": pl.String,
        "age_id": pl.Int16,
        "age_num": pl.String,
        "sex_code": pl.String,
        "race_id": pl.Int16,
        "ethnicity_id": pl.Int16,
        "resident_code": pl.String,
        "under_18_disposition_code": pl.String,
        "clearance_ind": pl.String,
        "age_range_low_num": pl.Int16,
        "age_range_high_num": pl.Int16,
    })
    CRIMINAL_ACT = pl.Schema({
        "data_year": pl.Int16,
        "criminal_act_id": pl.Int16,
        "offense_id": pl.Int64,
    })
    INCIDENT = pl.Schema({
	    "data_year": pl.Int16,
        "agency_id": pl.Int64,
        "incident_id": pl.Int64,
        "nibrs_month_id": pl.Int64,
        "cargo_theft_flag": pl.String,
        "submission_date": pl.String,
        "incident_date": pl.String,
        "report_date_flag": pl.String,
        "incident_hour": pl.Int16,
        "cleared_except_id": pl.Int16,
        "cleared_except_date": pl.String,
        "incident_status": pl.String,
        "data_home": pl.String,
        "orig_format": pl.String,
        "did": pl.Int64,
    })
    OFFENDER = pl.Schema({
        "data_year": pl.Int16,
        "offender_id": pl.Int64,
        "incident_id": pl.Int64,
        "offender_seq_num": pl.Int16,
        "age_id": pl.Int16,
        "age_num": pl.String,
        "sex_code": pl.String,
        "race_id": pl.Int16,
        "ethnicity_id": pl.Int16,
        "age_range_low_num": pl.Int16,
        "age_range_high_num": pl.Int16,
    })
    OFFENSE = pl.Schema({
        "data_year": pl.Int16,
        "offense_id": pl.Int64,
        "incident_id": pl.Int64,
        "offense_code": pl.String,
        "attempted_complete_flag": pl.String,
        "location_id": pl.Int64,
        "num_premises_entered": pl.Int16,
        "method_entry_code": pl.String,
    })
    SUSPECT_USING = pl.Schema({
        "data_year": pl.Int16,
        "suspect_using_id": pl.Int16,
        "offense_id": pl.Int64,
    })
    VICTIM = pl.Schema({
        "data_year": pl.Int16,
        "victim_id": pl.Int64,
        "incident_id": pl.Int64,
        "victim_seq_num": pl.Int16,
        "victim_type_id": pl.Int16,
        "assignment_type_id": pl.Int16,
        "activity_type_id": pl.Int16,
        "outside_agency_id": pl.Int64,
        "age_id": pl.Int16,
        "age_num": pl.String,
        "sex_code": pl.String,
        "race_id": pl.Int16,
        "ethnicity_id": pl.Int16,
        "resident_status_code": pl.String,
        "age_range_low_num": pl.Int16,
        "age_code_range_high": pl.Int16,
    })
    VICTIM_OFFENSE = pl.Schema({
        "data_year": pl.Int16,
        "victim_id": pl.Int64,
        "offense_id": pl.Int64,
    })


class SchemaExtension(enum.Enum):
    """
    The schema of the CsamData tables mostly is the same as for the original
    NIBRS tables, i.e., as specified by `NibrsSchema`. However, during
    ingestion, a few more columns are added to the `incidents` and `offenses`
    tables. This enumeration describes their additional columns.
    """

    INCIDENT = MappingProxyType({
        "offenders": pl.List(pl.Int64),
        "arrestees": pl.List(pl.Int64),
        "offense_id": pl.Int64,
        "other_offenses": pl.List(pl.Int64),
        "victims": pl.List(pl.Int64)
    })
    """
    Extra incident columns.

    A well-formed incident references exactly one offense through `offense`.
    That offense has offense code 370 and criminal act ID 4, i.e., pornography
    that exploits children. If the same incident comprises additional, non-CSAM
    offenses, they are referenced through `other_offenses`. Unfortunately, the
    victim for CSAM incidents always is of type 8, i.e., society, which renders
    the segment mostly meaningless.
    """

    OFFENSE = MappingProxyType({
        "using_ids": pl.List(pl.Int16),
        "criminal_act_id": pl.Int16,
        "other_criminal_act_ids": pl.List(pl.Int16),
        "activity": pl.Boolean,
    })
    """
    Extra offense columns.

    The primary `criminal_act_id` must be 4, i.e., exploitation of children. At
    most two `other_criminal_act_ids` are optional. If they include cultivation
    (2), distribution (3), promotion (5), or transmission (7), the offense is
    treated as a producing `activity`. In absence of these flags, it is treated
    as a consuming activity.
    """


# ======================================================================================
# NIBRS Data


class Clearance(enum.IntEnum):
    """The numeric identifiers of exceptional clearances."""
    DEATH_OF_OFFENDER = 1
    PROSECUTION_DECLINED = 2
    IN_OTHER_JURISDICTION = 3
    VICTIM_REFUSED_TO_COOPERATE = 4
    JUVENILE = 5
    NOT_APPLICABLE = 6


class CriminalAct(enum.IntEnum):
    """
    The numeric identifiers of criminal acts.

    Some offenses may be associated with up to three criminal acts that narrow
    down the broader offense category. For example, the manufacturer of CSAM
    commits a pornography offense that exploits children and involves publishing
    as well as distributing.
    """
    BUYING_RECEIVING = 1
    CULTIVATING_MANUFACTURING_PUBLISHING = 2
    DISTRIBUTING_SELLING = 3
    EXPLOITING_CHILDREN = 4
    OPERATING_PROMOTING_ASSISTING_ABETTING = 5
    POSSESSING_CONCEALING = 6
    TRANSPORTING_TRANSMITTING_IMPORTING = 7
    USING_CONSUMING = 8
    UNKNOWN = 9


class Ethnicity(enum.IntEnum):
    """The numeric identifiers for the ethnicity."""
    HISPANIC = 10
    NOT_HISPANIC = 20
    MULTIPLE = 30
    UNKNOWN = 40
    NOT_SPECIFIED = 50


class Id(enum.StrEnum):
    """The NIBRS identifiers serving as foreign keys."""
    ACTIVITY = "activity"
    AGE = "age_id"
    AGENCY = "agency_id"
    ARRESTEE = "arrestee_id"
    CLEARED_EXCEPT = "cleared_except_id"
    CRIMINAL_ACT = "criminal_act_id"
    ETHNICITY = "ethnicity_id"
    # Not a valid foreign key but makes API nicer:
    GROUP = "age_group"
    INCIDENT = "incident_id"
    LOCATION = "location_id"
    OFFENDER = "offender_id"
    OFFENSE = "offense_id"
    RACE = "race_id"
    SEX = "sex_code"
    SUSPECT_USING = "suspect_using_id"
    VICTIM = "victim_id"
    YEAR = "data_year"

    def value_model(self) -> None | type[enum.Enum]:
        """Get the enumeration of possible values for a column with this name."""
        if self == self.CLEARED_EXCEPT:
            return Clearance
        if self == self.CRIMINAL_ACT:
            return CriminalAct
        if self == self.ETHNICITY:
            return Ethnicity
        if self == self.GROUP:
            return Group
        if self == self.LOCATION:
            return Location
        if self == self.OFFENSE:
            return OffenseCode
        if self == self.RACE:
            return Race
        if self == self.SEX:
            return Sex
        if self == self.ACTIVITY:
            return Activity
        if self == self.SUSPECT_USING:
            return Using

        return None

    def humanized_values(self) -> None | dict[str,str]:
        value_model = self.value_model()
        if value_model is None:
            return None

        try:
            return {
                str(v.value): to_title(k)
                for k, v in value_model.__members__.items()
            }
        except:
            return None


def humanize_values(column: str) -> pl.Expr:
    try:
        ident = Id(column)
    except:
        return pl.col(column).alias(column.title())

    replacements = ident.humanized_values()
    if replacements is None:
        return pl.col(column).alias(ident.name.title())

    return pl.col(column).cast(pl.String).replace(
        replacements
    ).alias(ident.name.title())


def humanize_frame(frame: pl.DataFrame) -> pl.DataFrame:
    return frame.select(
        *(humanize_values(c) for c in frame.columns)
    )


class JuvenileDisposition(enum.StrEnum):
    """The letter codes for the juvenile disposition."""
    HANDLED_WITH_DEPARTMENT = "H"
    REFERRED_TO_OTHER_AUTHORITIES = "R"


class Location(enum.IntEnum):
    """The numeric identifiers for the location."""
    ABANDONED_CONDEMNED_STRUCTURE = 1
    AIR_BUS_TRAIN_TERMINAL = 2
    AMUSEMENT_PARK = 3
    ARENA_STADIUM_FAIRGROUNDS_COLISEUM = 4
    ATM_SEPARATE_FROM_BANK = 5
    AUTO_DEALERSHIP = 6
    BANK_SAVINGS_AND_LOAN = 7
    BAR_NIGHTCLUB = 8
    CAMP_CAMPGROUND = 9
    CHURCH_SYNAGOGUE_TEMPLE_MOSQUE = 10
    COMMERCIAL_OFFICE_BUILDING = 11
    COMMUNITY_CENTER = 12
    CONSTRUCTION_SITE = 13
    CONVENIENCE_STORE = 14
    CYBERSPACE = 15
    DAYCARE_FACILITY = 16
    DEPARTMENT_DISCOUNT_STORE = 17
    DOCK_WHARF_FREIGHT_MODAL_TERMINAL = 18
    DRUG_STORE_DOCTORS_OFFICE_HOSPITAL = 19
    FARM_FACILITY = 20
    FIELD_WOODS = 21
    GAMBLING_FACILITY_CASINO_RACE_TRACK = 22
    GOVERNMENT_PUBLIC_BUILDING = 23
    GROCERY_SUPERMARKET = 24
    HIGHWAY_ROAD_ALLEY_STREET_SIDEWALK = 25
    HOTEL_MOTEL = 26
    INDUSTRIAL_SITE = 27
    JAIL_PRISON_PENITENTIARY_CORRECTIONS_FACILITY = 28
    LAKE_WATERWAY_BEACH = 29
    LIQUOR_STORE = 30
    MILITARY_INSTALLATION = 31
    PARK_PLAYGROUND = 32
    PARKING_DROP_LOT_GARAGE = 33
    RENTAL_STORAGE_FACILITY = 34
    RESIDENCE_HOME = 35
    REST_AREA = 36
    RESTAURANT = 37
    SCHOOL_COLLEGE = 38
    SCHOOL_COLLEGE_UNIVERSITY = 39
    SCHOOL_ELEMENTARY_SECONDARY = 40
    SERVICE_GAS_STATION = 41
    SHELTER_MISSION_HOMELESS = 42
    SHOPPING_MALL = 43
    SPECIALTY_STORE = 44
    TRIBAL_LANDS = 45
    OTHER_UNKNOWN = 98
    NOT_SPECIFIED = 99


class OffenseCode(enum.StrEnum):
    """
    The three letter codes for the offense.

    The first two letters are digits, whereas the third letter is either zero
    (`0`) or a letter starting with a (`A`) in alphabetical order.
    """
    KIDNAPPING_ABDUCTION = "100"
    RAPE = "11A"
    SODOMY = "11B"
    SEXUAL_ASSAULT_WITH_AN_OBJECT = "11C"
    CRIMINAL_SEXUAL_CONTACT = "11D"
    ROBBERY = "120"
    AGGRAVATED_ASSAULT = "13A"
    SIMPLE_ASSAULT = "13B"
    INTIMIDATION = "13C"
    EXTORTION_BLACKMAIL = "210"
    BURGLARY_BREAKING_ENTERING = "220"
    POCKET_PICKING = "23A"
    THEFT_FROM_BUILDING = "23D"
    ALL_OTHER_LARCENY = "23H"
    MOTOR_VEHICLE_THEFT = "240"
    COUNTERFEITING_FORGERY = "250"
    FALSE_PRETENSES_SWINDLE_CONFIDENCE_GAME = "26A"
    CREDIT_CARD_AUTOMATED_TELLER_MACHINE_FRAUD = "26B"
    IMPERSONATION = "26C"
    WIRE_FRAUD = "26E"
    IDENTITY_THEFT = "26F"
    EMBEZZLEMENT = "270"
    DESTRUCTION_DAMAGE_VANDALISM_OF_PROPERTY = "290"
    DRUG_NARCOTIC_VIOLATIONS = "35A"
    DRUG_EQUIPMENT_VIOLATIONS = "35B"
    INCEST = "36A"
    STATUTORY_RAPE = "36B"
    PORNOGRAPHY_OBSCENE_MATERIAL = "370"
    PROSTITUTION = "40A"
    ASSISTING_OR_PROMOTING_PROSTITUTION = "40B"
    PURCHASING_PROSTITUTION = "40C"
    BRIBERY = "510"
    WEAPON_LAW_VIOLATION = "520"
    HUMAN_TRAFFICKING_COMMERCIAL_SEX_ACTS = "64A"
    HUMAN_TRAFFICKING_INVOLUNTARY_SERVITUDE = "64B"
    ANIMAL_CRUELTY = "720"


class Race(enum.IntEnum):
    """The numeric identifiers for the race."""
    WHITE = 10
    BLACK = 20
    AMERICAN_INDIAN = 30
    ASIAN = 40
    HAWAIIAN = 50
    OTHER = 60
    MULTIPLE = 70
    UNKNOWN = 98
    NOT_SPECIFIED = 99

    HISPANIC = 665  # Not in NIBRS, added to simplify folding of ethnicity


class Sex(enum.StrEnum):
    """The single letter codes for the sex."""
    FEMALE = "F"
    MALE = "M"
    UNKNOWN = "U"
    NOT_SPECIFIED = "X"


class Using(enum.IntEnum):
    """The numeric identifiers of the suspect using column."""
    ALCOHOL = 1
    COMPUTER_EQUIPMENT_HANDHELD_DEVICES = 2
    DRUGS_NARCOTICS = 3
    NOT_APPLICABLE = 4
    DRONE_UNMANNED_AIRCRAFT_SYSTEM = 5


# --------------------------------------------------------------------------------------
# Derived Data


class Activity(enum.Enum):
    """
    A coarse grouping of CSAM-related offenses into production/distribution
    versus consumption. Crime statistics in Australia and New Zealand happen to
    make the same distinction. United States statistics are more granular.
    Finally, Germany's statistics are granular enough to derive this variable.
    """
    CONSUMER = "false"
    PRODUCER = "true"


class Group(enum.IntEnum):
    """The age groups. The values were chosen to sort into a convenient order."""
    CHILD = 1
    ADOLESCENT = 2
    ADULT = 3
    UNKNOWN = 4


class Column(enum.StrEnum):
    """
    The column names of demographics and other descriptive statistics. The
    corresponding long table uses this enumeration thusly:

      - `YEAR` provides the year
      - `Id.AGE`, `AGE`, and `GROUP` characterize the age
      - `CATEGORY` and `VARIANT` provide two-level identifiers for variables
      - `COUNT` and `PERCENT` provide the actual values
    """
    AGE = "Age"
    GROUP = "Age Group"
    CATEGORY = "Category"
    VARIANT = "Variant"
    COUNT = "Count"
    PERCENT = "Percent"
    RANK = "Rank"
    YEAR = "Year"


class Entry(enum.StrEnum):
    """
    Common cell entries.

    The `TOTAL` variant's value is `🖩 Total`. The calculator icon serves as a
    visual marker that distinguishes the row from other rows showing variant
    values. Its Unicode code point is U+1F5A9 and it is included in the [Noto
    Sans Symbols 2](https://fonts.google.com/noto/specimen/Noto+Sans+Symbols+2)
    font.
    """
    ADOLESCENT = "Adolescent"
    ADULT = "Adult"
    CHILD = "Child"
    SIZE = "Size"
    TOTAL = TOTAL
    UNKNOWN = "Unknown"
