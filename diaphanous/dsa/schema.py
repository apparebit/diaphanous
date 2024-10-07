from dataclasses import dataclass
from datetime import datetime
from enum import auto, Enum


class DecisionVisibility(Enum):
    DECISION_VISIBILITY_CONTENT_REMOVED = auto()
    DECISION_VISIBILITY_CONTENT_DISABLED = auto()
    DECISION_VISIBILITY_CONTENT_DEMOTED = auto()
    DECISION_VISIBILITY_CONTENT_AGE_RESTRICTED = auto()
    DECISION_VISIBILITY_CONTENT_INTERACTION_RESTRICTED = auto()
    DECISION_VISIBILITY_CONTENT_LABELLED = auto()
    DECISION_VISIBILITY_OTHER = auto()


class DecisionMonetary(Enum):
    DECISION_MONETARY_SUSPENSION = auto()
    DECISION_MONETARY_TERMINATION = auto()
    DECISION_MONETARY_OTHER = auto()


class DecisionProvision(Enum):
    DECISION_PROVISION_PARTIAL_SUSPENSION = auto()
    DECISION_PROVISION_TOTAL_SUSPENSION = auto()
    DECISION_PROVISION_PARTIAL_TERMINATION = auto()
    DECISION_PROVISION_TOTAL_TERMINATION = auto()


class DecisionAccount(Enum):
    DECISION_ACCOUNT_SUSPENDED = auto()
    DECISION_ACCOUNT_TERMINATED = auto()


class AccountType(Enum):
    ACCOUNT_TYPE_BUSINESS = auto()
    ACCOUNT_TYPE_PRIVATE = auto()


class DecisionGround(Enum):
    DECISION_GROUND_ILLEGAL_CONTENT = auto()
    DECISION_GROUND_INCOMPATIBLE_CONTENT = auto()


class ContentType(Enum):
    CONTENT_TYPE_APP = auto()
    CONTENT_TYPE_AUDIO = auto()
    CONTENT_TYPE_IMAGE = auto()
    CONTENT_TYPE_PRODUCT = auto()
    CONTENT_TYPE_SYNTHETIC_MEDIA = auto()
    CONTENT_TYPE_TEXT = auto()
    CONTENT_TYPE_VIDEO = auto()
    CONTENT_TYPE_OTHER = auto()


# See
# https://transparency.dsa.ec.europa.eu/page/additional-explanation-for-statement-attributes
# for two-level classification of types of violative activity.


class StatementCategory(Enum):
    STATEMENT_CATEGORY_ANIMAL_WELFARE = auto()
    STATEMENT_CATEGORY_DATA_PROTECTION_AND_PRIVACY_VIOLATIONS = auto()
    STATEMENT_CATEGORY_ILLEGAL_OR_HARMFUL_SPEECH = auto()
    STATEMENT_CATEGORY_INTELLECTUAL_PROPERTY_INFRINGEMENTS = auto()
    STATEMENT_CATEGORY_NEGATIVE_EFFECTS_ON_CIVIC_DISCOURSE_OR_ELECTIONS = auto()
    STATEMENT_CATEGORY_NON_CONSENSUAL_BEHAVIOUR = auto()
    STATEMENT_CATEGORY_PORNOGRAPHY_OR_SEXUALIZED_CONTENT= auto()
    STATEMENT_CATEGORY_PROTECTION_OF_MINORS = auto()
    STATEMENT_CATEGORY_RISK_FOR_PUBLIC_SECURITY = auto()
    STATEMENT_CATEGORY_SCAMS_AND_FRAUD = auto()
    STATEMENT_CATEGORY_SELF_HARM = auto()
    STATEMENT_CATEGORY_SCOPE_OF_PLATFORM_SERVICE = auto()
    STATEMENT_CATEGORY_UNSAFE_AND_ILLEGAL_PRODUCTS = auto()
    STATEMENT_CATEGORY_VIOLENCE = auto()


