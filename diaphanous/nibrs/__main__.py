from pathlib import Path
from .util import configure
from .data import load


if __name__ == "__main__":
    configure()
    data = load()
    offenders = data.offender_demographics()
    offender_age_sex_race = offenders.age_group_sex_race()
    offender_age_sex_race.write_csv(
        Path(__file__).parent.parent.parent
        / "data" / "nibrs" / "offender-age-group-sex-race.csv"
    )

    print(data.caseload())
    print(data.severity())
    print(data.completion())
    print(offender_age_sex_race)
    print((lambda pair: pair[1])(offenders.age_distribution()))
