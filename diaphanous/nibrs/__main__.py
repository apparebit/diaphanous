from pathlib import Path
import shutil

from .data import load_all
from .model import humanize_frame, Id
from ..util import configure


CRITERIA = (Id.YEAR, Id.GROUP, Id.RACE, Id.SEX)


if __name__ == "__main__":
    root = Path(__file__).parent.parent.parent
    width, _ = shutil.get_terminal_size()
    configure()

    nibrs = load_all()
    # offenders = humanize_frame(
    #     nibrs.offender_demographics().by(
    #         Id.YEAR, Id.GROUP, Id.RACE, Id.SEX, sorted=True
    #     )
    # )
    # offenders.write_csv(root / "data" / "nibrs" / "offenders.csv")

    print(nibrs.offender_demographics().age_distribution())