class Keyword(Enum):
    # --- Animal welfare
    KEYWORD_ANIMAL_HARM = auto()
    KEYWORD_UNLAWFUL_SALE_ANIMALS = auto()

    # --- Data protection and privacy violations
    KEYWORD_BIOMETRIC_DATA_BREACH = auto()
    KEYWORD_MISSING_PROCESSING_GROUND = auto()
    KEYWORD_RIGHT_TO_BE_FORGOTTEN = auto()
    KEYWORD_DATA_FALSIFICATION = auto()

    # --- Illegal or harmful speech
    KEYWORD_DEFAMATION= auto()
    KEYWORD_DISCRIMINATION = auto()
    KEYWORD_HATE_SPEECH = auto()

    # --- Intellectual property infringements
    KEYWORD_COPYRIGHT_INFRINGEMENT = auto()
    KEYWORD_DESIGN_INFRINGEMENT = auto()
    KEYWORD_GEOGRAPHIC_INDICATIONS_INFRINGEMENT = auto()
    KEYWORD_PATENT_INFRINGEMENT = auto()
    KEYWORD_TRADE_SECRET_INFRINGEMENT = auto()
    KEYWORD_TRADEMARK_INFRINGEMENT = auto()

    # --- Negative effects on civic discourse or elections
    KEYWORD_DISINFORMATION = auto()
    KEYWORD_FOREIGN_INFORMATION_MANIPULATION = auto()
    KEYWORD_MISINFORMATION = auto()

    # --- Non-consensual behavior
    KEYWORD_NON_CONSENSUAL_IMAGE_SHARING = auto()
    KEYWORD_NON_CONSENSUAL_ITEMS_DEEPFAKE = auto()
    KEYWORD_ONLINE_BULLYING_INTIMIDATION = auto()
    KEYWORD_STALKING = auto()

    # --- Pornography or sexualized content
    KEYWORD_ADULT_SEXUAL_MATERIAL = auto()
    KEYWORD_IMAGE_BASED_SEXUAL_ABUSE = auto()

    # --- Protection of minors
    KEYWORD_AGE_SPECIFIC_RESTRICTIONS_MINORS = auto()
    KEYWORD_CHILD_SEXUAL_ABUSE_MATERIAL = auto()
    KEYWORD_GROOMING_SEXUAL_ENTICEMENT_MINORS = auto()
    KEYWORD_UNSAFE_CHALLENGES = auto()

    # --- Risk for public security
    KEYWORD_ILLEGAL_ORGANIZATIONS = auto()
    KEYWORD_RISK_ENVIRONMENTAL_DAMAGE = auto()
    KEYWORD_RISK_PUBLIC_HEALTH = auto()
    KEYWORD_TERRORIST_CONTENT = auto()

    # --- Scams and/or fraud
    KEYWORD_INAUTHENTIC_ACCOUNTS = auto()
    KEYWORD_INAUTHENTIC_LISTINGS = auto()
    KEYWORD_INAUTHENTIC_USER_REVIEWS = auto()
    KEYWORD_IMPERSONATION_ACCOUNT_HIJACKING = auto()
    KEYWORD_PHISHING = auto()
    KEYWORD_PYRAMID_SCHEMES = auto()

    # --- Self-harm
    KEYWORD_CONTENT_PROMOTING_EATING_DISORDERS = auto()
    KEYWORD_SELF_MUTILATION = auto()
    KEYWORD_SUICIDE = auto()

    # --- Scope of platform service
    KEYWORD_AGE_SPECIFIC_RESTRICTIONS = auto()
    KEYWORD_GEOGRAPHICAL_REQUIREMENTS = auto()
    KEYWORD_GOODS_SERVICES_NOT_PERMITTED = auto()
    KEYWORD_LANGUAGE_REQUIREMENTS = auto()
    KEYWORD_NUDITY = auto()

    # --- Unsafe and/or illegal products
    KEYWORD_INSUFFICIENT_INFORMATION_TRADERS = auto()
    KEYWORD_REGULATED_GOODS_SERVICES = auto()
    KEYWORD_DANGEROUS_TOYS = auto()

    # --- Violence
    KEYWORD_COORDINATED_HARM = auto()
    KEYWORD_GENDER_BASED_VIOLENCE = auto()
    KEYWORD_HUMAN_EXPLOITATION = auto()
    KEYWORD_HUMAN_TRAFFICKING = auto()
    KEYWORD_INCITEMENT_VIOLENCE_HATRED = auto()

    # --- Other
    KEYWORD_OTHER = auto()


