"""
R ("arr") integration:

  - Use `install()` to ensure that necessary R packages are installed.
  - Use `%load_ext rpy2.ipython` to enable the notebook integration.
  - Use the following incantations in the first R cell:

    ```
    %%R -i RLIB

    .libPaths(RLIB)

    library(...)
    ```
"""
from collections.abc import Sequence
from pathlib import Path

import rpy2.robjects.packages as r_packages
from rpy2.robjects.vectors import StrVector


PACKAGES = (
    "car",
    "dplyr",
    "estimatr",
    "ggplot2",
    "iccCounts",
    "patchwork",
    "purrr",
    "scales",
    "segmented",
    "svglite",
    "this.path",
    "tidyr",
)


try:
    from IPython import get_ipython
    IS_NOTEBOOK = get_ipython() is not None
except:
    IS_NOTEBOOK = False


if IS_NOTEBOOK:
    from .show import show
    def msg(s: str) -> None:
        show(f"<strong>{s}</strong>")
else:
    def msg(s: str) -> None:
        print(s)


RLIB = str(Path(__file__).parent.parent / "rlib")


def install(
    packages: Sequence[str] = PACKAGES,
    rlib: str = RLIB,
) -> None:
    # Ensure the directory exists
    Path(rlib).mkdir(exist_ok=True)

    # Check for uninstalled packages
    todo = [p for p in packages if not r_packages.isinstalled(p, lib_loc=rlib)]
    if not todo:
        return

    # Keep user appraised
    s = "Installing R package"
    if 1 < len(todo):
        s += "s"
    s += ", ".join(todo)
    s += "; this may take a while."

    msg(s)

    # Install missing R packages
    r_utils = r_packages.importr("utils")
    r_utils.chooseCRANmirror(ind=1)
    r_utils.install_packages(StrVector(todo), lib=rlib)
