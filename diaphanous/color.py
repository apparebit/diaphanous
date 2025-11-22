import enum

class Palette(enum.StrEnum):
    """
    Shantay's categorical color palette.

    This palette is based on and largely the same as [Observable's 2024 color
    palette](https://observablehq.com/blog/crafting-data-colors). This selection
    tends towards bright and saturated colors, which make charts "pop". That
    same quality can be a bit much at times, so manual curation still matters.
    """

    BLUE = "#4269d0"
    ORANGE = "#efb118"
    RED = "#ff725c"
    CYAN = "#6cc5b0"
    GREEN = "#3ca951"
    PINK = "#ff8ab7"
    PURPLE = "#a365ef"
    LIGHT_BLUE = "#97bbf5"
    BROWN = "#a57356"
    GRAY = "#9498a0"
    LIGHT_GRAY = "#aaaeb6"
    BLACK = "#1f2228"

    @classmethod
    def cycle(cls, index: int) -> str:
        """Cycle through the colors of the palette, ignoring gray."""
        return _COLORS[index % len(_COLORS)]

_COLORS = [c for c in Palette.__members__.values() if c is not Palette.GRAY]


class Scale(enum.Enum):
    RED = (
        "#ffb950",
        "#ffad33",
        "#ff931f",
        "#ff7e33",
        "#fa5e1f",
        "#ec3f13",
        "#b81702",
        "#a50104",
        "#8e0103",
        "#7a0103",
    )

    BLUE = (
        #"#caf0f8",
        "#ade8f4",
        "#90e0ef",
        "#48cae4",
        "#00b4d8",
        "#0096c7",
        "#0077b6",
        "#015ba0",
        "#023e8a",
        "#032174",
        "#03045e",
    )
