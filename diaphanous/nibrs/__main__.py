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

    nibrs = load_all()
    offenders = humanize_frame(
        nibrs.offender_demographics().by(
            Id.YEAR, Id.GROUP, Id.RACE, Id.SEX, sorted=True
        )
    )

    print(offenders)
    offenders.write_csv(root / "data" / "nibrs" / "offenders.csv")