class TerritorialScope(Enum):
    AT = "Austria"
    BE = "Belgium"
    BG = "Bulgaria"
    CY = "Cyprus"
    CZ = "Czechia"
    DE = "Germany"
    DK = "Denmark"
    EE = "Estonia"
    ES = "Spain"
    FI = "Finland"
    FR = "France"
    GR = "Greece"
    HR = "Croatia"
    HU = "Hungary"
    IE = "Ireland"
    IS = "Iceland"
    IT = "Italy"
    LI = "Liechtenstein"
    LT = "Lithuania"
    LU = "Luxembourg"
    LV = "Latvia"
    MT = "Malta"
    NL = "Netherlands"
    NO = "Norway"
    PL = "Poland"
    PT = "Portugal"
    RO = "Romania"
    SE = "Sweden"
    SI = "Slovenia"
    SK = "Slovakia"

EU = (
    TerritorialScope.AT,
    TerritorialScope.BE,
    TerritorialScope.BG,
    TerritorialScope.CY,
    TerritorialScope.CZ,
    TerritorialScope.DE,
    TerritorialScope.DK,
    TerritorialScope.EE,
    TerritorialScope.ES,
    TerritorialScope.FI,
    TerritorialScope.FR,
    TerritorialScope.GR,
    TerritorialScope.HR,
    TerritorialScope.HU,
    TerritorialScope.IE,
    TerritorialScope.IT,
    TerritorialScope.LT,
    TerritorialScope.LU,
    TerritorialScope.LV,
    TerritorialScope.MT,
    TerritorialScope.NL,
    TerritorialScope.PL,
    TerritorialScope.PT,
    TerritorialScope.RO,
    TerritorialScope.SE,
    TerritorialScope.SI,
    TerritorialScope.SK,
)

EEA = (
    TerritorialScope.AT,
    TerritorialScope.BE,
    TerritorialScope.BG,
    TerritorialScope.CY,
    TerritorialScope.CZ,
    TerritorialScope.DE,
    TerritorialScope.DK,
    TerritorialScope.EE,
    TerritorialScope.ES,
    TerritorialScope.FI,
    TerritorialScope.FR,
    TerritorialScope.GR,
    TerritorialScope.HR,
    TerritorialScope.HU,
    TerritorialScope.IE,
    TerritorialScope.IS,
    TerritorialScope.IT,
    TerritorialScope.LI,
    TerritorialScope.LT,
    TerritorialScope.LU,
    TerritorialScope.LV,
    TerritorialScope.MT,
    TerritorialScope.NL,
    TerritorialScope.NO,
    TerritorialScope.PL,
    TerritorialScope.PT,
    TerritorialScope.RO,
    TerritorialScope.SE,
    TerritorialScope.SI,
    TerritorialScope.SK,
)


class ContentLanguage(Enum):
    BG = "Bulgarian"
    BR = "Breton"
    CA = "Catalan"
    CO = "Corsican"
    CS = "Czech"
    CU = "Church Slavonic"
    CY = "Welsh"
    DA = "Danish"
    DE = "German"
    EL = "Greek"
    EN = "English"
    ES = "Spanish"
    ET = "Estonian"
    EU = "Basque"
    FI = "Finnish"
    FR = "French"
    FY = "Western Frisian"
    GA = "Irish"
    GD = "Gaelic"
    GL = "Galician"
    GV = "Manx"
    HR = "Croatian"
    HU = "Hungarian"
    IS = "Icelandic"
    IT = "Italian"
    KL = "Kalaallisut"
    KW = "Cornish"
    LA = "Latin"
    LB = "Luxembourgish"
    LI = "Limburgan"
    LT = "Lithuanian"
    LV = "Latvian"
    MT = "Maltese"
    NB = "Norwegian Bokmål"
    NL = "Dutch"
    NN = "Norwegian Nynorsk"
    NO = "Norwegian"
    OC = "Occitan"
    PL = "Polish"
    PT = "Portuguese"
    RM = "Romansh"
    RO = "Romanian"
    SC = "Sardinian"
    SE = "Northern Sami"
    SK = "Slovak"
    SL = "Slovenian"
    SV = "Swedish"
    VO = "Volapük"
    WA = "Walloon"


