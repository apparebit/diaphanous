from pathlib import Path
import shutil

from .data import load_all
from .model import Id, Column
from .util import configure, humanize_frame


CRITERIA = (Id.YEAR, Id.GROUP, Id.RACE, Id.SEX)


if __name__ == "__main__":
    root = Path(__file__).parent.parent.parent
    width, _ = shutil.get_terminal_size()
    configure()

    data = load_all()
    offenders = data.offender_demographics()

    humanize_frame(offenders.data()).write_csv(
        root / "data" / "nibrs" / "offenders.csv"
    )

    by_age_race_sex = humanize_frame(offenders.by(
        Id.YEAR, Id.GROUP, Id.RACE, Id.SEX, sorted=True
    ))
    by_age_race_sex.write_csv(
        root / "data" / "nibrs" / "offenders-by-group-race-sex.csv"
    )
