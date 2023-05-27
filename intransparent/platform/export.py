import json
from typing import cast

from .type import (
    CellType,
    CitationType,
    DisclosureCollectionType,
    DisclosureType,
    RowType,
)

def _format_row_json(row: RowType) -> str:
    for header, cell_values in row.items():
        if header != "redundant":
            break

    cells = []
    for cell in cast(list[CellType], cell_values):
        if cell is None:
            cells.append("null")
        elif isinstance(cell, int):
            cells.append(f"{cell}")
        elif isinstance(cell, float):
            cells.append(f"{cell:f}")
        elif isinstance(cell, str):
            cells.append(f'"{cell}"')
        else:
            raise ValueError(f'Invalid cell "{cell}"')

    line = ", ".join(cells)
    line = f"      {{{json.dumps(header)}: [{line}]"
    if row.get("redundant"):
        line = f'{line}, "redundant": true'
    line = f"{line}}}"
    return line


def _format_citation(citation: CitationType):
    keys, values = zip(*citation.items())
    key_width = max(len(key) for key in keys)
    rule_width = key_width + max(len(value) for value in values) + 10
    rule = "━" * rule_width

    # In ASCII and UTF-8: '!' < [A-Za-z] < '|'
    lines = [f'    "!": "{rule}",']
    for key, value in zip(keys, values):
        key = json.dumps(key).rjust(key_width + 2 + 4)
        lines.append(f"       {key}: {json.dumps(value)},")
    lines.append(f'    "|": "{rule}"')
    lines.append("  }")

    return lines


def export_reports_per_platform(disclosure_collection: DisclosureCollectionType) -> str:
    lines = ["{"]

    def append_comma_if_not(flag: bool) -> bool:
        if not flag:
            lines[-1] = lines[-1] + ","
        return False

    first_platform = True
    for platform, platform_object in disclosure_collection.items():
        first_platform = append_comma_if_not(first_platform)

        if platform_object is None:
            lines.append(f"  {json.dumps(platform)}: null")
            continue

        lines.append(f"  {json.dumps(platform)}: {{")
        if platform == "@":
            lines.extend(_format_citation(cast(CitationType, platform_object)))
            continue

        first_property = True
        for key, value in cast(DisclosureType, platform_object).items():
            first_property = append_comma_if_not(first_property)

            if key == "brands":
                s = ", ".join([json.dumps(item) for item in cast(list[str], value)])
                lines.append(f'    "brands": [{s}]')
            elif key == "row_index":
                lines.append(f'    "row_index": {json.dumps(value)}')
            elif key in ("columns", "comments", "rows", "nonintegers", "sources"):
                lines.append(f'    "{key}": [')
                first_item = True
                for item in cast(list, value):
                    first_item = append_comma_if_not(first_item)
                    if key == "rows":
                        lines.append(_format_row_json(item))
                    else:
                        lines.append(f"      {json.dumps(item)}")
                lines.append(f"    ]")
            else:
                raise ValueError(f'Unknown platform object property "{key}"')

        lines.append("  }")

    lines.append("}")
    return "\n".join(lines)