class InformationSource(Enum):
    SOURCE_ARTICLE_16 = auto()
    SOURCE_TRUSTED_FLAGGER = auto()
    SOURCE_TYPE_OTHER_NOTIFICATION = auto()
    SOURCE_VOLUNTARY = auto()


class AutomatedDecision(Enum):
    AUTOMATED_DECISION_FULLY = auto()
    AUTOMATED_DECISION_PARTIALLY = auto()
    AUTOMATED_DECISION_NOT_AUTOMATED = auto()


@dataclass(frozen=True, slots=True)
class Row:
    uuid: str
    created_at: datetime

    # ----------------------------------------------------------------------------------
    # SUBMISSION OF CLEAR AND SPECIFIC STATEMENTS

    # 1. Platform Unique Identifier
    puid: str

    # 2. Specifications of the content affected by the decision
    content_type: ContentType
    content_type_other: None | str  # <= 500 characters, required
    content_date: datetime  # YYYY-MM-DD format, not before 2000-01-01
    content_language: None | ContentLanguage

    # ----------------------------------------------------------------------------------
    # INFORMATION ON THE TYPE OF RESTRICTION(S) IMPOSED,
    # ON THE TERRITORIAL SCOPE,
    # AND THE DURATION OF THE RESTRICTION

    # 3. The type of restriction(s) imposed: At least one
    decision_visibility: tuple[DecisionVisibility]
    decision_visibility_other: None | str   # <= 500 characters, required
    decision_monetary: DecisionMonetary
    decision_monetary_other: None | str   # <= 500 characters, required
    decision_provision: DecisionProvision
    decision_account: DecisionAccount

    # 4. The duration of the decision
    application_date: datetime  # YYYY-MM-DD format, not before 2020-01-01
    end_date_visibility_restriction: None | datetime   # longest restriction
    end_date_monetary_restriction: None | datetime
    end_date_service_restriction: None | datetime
    end_date_account_restriction: None | datetime

    # 5. The territorial scope of the decision
    territorial_scope: tuple[TerritorialScope]

    # ----------------------------------------------------------------------------------
    # INFORMATION ON THE FACTS AND CIRCUMSTANCES RELIED ON IN TAKING THE DECISION

    # 6. Description of the facts and circumstances
    decision_facts: str  # <= 5000 characters, required

    # 7. Information on the source of the investigation
    source_type: InformationSource
    source_identity: None | str  # <= 500 characters, optional

    # 8. Information on the account affected by the decision
    account_type: None | AccountType

    # ----------------------------------------------------------------------------------
    # INFORMATION ON THE USE MADE OF AUTOMATED MEANS

    # 9. Automated detection
    automated_detection: bool

    # 10. Automated decision
    automated_decision: AutomatedDecision

    # ----------------------------------------------------------------------------------
    # THE LEGAL OR CONTRACTUAL GROUNDS RELIED ON IN TAKING THE DECISION

    # 11. Decision grounds
    decision_ground: DecisionGround

    # 12. For allegedly illegal information: the legal ground relied upon
    illegal_content_legal_ground: None | str  # <= 500 characters
    illegal_content_explanation: None | str  # <= 2000 characters

    # 13. For allegedly incompatible information: the contractual ground relied upon
    incompatible_content_ground: None | str   # <= 500 characters
    incompatible_content_explanation: None | str  # <= 2000 characters

    # 14. Overlap between TOS incompatibility and illegality
    incompatible_content_illegal: None | bool

    # 15. Reference URL to the legal or contractual ground
    decision_ground_reference_url: None | str  # TOS or Law, optional

    # 16. Category & specification
    category: StatementCategory
    category_addition: tuple[StatementCategory]
    category_specification: tuple[Keyword]
    category_specification_other: None | str  # <= 500 characters, optional
