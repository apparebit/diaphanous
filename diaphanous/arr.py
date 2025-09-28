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
from io import StringIO
from pathlib import Path

import rpy2.rinterface_lib as rinterface_lib
import rpy2.robjects.packages as rpackages
from rpy2.robjects.vectors import StrVector


PACKAGES = (
    "tidyverse",
    "car",
    "estimatr",
    "iccCounts",
    "patchwork",
    "scales",
    "segmented",
    "svglite",
    "this.path",
    "vcd",
    "vcdExtra",
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
    todo = [p for p in packages if not rpackages.isinstalled(p, lib_loc=rlib)]
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
    r_utils = rpackages.importr("utils")
    r_utils.chooseCRANmirror(ind=1)
    r_utils.install_packages(StrVector(todo), lib=rlib)


if not IS_NOTEBOOK:

    def enable_write_hook() -> None:
        pass

    def disable_write_hook() -> None:
        pass

else:

    _write_console_buffer = StringIO()
    _original_consolewrite_print = rinterface_lib.callbacks.consolewrite_print

    def flush_console() -> None:
        from IPython.display import display, HTML

        if _write_console_buffer.tell() == 0:
            return

        s = _write_console_buffer.getvalue()
        display(HTML(f"<pre><code>{s}</code></pre>"))
        _write_console_buffer.seek(0)
        _write_console_buffer.truncate(0)

    def write_console(s: str) -> None:
        from IPython.display import display, HTML

        if s == "[1]":
            return

        if s.startswith(' "') and s.endswith('"'):
            s = s[2:-1]
        if not s.startswith("𝐇"):
            _write_console_buffer.write(s)
            return

        flush_console()
        display(HTML(s[1:]))

    def enable_write_hook() -> None:
        rinterface_lib.callbacks.consolewrite_print = write_console

    def disable_write_hook() -> None:
        rinterface_lib.callbacks.consolewrite_print = _original_consolewrite_print
